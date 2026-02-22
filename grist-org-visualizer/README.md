# grist-org-visualizer

> **Outil de visualisation PI Planning SDID**  
> Grist → draw.io + Analyse fragmentation + PowerPoint + Rapports

---

## 🚀 Démarrage rapide

```bash
# 1. Installer les dépendances Python
pip install -e .

# 2. (Optionnel) Configurer l'API Grist
cp config/example.env .env
# Éditer .env avec vos clés

# 3. Lancer le run complet
python -m src.cli full-run --pi PI-10
```

---

## 📋 Prérequis

| Outil | Usage | Requis |
|-------|-------|--------|
| Python 3.9+ | Moteur principal | ✅ |
| Node.js 18+ | Génération PowerPoint (pptxgenjs) | ⚠️ Optionnel |
| Compte Grist | Mode API | ⚠️ Optionnel |

---

## 🔐 Configuration API Grist

Copiez `config/example.env` en `.env` et renseignez :

```env
GRIST_API_KEY=votre_cle_api
GRIST_DOC_ID=votre_doc_id
GRIST_BASE_URL=https://docs.getgrist.com  # optionnel
```

> **Si l'API n'est pas configurée**, l'outil bascule automatiquement sur un fichier `.grist` local dans `data/`.

---

## 📂 Modes de fonctionnement

### Mode API
```bash
python -m src.cli full-run --api --pi PI-10
```

### Mode fichier local automatique
```bash
# Déposer votre fichier dans data/mon_doc.grist
python -m src.cli full-run --pi PI-10
```

### Mode fichier explicite
```bash
python -m src.cli full-run --source chemin/vers/fichier.grist --pi PI-10
```

**Priorité de résolution** : `--source` > `--api` > fallback `data/`

---

## 📊 Modèle Grist attendu

### Tables

| Table | Description |
|-------|-------------|
| `Equipes` | Features teams |
| `Personnes` | Membres (PM, PO, DEV) |
| `Epics` | Epics métier |
| `Features` | Features rattachées aux Epics |
| `Affectations` | Liens Personne ↔ Équipe ↔ Epic |

### Colonnes clés

**Affectations** :
```
Affecte_a_l_equipe  →  ID équipe
Affecte_a_l_Epic    →  ID epic
Personne            →  ID personne
Charge              →  % de charge (ex: 50)
Role                →  PM / PO / DEV
```

**Epics** :
```
Nom
Description_EPIC
Intention_du_PI_en_cours
Intention_du_prochain_Increment_ou_MVP_impact_a_3_mois_
```

**Features** :
```
Epic      →  ID epic parente
Nom
Description
pi_Num    →  ex: PI-10
```

---

## 🗺️ Visualisation draw.io

Le fichier `output/orgchart.drawio` peut être ouvert sur [diagrams.net](https://diagrams.net).

**Structure** :
```
[Cartouche] PI Planning SDID – PI-10

[Équipe A]
  PM: Alice
  [Epic 1]
    PO: Bob
    ⚡ Feature X
    ⚡ Feature Y

[⚠️ EPIC SÉPARÉE]   ← Epic dont les membres ⊄ équipe principale
  PO: Charlie
  ⚡ Feature Z
```

---

## 📉 Score de Fragmentation

Mesure la dispersion d'un agent :

```
score = nb_équipes + nb_epics + max(0, nb_affectations - 3)
```

| Score | Niveau |
|-------|--------|
| < 5   | 🟢 Normal |
| 5–7   | 🟠 Élevé |
| ≥ 8   | 🔴 Critique |

---

## 🖥️ Commandes disponibles

```bash
# Run complet
python -m src.cli full-run --pi PI-10

# draw.io uniquement
python -m src.cli drawio --pi PI-10

# Analyse fragmentation uniquement
python -m src.cli analytics --pi PI-10

# PowerPoint uniquement (nécessite Node.js)
python -m src.cli pptx --pi PI-10

# Aide
python -m src.cli --help
python -m src.cli full-run --help
```

**Options globales** :
```
--pi         Numéro du PI (ex: PI-10 ou 10)          [requis]
--api        Forcer le mode API Grist
--source     Chemin explicite vers un .grist
--output     Répertoire de sortie (défaut: output/)
--data-dir   Répertoire des fichiers locaux (défaut: data/)
--skip-pptx  Ignorer la génération PowerPoint
```

---

## 📁 Fichiers produits

```
output/
├── orgchart.drawio              # Visualisation draw.io
├── multi_affectations.csv       # Scores de fragmentation
├── synthesis.md                 # Analyse narrative
├── PI-10_Synthese_SDID.pptx    # PowerPoint de revue
├── README_generated.md          # Rapport contextuel
└── run_summary.md               # Checklist de fin de run
```

---

## 🏗️ Structure du projet

```
grist-org-visualizer/
├── README.md
├── pyproject.toml
├── config/
│   ├── mapping.yml          # Mapping tables/colonnes
│   └── example.env          # Template configuration
├── data/
│   └── example_empty.grist  # Placeholder (déposer votre .grist ici)
├── output/                  # Fichiers générés
└── src/
    ├── cli.py               # Entrée CLI
    ├── config_checker.py    # Vérification API + fallback
    ├── api_client.py        # Client HTTP Grist
    ├── grist_loader.py      # Chargement API ou fichier
    ├── model_builder.py     # Construction du modèle
    ├── rules.py             # Règles métier SDID
    ├── layout_engine.py     # Calcul positions draw.io
    ├── drawio_generator.py  # Export XML draw.io
    ├── analytics.py         # Analyse fragmentation
    ├── ppt_generator.py     # Génération PowerPoint
    ├── readme_generator.py  # Génération README
    └── report_generator.py  # Run summary
```

---

## 🤖 Compatibilité CI

En environnement CI (GitHub Actions, GitLab CI...) :

```yaml
# .github/workflows/pi-planning.yml
- name: Run PI Planning
  env:
    GRIST_API_KEY: ${{ secrets.GRIST_API_KEY }}
    GRIST_DOC_ID: ${{ secrets.GRIST_DOC_ID }}
  run: |
    pip install -e .
    python -m src.cli full-run --api --pi PI-10 --skip-pptx
```

---

## 🔧 Personnalisation

Modifiez `config/mapping.yml` si vos noms de tables ou colonnes diffèrent :

```yaml
tables:
  equipes: MesEquipes        # nom personnalisé
  affectations: Assignments  # etc.

columns:
  affectations:
    equipe: team_id
    charge: workload_percent
```

---

*grist-org-visualizer v1.0 – Compatible Python 3.9+*
