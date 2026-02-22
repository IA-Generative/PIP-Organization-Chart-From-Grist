from __future__ import annotations

import json
import math
import re
from typing import Any, List, Optional


def parse_ref_id(value: Any) -> Optional[int]:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if value > 0 else None

    if isinstance(value, float):
        if math.isnan(value):
            return None
        iv = int(value)
        return iv if iv > 0 else None

    if isinstance(value, dict):
        for key in ("id", "rowId", "record", "value"):
            if key in value:
                return parse_ref_id(value[key])
        return None

    if isinstance(value, (list, tuple)):
        if not value:
            return None
        # Some APIs expose refs as [id, label]
        return parse_ref_id(value[0])

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None

        if s.isdigit():
            iv = int(s)
            return iv if iv > 0 else None

        if s.startswith("{") or s.startswith("["):
            try:
                parsed = json.loads(s)
                return parse_ref_id(parsed)
            except Exception:
                pass

        m = re.search(r"\d+", s)
        if m:
            iv = int(m.group(0))
            return iv if iv > 0 else None

    return None


def parse_ref_list(value: Any) -> List[int]:
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        ids = []
        for item in value:
            rid = parse_ref_id(item)
            if rid is not None:
                ids.append(rid)
        return ids

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    return [rid for rid in (parse_ref_id(x) for x in arr) if rid is not None]
            except Exception:
                pass
        return [int(x) for x in re.findall(r"\d+", s)]

    rid = parse_ref_id(value)
    return [rid] if rid is not None else []
