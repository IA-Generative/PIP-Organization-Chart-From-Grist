# grist-org-visualizer

Génère automatiquement (à partir d’un Grist SDID) :

- une **visualisation draw.io** : **Équipes → Epics → Features** (+ cartouche PI)
- une **analyse de fragmentation** : agents multi-affectés / multi-contextes
- un **PowerPoint de synthèse** PI Planning (planche de synthèse + slides équipes/epics)
- un **README généré** contextualisé pour le PI

## Prérequis

- Python 3.10+
- Dépendances : `pandas`, `python-pptx`, `requests`

Installation rapide :

```zsh
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### Utilisateurs Conda

Si vous êtes dans l'environnement `base` de Conda, vous pouvez voir des conflits de dépendances.
Recommandation : utiliser un environnement virtuel dédié au projet.

```zsh
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

## Utilisation

### 1) Mode fichier local (recommandé)
Déposez un fichier `.grist` dans `data/` (exemple fourni : `data/example_empty.grist`) ou pointez-le avec `--source`.

```zsh
python -m src.cli full-run --source data/example_empty.grist --pi PI-10
```

### 2) Mode API Grist (optionnel)
Configurer les variables :

- `GRIST_API_KEY`
- `GRIST_DOC_ID`
- (optionnel) `GRIST_BASE_URL` (défaut: https://grist.numerique.gouv.fr/)

Vous pouvez utiliser le script interactif :

```zsh
chmod +x scripts/setup_grist_env.sh
./scripts/setup_grist_env.sh
```

Sur macOS (shell par défaut `zsh`), rechargez le profil :

```zsh
source ~/.zshrc
```

Puis lancez :

```zsh
python -m src.cli full-run --api --pi PI-10
```

Option mission d'equipe par LLM (Scaleway) :
- définir `SCW_SECRET_KEY_LLM` dans l'environnement
- optionnel : `SCW_LLM_MODEL` (défaut `gpt-oss-120b`) et `SCW_LLM_BASE_URL`
- sans clé ou en cas d'erreur API, le script utilise un fallback local

Si les paramètres API ne sont pas configurés, le script bascule en mode fichier local et vous indiquera quoi faire.

## Sorties

Dans `output/` :

- `orgchart.drawio`
- `multi_affectations.csv`
- `synthesis.md`
- `PI-<X>_Synthese_SDID.pptx`
- `README_generated.md`
- `run_summary.md`

## Logique métier

- **PM** : affichés au niveau **Équipe** (container).
- **PO** : affichés sur les **Epics séparées**.
- **Epic séparée** : si les personnes affectées à l’Epic ne sont pas un sous-ensemble des personnes de l’équipe (`people_epic ⊄ people_team`).

## Commandes

- Pipeline complet : `full-run`
- Diagramme seul : `diagram`
- Analyse seule : `analyze`
- PPT seul : `ppt`

Voir `python -m src.cli --help`.

## Évolutions possibles

- Export PNG automatique du `.drawio` via diagrams.net CLI
- Styles avancés (couleurs par équipe, icônes par rôle)
- Détection fine de transversalité (seuils, exceptions)
