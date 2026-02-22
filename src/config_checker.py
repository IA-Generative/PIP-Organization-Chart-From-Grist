from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    doc_id: str
    api_key: str


def _clean_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def get_api_config_from_env() -> tuple[Optional[ApiConfig], List[str]]:
    missing: List[str] = []
    api_key = _clean_env("GRIST_API_KEY")
    doc_id = _clean_env("GRIST_DOC_ID")
    base_url = _clean_env("GRIST_BASE_URL", "https://grist.numerique.gouv.fr/")

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
