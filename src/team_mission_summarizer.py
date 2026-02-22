from __future__ import annotations

import os
from typing import List, Optional, Tuple

from .model_builder import BuiltModel, TeamModel

DEFAULT_SCW_BASE_URL = "https://api.scaleway.ai/a9158aac-8404-46ea-8bf5-1ca048cd6ab4/v1"
DEFAULT_SCW_MODEL = "gpt-oss-120b"


def _clean(text: str) -> str:
    return (text or "").strip()


def _build_team_context(team: TeamModel) -> str:
    lines: List[str] = []
    for epic in team.epics:
        desc = _clean(epic.description)
        int_pi = _clean(epic.intention_pi)
        int_next = _clean(epic.intention_next)
        if not (desc or int_pi or int_next):
            continue
        lines.append(f"- Epic: {epic.name}")
        if desc:
            lines.append(f"  Description: {desc}")
        if int_pi:
            lines.append(f"  Intention PI: {int_pi}")
        if int_next:
            lines.append(f"  Intention suivante: {int_next}")
    return "\n".join(lines)


def _compression_level(context: str) -> str:
    size = len(context)
    return "fortement" if size >= 1200 else "moyennement"


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
    epic_names = [e.name for e in team.epics if _clean(e.name)]
    focus = ", ".join(epic_names[:2]) if epic_names else "les epics du portefeuille"
    suggestion = (
        f"Suggestion IA: pour {team.name}, prioriser {focus}; "
        "definir 2-3 KPI cibles (delai, adoption, qualite) "
        "et rattacher chaque KPI a des Features mesurables."
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


def _llm_summaries(team: TeamModel, context: str) -> Optional[Tuple[str, str, str, str, str]]:
    api_key = os.getenv("SCW_SECRET_KEY_LLM")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except Exception:
        return None

    base_url = os.getenv("SCW_LLM_BASE_URL", DEFAULT_SCW_BASE_URL)
    model = os.getenv("SCW_LLM_MODEL", DEFAULT_SCW_MODEL)
    client = OpenAI(base_url=base_url, api_key=api_key)

    compression_level = _compression_level(context)
    user_prompt = (
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
        "- format phrases courtes (pas de markdown, pas de puces numerotees)\n"
        "Repond STRICTEMENT avec:\n"
        "MISSION:\\n...\\nINTENTIONS_MAJEURES:\\n...\\nINDICATEURS_CLES_OKR_KPI:\\n...\\nSUGGESTION_IA:\\n...\n\n"
        f"Equipe: {team.name}\n"
        f"Contexte epics:\n{context}"
    )

    try:
        stream = client.chat.completions.create(
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
            stream=True,
            reasoning_effort="medium",
            response_format={"type": "text"},
        )
        chunks: List[str] = []
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)
        text = _clean("".join(chunks))
        if not text:
            return None
        marker_m = "MISSION:"
        marker_i = "INTENTIONS_MAJEURES:"
        marker_k = "INDICATEURS_CLES_OKR_KPI:"
        marker_s = "SUGGESTION_IA:"
        if marker_m not in text or marker_i not in text or marker_k not in text or marker_s not in text:
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
            return None
        if not intentions:
            intentions = "Intention prochain increment non renseignee."
        if not kpis:
            kpis = "Indicateurs non renseignes."
        if not suggestion:
            suggestion = "Suggestion IA non disponible."
        suggestion = _ensure_contextual_suggestion(team, suggestion)
        return mission, intentions, kpis, suggestion, compression_level
    except Exception:
        return None


def populate_team_missions(model: BuiltModel) -> None:
    for team in model.teams:
        context = _build_team_context(team)
        compression_level = _compression_level(context) if context else "moyennement"
        if not context:
            team.mission_summary = _local_fallback_summary(team)
            team.next_increment_summary = _summarize_next_increment_local(team)
            team.kpi_summary, team.kpi_ai_suggestion = _summarize_kpis_local(team)
            team.summary_ai_used = False
            team.summary_warning = ""
            continue

        llm_payload = _llm_summaries(team, context)
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
        else:
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
