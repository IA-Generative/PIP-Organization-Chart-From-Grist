from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import threading
from typing import List, Optional, Tuple

from .model_builder import BuiltModel, TeamModel

DEFAULT_SCW_BASE_URL = "https://api.scaleway.ai/a9158aac-8404-46ea-8bf5-1ca048cd6ab4/v1"
DEFAULT_SCW_MODEL = "mistral-small-3.2-24b-instruct-2506"
_LLM_SYNTH_STATS = {
    "planned": 0,
    "calls": 0,
    "ok": 0,
    "fallback": 0,
    "stream_empty_retry_ok": 0,
}
_LLM_SYNTH_FALLBACK_REASONS: dict[str, int] = {}
_LLM_SYNTH_LOCK = threading.Lock()


def get_llm_status(deep_check: bool = False) -> tuple[bool, str]:
    if os.getenv("ENABLE_LLM", "0") != "1":
        return False, "flag --llm non active"
    api_key = os.getenv("SCW_SECRET_KEY_LLM")
    if not api_key:
        return False, "SCW_SECRET_KEY_LLM non definie"
    try:
        from openai import OpenAI
    except Exception as exc:
        return False, f"package openai indisponible ({type(exc).__name__})"
    if not deep_check:
        return True, "ok (precheck local)"
    base_url = os.getenv("SCW_LLM_BASE_URL", DEFAULT_SCW_BASE_URL)
    model = os.getenv("SCW_LLM_MODEL", DEFAULT_SCW_MODEL)
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ok"}],
            max_tokens=8,
            temperature=0,
            stream=False,
            response_format={"type": "text"},
        )
    except Exception as exc:
        msg = str(exc).replace("\n", " ").strip()
        if len(msg) > 140:
            msg = msg[:137] + "..."
        return False, f"echec appel API LLM ({type(exc).__name__}: {msg})"
    return True, "ok"


def _llm_log_mode() -> str:
    mode = os.getenv("LLM_LOG_MODE", "compact").strip().lower()
    if mode not in {"quiet", "compact", "verbose"}:
        return "compact"
    return mode


def _llm_synth_log(event: str, team_name: str = "", reason: str = "") -> None:
    mode = _llm_log_mode()
    if mode == "quiet":
        return
    msg = ""
    should_print = False
    with _LLM_SYNTH_LOCK:
        if event == "call":
            _LLM_SYNTH_STATS["calls"] += 1
        elif event == "ok":
            _LLM_SYNTH_STATS["ok"] += 1
        elif event == "fallback":
            _LLM_SYNTH_STATS["fallback"] += 1
            key = (reason or "unknown").strip().lower()
            _LLM_SYNTH_FALLBACK_REASONS[key] = _LLM_SYNTH_FALLBACK_REASONS.get(key, 0) + 1
        elif event == "stream_retry_ok":
            _LLM_SYNTH_STATS["stream_empty_retry_ok"] += 1

        if mode == "compact":
            planned = _LLM_SYNTH_STATS["planned"]
            done = _LLM_SYNTH_STATS["ok"] + _LLM_SYNTH_STATS["fallback"]
            width = 12
            denom = planned if planned > 0 else _LLM_SYNTH_STATS["calls"]
            ratio = (done / denom) if denom else 0.0
            filled = min(width, max(0, int(round(ratio * width))))
            bar = "#" * filled + "-" * (width - filled)
            msg = (
                f"[LLM][Synthese] appels={_LLM_SYNTH_STATS['calls']} "
                f"ok={_LLM_SYNTH_STATS['ok']} fallback={_LLM_SYNTH_STATS['fallback']}"
            )
            if event == "fallback" and reason:
                msg += f" ({reason})"
            if team_name:
                msg += f" | equipe={team_name}"
            msg += f" | [{bar}] {done}/{denom if denom else 0}"
            should_print = event in {"ok", "fallback"}
    if mode == "compact":
        if should_print:
            print(msg)
        return

    # verbose
    if team_name:
        print(f"[LLM][Synthese] {event} | equipe={team_name}")
    else:
        print(f"[LLM][Synthese] {event}")


def _clean(text: str) -> str:
    return (text or "").strip()


def _build_team_context(team: TeamModel) -> str:
    lines: List[str] = []
    pm = ", ".join([p for p in team.pm_list if _clean(p)]) or "non renseigne"
    po = ", ".join([p for p in team.po_list if _clean(p)]) or "non renseigne"
    members_count = len([p for p in team.people_team if _clean(p) and _clean(p) != "UNKNOWN"])
    lines.append(f"Equipe: {team.name}")
    lines.append(f"PM: {pm}")
    lines.append(f"PO equipe: {po}")
    lines.append(f"Nb membres equipe: {members_count}")

    for epic in team.epics:
        desc = _clean(epic.description)
        int_pi = _clean(epic.intention_pi)
        int_next = _clean(epic.intention_next)
        feature_list = [_clean(f) for f in epic.features if _clean(f)]
        assignments = [
            f"{_clean(a.person)} ({_clean(a.role) or 'role non renseigne'} - {float(a.charge or 0.0):.1f}%)"
            for a in epic.assignments
            if _clean(a.person) and _clean(a.person) != "UNKNOWN"
        ]
        epic_po = ", ".join([p for p in epic.po_list if _clean(p)]) or "non renseigne"
        if not (desc or int_pi or int_next or feature_list or assignments):
            continue
        lines.append(f"- Epic: {epic.name}")
        lines.append(f"  PO epic: {epic_po}")
        if desc:
            lines.append(f"  Description: {desc}")
        if int_pi:
            lines.append(f"  Intention PI: {int_pi}")
        if int_next:
            lines.append(f"  Intention suivante: {int_next}")
        if feature_list:
            lines.append("  Features PI:")
            for feat in feature_list[:12]:
                lines.append(f"    - {feat}")
            if len(feature_list) > 12:
                lines.append(f"    - ... +{len(feature_list) - 12} autres")
        if assignments:
            lines.append("  Affectations:")
            for ass in assignments[:10]:
                lines.append(f"    - {ass}")
            if len(assignments) > 10:
                lines.append(f"    - ... +{len(assignments) - 10} autres")
    return "\n".join(lines)


def _compression_level(context: str) -> str:
    size = len(context)
    return "fortement" if size >= 1200 else "moyennement"


def _compress_context_for_llm(context: str, max_chars: int = 2200) -> str:
    text = _clean(context)
    if len(text) <= max_chars:
        return text
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    kept: List[str] = []
    total = 0
    for ln in lines:
        add = len(ln) + 1
        if total + add > max_chars:
            break
        kept.append(ln)
        total += add
    if not kept:
        return text[:max_chars]
    omitted = max(0, len(lines) - len(kept))
    if omitted:
        kept.append(f"... ({omitted} lignes omises pour respecter la limite)")
    return "\n".join(kept)


def _clip_lines(summary: str, max_lines: int) -> str:
    text = _clean(summary)
    if not text:
        return ""
    text = text.replace("\r\n", "\n")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return "\n".join(lines[:max_lines])


def _local_fallback_summary(team: TeamModel) -> str:
    if not team.epics:
        return "Mission non detaillee pour ce PI."

    epic_names = [e.name for e in team.epics if _clean(e.name)]
    if not epic_names:
        return "Equipe sans mission detaillee (epics non renseignes)."

    headline = ", ".join(epic_names[:3])
    if len(epic_names) > 3:
        headline += f", +{len(epic_names) - 3} autres epics"

    intentions = []
    for e in team.epics:
        t = _clean(e.intention_pi) or _clean(e.intention_next)
        if t:
            intentions.append(t)
    if intentions:
        base = f"Mission: porter {headline}. Intentions clefs: {intentions[0]}"
    else:
        base = f"Mission: porter {headline}."
    return _clip_lines(base, 5) or "Mission non detaillee."


def _summarize_next_increment_local(team: TeamModel) -> str:
    intentions: List[str] = []
    for epic in team.epics:
        t = _clean(epic.intention_next)
        if t:
            intentions.append(t)
    if not intentions:
        return "Intention prochain increment non renseignee."

    uniq: List[str] = []
    seen = set()
    for t in intentions:
        if t in seen:
            continue
        seen.add(t)
        uniq.append(t)

    # 2-3 short lines max.
    lines = []
    for t in uniq[:6]:
        line = t.replace("\n", " ").strip()
        if len(line) > 110:
            line = line[:107].rstrip() + "..."
        lines.append(f"- {line}")
    return _clip_lines("\n".join(lines), 10)


def _summarize_kpis_local(team: TeamModel) -> Tuple[str, str]:
    nb_epics = len(team.epics)
    nb_features = sum(len(e.features) for e in team.epics)
    with_assignments = sum(1 for e in team.epics if e.assignments)
    total_charge = 0.0
    people = set()
    for epic in team.epics:
        for a in epic.assignments:
            total_charge += float(a.charge or 0.0)
            person = _clean(a.person)
            if person:
                people.add(person)

    kpi_lines = [
        f"- Nb epics portees : {nb_epics}",
        f"- Nb features PI : {nb_features}",
        f"- Epics avec affectations : {with_assignments}/{nb_epics if nb_epics else 0}",
        f"- Charge totale declaree : {round(total_charge, 1)}%",
        f"- Personnes impliquees : {len(people)}",
    ]
    epic_names = [_clean(e.name) for e in team.epics if _clean(e.name)]
    feature_rich = sorted(team.epics, key=lambda e: len(e.features), reverse=True)
    top_epics = [e for e in feature_rich if _clean(e.name)][:2]
    focus = ", ".join([_clean(e.name) for e in top_epics]) if top_epics else ", ".join(epic_names[:2])
    if not focus:
        focus = "les epics du portefeuille"

    missing_intentions = sum(
        1 for e in team.epics if not (_clean(e.intention_pi) or _clean(e.intention_next))
    )
    epics_without_features = sum(1 for e in team.epics if not e.features)
    epics_without_assignments = sum(1 for e in team.epics if not e.assignments)

    critique_bits: List[str] = []
    if missing_intentions:
        critique_bits.append(
            f"{missing_intentions}/{nb_epics} epics sans intention explicite"
        )
    if epics_without_features:
        critique_bits.append(
            f"{epics_without_features}/{nb_epics} epics sans features rattachees"
        )
    if epics_without_assignments:
        critique_bits.append(
            f"{epics_without_assignments}/{nb_epics} epics sans affectation detaillee"
        )

    critique = "; ".join(critique_bits) if critique_bits else "contenu globalement structure"
    next_action = (
        "definir 2-3 KPI cibles (delai, adoption, qualite) et lier chaque KPI a 1 feature mesurable"
    )
    if top_epics and top_epics[0].features:
        next_action = (
            f"prioriser les livrables de '{_clean(top_epics[0].name)}' et "
            "associer chaque feature a un indicateur de resultat"
        )

    suggestion = (
        f"Suggestion IA: equipe {team.name}. "
        f"Contexte prioritaire: {focus}. "
        f"Point critique: {critique}. "
        f"Action PO/PM: {next_action}."
    )
    return _clip_lines("\n".join(kpi_lines), 8), _clip_lines(suggestion, 4)


def _ensure_contextual_suggestion(team: TeamModel, suggestion: str) -> str:
    text = _clean(suggestion)
    if not text:
        return text
    epic_names = [e.name for e in team.epics if _clean(e.name)]
    # If suggestion does not reference any known epic, add a short contextual anchor.
    if epic_names and not any(name in text for name in epic_names):
        text = (
            f"Pour {team.name}, focus prioritaire sur {epic_names[0]}. "
            + text
        )
    return _clip_lines(text, 4)


def _extract_completion_text(resp: object) -> str:
    """Best-effort extraction compatible with different OpenAI-like providers."""
    def _collect_text(node: object) -> str:
        if isinstance(node, str):
            return node
        if isinstance(node, list):
            return "".join(_collect_text(item) for item in node)
        if isinstance(node, dict):
            parts: List[str] = []
            txt = node.get("text")
            if isinstance(txt, str):
                parts.append(txt)
            elif txt is not None:
                parts.append(_collect_text(txt))
            val = node.get("value")
            if isinstance(val, str):
                parts.append(val)
            elif val is not None:
                parts.append(_collect_text(val))
            return "".join(parts)
        text_attr = getattr(node, "text", None)
        value_attr = getattr(node, "value", None)
        return _collect_text(text_attr) + _collect_text(value_attr)

    try:
        choices = getattr(resp, "choices", None) or []
        if not choices:
            return ""
        first = choices[0]
        # Some OpenAI-compatible providers place plain text directly on choice.
        choice_text = getattr(first, "text", None)
        if isinstance(choice_text, str) and choice_text.strip():
            return _clean(choice_text)
        message = getattr(first, "message", None)
        if not message:
            return ""
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return _clean(content)
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                extracted = _collect_text(item)
                if extracted:
                    parts.append(extracted)
            return _clean("".join(parts))
        return ""
    except Exception:
        return ""


def _finish_reason(resp: object) -> str:
    try:
        choices = getattr(resp, "choices", None) or []
        if not choices:
            return ""
        return str(getattr(choices[0], "finish_reason", "") or "")
    except Exception:
        return ""


def _llm_summaries(team: TeamModel, context: str) -> Optional[Tuple[str, str, str, str, str]]:
    if os.getenv("ENABLE_LLM", "0") != "1":
        return None

    api_key = os.getenv("SCW_SECRET_KEY_LLM")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except Exception:
        return None

    base_url = os.getenv("SCW_LLM_BASE_URL", DEFAULT_SCW_BASE_URL)
    model = os.getenv("SCW_LLM_MODEL", DEFAULT_SCW_MODEL)
    debug_enabled = os.getenv("LLM_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
    client = OpenAI(base_url=base_url, api_key=api_key)

    compression_level = _compression_level(context)
    prompt_header = (
        "A partir du contexte, produis quatre blocs de texte en francais:\n"
        "MISSION:\n"
        "- max 5 lignes\n"
        "- orientation execution / priorites\n"
        "INTENTIONS_MAJEURES:\n"
        "- max 10 lignes\n"
        "- se concentrer sur le prochain increment (3 mois)\n"
        "INDICATEURS_CLES_OKR_KPI:\n"
        "- max 8 lignes\n"
        "- indicateurs concrets, mesurables, orientés resultat\n"
        "SUGGESTION_IA:\n"
        "- max 4 lignes\n"
        "- critique + suggestion actionnable pour PO/PM\n"
        "- obligatoirement contextualisee a l'equipe et aux epics cites\n"
        "- citer explicitement 1 a 3 epics (noms exacts) et au moins 1 element concret "
        "(feature, intention, charge ou role)\n"
        "- mentionner au moins 1 faiblesse concrete detectee dans le contenu (manque, incoherence ou angle mort)\n"
        "- interdiction des formulations generiques repetitives (ex: 'definir 2-3 KPI cibles...' sans contexte)\n"
        "- format phrases courtes (pas de markdown, pas de puces numerotees)\n"
        "Repond STRICTEMENT avec:\n"
        "MISSION:\\n...\\nINTENTIONS_MAJEURES:\\n...\\nINDICATEURS_CLES_OKR_KPI:\\n...\\nSUGGESTION_IA:\\n...\n\n"
    )
    context_for_prompt = _compress_context_for_llm(context, max_chars=3000)
    user_prompt = (
        prompt_header
        + 
        f"Equipe: {team.name}\n"
        f"Contexte epics:\n{context_for_prompt}"
    )

    try:
        _llm_synth_log("call", team_name=team.name)
        # Prefer non-stream for provider compatibility; progress is handled at call level.
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un coach PM/PO. "
                        "Tes critiques sont factuelles, priorisees, contextualisees et actionnables."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=420,
            temperature=0.2,
            top_p=1,
            presence_penalty=0,
            stream=False,
            response_format={"type": "text"},
        )
        text = _extract_completion_text(resp)
        finish_reason = _finish_reason(resp)
        if not text:
            if debug_enabled:
                try:
                    fr = finish_reason or "n/a"
                    print(f"[LLM][Synthese][DEBUG] empty first response | finish_reason={fr} | equipe={team.name}")
                except Exception:
                    pass
            # Retry with looser options if provider ignores strict text format.
            retry_context = context_for_prompt
            retry_max_tokens = 420
            if finish_reason == "length":
                retry_context = _compress_context_for_llm(context, max_chars=1600)
                retry_max_tokens = 900
            retry_prompt = (
                prompt_header
                +
                f"Equipe: {team.name}\n"
                f"Contexte epics:\n{retry_context}"
            )
            retry = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un coach PM/PO. "
                            "Tes critiques sont factuelles, priorisees, contextualisees et actionnables."
                        ),
                    },
                    {"role": "user", "content": retry_prompt},
                ],
                max_tokens=retry_max_tokens,
                temperature=0.2,
                top_p=1,
                presence_penalty=0,
                stream=False,
                reasoning_effort="low",
            )
            text = _extract_completion_text(retry)
            retry_finish_reason = _finish_reason(retry)
            if debug_enabled:
                try:
                    fr2 = retry_finish_reason or "n/a"
                    print(
                        f"[LLM][Synthese][DEBUG] retry content_len={len(text)} "
                        f"| finish_reason={fr2} | equipe={team.name}"
                    )
                except Exception:
                    pass
            if not text:
                # Last resort: ultra-compact prompt to force short structured output.
                tiny_context = _compress_context_for_llm(context, max_chars=700)
                tiny_prompt = (
                    "Produit 4 blocs STRICTS en francais:\n"
                    "MISSION:\n1 phrase.\n"
                    "INTENTIONS_MAJEURES:\n2 phrases.\n"
                    "INDICATEURS_CLES_OKR_KPI:\n2 phrases.\n"
                    "SUGGESTION_IA:\n1 phrase actionnable.\n\n"
                    f"Equipe: {team.name}\nContexte:\n{tiny_context}"
                )
                final_try = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": tiny_prompt}],
                    max_tokens=380,
                    temperature=0.1,
                    stream=False,
                    reasoning_effort="low",
                )
                text = _extract_completion_text(final_try)
                final_finish = _finish_reason(final_try)
                if debug_enabled:
                    print(
                        f"[LLM][Synthese][DEBUG] final_try content_len={len(text)} "
                        f"| finish_reason={final_finish or 'n/a'} | equipe={team.name}"
                    )
                if not text:
                    reason = "empty_response"
                    if finish_reason == "length" or retry_finish_reason == "length" or final_finish == "length":
                        reason = "token_limit_no_content"
                    _llm_synth_log("fallback", team_name=team.name, reason=reason)
                    return None
            _llm_synth_log("stream_retry_ok", team_name=team.name)
        marker_m = "MISSION:"
        marker_i = "INTENTIONS_MAJEURES:"
        marker_k = "INDICATEURS_CLES_OKR_KPI:"
        marker_s = "SUGGESTION_IA:"
        if marker_m not in text or marker_i not in text or marker_k not in text or marker_s not in text:
            _llm_synth_log("fallback", team_name=team.name, reason="invalid_format")
            return None
        mission_part = text.split(marker_m, 1)[1].split(marker_i, 1)[0].strip()
        intent_part = text.split(marker_i, 1)[1].split(marker_k, 1)[0].strip()
        kpi_part = text.split(marker_k, 1)[1].split(marker_s, 1)[0].strip()
        suggestion_part = text.split(marker_s, 1)[1].strip()
        mission = _clip_lines(mission_part, 5)
        intentions = _clip_lines(intent_part, 10)
        kpis = _clip_lines(kpi_part, 8)
        suggestion = _clip_lines(suggestion_part, 4)
        if not mission:
            _llm_synth_log("fallback", team_name=team.name, reason="missing_mission")
            return None
        if not intentions:
            intentions = "Intention prochain increment non renseignee."
        if not kpis:
            kpis = "Indicateurs non renseignes."
        if not suggestion:
            suggestion = "Suggestion IA non disponible."
        suggestion = _ensure_contextual_suggestion(team, suggestion)
        _llm_synth_log("ok", team_name=team.name)
        return mission, intentions, kpis, suggestion, compression_level
    except Exception as exc:
        _llm_synth_log("fallback", team_name=team.name, reason=f"exception:{type(exc).__name__}")
        return None


def _llm_synth_log_summary() -> None:
    mode = _llm_log_mode()
    if mode == "quiet" or os.getenv("ENABLE_LLM", "0") != "1":
        return
    with _LLM_SYNTH_LOCK:
        planned = _LLM_SYNTH_STATS["planned"]
        calls = _LLM_SYNTH_STATS["calls"]
        ok = _LLM_SYNTH_STATS["ok"]
        fallback = _LLM_SYNTH_STATS["fallback"]
        stream_retry_ok = _LLM_SYNTH_STATS["stream_empty_retry_ok"]
        reasons = dict(_LLM_SYNTH_FALLBACK_REASONS)
    print(
        "[LLM][Synthese] resume: "
        f"planifies={planned} appels={calls} "
        f"ok={ok} fallback={fallback} "
        f"stream_empty_retry_ok={stream_retry_ok}"
    )
    if reasons:
        breakdown = ", ".join(
            f"{reason}={count}" for reason, count in sorted(
                reasons.items(), key=lambda item: (-item[1], item[0])
            )
        )
        print(f"[LLM][Synthese] fallback raisons: {breakdown}")


def _llm_synth_max_workers() -> int:
    raw = os.getenv("LLM_SYNTH_MAX_WORKERS", "32").strip()
    try:
        value = int(raw)
    except Exception:
        value = 32
    return max(1, min(256, value))


def _apply_team_summaries(
    team: TeamModel,
    llm_payload: Optional[Tuple[str, str, str, str, str]],
    compression_level: str,
) -> None:
    if llm_payload:
        mission, intentions, kpis, suggestion, compression_level = llm_payload
        team.mission_summary = mission
        team.next_increment_summary = intentions
        team.kpi_summary = kpis
        team.kpi_ai_suggestion = suggestion
        team.summary_ai_used = True
        if compression_level == "fortement":
            team.summary_warning = (
                "PO/PM: contenu fortement resume par IA. "
                "Ajouter le detail operationnel dans les Features."
            )
        else:
            team.summary_warning = ""
        return

    team.mission_summary = _local_fallback_summary(team)
    team.next_increment_summary = _summarize_next_increment_local(team)
    team.kpi_summary, team.kpi_ai_suggestion = _summarize_kpis_local(team)
    team.summary_ai_used = False
    if compression_level == "fortement":
        team.summary_warning = (
            "PO/PM: contenu fortement resume. "
            "Ajouter le detail operationnel dans les Features."
        )
    else:
        team.summary_warning = ""


def populate_team_missions(model: BuiltModel) -> None:
    llm_ok, _ = get_llm_status(deep_check=False)
    with _LLM_SYNTH_LOCK:
        _LLM_SYNTH_STATS["calls"] = 0
        _LLM_SYNTH_STATS["ok"] = 0
        _LLM_SYNTH_STATS["fallback"] = 0
        _LLM_SYNTH_STATS["stream_empty_retry_ok"] = 0
        _LLM_SYNTH_FALLBACK_REASONS.clear()

    team_data: List[Tuple[TeamModel, str, str]] = []
    planned = 0
    for team in model.teams:
        context = _build_team_context(team)
        compression_level = _compression_level(context) if context else "moyennement"
        team_data.append((team, context, compression_level))
        if context:
            planned += 1

    llm_enabled = os.getenv("ENABLE_LLM", "0") == "1" and llm_ok
    with _LLM_SYNTH_LOCK:
        _LLM_SYNTH_STATS["planned"] = planned if llm_enabled else 0
    if os.getenv("ENABLE_LLM", "0") == "1" and _llm_log_mode() in {"compact", "verbose"}:
        print(f"[LLM][Synthese] appels planifies: {_LLM_SYNTH_STATS['planned']}")

    llm_candidates: List[Tuple[TeamModel, str, str]] = []
    for team, context, compression_level in team_data:
        if not context:
            _apply_team_summaries(team, None, compression_level)
            continue
        llm_candidates.append((team, context, compression_level))

    if llm_enabled and llm_candidates:
        max_workers = min(_llm_synth_max_workers(), len(llm_candidates))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_team = {
                executor.submit(_llm_summaries, team, context): (team, compression_level)
                for team, context, compression_level in llm_candidates
            }
            for future in as_completed(future_to_team):
                team, compression_level = future_to_team[future]
                llm_payload: Optional[Tuple[str, str, str, str, str]] = None
                try:
                    llm_payload = future.result()
                except Exception:
                    llm_payload = None
                _apply_team_summaries(team, llm_payload, compression_level)
    else:
        for team, _context, compression_level in llm_candidates:
            _apply_team_summaries(team, None, compression_level)
    _llm_synth_log_summary()
