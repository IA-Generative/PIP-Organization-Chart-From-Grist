"""
layout_engine.py
----------------
Calcul des positions et dimensions pour le rendu draw.io.
Génère une mise en page automatique en grille.
"""

from typing import Any, Dict, List


# Constantes de layout (en unités draw.io)
MARGIN = 20
TEAM_PAD = 15
EPIC_PAD = 10
TEAM_WIDTH = 300
EPIC_WIDTH = 260
FEATURE_WIDTH = 220
NODE_HEIGHT = 40
PERSON_HEIGHT = 30
FEATURE_HEIGHT = 35
TEAM_HEADER = 50
EPIC_HEADER = 45
GAP_H = 30   # gap horizontal entre équipes
GAP_V = 20   # gap vertical entre éléments


def compute_epic_height(epic_node: dict) -> int:
    """Calcule la hauteur d'un container epic selon son contenu."""
    n_features = len(epic_node.get("features", []))
    n_pos = len(epic_node.get("pos", []))
    return EPIC_HEADER + (n_pos * PERSON_HEIGHT) + (n_features * FEATURE_HEIGHT) + 2 * EPIC_PAD + 10


def compute_team_height(team_node: dict) -> int:
    """Calcule la hauteur d'un container équipe."""
    n_pms = len(team_node.get("pms", []))
    total = TEAM_HEADER + (n_pms * PERSON_HEIGHT) + TEAM_PAD
    for epic in team_node.get("epics", []):
        total += compute_epic_height(epic) + GAP_V
    return total + TEAM_PAD


def layout_structure(structure: dict) -> dict:
    """
    Calcule les positions x,y,w,h pour tous les éléments.
    
    Returns:
        structure enrichie avec positions
    """
    x = MARGIN
    y = MARGIN

    # Layout des équipes
    for team_node in structure["equipes"]:
        team_h = compute_team_height(team_node)
        team_node["layout"] = {"x": x, "y": y, "w": TEAM_WIDTH, "h": team_h}

        # Contenu de l'équipe
        inner_y = y + TEAM_HEADER
        inner_x = x + TEAM_PAD

        # PMs
        for pm in team_node.get("pms", []):
            pm["layout"] = {"x": inner_x, "y": inner_y, "w": TEAM_WIDTH - 2*TEAM_PAD, "h": PERSON_HEIGHT}
            inner_y += PERSON_HEIGHT + 5

        inner_y += EPIC_PAD

        # Epics internes
        for epic_node in team_node.get("epics", []):
            epic_h = compute_epic_height(epic_node)
            epic_node["layout"] = {"x": inner_x, "y": inner_y, "w": EPIC_WIDTH, "h": epic_h}

            ey = inner_y + EPIC_HEADER
            ex = inner_x + EPIC_PAD

            # POs
            for po in epic_node.get("pos", []):
                po["layout"] = {"x": ex, "y": ey, "w": EPIC_WIDTH - 2*EPIC_PAD, "h": PERSON_HEIGHT}
                ey += PERSON_HEIGHT + 5

            ey += 5

            # Features
            for feat in epic_node.get("features", []):
                feat["layout"] = {"x": ex, "y": ey, "w": FEATURE_WIDTH, "h": FEATURE_HEIGHT}
                ey += FEATURE_HEIGHT + 5

            inner_y += epic_h + GAP_V

        x += TEAM_WIDTH + GAP_H

    # Layout des epics séparées (en bas)
    sep_x = MARGIN
    sep_y = y + max(
        (compute_team_height(t) for t in structure["equipes"]), default=200
    ) + 60

    for epic_node in structure["epics_separees"]:
        epic_h = compute_epic_height(epic_node)
        epic_node["layout"] = {"x": sep_x, "y": sep_y, "w": EPIC_WIDTH + 40, "h": epic_h}
        epic_node["separee_label"] = "⚠️ EPIC SÉPARÉE"

        ey = sep_y + EPIC_HEADER
        ex = sep_x + EPIC_PAD

        for po in epic_node.get("pos", []):
            po["layout"] = {"x": ex, "y": ey, "w": EPIC_WIDTH - 2*EPIC_PAD + 40, "h": PERSON_HEIGHT}
            ey += PERSON_HEIGHT + 5

        for feat in epic_node.get("features", []):
            feat["layout"] = {"x": ex, "y": ey, "w": FEATURE_WIDTH + 20, "h": FEATURE_HEIGHT}
            ey += FEATURE_HEIGHT + 5

        sep_x += EPIC_WIDTH + 50 + GAP_H

    return structure
