from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd
import requests

from .config_checker import ApiConfig
from .grist_loader import GristData


def _fetch_table_records(cfg: ApiConfig, table_name: str) -> pd.DataFrame:
    url = f"{cfg.base_url}/api/docs/{cfg.doc_id}/tables/{table_name}/records"
    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    resp = requests.get(url, headers=headers, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Erreur API Grist {resp.status_code} sur {table_name}: {resp.text[:300]}")
    payload = resp.json()
    records = payload.get("records", [])
    # records: [{id:..., fields:{...}}]
    rows = []
    for r in records:
        row = {"id": r.get("id")}
        fields = r.get("fields", {}) or {}
        row.update(fields)
        rows.append(row)
    return pd.DataFrame(rows)


def load_from_api(cfg: ApiConfig, mapping: Dict) -> GristData:
    tables = mapping["tables"]
    equipes = _fetch_table_records(cfg, tables["equipes"])
    personnes = _fetch_table_records(cfg, tables["personnes"])
    epics = _fetch_table_records(cfg, tables["epics"])
    features = _fetch_table_records(cfg, tables["features"])
    affectations = _fetch_table_records(cfg, tables["affectations"])
    return GristData(equipes=equipes, personnes=personnes, epics=epics, features=features, affectations=affectations)
