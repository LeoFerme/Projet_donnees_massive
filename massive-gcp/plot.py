import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def generate_plot(csv_file, output_img, title, xlabel):
    df = pd.read_csv(csv_file, sep=';')

    df['time_val_s'] = df['AVG_TIME'] / 1000  # Conversion de ms en s

    plt.figure(figsize=(10, 6))

    sns.barplot(data=df, x='PARAM', y='time_val_s', errorbar='sd', capsize=.1, color='#1f77b4')

    plt.title(title, fontsize=14)
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel("Temps moyen par requête (s)", fontsize=12) 
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(output_img)
    print(f"Generated {output_img}")

if __name__ == '__main__':
    # 1. Concurrence
    generate_plot('conc.csv', 'conc.png',
                  'Exp. 1 : Temps moyen par requête selon la Concurrence',
                  'Nombre d\'utilisateurs concurrents')

    # 2. Posts Scale
    generate_plot('post.csv', 'post.png',
                  'Exp. 2 : Temps moyen par requête selon le nombre de Posts',
                  'Nombre de posts par utilisateur')

    # 3. Fanout Scale
    generate_plot('fanout.csv', 'fanout.png',
                  'Exp. 3 : Temps moyen par requête selon le Fanout (Suivis)',
                  'Nombre de followees par utilisateur')