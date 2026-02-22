from __future__ import annotations

from typing import Dict, List

from pptx import Presentation
from pptx.util import Inches, Pt

from .model_builder import BuiltModel, TeamModel, EpicModel


def _add_title(slide, text: str) -> None:
    title = slide.shapes.title
    title.text = text


def _add_bullets(slide, left, top, width, height, title: str, bullets: List[str]) -> None:
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = title
    p.font.bold = True
    p.font.size = Pt(18)
    for b in bullets:
        p = tf.add_paragraph()
        p.text = b
        p.level = 1
        p.font.size = Pt(14)


def _epic_ambition(epic: EpicModel) -> str:
    parts = []
    if epic.description:
        parts.append(epic.description.strip())
    if epic.intention_pi:
        parts.append(f"Intention PI : {epic.intention_pi.strip()}")
    if epic.intention_next:
        parts.append(f"Prochain incrément : {epic.intention_next.strip()}")
    text = " ".join(parts)
    # keep concise
    if len(text) > 450:
        text = text[:447] + "..."
    return text or "—"


def generate_ppt(model: BuiltModel, frag_kpis: Dict[str, int], out_path: str) -> None:
    prs = Presentation()

    # Slide 1: synthesis
    slide_layout = prs.slide_layouts[0]  # Title slide
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = f"PI Planning SDID – {model.pi}"
    subtitle = slide.placeholders[1]
    subtitle.text = "Synthèse automatique (équipes / epics / features / fragmentation)"

    # Add KPIs as textbox
    slide_layout = prs.slide_layouts[5]  # Title Only
    slide = prs.slides.add_slide(slide_layout)
    _add_title(slide, "Planche de synthèse")
    kpis = [
        f"Équipes : {model.stats.get('teams', 0)}",
        f"Epics : {model.stats.get('epics_total', 0)} (séparées : {model.stats.get('epics_separate', 0)})",
        f"Features (PI) : {model.stats.get('features_pi', 0)}",
        f"Agents multi-équipes : {frag_kpis.get('agents_multi_team', 0)}",
        f"Agents >100% : {frag_kpis.get('agents_over_100', 0)}",
    ]
    _add_bullets(slide, Inches(0.8), Inches(1.6), Inches(8.5), Inches(4.8), "Indicateurs clés", kpis)

    # 5 bullets ambition from epics (first 5 epics by appearance)
    epics_all = [e for t in model.teams for e in t.epics] + list(model.separate_epics)
    ambition_bullets = []
    for e in epics_all[:5]:
        ambition_bullets.append(f"{e.name} : {(_epic_ambition(e)[:140] + '...') if len(_epic_ambition(e))>140 else _epic_ambition(e)}")
    if not ambition_bullets:
        ambition_bullets = ["Aucune epic détectée pour ce PI / template vide."]
    _add_bullets(slide, Inches(0.8), Inches(5.2), Inches(8.5), Inches(2.0), "Ambition PI (extraits)", ambition_bullets)

    # Slide 3: org view (textual)
    slide_layout = prs.slide_layouts[5]
    slide = prs.slides.add_slide(slide_layout)
    _add_title(slide, "Vue organisationnelle (équipes → epics → features)")
    lines = []
    for t in model.teams:
        pm = ", ".join(t.pm_list) if t.pm_list else "—"
        lines.append(f"• {t.name} (PM: {pm})")
        for e in t.epics:
            lines.append(f"   - {e.name} (features PI: {len(e.features)})")
    if model.separate_epics:
        lines.append("")
        lines.append("Epics séparées / transverses :")
        for e in model.separate_epics:
            po = ", ".join(e.po_list) if e.po_list else "—"
            lines.append(f"• {e.name} (PO: {po}) (features PI: {len(e.features)})")
    _add_bullets(slide, Inches(0.8), Inches(1.6), Inches(9.0), Inches(5.5), "Structure", lines[:40] if lines else ["—"])

    # Slides per team
    for t in model.teams:
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        _add_title(slide, f"Équipe — {t.name}")
        pm = ", ".join(t.pm_list) if t.pm_list else "—"
        bullets = [f"PM : {pm}", f"Epics : {len(t.epics)}"]
        _add_bullets(slide, Inches(0.8), Inches(1.6), Inches(4.4), Inches(2.0), "Résumé", bullets)

        # list epics & features
        lines = []
        for e in t.epics:
            lines.append(f"{e.name}")
            for f in e.features[:10]:
                lines.append(f"  • {f}")
            if len(e.features) > 10:
                lines.append(f"  … +{len(e.features)-10} autres")
        if not lines:
            lines = ["—"]
        _add_bullets(slide, Inches(0.8), Inches(3.2), Inches(9.0), Inches(3.8), "Epics & Features (PI)", lines[:60])

    # Slides per epic (for epics that have features in PI; fallback all if none)
    epics_pi = [e for e in epics_all if e.features]
    if not epics_pi:
        epics_pi = epics_all

    for e in epics_pi:
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        _add_title(slide, f"Epic — {e.name}")
        po = ", ".join(e.po_list) if e.po_list else "—"
        if e.is_separate:
            header = [f"PO : {po}", "Epic séparée / transverse : OUI"]
        else:
            header = [f"PO : {po}", "Epic séparée / transverse : NON"]
        _add_bullets(slide, Inches(0.8), Inches(1.6), Inches(4.4), Inches(1.6), "Gouvernance", header)

        ambition = _epic_ambition(e)
        _add_bullets(slide, Inches(0.8), Inches(3.0), Inches(9.0), Inches(2.4), "Ambition / finalité (synthèse)", [ambition])

        feats = [f"• {f}" for f in (e.features[:15] if e.features else [])]
        if not feats:
            feats = ["—"]
        _add_bullets(slide, Inches(0.8), Inches(5.3), Inches(9.0), Inches(2.0), "Features (PI)", feats[:18])

    prs.save(out_path)
