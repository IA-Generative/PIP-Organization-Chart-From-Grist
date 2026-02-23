# grist-org-visualizer

Génère automatiquement (à partir d’un Grist SDID) :

- une **visualisation draw.io** : **Équipes → Epics → Features** (+ cartouche PI)
- une **analyse de fragmentation** : agents multi-affectés / multi-contextes
- un **PowerPoint de synthèse** PI Planning (basé sur template, avec slides de cadrage puis groupes par équipe)
- un **Excel de synthèse des EPICs** (résumés + couverture intention/features + propositions de nouvelles features)
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

Pour les jeux de données réels/sensibles, utilisez plutôt un dossier non versionné (ex: `local-no-upload/`) :

```zsh
python -m src.cli full-run --source "local-no-upload/🏗️Gestion PI SDID (15).grist" --pi PI-6
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
- optionnel : `SCW_LLM_MODEL` (défaut `mistral-small-3.2-24b-instruct-2506`) et `SCW_LLM_BASE_URL`
- activer explicitement avec le flag `--llm` (sinon fallback local forcé)
- sans clé ou en cas d'erreur API, le script utilise un fallback local

Si les paramètres API ne sont pas configurés, le script bascule en mode fichier local et vous indiquera quoi faire.

### 3) Générer uniquement le PowerPoint

Mode fichier local :

```zsh
python -m src.cli ppt --source data/example_empty.grist --pi PI-6
```

Mode fichier local + LLM :

```zsh
python -m src.cli ppt --llm --source data/example_empty.grist --pi PI-6
```

Mode API (avec fallback automatique sur fichier local si API indisponible) :

```zsh
python -m src.cli ppt --api --pi PI-6
```

Mode API + LLM :

```zsh
python -m src.cli ppt --llm --api --pi PI-6
```

## Sorties

Dans `output/` :

- `PI-<X>_orgchart.drawio`
- `PI-<X>_multi_affectations.csv`
- `PI-<X>_<YYMMDD-HHMM>_synthesis.md`
- `PI-<X>_Synthese_SDID.pptx`
- `PI-<X>_Synthese_Epics.xlsx`
- `PI-<X>_<YYMMDD-HHMM>_README_generated.md`
- `PI-<X>_<YYMMDD-HHMM>_run_summary.md`

Le fichier Excel contient 2 onglets :
- `Synthese_Epics` : identifiant EPIC, titre, description/intention originales, synthèse courte, évaluation de couverture des features.
- `Propositions_Features` : propositions de nouvelles features avec gains espérés.
- Les textes reformulés par IA sont suffixés avec `(🤖)`.

## PowerPoint (template)

- Le générateur PPT utilise `data/template.ppt.pptx`.
- Le fichier généré est `output/PI-<X>_Synthese_SDID.pptx`.
- Structure actuelle du template :
  - Planche 1 : titre général
  - Planche 2 : vue d’ensemble PI (infos + stats + population d’agents)
  - Planche 3 : agents avec fragmentation d’affectation
  - Planche 4 : agents avec faible affectation (`<10%`)
  - Puis, par équipe :
    - Équipe
    - Finalités et ambition du PIP (découpage automatique en `x/total` si texte long)
    - Features
- Le nombre de planches par équipe est donc **dynamique** :
  - si le contenu Finalités/Ambition est long, des planches supplémentaires sont créées.
  - sur les planches suivantes, si `Finalités` est vide, le bloc `Ambition du PIP` est remonté en haut.
- La planche **Équipe** inclut un tableau : `Membre | Qualité | Affectation %` (lignes à `0.0%` filtrées).
- La planche **Fragmentation** inclut un tableau : `Agent | Equipes | Epics | Affect. | Charge % | Score`.
- Mise en forme appliquée par le générateur :
  - police `Marianne`
  - retour à la ligne automatique (`word wrap`)
  - ajustement automatique du texte à la zone (`text-to-fit`)
  - limitation des indentations pour exploiter toute la largeur des blocs du template
  - titres de planches en capitales
- En fin de génération `ppt` / `full-run`, le fichier `.pptx` est ouvert automatiquement si une application compatible est disponible.

## Logique métier

- **PM** : affichés au niveau **Équipe** (container).
- **PO** : affichés sur les **Epics séparées**.
- **Epic séparée** : si les personnes affectées à l’Epic ne sont pas un sous-ensemble des personnes de l’équipe (`people_epic ⊄ people_team`).

### Règles Draw.io (actuelles)

- Bloc **Affecté sur plusieurs EPICS** : personne affichée si `Nb_Epics >= 3` ou `Nb_Equipes >= 2`.
- Bloc **Affecté sur plusieurs EPICS** : chaque ligne inclut le nombre d’EPICs de la personne (`[n EPICS]`).
- Bloc **Sans affectation ou total < 25%** : inclut les personnes sans affectation et celles dont la charge totale est `< 25%`.
- Blocs **Équipe** (PM/PO/Membres) : les acteurs avec charge `= 0` ne sont pas affichés.
- Lignes d’affectation dans les blocs EPIC : les charges `< 10%` sont rendues en gris sombre.
- **Epics séparées** : ajout d’un sous-titre bleu **Intention prochain PI** avec un résumé description+intentions (moins de 5 lignes).

## Commandes

- Pipeline complet : `full-run`
- Diagramme seul : `diagram`
- Analyse seule : `analyze`
- PPT seul : `ppt` (`--source` ou `--api`)
- Excel seul : `excel` (`--source` ou `--api`)
- Le flag `--llm` est disponible sur `full-run`, `diagram`, `ppt` et `excel`.
- Variables utiles de parallélisme LLM :
  - `LLM_SYNTH_MAX_WORKERS` (synthèse équipe pour Draw.io/PPT, défaut `32`, plafond `256`)
  - `LLM_PPT_MAX_WORKERS` (reformulation PPT, défaut `16`, plafond `256`)
  - `EXCEL_LLM_MAX_WORKERS` (analyse EPICs pour Excel, défaut `32`, plafond `256`)
- Modèle LLM Excel :
  - `EXCEL_LLM_MODEL` (défaut `ossgpt`)

## Statut LLM

- Au démarrage, le CLI affiche l'état LLM :
  - `🤖 LLM Synthèse/Draw.io: actif|inactif (...)`
  - `🤖 LLM PPT: actif|inactif (...)`
- Sans `--llm`, les appels LLM sont désactivés (`fallback` local).
- Le mode de logs se règle avec `--llm-log` (`quiet|compact|verbose`).
- Pour diagnostiquer finement les réponses LLM, activer ponctuellement `LLM_DEBUG=1`.

Voir `python -m src.cli --help`.

## Évolutions possibles

- Export PNG automatique du `.drawio` via diagrams.net CLI
- Styles avancés (couleurs par équipe, icônes par rôle)
- Détection fine de transversalité (seuils, exceptions)
