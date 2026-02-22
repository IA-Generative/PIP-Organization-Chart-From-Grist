from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    doc_id: str
    api_key: str


def get_api_config_from_env() -> tuple[Optional[ApiConfig], List[str]]:
    missing: List[str] = []
    api_key = os.getenv("GRIST_API_KEY")
    doc_id = os.getenv("GRIST_DOC_ID")
    base_url = os.getenv("GRIST_BASE_URL", "https://docs.getgrist.com")

    if not api_key:
        missing.append("GRIST_API_KEY")
    if not doc_id:
        missing.append("GRIST_DOC_ID")

    if missing:
        return None, missing
    return ApiConfig(base_url=base_url.rstrip("/"), doc_id=doc_id, api_key=api_key), []


def print_api_missing(missing: List[str]) -> None:
    print("⚠️ Paramètres API Grist incomplets.")
    print("Les variables suivantes sont manquantes :")
    for m in missing:
        print(f"- {m}")
    print()
    print("Veuillez :")
    print("1️⃣ Configurer les variables d’environnement (ou un fichier .env) puis relancer avec --api")
    print("OU")
    print("2️⃣ Déposer un fichier .grist dans le répertoire data/ (ou fournir --source)")
