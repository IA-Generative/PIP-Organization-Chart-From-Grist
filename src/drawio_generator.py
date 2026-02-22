from __future__ import annotations

import html
import xml.etree.ElementTree as ET
from typing import List, Optional

from .layout_engine import Layout
from .model_builder import BuiltModel, EpicModel, TeamModel


def _mx_cell(el: ET.Element, **attrs) -> ET.Element:
    return ET.SubElement(el, "mxCell", {k: str(v) for k, v in attrs.items()})


def _mx_geometry(cell: ET.Element, x: int, y: int, w: int, h: int) -> None:
    ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry"})


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _html_escape(s: str) -> str:
    return html.escape(s, quote=False)


def _format_charge_percent(charge: float) -> str:
    value = float(charge)
    # Some sources store charge as ratio (0..1) instead of percent.
    if 0.0 <= value <= 1.0:
        value *= 100.0
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value))}%"
    return f"{value:.1f}%"


def _sorted_members(members: set[str]) -> List[str]:
    return sorted([m for m in members if m and m != "UNKNOWN"])


def _format_team_info_value(team: TeamModel, max_members_display: int = 12) -> str:
    pm = ", ".join(team.pm_list) if team.pm_list else "—"
    po = ", ".join(team.po_list) if team.po_list else "—"
    members = _sorted_members(team.people_team)

    lines = [f"<b>PM :</b> {_html_escape(pm)}", f"<b>PO :</b> {_html_escape(po)}", "<b>Membres :</b>"]
    if members:
        lines.extend([f"- {_html_escape(m)}" for m in members])
    else:
        lines.append("- aucun membre détecté")
    return "<br/>".join(lines)


def build_drawio(
    model: BuiltModel,
    layout: Layout,
    high_fragmented_people: Optional[List[str]] = None,
    low_or_unassigned_people: Optional[List[str]] = None,
) -> str:
    mx = ET.Element("mxGraphModel", {"dx": "1200", "dy": "800", "grid": "1", "gridSize": "10", "guides": "1",
                                    "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1", "page": "1",
                                    "pageScale": "1", "pageWidth": "1169", "pageHeight": "827", "math": "0",
                                    "shadow": "0"})
    root = ET.SubElement(mx, "root")
    _mx_cell(root, id="0")
    _mx_cell(root, id="1", parent="0")

    next_id = 2

    # Cartouche
    cart = layout.cartouche
    cart_value = _escape(f"🗂️ PI Planning SDID – {model.pi}")
    cart_style = "rounded=1;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;fontSize=18;fontStyle=1;fillColor=#f5f5f5;strokeColor=#999999;spacingLeft=10;spacingRight=10;"
    c = _mx_cell(root, id=str(next_id), value=cart_value, style=cart_style, vertex="1", parent="1")
    _mx_geometry(c, cart.x, cart.y, cart.w, cart.h)
    next_id += 1

    alert_style_left = "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;fontSize=12;spacing=6;spacingLeft=12;spacingRight=10;fillColor=#fde2e2;strokeColor=#c0392b;"
    alert_style_right = "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;fontSize=12;spacing=6;spacingLeft=12;spacingRight=10;fillColor=#fff3cd;strokeColor=#d6b656;"
    if layout.high_fragmentation_box:
        people = high_fragmented_people or []
        lines = ['<div style="text-align:center;"><b>Affecté sur plusieurs EPICS</b></div>']
        if people:
            lines.extend([f"- {_html_escape(p)}" for p in people])
        else:
            lines.append("- aucun")
        value = "<br/>".join(lines)
        b = layout.high_fragmentation_box
        cell = _mx_cell(root, id=str(next_id), value=value, style=alert_style_left, vertex="1", parent="1")
        _mx_geometry(cell, b.x, b.y, b.w, b.h)
        next_id += 1

    if layout.unassigned_people_box:
        people = low_or_unassigned_people or []
        lines = ['<div style="text-align:center;"><b>Sans affectation ou total &lt; 25%</b></div>']
        if people:
            lines.extend([f"- {_html_escape(p)}" for p in people])
        else:
            lines.append("- aucun")
        value = "<br/>".join(lines)
        b = layout.unassigned_people_box
        cell = _mx_cell(root, id=str(next_id), value=value, style=alert_style_right, vertex="1", parent="1")
        _mx_geometry(cell, b.x, b.y, b.w, b.h)
        next_id += 1

    # Teams containers
    team_style = "swimlane;rounded=1;whiteSpace=wrap;html=1;startSize=40;fillColor=#ffffff;strokeColor=#666666;fontSize=14;spacingLeft=10;spacingRight=8;"
    team_info_style = "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;fontSize=11;spacing=6;spacingLeft=12;spacingRight=10;fillColor=#f8f9fa;strokeColor=#b0b0b0;"
    epic_style = "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;fontSize=12;spacing=6;spacingLeft=12;spacingRight=10;fillColor=#dae8fc;strokeColor=#6c8ebf;"
    epic_sep_style = "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;fontSize=12;spacing=6;spacingLeft=12;spacingRight=10;fillColor=#fff2cc;strokeColor=#d6b656;"
    sep_header_style = "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;fontSize=14;fontStyle=1;spacingLeft=12;spacingRight=10;fillColor=#fff2cc;strokeColor=#d6b656;"

    # Add team cells and child epics
    for team in model.teams:
        tb = layout.team_boxes[team.id]
        team_value = _escape(f"👥 {team.name}")
        tcell = _mx_cell(root, id=str(next_id), value=team_value, style=team_style, vertex="1", parent="1")
        team_id = str(next_id)
        _mx_geometry(tcell, tb.x, tb.y, tb.w, tb.h)
        next_id += 1

        info_box = layout.team_info_boxes[team.id]
        info_value = _format_team_info_value(team)
        icell = _mx_cell(root, id=str(next_id), value=info_value, style=team_info_style, vertex="1", parent=team_id)
        _mx_geometry(icell, info_box.x - tb.x, info_box.y - tb.y, info_box.w, info_box.h)
        next_id += 1

        # epics inside
        for epic in team.epics:
            eb = layout.epic_boxes.get((team.id, epic.id))
            if not eb:
                continue
            epic_value = _format_epic_value(
                epic,
                show_po=True,
                po=", ".join(epic.po_list) if epic.po_list else "—",
                team_name=team.name,
                team_po_list=team.po_list,
                team_members=_sorted_members(team.people_team),
            )
            ecell = _mx_cell(root, id=str(next_id), value=epic_value, style=epic_style, vertex="1", parent=team_id)
            _mx_geometry(ecell, eb.x - tb.x, eb.y - tb.y, eb.w, eb.h)  # relative to container
            next_id += 1

    # Separate epics section header (if any)
    if model.separate_epics:
        # header box above first separate epic
        first = next(iter(layout.separate_epic_boxes.values()))
        header = _mx_cell(root, id=str(next_id), value=_escape("🧩 Epics séparées / transverses"), style=sep_header_style, vertex="1", parent="1")
        _mx_geometry(header, first.x, first.y - 45, first.w, 35)
        next_id += 1

    for epic in model.separate_epics:
        eb = layout.separate_epic_boxes[epic.id]
        po = ", ".join(epic.po_list) if epic.po_list else "—"
        epic_value = _format_epic_value(epic, show_po=True, po=po)
        ecell = _mx_cell(root, id=str(next_id), value=epic_value, style=epic_sep_style, vertex="1", parent="1")
        _mx_geometry(ecell, eb.x, eb.y, eb.w, eb.h)
        next_id += 1

    # Wrap into <diagram> container expected by diagrams.net (uncompressed format).
    diagram = ET.Element("mxfile", {"host": "app.diagrams.net", "compressed": "false"})
    d = ET.SubElement(diagram, "diagram", {"name": "PI Planning"})
    d.append(mx)
    return ET.tostring(diagram, encoding="unicode")


def _format_epic_value(
    epic: EpicModel,
    show_po: bool,
    po: str = "",
    team_name: Optional[str] = None,
    team_po_list: Optional[List[str]] = None,
    team_members: Optional[List[str]] = None,
) -> str:
    lines = [f"<div style=\"text-align:center;\"><b>🧩 {_html_escape(epic.name)}</b></div>"]
    if team_name:
        lines.append(f"<b>Equipe :</b> {_html_escape(team_name)}")
    if team_po_list is not None and epic.assignments:
        lines.append(f"<b>PO equipe :</b> {_html_escape(', '.join(team_po_list) if team_po_list else '—')}")
    if team_members is not None and epic.assignments:
        members_text = ", ".join(team_members) if team_members else "—"
        lines.append(f"<b>Membres equipe :</b> {_html_escape(members_text)}")
    if show_po and epic.assignments:
        lines.append(f"<b>PO epic :</b> {_html_escape(po)}")
    lines.append("—")
    if epic.assignments:
        for a in epic.assignments:
            lines.append(
                f"{_html_escape(a.person)} – {_html_escape(a.role)} – {_format_charge_percent(a.charge)}"
            )
    else:
        lines.append("(aucune affectation specifique)")
    if epic.features:
        lines.append("")
        lines.append("✨ Features (PI) :")
        for f in epic.features:
            lines.append(f"✨ {_html_escape(f)}")
    return "<br/>".join(lines)
