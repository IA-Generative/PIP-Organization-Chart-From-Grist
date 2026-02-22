"""
drawio_generator.py
-------------------
Génère le fichier XML draw.io à partir de la structure layoutée.
Produit un fichier .drawio directement ouvrable dans draw.io / diagrams.net
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict


# Couleurs
COLOR_TEAM_BG       = "#DAE8FC"
COLOR_TEAM_BORDER   = "#6C8EBF"
COLOR_TEAM_HEADER   = "#4472C4"
COLOR_EPIC_BG       = "#D5E8D4"
COLOR_EPIC_BORDER   = "#82B366"
COLOR_EPIC_HEADER   = "#2D7A4F"
COLOR_EPIC_SEP_BG   = "#FFE6CC"
COLOR_EPIC_SEP_BORDER = "#D6B656"
COLOR_EPIC_SEP_HEADER = "#B85000"
COLOR_PM_BG         = "#E1D5E7"
COLOR_PO_BG         = "#FFF2CC"
COLOR_FEATURE_BG    = "#F5F5F5"
COLOR_CARTOUCHE_BG  = "#1E2761"
COLOR_WHITE         = "#FFFFFF"


_id_counter = [1]

def _new_id():
    _id_counter[0] += 1
    return str(_id_counter[0])


def _add_cell(root, cell_id, label, style, x, y, w, h, parent="1", vertex="1"):
    cell = ET.SubElement(root, "mxCell")
    cell.set("id", cell_id)
    cell.set("value", label)
    cell.set("style", style)
    cell.set("vertex", vertex)
    cell.set("parent", parent)
    geo = ET.SubElement(cell, "mxGeometry")
    geo.set("x", str(x))
    geo.set("y", str(y))
    geo.set("width", str(w))
    geo.set("height", str(h))
    geo.set("as", "geometry")
    return cell


def _style_container(fill, stroke):
    return (
        f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};"
        f"strokeColor={stroke};swimlane=0;container=1;expand=1;"
    )


def _style_header(fill, font_color=COLOR_WHITE):
    return (
        f"rounded=0;whiteSpace=wrap;html=1;fillColor={fill};"
        f"strokeColor=none;fontColor={font_color};fontStyle=1;fontSize=11;"
    )


def _style_person(fill):
    return (
        f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};"
        f"strokeColor=#666666;fontSize=10;"
    )


def _style_feature():
    return (
        f"rounded=1;whiteSpace=wrap;html=1;fillColor={COLOR_FEATURE_BG};"
        f"strokeColor=#9E9E9E;fontSize=9;align=left;"
    )


def generate_drawio(structure: dict, pi_num: str, output_path: str) -> str:
    """
    Génère le fichier draw.io.
    
    Args:
        structure: structure layoutée (avec positions)
        pi_num: identifiant du PI
        output_path: chemin de sortie
    
    Returns:
        chemin du fichier généré
    """
    _id_counter[0] = 10  # reset

    # Racine XML
    mxgraph = ET.Element("mxGraphModel")
    mxgraph.set("dx", "1422")
    mxgraph.set("dy", "762")
    mxgraph.set("grid", "1")
    mxgraph.set("gridSize", "10")
    mxgraph.set("guides", "1")
    mxgraph.set("tooltips", "1")
    mxgraph.set("connect", "1")
    mxgraph.set("arrows", "1")
    mxgraph.set("fold", "1")
    mxgraph.set("page", "1")
    mxgraph.set("pageScale", "1")
    mxgraph.set("pageWidth", "1654")
    mxgraph.set("pageHeight", "1169")

    root = ET.SubElement(mxgraph, "root")
    ET.SubElement(root, "mxCell").set("id", "0")
    parent = ET.SubElement(root, "mxCell")
    parent.set("id", "1")
    parent.set("parent", "0")

    # ── Cartouche
    cartouche_style = (
        f"rounded=0;whiteSpace=wrap;html=1;fillColor={COLOR_CARTOUCHE_BG};"
        f"strokeColor=none;fontColor={COLOR_WHITE};fontStyle=1;fontSize=16;"
        f"align=center;"
    )
    _add_cell(root, _new_id(), f"PI Planning SDID – {pi_num}", cartouche_style,
              10, 10, 600, 50)

    # ── Équipes
    for team_node in structure["equipes"]:
        L = team_node["layout"]
        team_cell_id = _new_id()

        # Container équipe
        _add_cell(
            root, team_cell_id,
            f"🏢 {team_node['nom']}",
            _style_container(COLOR_TEAM_BG, COLOR_TEAM_BORDER),
            L["x"], L["y"], L["w"], L["h"]
        )

        # PMs dans l'équipe
        for pm in team_node.get("pms", []):
            pl = pm.get("layout", {})
            if pl:
                _add_cell(
                    root, _new_id(),
                    f"👔 PM: {pm['nom']}",
                    _style_person(COLOR_PM_BG),
                    pl["x"] - L["x"], pl["y"] - L["y"], pl["w"], pl["h"],
                    parent=team_cell_id
                )

        # Epics internes
        for epic_node in team_node.get("epics", []):
            el = epic_node["layout"]
            epic_cell_id = _new_id()

            _add_cell(
                root, epic_cell_id,
                f"📌 {epic_node['nom']}",
                _style_container(COLOR_EPIC_BG, COLOR_EPIC_BORDER),
                el["x"] - L["x"], el["y"] - L["y"], el["w"], el["h"],
                parent=team_cell_id
            )

            # POs
            for po in epic_node.get("pos", []):
                pol = po.get("layout", {})
                if pol:
                    _add_cell(
                        root, _new_id(),
                        f"🎯 PO: {po['nom']}",
                        _style_person(COLOR_PO_BG),
                        pol["x"] - el["x"], pol["y"] - el["y"], pol["w"], pol["h"],
                        parent=epic_cell_id
                    )

            # Features
            for feat in epic_node.get("features", []):
                fl = feat.get("layout", {})
                if fl:
                    _add_cell(
                        root, _new_id(),
                        f"⚡ {feat['nom']}",
                        _style_feature(),
                        fl["x"] - el["x"], fl["y"] - el["y"], fl["w"], fl["h"],
                        parent=epic_cell_id
                    )

    # ── Epics séparées
    for epic_node in structure.get("epics_separees", []):
        el = epic_node["layout"]
        epic_cell_id = _new_id()

        _add_cell(
            root, epic_cell_id,
            f"⚠️ EPIC SÉPARÉE – {epic_node['nom']}",
            _style_container(COLOR_EPIC_SEP_BG, COLOR_EPIC_SEP_BORDER),
            el["x"], el["y"], el["w"], el["h"]
        )

        for po in epic_node.get("pos", []):
            pol = po.get("layout", {})
            if pol:
                _add_cell(
                    root, _new_id(),
                    f"🎯 PO: {po['nom']}",
                    _style_person(COLOR_PO_BG),
                    pol["x"] - el["x"], pol["y"] - el["y"], pol["w"], pol["h"],
                    parent=epic_cell_id
                )

        for feat in epic_node.get("features", []):
            fl = feat.get("layout", {})
            if fl:
                _add_cell(
                    root, _new_id(),
                    f"⚡ {feat['nom']}",
                    _style_feature(),
                    fl["x"] - el["x"], fl["y"] - el["y"], fl["w"], fl["h"],
                    parent=epic_cell_id
                )

    # ── Export XML
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.ElementTree(mxgraph)
    ET.indent(tree, space="  ")
    tree.write(str(out_path), encoding="utf-8", xml_declaration=True)

    print(f"  ✅  draw.io généré : {out_path}")
    return str(out_path)
