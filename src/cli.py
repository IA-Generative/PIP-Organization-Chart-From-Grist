from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import List, Tuple
import yaml

from .config_checker import get_api_config_from_env, print_api_missing
from .grist_loader import load_from_grist_file
from .api_client import load_from_api
from .rules import normalize_pi
from .model_builder import build_model
from .layout_engine import compute_layout
from .drawio_generator import build_drawio
from .analytics import compute_fragmentation
from .report_generator import write_fragmentation_reports, write_run_summary
from .readme_generator import generate_readme
from .ref_utils import parse_ref_id


def _load_mapping(repo_root: Path) -> dict:
    mapping_path = repo_root / "config" / "mapping.yml"
    with open(mapping_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _find_default_grist(repo_root: Path) -> str | None:
    data_dir = repo_root / "data"
    if not data_dir.exists():
        return None
    for p in data_dir.iterdir():
        if p.suffix.lower() == ".grist":
            return str(p)
    return None


def _ensure_output_dir(repo_root: Path) -> Path:
    out = repo_root / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _load_generate_ppt():
    try:
        from .ppt_generator import generate_ppt as _generate_ppt
    except ModuleNotFoundError as exc:
        if exc.name == "pptx":
            print("❌ Dépendance manquante: python-pptx")
            print("Installez les dépendances puis relancez :")
            print("python -m pip install -e .")
            raise SystemExit(2)
        raise
    return _generate_ppt


def _open_orgchart_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        if sys.platform == "darwin":
            # Prefer local desktop app first.
            for app_name in ("draw.io", "diagrams.net"):
                probe = subprocess.run(
                    ["open", "-Ra", app_name],
                    capture_output=True,
                    text=True,
                )
                if probe.returncode != 0:
                    continue
                res = subprocess.run(
                    ["open", "-a", app_name, str(path)],
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0:
                    print(f"Ouverture locale dans {app_name}: {path}")
                    return

            subprocess.run(["open", "https://app.diagrams.net/"], check=False)
            print("Application locale draw.io introuvable, ouverture dans le navigateur.")
            print(f"Fichier à importer : {path}")
            return

        if sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(path)], check=False)
            print(f"Ouverture locale: {path}")
            return
    except Exception as exc:
        print(f"⚠️ Impossible d'ouvrir automatiquement le diagramme: {exc}")


def _compute_alert_people_lists(data, mapping: dict, frag_df) -> Tuple[List[str], List[str]]:
    cols = mapping["columns"]
    person_label_col = cols["personne_label"]
    aff_person_col = cols["aff_person_ref"]
    aff_epic_col = cols.get("aff_epic_ref")
    epic_name_col = cols.get("epic_name")

    all_people = sorted(
        {
            str(v).strip()
            for v in data.personnes.get(person_label_col, [])
            if str(v).strip() and str(v).strip() != "UNKNOWN"
        }
    )

    if frag_df is None or frag_df.empty:
        return [], all_people

    # Rule: elevated fragmentation if a person is assigned to at least 2 epics.
    high_frag_df = frag_df.loc[frag_df["Nb_Epics"] >= 2].sort_values(
        ["Nb_Epics", "Score_Fragmentation", "Total_Charge", "Agent"],
        ascending=[False, False, False, True],
    )
    high_fragmented_names = [
        str(x).strip() for x in high_frag_df["Agent"].tolist() if str(x).strip() and str(x) != "UNKNOWN"
    ]

    person_map = dict(zip(data.personnes["id"], data.personnes[person_label_col].astype(str)))
    epic_name_map = {}
    if epic_name_col and not data.epics.empty and epic_name_col in data.epics.columns:
        epic_name_map = dict(zip(data.epics["id"], data.epics[epic_name_col].astype(str)))
    aff_people = set()
    person_epics: dict[str, set[str]] = {}
    if not data.affectations.empty and aff_person_col in data.affectations.columns:
        person_ids = data.affectations[aff_person_col].apply(parse_ref_id)
        aff_people = {
            str(person_map.get(pid, "")).strip()
            for pid in person_ids.dropna().astype(int).tolist()
            if str(person_map.get(pid, "")).strip() and str(person_map.get(pid, "")).strip() != "UNKNOWN"
        }
        if aff_epic_col and aff_epic_col in data.affectations.columns:
            for _, row in data.affectations.iterrows():
                pid = parse_ref_id(row.get(aff_person_col))
                if pid is None:
                    continue
                person = str(person_map.get(pid, "")).strip()
                if not person or person == "UNKNOWN":
                    continue
                eid = parse_ref_id(row.get(aff_epic_col))
                if eid is None:
                    continue
                ename = str(epic_name_map.get(eid, "")).strip()
                if not ename:
                    continue
                person_epics.setdefault(person, set()).add(ename)

    low_load = set(
        str(x).strip()
        for x in frag_df.loc[frag_df["Total_Charge"] < 25.0, "Agent"].tolist()
        if str(x).strip() and str(x) != "UNKNOWN"
    )
    unassigned = set(all_people) - set(aff_people)
    low_or_unassigned = sorted(unassigned | low_load)

    high_fragmented: List[str] = []
    for person in list(dict.fromkeys(high_fragmented_names)):
        epics = sorted(person_epics.get(person, set()))
        if epics:
            high_fragmented.append(f"{person} ({', '.join(epics)})")
        else:
            high_fragmented.append(f"{person} (—)")

    return high_fragmented, low_or_unassigned


def cmd_full_run(args) -> int:
    generate_ppt = _load_generate_ppt()
    repo_root = Path(__file__).resolve().parents[1]
    mapping = _load_mapping(repo_root)

    pi = normalize_pi(args.pi)

    # Determine source
    source_label = ""
    data = None

    if args.source:
        source_label = f"fichier ({args.source})"
        data = load_from_grist_file(args.source, mapping)
    elif args.api:
        cfg, missing = get_api_config_from_env()
        if missing:
            print_api_missing(missing)
            # fallback to file
            default_file = _find_default_grist(repo_root)
            if not default_file:
                print("❌ Aucun fichier .grist trouvé dans le répertoire data/.")
                print("Merci de déposer votre fichier Grist dans :")
                print("data/example_empty.grist")
                print("OU de fournir le chemin avec --source")
                return 2
            print(f"➡️ Bascule en mode fichier local: {default_file}")
            source_label = f"fichier ({default_file})"
            data = load_from_grist_file(default_file, mapping)
        else:
            source_label = "API Grist"
            data = load_from_api(cfg, mapping)
    else:
        default_file = _find_default_grist(repo_root)
        if not default_file:
            # If API env is set, try API; else guide user
            cfg, missing = get_api_config_from_env()
            if not missing:
                source_label = "API Grist"
                data = load_from_api(cfg, mapping)
            else:
                print_api_missing(missing)
                print("❌ Aucun fichier .grist trouvé dans le répertoire data/.")
                print("Merci de déposer votre fichier Grist dans :")
                print("data/example_empty.grist")
                print("OU de fournir le chemin avec --source")
                return 2
        else:
            source_label = f"fichier ({default_file})"
            data = load_from_grist_file(default_file, mapping)

    out = _ensure_output_dir(repo_root)

    frag_df = compute_fragmentation(data, mapping)
    high_fragmented, low_or_unassigned = _compute_alert_people_lists(data, mapping, frag_df)

    model = build_model(data=data, mapping=mapping, pi=pi)
    layout = compute_layout(
        model,
        high_fragmented_people=high_fragmented,
        unassigned_people=low_or_unassigned,
    )
    drawio_xml = build_drawio(
        model,
        layout,
        high_fragmented_people=high_fragmented,
        low_or_unassigned_people=low_or_unassigned,
    )
    orgchart_path = out / "orgchart.drawio"
    orgchart_path.write_text(drawio_xml, encoding="utf-8")

    frag_kpis = write_fragmentation_reports(
        frag_df,
        out_csv=str(out / "multi_affectations.csv"),
        out_md=str(out / "synthesis.md"),
    )

    # find epics missing intentions/description
    missing = []
    for t in model.teams:
        for e in t.epics:
            if not (e.description.strip() or e.intention_pi.strip() or e.intention_next.strip()):
                missing.append(e.name)
    for e in model.separate_epics:
        if not (e.description.strip() or e.intention_pi.strip() or e.intention_next.strip()):
            missing.append(e.name)

    # README generated
    generate_readme(model, str(out / "README_generated.md"))

    # PPT
    ppt_path = out / f"{model.pi}_Synthese_SDID.pptx"
    generate_ppt(model, frag_kpis, str(ppt_path))

    # Run summary
    write_run_summary(
        model=model,
        frag_kpis=frag_kpis,
        source_label=source_label,
        out_md=str(out / "run_summary.md"),
        features_table_empty=bool(data.features.empty),
        epics_missing_intentions=sorted(set(missing)),
    )
    _open_orgchart_file(orgchart_path)

    return 0


def cmd_diagram(args) -> int:
    # just call full-run but skip other outputs (simple for now)
    return cmd_full_run(args)


def cmd_analyze(args) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    mapping = _load_mapping(repo_root)
    # Load source
    if not args.source:
        default_file = _find_default_grist(repo_root)
        if not default_file:
            print("❌ Aucun fichier .grist trouvé. Fournir --source.")
            return 2
        args.source = default_file
    data = load_from_grist_file(args.source, mapping)
    out = _ensure_output_dir(repo_root)
    frag_df = compute_fragmentation(data, mapping)
    write_fragmentation_reports(
        frag_df,
        out_csv=str(out / "multi_affectations.csv"),
        out_md=str(out / "synthesis.md"),
    )
    print("✅ Analyse générée dans output/")
    return 0


def cmd_ppt(args) -> int:
    generate_ppt = _load_generate_ppt()
    repo_root = Path(__file__).resolve().parents[1]
    mapping = _load_mapping(repo_root)
    pi = normalize_pi(args.pi)
    if not args.source:
        default_file = _find_default_grist(repo_root)
        if not default_file:
            print("❌ Aucun fichier .grist trouvé. Fournir --source.")
            return 2
        args.source = default_file
    data = load_from_grist_file(args.source, mapping)
    model = build_model(data=data, mapping=mapping, pi=pi)
    out = _ensure_output_dir(repo_root)
    frag_df = compute_fragmentation(data, mapping)
    frag_kpis = {"agents_over_100": int((frag_df["Total_Charge"]>100).sum()) if not frag_df.empty else 0,
                "agents_multi_team": int((frag_df["Nb_Equipes"]>1).sum()) if not frag_df.empty else 0}
    ppt_path = out / f"{model.pi}_Synthese_SDID.pptx"
    generate_ppt(model, frag_kpis, str(ppt_path))
    print(f"✅ PowerPoint généré: {ppt_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SDID PI Planning: Grist → draw.io + fragmentation + PPT")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("--pi", required=True, help="Numéro de PI (ex: PI-10 ou 10)")
        sp.add_argument("--source", help="Chemin vers un fichier .grist local")
        sp.add_argument("--api", action="store_true", help="Utiliser l'API Grist (si variables env configurées)")

    sp = sub.add_parser("full-run", help="Génère draw.io + analyse + ppt + readme + summary")
    add_common(sp)
    sp.set_defaults(func=cmd_full_run)

    sp2 = sub.add_parser("diagram", help="Génère seulement le draw.io (implémentation: pipeline complet)")
    add_common(sp2)
    sp2.set_defaults(func=cmd_diagram)

    sp3 = sub.add_parser("analyze", help="Génère seulement l'analyse fragmentation")
    sp3.add_argument("--source", help="Chemin vers un fichier .grist local")
    sp3.set_defaults(func=cmd_analyze)

    sp4 = sub.add_parser("ppt", help="Génère seulement le PowerPoint")
    sp4.add_argument("--pi", required=True, help="Numéro de PI (ex: PI-10 ou 10)")
    sp4.add_argument("--source", help="Chemin vers un fichier .grist local")
    sp4.set_defaults(func=cmd_ppt)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    rc = args.func(args)
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
