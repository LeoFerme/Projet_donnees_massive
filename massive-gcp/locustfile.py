from locust import HttpUser, task, between
import random

USER_PREFIX = "user"
USER_COUNT = 1000

class TinyInstagramUser(HttpUser):
    # Temps d'attente aléatoire entre 1 et 5 secondes entre chaque requête (optionnel)
    wait_time = between(1, 5) 

    def on_start(self):
        """Initialise l'utilisateur et lui assigne un ID aléatoire."""
        self.user_id = random.randint(1, USER_COUNT)
        self.username = f"{USER_PREFIX}{self.user_id}"

    @task
    def load_timeline(self):
        """Simule le chargement de la timeline pour l'utilisateur assigné."""
        self.client.get(f"/api/timeline?user={self.username}&limit=20")