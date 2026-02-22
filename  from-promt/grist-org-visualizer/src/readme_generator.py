"""
readme_generator.py
-------------------
Génère un README pédagogique adapté au contexte du run actuel.
"""

from pathlib import Path


def generate_readme(model: dict, output_path: str) -> str:
    """Génère le README_generated.md dans le répertoire output."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pi_num = model["pi_num"]
    stats = model["stats"]

    content = f"""# Rapport grist-org-visualizer – {pi_num}

> Généré automatiquement. Ce fichier décrit les données, la structure et les résultats de l'analyse.

---

## 1. Qu'est-ce que cet outil ?

**grist-org-visualizer** permet de :
- Lire un document Grist (via API ou fichier local)
- Générer une visualisation draw.io de l'organisation PI Planning
- Analyser les multi-affectations et la fragmentation des agents
- Produire un PowerPoint de synthèse pour les revues PI
- Exporter des rapports structurés

---

## 2. Modèle de données Grist

L'outil attend les tables suivantes dans votre document Grist :

| Table | Description |
|-------|-------------|
| `Equipes` | Les équipes Agile (features teams) |
| `Personnes` | Les membres (PM, PO, développeurs) |
| `Epics` | Les Epics métier |
| `Features` | Les Features rattachées aux Epics |
| `Affectations` | Les liens Personne ↔ Équipe ↔ Epic avec charge et rôle |

### Colonnes clés

**Affectations** :
- `Affecte_a_l_equipe` – ID de l'équipe
- `Affecte_a_l_Epic` – ID de l'Epic
- `Personne` – ID de la personne
- `Charge` – pourcentage de charge (ex: 50 pour 50%)
- `Role` – PM / PO / DEV

**Epics** :
- `Nom`, `Description_EPIC`
- `Intention_du_PI_en_cours` – ambition PI
- `Intention_du_prochain_Increment_ou_MVP_impact_a_3_mois_` – ambition MVP

**Features** :
- `Epic` – ID de l'epic parente
- `Nom`, `Description`, `pi_Num` – numéro du PI

---

## 3. Modes d'utilisation

### Mode API (connexion directe à Grist)

```bash
# Configurer les variables d'environnement
cp config/example.env .env
# Éditer .env avec vos valeurs GRIST_API_KEY et GRIST_DOC_ID

python -m src.cli full-run --api --pi PI-10
```

### Mode fichier local

```bash
# Déposer votre fichier dans data/
python -m src.cli full-run --pi PI-10

# OU chemin explicite
python -m src.cli full-run --source data/mon_doc.grist --pi PI-10
```

### Priorité de résolution de la source :
1. `--source` (explicite)
2. `--api` (si variables définies)
3. Fichier `.grist` dans `data/` (fallback automatique)

---

## 4. Détection des Epics Séparées

Une Epic est dite **séparée** lorsque ses membres (PO, DEV) **ne font pas partie** de l'équipe principale à laquelle elle est rattachée.

Formellement : `people_epic ⊄ people_team`

Dans draw.io, ces epics apparaissent **en orange** avec le label ⚠️ EPIC SÉPARÉE.

---

## 5. Score de Fragmentation

Le score mesure la dispersion d'un agent entre les projets :

```
fragmentation_score = nb_équipes + nb_epics + max(0, nb_affectations - 3)
```

| Score | Niveau |
|-------|--------|
| < 5   | 🟢 Normal |
| 5–7   | 🟠 Élevé |
| ≥ 8   | 🔴 Critique |

---

## 6. Données du run {pi_num}

| Métrique | Valeur |
|----------|--------|
| Équipes | {stats['nb_equipes']} |
| Epics | {stats['nb_epics']} |
| Epics séparées | {len(model['epics_separees'])} |
| Features PI | {stats['nb_features_pi']} |
| Personnes | {stats['nb_personnes']} |
| Affectations | {stats['nb_affectations']} |
| Agents >100% | **{stats['nb_agents_surcharges']}** |
| Agents multi-équipes | **{stats['nb_agents_multi_equipes']}** |

---

## 7. Fichiers produits

| Fichier | Description |
|---------|-------------|
| `output/orgchart.drawio` | Visualisation draw.io ouvrable sur diagrams.net |
| `output/multi_affectations.csv` | Tableur des scores de fragmentation |
| `output/synthesis.md` | Analyse narrative des multi-affectations |
| `output/{pi_num}_Synthese_SDID.pptx` | PowerPoint de revue PI |
| `output/README_generated.md` | Ce fichier |
| `output/run_summary.md` | Checklist de fin de run |

---

## 8. Commandes CLI complètes

```bash
# Run complet (tous les outputs)
python -m src.cli full-run --pi PI-10

# Draw.io seulement
python -m src.cli drawio --pi PI-10

# Analyse fragmentation seulement
python -m src.cli analytics --pi PI-10

# PowerPoint seulement
python -m src.cli pptx --pi PI-10

# Afficher l'aide
python -m src.cli --help
```

---

*grist-org-visualizer – outil de visualisation PI Planning SDID*
"""

    out.write_text(content, encoding="utf-8")
    print(f"  ✅  README généré : {out}")
    return str(out)
