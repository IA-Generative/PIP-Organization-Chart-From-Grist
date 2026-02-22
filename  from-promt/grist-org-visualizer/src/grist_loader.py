"""
grist_loader.py
---------------
Chargement des données Grist depuis :
  - l'API REST (mode api)
  - un fichier .grist local (SQLite avec tables Grist)

Retourne un dict unifié : { nom_table: [liste de dicts] }
"""

import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.api_client import GristAPIClient
from src.config_checker import get_api_config


def load_mapping() -> dict:
    """Charge le mapping tables/colonnes depuis config/mapping.yml."""
    mapping_path = Path("config/mapping.yml")
    if mapping_path.exists():
        with open(mapping_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    # Mapping par défaut
    return {
        "tables": {
            "equipes": "Equipes",
            "personnes": "Personnes",
            "epics": "Epics",
            "features": "Features",
            "affectations": "Affectations",
        }
    }


def load_from_api() -> Dict[str, List[Dict]]:
    """Charge les données depuis l'API Grist."""
    cfg = get_api_config()
    mapping = load_mapping()
    table_names = list(mapping["tables"].values())

    print(f"🌐  Connexion à l'API Grist : {cfg['base_url']}")
    client = GristAPIClient(
        api_key=cfg["api_key"],
        doc_id=cfg["doc_id"],
        base_url=cfg["base_url"],
    )
    raw = client.get_all_tables(table_names)

    # Normalise les clés en noms logiques
    result = {}
    for logical, physical in mapping["tables"].items():
        result[logical] = raw.get(physical, [])
    return result


def load_from_file(file_path: str) -> Dict[str, List[Dict]]:
    """
    Charge les données depuis un fichier .grist (SQLite).
    
    Les fichiers .grist sont des bases SQLite avec une table par table Grist.
    Les données utilisateur sont dans des tables nommées 'GristData_<TableName>'.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"\n❌  Fichier introuvable : {file_path}\n")
        sys.exit(1)

    mapping = load_mapping()

    print(f"📂  Lecture fichier local : {path.name}")

    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Liste les tables disponibles
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        available_tables = {row["name"] for row in cursor.fetchall()}

        result = {}
        for logical, physical in mapping["tables"].items():
            # Cherche la table dans plusieurs formats possibles
            candidates = [
                physical,
                f"GristData_{physical}",
                f"Table_{physical}",
                physical.lower(),
            ]
            found = None
            for candidate in candidates:
                if candidate in available_tables:
                    found = candidate
                    break

            if found:
                cursor.execute(f"SELECT * FROM [{found}]")
                rows = [dict(row) for row in cursor.fetchall()]
                result[logical] = rows
                print(f"  ✅  {physical}: {len(rows)} lignes")
            else:
                print(f"  ⚠️   Table '{physical}' non trouvée dans le fichier")
                result[logical] = []

        conn.close()
        return result

    except sqlite3.Error as e:
        print(f"\n❌  Erreur lecture fichier .grist : {e}")
        print("    Assurez-vous que le fichier est bien un export Grist valide.\n")
        sys.exit(1)


def load_data(mode: str, source_path: str = None) -> Dict[str, List[Dict]]:
    """
    Point d'entrée unifié pour le chargement des données.
    
    Args:
        mode: "api" ou "file"
        source_path: chemin du fichier (mode "file" uniquement)
    
    Returns:
        Dict { nom_logique: [liste de lignes] }
    """
    if mode == "api":
        return load_from_api()
    elif mode == "file":
        if not source_path:
            print("\n❌  Mode 'file' sans chemin de fichier.\n")
            sys.exit(1)
        return load_from_file(source_path)
    else:
        print(f"\n❌  Mode inconnu : {mode}\n")
        sys.exit(1)
