from __future__ import annotations

import re
from typing import Optional


def normalize_pi(pi_raw: str) -> str:
    if not pi_raw:
        raise ValueError("PI manquant. Exemple attendu: PI-10 ou 10")
    s = pi_raw.strip().lower()
    # Extract first integer group
    m = re.search(r"(\d+)", s)
    if not m:
        raise ValueError(f"Impossible de normaliser le PI depuis: {pi_raw!r}")
    num = int(m.group(1))
    return f"PI-{num}"


def normalize_pi_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    try:
        return normalize_pi(str(value))
    except Exception:
        # Some grist values might be numeric without 'PI'
        s = str(value).strip()
        m = re.search(r"(\d+)", s)
        if m:
            return f"PI-{int(m.group(1))}"
        return None
