from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd


@dataclass(frozen=True)
class GristData:
    equipes: pd.DataFrame
    personnes: pd.DataFrame
    epics: pd.DataFrame
    features: pd.DataFrame
    affectations: pd.DataFrame


def _read_sqlite_table(conn: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
    except Exception as e:
        raise RuntimeError(f"Impossible de lire la table {table_name!r} dans le .grist: {e}") from e


def load_from_grist_file(path: str, mapping: Dict) -> GristData:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier .grist introuvable: {path}")

    tables = mapping["tables"]
    conn = sqlite3.connect(path)
    try:
        equipes = _read_sqlite_table(conn, tables["equipes"])
        personnes = _read_sqlite_table(conn, tables["personnes"])
        epics = _read_sqlite_table(conn, tables["epics"])
        features = _read_sqlite_table(conn, tables["features"])
        affectations = _read_sqlite_table(conn, tables["affectations"])
    finally:
        conn.close()

    return GristData(
        equipes=equipes,
        personnes=personnes,
        epics=epics,
        features=features,
        affectations=affectations,
    )
