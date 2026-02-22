"""
cli.py
------
Interface en ligne de commande pour grist-org-visualizer.

Usage :
  python -m src.cli full-run --pi PI-10
  python -m src.cli full-run --api --pi PI-10
  python -m src.cli full-run --source data/mon.grist --pi PI-10
  python -m src.cli drawio --pi PI-10
  python -m src.cli analytics --pi PI-10
  python -m src.cli pptx --pi PI-10
"""

import argparse
import sys
from pathlib import Path


def normalize_pi(pi: str) -> str:
    """Normalise le numéro de PI en PI-<num>."""
    pi = pi.strip().upper()
    if not pi.startswith("PI"):
        return f"PI-{pi}"
    if "PI" in pi and "-" not in pi:
        num = pi.replace("PI", "").strip()
        return f"PI-{num}"
    return pi


def run_full(args):
    """Exécute le pipeline complet."""
    from src.config_checker import resolve_source
    from src.grist_loader import load_data
    from src.model_builder import build_model
    from src.rules import build_org_structure
    from src.layout_engine import layout_structure
    from src.drawio_generator import generate_drawio
    from src.analytics import compute_fragmentation, export_csv, export_synthesis_md
    from src.ppt_generator import generate_pptx
    from src.readme_generator import generate_readme
    from src.report_generator import generate_run_summary

    pi_num = normalize_pi(args.pi)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  grist-org-visualizer – {pi_num}")
    print(f"{'='*60}\n")

    # ── Résolution de la source
    mode, source_path = resolve_source(
        source_arg=args.source,
        use_api=args.api,
        data_dir=args.data_dir,
    )
    source_label = "API Grist" if mode == "api" else source_path

    # ── Chargement
    print(f"\n📥  Chargement des données ({mode.upper()})...")
    raw_data = load_data(mode, source_path)

    # ── Construction du modèle
    print(f"\n🔧  Construction du modèle SDID...")
    model = build_model(raw_data, pi_num)

    stats = model["stats"]
    print(f"  → {stats['nb_equipes']} équipes, {stats['nb_epics']} epics, "
          f"{stats['nb_features_pi']} features, {stats['nb_personnes']} personnes")

    # ── Structure org
    structure = build_org_structure(model)
    structure = layout_structure(structure)

    outputs = {}

    # ── draw.io
    print(f"\n🗺️   Génération du diagramme draw.io...")
    drawio_path = generate_drawio(
        structure, pi_num,
        str(output_dir / "orgchart.drawio")
    )
    outputs["draw.io"] = drawio_path

    # ── Analyse fragmentation
    print(f"\n📊  Analyse des multi-affectations...")
    frag_data = compute_fragmentation(model)
    csv_path = export_csv(frag_data, str(output_dir / "multi_affectations.csv"))
    synth_path = export_synthesis_md(frag_data, model, str(output_dir / "synthesis.md"))
    outputs["CSV fragmentation"] = csv_path
    outputs["Synthèse MD"] = synth_path

    # ── PowerPoint
    if not args.skip_pptx:
        print(f"\n📊  Génération du PowerPoint...")
        pptx_path = generate_pptx(
            model, structure, frag_data,
            str(output_dir / f"{pi_num}_Synthese_SDID.pptx")
        )
        outputs["PowerPoint"] = pptx_path
    else:
        print(f"\n⏭️   PowerPoint ignoré (--skip-pptx)")

    # ── README
    print(f"\n📘  Génération du README pédagogique...")
    readme_path = generate_readme(model, str(output_dir / "README_generated.md"))
    outputs["README"] = readme_path

    # ── Run summary
    print(f"\n📋  Génération du run summary...")
    summary_path = generate_run_summary(
        model, source_label, outputs,
        str(output_dir / "run_summary.md")
    )
    outputs["Run Summary"] = summary_path

    print(f"\n✅  Run {pi_num} terminé. Outputs dans : {output_dir}\n")


def run_drawio(args):
    """Génère uniquement le diagramme draw.io."""
    from src.config_checker import resolve_source
    from src.grist_loader import load_data
    from src.model_builder import build_model
    from src.rules import build_org_structure
    from src.layout_engine import layout_structure
    from src.drawio_generator import generate_drawio

    pi_num = normalize_pi(args.pi)
    mode, source_path = resolve_source(args.source, args.api, args.data_dir)

    raw_data = load_data(mode, source_path)
    model = build_model(raw_data, pi_num)
    structure = build_org_structure(model)
    structure = layout_structure(structure)

    Path(args.output).mkdir(parents=True, exist_ok=True)
    generate_drawio(structure, pi_num, str(Path(args.output) / "orgchart.drawio"))


def run_analytics(args):
    """Génère uniquement l'analyse de fragmentation."""
    from src.config_checker import resolve_source
    from src.grist_loader import load_data
    from src.model_builder import build_model
    from src.analytics import compute_fragmentation, export_csv, export_synthesis_md

    pi_num = normalize_pi(args.pi)
    mode, source_path = resolve_source(args.source, args.api, args.data_dir)

    raw_data = load_data(mode, source_path)
    model = build_model(raw_data, pi_num)

    frag_data = compute_fragmentation(model)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    export_csv(frag_data, str(out / "multi_affectations.csv"))
    export_synthesis_md(frag_data, model, str(out / "synthesis.md"))


def run_pptx(args):
    """Génère uniquement le PowerPoint."""
    from src.config_checker import resolve_source
    from src.grist_loader import load_data
    from src.model_builder import build_model
    from src.rules import build_org_structure
    from src.layout_engine import layout_structure
    from src.analytics import compute_fragmentation
    from src.ppt_generator import generate_pptx

    pi_num = normalize_pi(args.pi)
    mode, source_path = resolve_source(args.source, args.api, args.data_dir)

    raw_data = load_data(mode, source_path)
    model = build_model(raw_data, pi_num)
    structure = build_org_structure(model)
    structure = layout_structure(structure)
    frag_data = compute_fragmentation(model)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    generate_pptx(model, structure, frag_data, str(out / f"{pi_num}_Synthese_SDID.pptx"))


def main():
    parser = argparse.ArgumentParser(
        description="grist-org-visualizer – PI Planning SDID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python -m src.cli full-run --pi PI-10
  python -m src.cli full-run --api --pi PI-10
  python -m src.cli full-run --source data/mon.grist --pi PI-10
  python -m src.cli drawio --pi PI-10
  python -m src.cli analytics --pi PI-10
  python -m src.cli pptx --pi PI-10
        """
    )

    # Arguments globaux
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--pi", required=True,
                        help="Numéro du PI (ex: PI-10 ou 10)")
    parent.add_argument("--api", action="store_true",
                        help="Utiliser l'API Grist (nécessite .env configuré)")
    parent.add_argument("--source", default=None,
                        help="Chemin explicite vers un fichier .grist")
    parent.add_argument("--output", default="output",
                        help="Répertoire de sortie (défaut: output/)")
    parent.add_argument("--data-dir", default="data",
                        help="Répertoire pour les fichiers .grist locaux (défaut: data/)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # full-run
    p_full = subparsers.add_parser("full-run", parents=[parent],
                                    help="Run complet (tous les outputs)")
    p_full.add_argument("--skip-pptx", action="store_true",
                        help="Ignorer la génération PowerPoint")

    # drawio
    subparsers.add_parser("drawio", parents=[parent],
                          help="Générer uniquement le diagramme draw.io")

    # analytics
    subparsers.add_parser("analytics", parents=[parent],
                          help="Générer uniquement l'analyse de fragmentation")

    # pptx
    subparsers.add_parser("pptx", parents=[parent],
                          help="Générer uniquement le PowerPoint")

    args = parser.parse_args()

    dispatch = {
        "full-run":  run_full,
        "drawio":    run_drawio,
        "analytics": run_analytics,
        "pptx":      run_pptx,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
