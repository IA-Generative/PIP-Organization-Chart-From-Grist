from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
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
from .ppt_generator import generate_ppt
from .readme_generator import generate_readme


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


def cmd_full_run(args) -> int:
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

    model = build_model(data=data, mapping=mapping, pi=pi)
    layout = compute_layout(model)
    drawio_xml = build_drawio(model, layout)
    (out / "orgchart.drawio").write_text(drawio_xml, encoding="utf-8")

    frag_df = compute_fragmentation(data, mapping)
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
