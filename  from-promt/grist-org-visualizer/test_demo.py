"""
test_demo.py
------------
Test du pipeline complet avec des données de démonstration.
Simule un document Grist avec 3 équipes, 4 epics, 8 features, 6 personnes.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model_builder import build_model
from src.rules import build_org_structure
from src.layout_engine import layout_structure
from src.drawio_generator import generate_drawio
from src.analytics import compute_fragmentation, export_csv, export_synthesis_md
from src.readme_generator import generate_readme
from src.report_generator import generate_run_summary

# ── Données fictives SDID
RAW_DATA = {
    "equipes": [
        {"id": 1, "Nom": "Team Alpha"},
        {"id": 2, "Nom": "Team Beta"},
        {"id": 3, "Nom": "Team Gamma"},
    ],
    "personnes": [
        {"id": 10, "Nom": "Alice Martin"},
        {"id": 11, "Nom": "Bob Dupont"},
        {"id": 12, "Nom": "Claire Lemaire"},
        {"id": 13, "Nom": "David Morin"},
        {"id": 14, "Nom": "Eva Girard"},
        {"id": 15, "Nom": "François Bernard"},
    ],
    "epics": [
        {
            "id": 100, "Nom": "Epic Paiement Digital",
            "Description_EPIC": "Modernisation du système de paiement",
            "Intention_du_PI_en_cours": "Livrer le socle API paiement v2",
            "Intention_du_prochain_Increment_ou_MVP_impact_a_3_mois_": "MVP paiement mobile opérationnel",
        },
        {
            "id": 101, "Nom": "Epic Onboarding Client",
            "Description_EPIC": "Simplification du parcours d'inscription",
            "Intention_du_PI_en_cours": "Réduire le temps d'onboarding de 30%",
            "Intention_du_prochain_Increment_ou_MVP_impact_a_3_mois_": "Nouveau flow KYC automatisé",
        },
        {
            "id": 102, "Nom": "Epic Reporting Analytics",
            "Description_EPIC": "Tableaux de bord décisionnels",
            "Intention_du_PI_en_cours": "Déployer 5 KPIs critiques",
            "Intention_du_prochain_Increment_ou_MVP_impact_a_3_mois_": "Dashboard self-service métier",
        },
        {
            "id": 103, "Nom": "Epic Sécurité & Conformité",
            "Description_EPIC": "Mise en conformité RGPD et ISO 27001",
            "Intention_du_PI_en_cours": "Audit sécurité complet",
            "Intention_du_prochain_Increment_ou_MVP_impact_a_3_mois_": "Certification ISO 27001",
        },
    ],
    "features": [
        {"id": 200, "Epic": 100, "Nom": "API Paiement v2", "Description": "", "pi_Num": "PI-10"},
        {"id": 201, "Epic": 100, "Nom": "Wallet Mobile", "Description": "", "pi_Num": "PI-10"},
        {"id": 202, "Epic": 101, "Nom": "Flow KYC Auto", "Description": "", "pi_Num": "PI-10"},
        {"id": 203, "Epic": 101, "Nom": "Portail Client SSO", "Description": "", "pi_Num": "PI-10"},
        {"id": 204, "Epic": 102, "Nom": "Dashboard KPIs", "Description": "", "pi_Num": "PI-10"},
        {"id": 205, "Epic": 102, "Nom": "Export BI", "Description": "", "pi_Num": "PI-10"},
        {"id": 206, "Epic": 103, "Nom": "Audit RGPD", "Description": "", "pi_Num": "PI-10"},
        {"id": 207, "Epic": 103, "Nom": "Pentest Infra", "Description": "", "pi_Num": "PI-10"},
    ],
    "affectations": [
        # Team Alpha → Epic Paiement
        {"Affecte_a_l_equipe": 1, "Affecte_a_l_Epic": 100, "Personne": 10, "Charge": 100, "Role": "PM"},
        {"Affecte_a_l_equipe": 1, "Affecte_a_l_Epic": 100, "Personne": 11, "Charge": 80,  "Role": "PO"},
        {"Affecte_a_l_equipe": 1, "Affecte_a_l_Epic": 100, "Personne": 12, "Charge": 60,  "Role": "DEV"},
        # Team Beta → Epic Onboarding
        {"Affecte_a_l_equipe": 2, "Affecte_a_l_Epic": 101, "Personne": 13, "Charge": 100, "Role": "PM"},
        {"Affecte_a_l_equipe": 2, "Affecte_a_l_Epic": 101, "Personne": 14, "Charge": 80,  "Role": "PO"},
        # Team Gamma → Epic Reporting
        {"Affecte_a_l_equipe": 3, "Affecte_a_l_Epic": 102, "Personne": 15, "Charge": 100, "Role": "PM"},
        {"Affecte_a_l_equipe": 3, "Affecte_a_l_Epic": 102, "Personne": 11, "Charge": 40,  "Role": "PO"},
        # Multi-affectation : Bob aussi sur Team Gamma + Sécurité (surcharge)
        {"Affecte_a_l_equipe": 3, "Affecte_a_l_Epic": 103, "Personne": 11, "Charge": 40,  "Role": "PO"},
        # Epic Sécurité hors équipe (séparée car PO=Bob dans team alpha et gamma)
        {"Affecte_a_l_equipe": 1, "Affecte_a_l_Epic": 103, "Personne": 12, "Charge": 30,  "Role": "DEV"},
    ],
}


def main():
    PI_NUM = "PI-10"
    OUT_DIR = "output"

    print(f"\n{'='*60}")
    print(f"  TEST DEMO – {PI_NUM}")
    print(f"{'='*60}\n")

    # Build model
    print("🔧  Construction du modèle...")
    model = build_model(RAW_DATA, PI_NUM)
    stats = model["stats"]
    print(f"  → {stats['nb_equipes']} équipes, {stats['nb_epics']} epics")
    print(f"  → {stats['nb_features_pi']} features, {stats['nb_personnes']} personnes")
    print(f"  → {len(model['epics_separees'])} epic(s) séparée(s)")
    print(f"  → {stats['nb_agents_surcharges']} agent(s) >100%")
    print(f"  → {stats['nb_agents_multi_equipes']} agent(s) multi-équipes")

    # Org structure
    structure = build_org_structure(model)
    structure = layout_structure(structure)

    # draw.io
    print("\n🗺️   Génération draw.io...")
    generate_drawio(structure, PI_NUM, f"{OUT_DIR}/orgchart.drawio")

    # Analytics
    print("\n📊  Analyse fragmentation...")
    frag = compute_fragmentation(model)
    csv_path = export_csv(frag, f"{OUT_DIR}/multi_affectations.csv")
    synth_path = export_synthesis_md(frag, model, f"{OUT_DIR}/synthesis.md")

    # README
    print("\n📘  Génération README...")
    readme_path = generate_readme(model, f"{OUT_DIR}/README_generated.md")

    # Summary
    print("\n📋  Run summary...")
    outputs = {
        "draw.io":            f"{OUT_DIR}/orgchart.drawio",
        "CSV fragmentation":  csv_path,
        "Synthèse MD":        synth_path,
        "README":             readme_path,
    }
    generate_run_summary(model, "demo (données fictives)", outputs, f"{OUT_DIR}/run_summary.md")

    print(f"\n✅  Test démo terminé. Outputs dans : {OUT_DIR}/\n")


if __name__ == "__main__":
    main()
