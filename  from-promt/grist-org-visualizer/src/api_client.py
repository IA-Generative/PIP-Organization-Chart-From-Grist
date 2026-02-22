"""
api_client.py
-------------
Client HTTP pour l'API REST Grist.
Récupère les données des tables du document.
"""

import sys
from typing import Any, Dict, List

import requests


class GristAPIClient:
    """Client pour l'API Grist."""

    def __init__(self, api_key: str, doc_id: str, base_url: str = "https://docs.getgrist.com"):
        self.api_key = api_key
        self.doc_id = doc_id
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/docs/{self.doc_id}/{path}"

    def get_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Récupère toutes les lignes d'une table Grist."""
        url = self._url(f"tables/{table_name}/records")
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            print(f"\n❌  Impossible de joindre le serveur Grist : {self.base_url}")
            print("    Vérifiez votre connexion réseau ou l'URL GRIST_BASE_URL.\n")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 401:
                print("\n❌  Authentification refusée. Vérifiez votre GRIST_API_KEY.\n")
            elif resp.status_code == 404:
                print(f"\n❌  Document ou table introuvable : {table_name}")
                print(f"    Vérifiez votre GRIST_DOC_ID et le nom de la table.\n")
            else:
                print(f"\n❌  Erreur API Grist ({resp.status_code}) : {e}\n")
            sys.exit(1)

        data = resp.json()
        records = data.get("records", [])

        # Normalise : chaque record → dict plat
        rows = []
        for rec in records:
            row = {"id": rec.get("id")}
            row.update(rec.get("fields", {}))
            rows.append(row)
        return rows

    def get_all_tables(self, table_names: List[str]) -> Dict[str, List[Dict]]:
        """Récupère plusieurs tables en une passe."""
        result = {}
        for name in table_names:
            print(f"  📥  Chargement table : {name}")
            result[name] = self.get_table(name)
        return result
