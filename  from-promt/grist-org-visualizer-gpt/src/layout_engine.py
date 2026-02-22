from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .model_builder import BuiltModel, EpicModel, TeamModel


@dataclass
class Box:
    x: int
    y: int
    w: int
    h: int


@dataclass
class Layout:
    cartouche: Box
    team_boxes: Dict[int, Box]
    epic_boxes: Dict[int, Box]
    separate_epic_boxes: Dict[int, Box]


def _epic_height(epic: EpicModel) -> int:
    # title + assignments + features + padding
    lines = 2  # title + maybe PO
    lines += max(1, len(epic.assignments)) if epic.assignments else 1
    if epic.features:
        lines += 1 + min(6, len(epic.features))  # header + up to 6 features
    return 30 + lines * 16 + 18


def compute_layout(model: BuiltModel) -> Layout:
    margin = 20
    cartouche_h = 50
    team_w = 460
    team_header_h = 40
    epic_w = team_w - 30
    col_gap = 30
    row_gap = 20

    cartouche = Box(x=margin, y=margin, w=3 * team_w + 2 * col_gap, h=cartouche_h)

    team_boxes: Dict[int, Box] = {}
    epic_boxes: Dict[int, Box] = {}
    separate_epic_boxes: Dict[int, Box] = {}

    x = margin
    y0 = margin + cartouche_h + 20

    # Teams in columns, wrap every 3 columns
    col = 0
    for team in model.teams:
        tx = x + col * (team_w + col_gap)
        ty = y0
        # compute team height by summing epics
        epics_h = 0
        for e in team.epics:
            epics_h += _epic_height(e) + row_gap
        team_h = team_header_h + max(120, epics_h + 20)

        team_boxes[team.id] = Box(tx, ty, team_w, team_h)

        # place epics inside
        ey = ty + team_header_h + 10
        for e in team.epics:
            eh = _epic_height(e)
            epic_boxes[e.id] = Box(tx + 15, ey, epic_w, eh)
            ey += eh + row_gap

        col += 1
        if col >= 3:
            col = 0
            y0 += team_h + 40

    # Separate epics area below all teams
    sep_x = margin
    sep_y = y0 + 40
    for e in model.separate_epics:
        eh = _epic_height(e) + 10
        separate_epic_boxes[e.id] = Box(sep_x, sep_y, team_w, eh)
        sep_y += eh + 15

    return Layout(
        cartouche=cartouche,
        team_boxes=team_boxes,
        epic_boxes=epic_boxes,
        separate_epic_boxes=separate_epic_boxes,
    )
