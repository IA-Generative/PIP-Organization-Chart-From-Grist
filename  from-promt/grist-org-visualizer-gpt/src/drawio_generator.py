from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional

from .layout_engine import Layout
from .model_builder import BuiltModel, EpicModel, TeamModel


def _mx_cell(el: ET.Element, **attrs) -> ET.Element:
    return ET.SubElement(el, "mxCell", {k: str(v) for k, v in attrs.items()})


def _mx_geometry(cell: ET.Element, x: int, y: int, w: int, h: int) -> None:
    ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry"})


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_drawio(model: BuiltModel, layout: Layout) -> str:
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
    cart_value = _escape(f"PI Planning SDID – {model.pi}")
    cart_style = "rounded=1;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;fontSize=18;fontStyle=1;fillColor=#f5f5f5;strokeColor=#999999;"
    c = _mx_cell(root, id=str(next_id), value=cart_value, style=cart_style, vertex="1", parent="1")
    _mx_geometry(c, cart.x, cart.y, cart.w, cart.h)
    next_id += 1

    # Teams containers
    team_style = "swimlane;rounded=1;whiteSpace=wrap;html=1;startSize=40;fillColor=#ffffff;strokeColor=#666666;fontSize=14;"
    epic_style = "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;fontSize=12;spacing=6;fillColor=#dae8fc;strokeColor=#6c8ebf;"
    epic_sep_style = "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;fontSize=12;spacing=6;fillColor=#fff2cc;strokeColor=#d6b656;"
    sep_header_style = "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;fontSize=14;fontStyle=1;fillColor=#fff2cc;strokeColor=#d6b656;"

    # Add team cells and child epics
    for team in model.teams:
        tb = layout.team_boxes[team.id]
        pm_text = ", ".join(team.pm_list) if team.pm_list else "—"
        team_value = _escape(f"{team.name}\nPM : {pm_text}")
        tcell = _mx_cell(root, id=str(next_id), value=team_value, style=team_style, vertex="1", parent="1")
        team_id = str(next_id)
        _mx_geometry(tcell, tb.x, tb.y, tb.w, tb.h)
        next_id += 1

        # epics inside
        for epic in team.epics:
            eb = layout.epic_boxes.get(epic.id)
            if not eb:
                continue
            epic_value = _escape(_format_epic_value(epic, show_po=False))
            ecell = _mx_cell(root, id=str(next_id), value=epic_value, style=epic_style, vertex="1", parent=team_id)
            _mx_geometry(ecell, eb.x - tb.x, eb.y - tb.y, eb.w, eb.h)  # relative to container
            next_id += 1

    # Separate epics section header (if any)
    if model.separate_epics:
        # header box above first separate epic
        first = next(iter(layout.separate_epic_boxes.values()))
        header = _mx_cell(root, id=str(next_id), value=_escape("Epics séparées / transverses"), style=sep_header_style, vertex="1", parent="1")
        _mx_geometry(header, first.x, first.y - 45, first.w, 35)
        next_id += 1

    for epic in model.separate_epics:
        eb = layout.separate_epic_boxes[epic.id]
        po = ", ".join(epic.po_list) if epic.po_list else "—"
        epic_value = _escape(_format_epic_value(epic, show_po=True, po=po))
        ecell = _mx_cell(root, id=str(next_id), value=epic_value, style=epic_sep_style, vertex="1", parent="1")
        _mx_geometry(ecell, eb.x, eb.y, eb.w, eb.h)
        next_id += 1

    # Wrap into <diagram> container expected by diagrams.net
    diagram = ET.Element("mxfile", {"host": "app.diagrams.net"})
    d = ET.SubElement(diagram, "diagram", {"name": "PI Planning"})
    d.text = ET.tostring(mx, encoding="unicode")
    return ET.tostring(diagram, encoding="unicode")


def _format_epic_value(epic: EpicModel, show_po: bool, po: str = "") -> str:
    lines = [f"{epic.name}"]
    if show_po:
        lines.append(f"PO : {po}")
    lines.append("—")
    if epic.assignments:
        for a in epic.assignments:
            lines.append(f"{a.person} – {a.role} – {int(round(a.charge))}%")
    else:
        lines.append("(aucune affectation)")
    if epic.features:
        lines.append("")
        lines.append("Features (PI) :")
        for f in epic.features[:6]:
            lines.append(f"• {f}")
        if len(epic.features) > 6:
            lines.append(f"… +{len(epic.features)-6} autres")
    return "\n".join(lines)
