"""
config_checker.py
-----------------
Vérification des paramètres API Grist avant toute tentative de connexion.
Gestion propre des cas d'erreur avec messages explicites pour l'utilisateur.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv


def load_env_files():
    """Charge les variables d'environnement depuis .env ou config/example.env."""
    # Priorité: .env local > config/.env > config/example.env (pour doc)
    for env_path in [".env", "config/.env", "config/example.env"]:
        p = Path(env_path)
        if p.exists():
            load_dotenv(p, override=False)


def check_api_params() -> Tuple[bool, list]:
    """
    Vérifie que les variables API Grist obligatoires sont définies.
    
    Returns:
        (ok: bool, missing: list of str)
    """
    load_env_files()
    
    required = {
        "GRIST_API_KEY": os.getenv("GRIST_API_KEY"),
        "GRIST_DOC_ID":  os.getenv("GRIST_DOC_ID"),
    }
    
    missing = [k for k, v in required.items() if not v or v.startswith("votre_")]
    return (len(missing) == 0), missing


def get_api_config() -> dict:
    """Retourne la configuration API complète."""
    load_env_files()
    return {
        "api_key":  os.getenv("GRIST_API_KEY", ""),
        "doc_id":   os.getenv("GRIST_DOC_ID", ""),
        "base_url": os.getenv("GRIST_BASE_URL", "https://docs.getgrist.com"),
    }


def print_api_missing_message(missing: list):
    """Affiche un message clair si les paramètres API sont absents."""
    vars_list = "\n".join(f"  - {v}" for v in missing)
    print(f"""
⚠️  Paramètres API Grist incomplets.
Les variables suivantes sont manquantes ou non configurées :
{vars_list}

Veuillez :
1️⃣  Configurer les variables d'environnement (copier config/example.env → .env et remplir)
    OU
2️⃣  Déposer un fichier .grist dans le répertoire data/ et relancer le script.
""")


def find_local_grist_file(data_dir: str = "data") -> Optional[Path]:
    """
    Recherche un fichier .grist dans le répertoire data/.
    
    Returns:
        Path du fichier trouvé, ou None
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        return None
    
    grist_files = [
        f for f in data_path.iterdir()
        if f.suffix == ".grist" and f.stat().st_size > 100  # ignore placeholder vide
    ]
    
    if grist_files:
        # Prend le plus récent
        return max(grist_files, key=lambda f: f.stat().st_mtime)
    return None


def print_no_local_file_message():
    """Affiche un message clair si aucun fichier local n'est trouvé."""
    print("""
❌  Aucun fichier .grist trouvé dans le répertoire data/.

Merci de déposer votre fichier Grist exporté dans :
  data/votre_document.grist

OU de fournir le chemin explicitement :
  python -m src.cli full-run --source chemin/vers/votre_fichier.grist --pi PI-10

Pour exporter depuis Grist :
  Menu → Exporter → Exporter le document complet (.grist)
""")


def resolve_source(
    source_arg: Optional[str],
    use_api: bool,
    data_dir: str = "data"
) -> Tuple[str, Optional[str]]:
    """
    Résout la source de données selon la priorité :
      1. --source (explicite)
      2. --api
      3. fallback data/

    Returns:
        (mode: "api"|"file", path: str|None)
        
    Raises:
        SystemExit si aucune source valide trouvée
    """
    # Priorité 1: source explicite
    if source_arg:
        p = Path(source_arg)
        if not p.exists():
            print(f"\n❌  Fichier introuvable : {source_arg}\n")
            sys.exit(1)
        return "file", str(p)
    
    # Priorité 2: API
    if use_api:
        ok, missing = check_api_params()
        if ok:
            return "api", None
        else:
            print_api_missing_message(missing)
            # Fallback automatique vers fichier local
            print("🔄  Tentative de fallback vers fichier local...\n")
    else:
        # Vérif silencieuse
        ok, missing = check_api_params()
        if not ok and not source_arg:
            # Pas de --api demandé, on va directement au fichier local
            pass
    
    # Priorité 3: fallback data/
    local_file = find_local_grist_file(data_dir)
    if local_file:
        print(f"📂  Fichier local détecté : {local_file}")
        return "file", str(local_file)
    
    # Aucune source valide
    print_no_local_file_message()
    sys.exit(1)
