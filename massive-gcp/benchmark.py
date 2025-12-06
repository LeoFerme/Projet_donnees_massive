import subprocess
import csv
import os
import re
import time
import sys
from google.cloud import datastore
from seed import cleanup_datastore

# --- CONFIGURATION GLOBALE ---
BASE_URL = "https://tinyinsta-benchmark-479308.appspot.com/api/timeline?user=user1&limit=20"
CSV_DELIMITER = ';'
CONCURRENCY_REQUESTS = 1000 # Nombre total de requêtes pour les tests de scaling (arbitraire mais grand)

def execute_seeding(users, posts_per_user, follows):
    """Lance le script seed.py avec les paramètres donnés après nettoyage."""
    total_posts = users * posts_per_user
    # 1. Nettoyage de la DB (appel direct à la fonction Datastore)
    client = datastore.Client()
    cleanup_datastore(client)

    # 2. Seeding
    seed_cmd = (
        f"python seed.py --users {users} --posts {total_posts} "
        f"--follows-min {follows} --follows-max {follows}"
    )
    print(f"   -> Seeding: {seed_cmd}")
    # On utilise subprocess.run pour exécuter le script seed.py modifié
    subprocess.run(seed_cmd, shell=True, check=True)
    time.sleep(5) # Laisser le temps à Datastore de stabiliser les écritures
    
def run_locust(concurrency, requests, param_value):
    """
    Exécute Locust en mode headless.
    CORRECTION : Utilise --run-time au lieu de --num-request.
    """
    host = BASE_URL.split('/api/timeline')[0]
    
    # Locust ajoute auto .csv, on retire le suffixe ici pour éviter double extension
    csv_report_name = f"locust_report_{param_value}_{concurrency}" 

    run_time = "30s" 
    locust_exec = [sys.executable, "-m", "locust"]

    cmd_list = locust_exec + [
        "-f", "locustfile.py",
        "--headless",
        "-u", str(concurrency),
        "-r", str(concurrency),
        "--host", host,
        "--csv", csv_report_name,
        "--run-time", run_time,
        "--exit-code-on-error", "0",
        "--stop-timeout", "10"
    ]

    print(f"   -> Running Locust: users={concurrency}, target_host={host}, time={run_time}...")

    try:
        result = subprocess.run(
            cmd_list,
            check=True,
            timeout=300, 
            capture_output=True,
            cwd=os.getcwd()
        )
        
        stats_file = f"{csv_report_name}_stats.csv"
        
        if not os.path.exists(stats_file):
            # Debugging amélioré : affiche la sortie réelle de Locust
            stderr_output = result.stderr.decode() if result.stderr else "Pas de stderr"
            raise Exception(f"Fichier de statistiques Locust non trouvé ({stats_file}).\nSTDERR de Locust:\n{stderr_output}")

        with open(stats_file, mode='r') as f:
            reader = csv.DictReader(f)
            total_stats = next(row for row in reader if row['Name'] == 'Aggregated')

        avg_time = float(total_stats.get('Average Response Time', 0))
        failed_requests = int(total_stats.get('Failure Count', 0))
        is_failed = 1 if failed_requests > 0 else 0

        subprocess.run(f"rm {csv_report_name}*", shell=True, cwd=os.getcwd())
        return int(avg_time), is_failed

    except subprocess.CalledProcessError as e:
        # Affiche la vraie erreur capturée dans stderr
        stderr_output = e.stderr.decode() if e.stderr else "Pas de stderr capturé."
        stdout_output = e.stdout.decode() if e.stdout else "Pas de stdout capturé."
        print(f"   -> ERREUR LOCUST (Code {e.returncode}).\n   STDERR: {stderr_output}\n   STDOUT: {stdout_output}")
        return 0, 1
    except Exception as e:
        print(f"   -> ERREUR CRITIQUE: {e}")
        return 0, 1

def save_csv(filename, data_rows):
    """Sauvegarde les résultats au format PARAM;AVG_TIME;RUN;FAILED."""
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=CSV_DELIMITER)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])
        writer.writerows(data_rows)
    print(f"Fichier {filename} généré.")

def run_benchmarks():
    # --- EXPÉRIENCE 1 : Charge (conc.csv) ---
    print("\n==================================")
    print("= EXPÉRIENCE 1 : CHARGE (conc.csv) =")
    print("==================================")

    # Seeding FIXE : 1000 users, 50 posts/user, 20 follows/user (Total 50k posts)
    execute_seeding(users=1000, posts_per_user=50, follows=20)

    results_conc = []
    concurrencies = [1, 10, 20, 50, 100, 1000]

    for c in concurrencies:
        for run in range(1, 4): # 3 runs
            time_ms, failed = run_locust(concurrency=c, requests=CONCURRENCY_REQUESTS, param_value=c) 
            results_conc.append([c, time_ms, run, failed])

    save_csv("conc.csv", results_conc)

    # --- EXPÉRIENCE 2 : Taille Données / Posts (post.csv) ---
    print("\n======================================")
    print("= EXPÉRIENCE 2 : POSTS SCALE (post.csv) =")
    print("======================================")
    results_post = []
    posts_per_user_list = [10, 100, 1000]

    for p in posts_per_user_list:
        # Seeding VARIABLE : 1000 users, P posts/user, 20 follows/user
        execute_seeding(users=1000, posts_per_user=p, follows=20)

        for run in range(1, 4):
            # Concurrence FIXE : 50
            time_ms, failed = run_locust(concurrency=50, requests=CONCURRENCY_REQUESTS, param_value=p) 
            results_post.append([p, time_ms, run, failed])

    save_csv("post.csv", results_post)

    # --- EXPÉRIENCE 3 : Taille Données / Fanout (fanout.csv) ---
    print("\n========================================")
    print("= EXPÉRIENCE 3 : FANOUT SCALE (fanout.csv) =")
    print("========================================")

    results_fanout = []
    follow_counts = [10, 50, 100]

    for f in follow_counts:
        # Seeding VARIABLE : 1000 users, 100 posts/user, F follows/user
        execute_seeding(users=1000, posts_per_user=100, follows=f)

        for run in range(1, 4):
            # Concurrence FIXE : 50
            time_ms, failed = run_locust(concurrency=50, requests=CONCURRENCY_REQUESTS, param_value=f) 
            results_fanout.append([f, time_ms, run, failed])

    save_csv("fanout.csv", results_fanout)


if __name__ == '__main__':
    run_benchmarks()
