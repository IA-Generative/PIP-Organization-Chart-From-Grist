from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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
    high_fragmentation_box: Optional[Box]
    unassigned_people_box: Optional[Box]
    theme_header_boxes: List[Tuple[str, Box]]
    team_boxes: Dict[int, Box]
    team_info_boxes: Dict[int, Box]
    team_mission_boxes: Dict[int, Box]
    team_kpi_boxes: Dict[int, Box]
    team_warning_boxes: Dict[int, Box]
    epic_boxes: Dict[Tuple[int, int], Box]
    separate_epic_boxes: Dict[int, Box]


def _theme_for_team(name: str) -> str:
    n = (name or "").lower()
    if "mirai agents" in n:
        return "Mirai Agents"
    if "mirai métiers" in n or "mirai metiers" in n:
        return "Mirai Metiers"
    if "plateforme" in n or "model serving" in n:
        return "Plateforme & Ops"
    if "data" in n or "fraude" in n or "amdac" in n:
        return "Data & Produits"
    if "value" in n or "discovery" in n or "ux" in n or "refapp" in n or "siaf" in n:
        return "Pilotage & Support"
    return "Autres"


def _theme_sort_key(theme: str) -> int:
    order = {
        "Mirai Agents": 0,
        "Mirai Metiers": 1,
        "Plateforme & Ops": 2,
        "Data & Produits": 3,
        "Pilotage & Support": 4,
        "Autres": 5,
    }
    return order.get(theme, 99)


def _wrapped_lines(lines: List[str], max_chars: int) -> int:
    total = 0
    for line in lines:
        text = line or " "
        # Respect explicit newlines and then estimate wrapping per visual line.
        for visual_line in str(text).splitlines() or [" "]:
            segment = visual_line or " "
            total += max(1, int(math.ceil(len(segment) / max_chars)))
    return total


def _alert_box_height(title: str, items: List[str], max_chars: int = 64) -> int:
    lines = [title]
    if items:
        lines.extend([f"- {x}" for x in items])
    else:
        lines.append("- aucun")
    wrapped = _wrapped_lines(lines, max_chars=max_chars)
    return max(72, wrapped * 15 + 20)


def _sorted_members(members: set[str]) -> List[str]:
    return sorted([m for m in members if m and m != "UNKNOWN"])


def _epic_height(epic: EpicModel, team: TeamModel | None = None, max_chars: int = 52) -> int:
    lines: List[str] = [epic.name]
    if team is not None:
        lines.append(f"Equipe : {team.name}")
        # Keep height estimation aligned with rendered content:
        # PO/Membres/PO epic are shown only when there are explicit assignments.
        if epic.assignments:
            lines.append(f"PO equipe : {', '.join(team.po_list) if team.po_list else '—'}")
            team_members = _sorted_members(team.people_team)
            members_text = ", ".join(team_members) if team_members else "—"
            lines.append(f"Membres equipe : {members_text}")
    if epic.assignments:
        lines.append(f"PO epic : {', '.join(epic.po_list) if epic.po_list else '—'}")
    has_details = bool(epic.assignments or epic.features)
    if has_details:
        lines.append("—")

    if epic.assignments:
        for a in epic.assignments:
            lines.append(f"{a.person} - {a.role} - {int(round(a.charge))}%")
    else:
        lines.append("(aucune affectation specifique)")

    if epic.features:
        lines.append("")
        lines.append("Features (PI) :")
        for f in epic.features:
            lines.append(f"- {f}")

    wrapped = _wrapped_lines(lines, max_chars=max_chars)
    base_bottom = 16 if not has_details else 24
    return 28 + wrapped * 16 + base_bottom


def _team_info_height(team: TeamModel, max_chars: int = 58) -> int:
    members = _sorted_members(team.people_team)
    lines = [
        f"PM : {', '.join(team.pm_list) if team.pm_list else '—'}",
        f"PO : {', '.join(team.po_list) if team.po_list else '—'}",
        "Membres :",
    ]
    lines.extend([f"- {m}" for m in members] if members else ["- aucun membre détecté"])
    wrapped = _wrapped_lines(lines, max_chars=max_chars)
    return max(96, wrapped * 15 + 20)


def _team_mission_height(team: TeamModel, max_chars: int = 62) -> int:
    mission = (team.mission_summary or "").strip() or "Mission non renseignee."
    next_inc = (team.next_increment_summary or "").strip() or "Intention prochain increment non renseignee."
    mission_lines = _wrapped_lines([mission], max_chars=max_chars)
    next_lines = _wrapped_lines([next_inc], max_chars=max_chars)
    # 2 label lines: "Mission" and "Intention prochain increment (3 mois)".
    content_lines = mission_lines + next_lines + 2

    # Adaptive safety: keep long texts safe, avoid large blanks on short texts.
    if content_lines <= 12:
        safety = 8
    elif content_lines <= 24:
        safety = 14
    else:
        safety = 24

    return max(112, content_lines * 15 + 34 + safety)


def _team_kpi_height(team: TeamModel, max_chars: int = 62) -> int:
    kpis = (team.kpi_summary or "").strip() or "Indicateurs non renseignes."
    suggestion = (team.kpi_ai_suggestion or "").strip() or "Suggestion IA non disponible."
    # KPI is rendered in 2 columns; estimate each side with half width and keep the tallest.
    half_chars = max(22, max_chars // 2)
    left_wrapped = _wrapped_lines(["Synthèse indicateurs", kpis], max_chars=half_chars)
    right_wrapped = _wrapped_lines(["Critique / suggestion IA", suggestion], max_chars=half_chars)
    wrapped = max(left_wrapped, right_wrapped)
    return max(130, wrapped * 16 + 40)


def _team_warning_height(team: TeamModel, max_chars: int = 62) -> int:
    warning = (team.summary_warning or "").strip()
    if not warning:
        return 0
    wrapped = _wrapped_lines([warning], max_chars=max_chars)
    return max(56, wrapped * 14 + 18)


def _build_layout_for_columns(
    model: BuiltModel,
    y_start: int,
    margin: int,
    full_w: int,
    cols: int,
    col_gap: int,
) -> tuple[
    List[Tuple[str, Box]],
    Dict[int, Box],
    Dict[int, Box],
    Dict[int, Box],
    Dict[int, Box],
    Dict[int, Box],
    Dict[Tuple[int, int], Box],
    Dict[int, Box],
    int,
]:
    theme_header_boxes: List[Tuple[str, Box]] = []
    team_boxes: Dict[int, Box] = {}
    team_info_boxes: Dict[int, Box] = {}
    team_mission_boxes: Dict[int, Box] = {}
    team_kpi_boxes: Dict[int, Box] = {}
    team_warning_boxes: Dict[int, Box] = {}
    epic_boxes: Dict[Tuple[int, int], Box] = {}
    separate_epic_boxes: Dict[int, Box] = {}

    col_w = int((full_w - (cols - 1) * col_gap) / cols)
    team_w = col_w
    epic_w = max(220, team_w - 30)

    # Width-aware wrapping approximations to keep heights realistic when columns change.
    info_chars = max(38, int(epic_w / 8))
    mission_chars = max(40, int(epic_w / 8))
    epic_chars = max(34, int(epic_w / 8))

    grouped: Dict[str, List[TeamModel]] = {}
    for team in model.teams:
        grouped.setdefault(_theme_for_team(team.name), []).append(team)
    theme_names = sorted(grouped.keys(), key=_theme_sort_key)

    theme_header_h = 28
    team_header_h = 52
    row_gap = 20
    section_gap_y = 24
    team_gap_y = 28
    page_h = 1169
    page_bottom_margin = 24

    col_heights = [y_start for _ in range(cols)]

    for theme in theme_names:
        teams_in_theme = grouped.get(theme, [])
        col_idx = min(range(cols), key=lambda i: col_heights[i])
        sx = margin + col_idx * (col_w + col_gap)
        cursor_y = col_heights[col_idx]

        def _page_top(y: int) -> int:
            return y_start + ((max(y, y_start) - y_start) // page_h) * page_h

        def _page_bottom(y: int) -> int:
            return _page_top(y) + page_h - page_bottom_margin

        def _abs_page_top(y: int) -> int:
            return (max(int(y), 0) // page_h) * page_h

        def _snap_theme_start(y: int) -> int:
            """
            Generic rule: thematic headers must start at page top (except the first page).
            If y is inside a later page body, push to next page top.
            """
            pt = _page_top(y)
            if pt == y_start:
                return y
            return pt if y == pt else (pt + page_h)

        # Pre-compute team block dimensions once for this theme.
        team_dims: Dict[int, Tuple[int, int, int, int, List[int], int]] = {}
        for t in teams_in_theme:
            info_h = _team_info_height(t, max_chars=info_chars)
            mission_h = _team_mission_height(t, max_chars=mission_chars)
            kpi_h = _team_kpi_height(t, max_chars=mission_chars)
            warning_h = _team_warning_height(t, max_chars=mission_chars)
            epic_heights = [_epic_height(e, team=t, max_chars=epic_chars) for e in t.epics]
            epics_content_h = (
                sum(epic_heights) + row_gap * (len(epic_heights) - 1)
                if epic_heights
                else 120
            )
            fixed_to_epics = team_header_h + 10 + info_h + 12 + mission_h + 12 + kpi_h + 10
            if warning_h > 0:
                fixed_to_epics += warning_h + 10
            team_h = fixed_to_epics + epics_content_h + 8
            team_dims[t.id] = (info_h, mission_h, kpi_h, warning_h, epic_heights, team_h)

        # Place theme header at the top of a new page when the theme cannot start cleanly
        # in the remaining space of the current page.
        first_team_h = min((dims[5] for dims in team_dims.values()), default=None)

        default_header_gap = 8
        jump_header_gap = 2
        moved_to_new_page_for_header = False

        need_space = theme_header_h + default_header_gap + (first_team_h or 0)
        if cursor_y + max(theme_header_h, need_space) > _page_bottom(cursor_y) and _page_top(cursor_y) != y_start:
            cursor_y = _page_top(cursor_y) + page_h
            moved_to_new_page_for_header = True
        snapped_cursor_y = _snap_theme_start(cursor_y)
        if snapped_cursor_y != cursor_y:
            moved_to_new_page_for_header = True
            cursor_y = snapped_cursor_y
        # If a header is explicitly moved to a new page, align it to the absolute
        # top of the draw.io page grid (0, 1169, 2338, ...).
        if moved_to_new_page_for_header and cursor_y >= page_h:
            cursor_y = _abs_page_top(cursor_y) + 2
        theme_header_boxes.append((theme, Box(sx, cursor_y, col_w, theme_header_h)))
        is_later_page = _page_top(cursor_y) != y_start
        header_gap = jump_header_gap if (moved_to_new_page_for_header or is_later_page) else default_header_gap
        cursor_y += theme_header_h + header_gap

        if not teams_in_theme:
            cursor_y += 40

        pending = list(teams_in_theme)
        while pending:
            remaining = _page_bottom(cursor_y) - cursor_y
            fit = [t for t in pending if team_dims[t.id][5] <= remaining]
            # Best-fit: choose the tallest team that fits remaining page space.
            # This reduces local holes without breaking thematic grouping.
            if fit:
                team = max(fit, key=lambda t: team_dims[t.id][5])
            else:
                # Nothing fits: pick the smallest to minimize immediate overflow.
                team = min(pending, key=lambda t: team_dims[t.id][5])

            info_h, mission_h, kpi_h, warning_h, epic_heights, team_h = team_dims[team.id]

            # If team block doesn't fit in current page, move to next page when relevant.
            fresh_page_capacity = page_h - page_bottom_margin - (theme_header_h + 8)
            is_first_page = _page_top(cursor_y) == y_start
            page_bottom = _page_bottom(cursor_y)
            overflow_current = max(0, cursor_y + team_h - page_bottom)
            # Generic pagination rule:
            # move to next page only for blocks that can fit on a fresh page.
            # Oversized blocks stay in flow to avoid artificial white gaps after page breaks.
            should_move = (
                overflow_current > 0
                and not is_first_page
                and team_h <= fresh_page_capacity
            )
            if should_move:
                cursor_y = _page_top(cursor_y) + page_h
                # Do not repeat thematic headers on page breaks.

            team_boxes[team.id] = Box(sx, cursor_y, team_w, team_h)
            team_info_boxes[team.id] = Box(sx + 15, cursor_y + team_header_h + 10, epic_w, info_h)
            team_mission_boxes[team.id] = Box(
                sx + 15,
                cursor_y + team_header_h + 10 + info_h + 12,
                epic_w,
                mission_h,
            )
            team_kpi_boxes[team.id] = Box(
                sx + 15,
                cursor_y + team_header_h + 10 + info_h + 12 + mission_h + 10,
                epic_w,
                kpi_h,
            )
            if warning_h > 0:
                team_warning_boxes[team.id] = Box(
                    sx + 15,
                    cursor_y + team_header_h + 10 + info_h + 12 + mission_h + 10 + kpi_h + 10,
                    epic_w,
                    warning_h,
                )

            ey = cursor_y + team_header_h + 10 + info_h + 12 + mission_h + 12 + kpi_h + 10
            if warning_h > 0:
                ey += warning_h + 10
            for e, eh in zip(team.epics, epic_heights):
                epic_boxes[(team.id, e.id)] = Box(sx + 15, ey, epic_w, eh)
                ey += eh + row_gap

            cursor_y += team_h + team_gap_y
            pending.remove(team)

        col_heights[col_idx] = cursor_y + section_gap_y

    # Separate epics: keep them on same page by distributing cards on columns.
    if model.separate_epics:
        sep_header_h = 28
        sep_header_y = max(col_heights) + 6
        theme_header_boxes.append(("Epics séparées / transverses", Box(margin, sep_header_y, full_w, sep_header_h)))

        sep_col_heights = [sep_header_y + sep_header_h + 8 for _ in range(cols)]
        sep_chars = max(34, int((col_w - 30) / 8))

        def _sep_page_top(y: int) -> int:
            return y_start + ((max(y, y_start) - y_start) // page_h) * page_h

        def _sep_page_bottom(y: int) -> int:
            return _sep_page_top(y) + page_h - page_bottom_margin

        for e in model.separate_epics:
            col_idx = min(range(cols), key=lambda i: sep_col_heights[i])
            sx = margin + col_idx * (col_w + col_gap)
            sy = sep_col_heights[col_idx]
            eh = _epic_height(e, max_chars=sep_chars) + 10
            if sy + eh > _sep_page_bottom(sy):
                sy = _sep_page_top(sy) + page_h
            separate_epic_boxes[e.id] = Box(sx, sy, col_w, eh)
            sep_col_heights[col_idx] = sy + eh + 15

        max_y = max(sep_col_heights)
    else:
        max_y = max(col_heights) if col_heights else y_start

    return (
        theme_header_boxes,
        team_boxes,
        team_info_boxes,
        team_mission_boxes,
        team_kpi_boxes,
        team_warning_boxes,
        epic_boxes,
        separate_epic_boxes,
        max_y,
    )


def compute_layout(
    model: BuiltModel,
    high_fragmented_people: Optional[List[str]] = None,
    unassigned_people: Optional[List[str]] = None,
) -> Layout:
    margin = 20
    cartouche_h = 50
    page_w = 1654  # A3 landscape
    page_h = 1169  # A3 landscape
    full_w = page_w - 2 * margin

    cartouche = Box(x=margin, y=margin, w=full_w, h=cartouche_h)
    high_fragmentation_box: Optional[Box] = None
    unassigned_people_box: Optional[Box] = None

    y0 = margin + cartouche_h + 20

    hfp = high_fragmented_people or []
    unassigned = unassigned_people or []
    alert_h = 0
    if hfp or unassigned:
        alert_gap = 20
        half_w = (full_w - alert_gap) // 2
        left_h = _alert_box_height("Affecté sur plusieurs EPICS", hfp)
        right_h = _alert_box_height("Sans affectation ou total < 25%", unassigned)
        alert_h = max(left_h, right_h)
        # Keep teams at the top: alerts are positioned after teams/epics later.
        high_fragmentation_box = Box(x=margin, y=0, w=half_w, h=alert_h)
        unassigned_people_box = Box(x=margin + half_w + alert_gap, y=0, w=half_w, h=alert_h)

    # Keep a readable layout: fixed landscape organization (3 columns), no geometric compression.
    (
        theme_header_boxes,
        team_boxes,
        team_info_boxes,
        team_mission_boxes,
        team_kpi_boxes,
        team_warning_boxes,
        epic_boxes,
        separate_epic_boxes,
        _max_y,
    ) = _build_layout_for_columns(
        model=model,
        y_start=y0,
        margin=margin,
        full_w=full_w,
        cols=3,
        col_gap=20,
    )

    if alert_h > 0 and high_fragmentation_box and unassigned_people_box:
        # Place alerts on a dedicated new page.
        alert_top_margin = 12
        alerts_y = ((int(_max_y) // page_h) + 1) * page_h + alert_top_margin
        high_fragmentation_box = Box(
            x=high_fragmentation_box.x,
            y=alerts_y,
            w=high_fragmentation_box.w,
            h=high_fragmentation_box.h,
        )
        unassigned_people_box = Box(
            x=unassigned_people_box.x,
            y=alerts_y,
            w=unassigned_people_box.w,
            h=unassigned_people_box.h,
        )

    return Layout(
        cartouche=cartouche,
        high_fragmentation_box=high_fragmentation_box,
        unassigned_people_box=unassigned_people_box,
        theme_header_boxes=theme_header_boxes,
        team_boxes=team_boxes,
        team_info_boxes=team_info_boxes,
        team_mission_boxes=team_mission_boxes,
        team_kpi_boxes=team_kpi_boxes,
        team_warning_boxes=team_warning_boxes,
        epic_boxes=epic_boxes,
        separate_epic_boxes=separate_epic_boxes,
    )
