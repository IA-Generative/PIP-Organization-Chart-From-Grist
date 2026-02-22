# Analyse des Multi-Affectations – PI-10

## Résumé Global

| Métrique | Valeur |
|----------|--------|
| Équipes | 3 |
| Epics | 4 |
| Features PI | 8 |
| Personnes | 6 |
| Affectations totales | 9 |
| Agents >100% | **1** |
| Agents multi-équipes | **1** |

---

## Agents en Surcharge (>100%)

| Nom | Charge Totale | Équipes | Score Fragmentation |
|-----|--------------|---------|---------------------|
| Bob Dupont | **160.0%** | 2 | 5 |

---

## Agents Multi-Équipes

| Nom | Nb Équipes | Nb Epics | Score Fragmentation |
|-----|-----------|---------|---------------------|
| Bob Dupont | 2 | 3 | 5 |

---

## Top 5 – Score de Fragmentation

> 🔢 Score = nb_équipes + nb_epics + max(0, nb_affectations - 3)

| Rang | Nom | Score | Équipes | Epics | Affectations | Charge |
|------|-----|-------|---------|-------|-------------|--------|
| 1 | Bob Dupont | 🟠 **5** | 2 | 3 | 3 | 160.0% |
| 2 | Claire Lemaire | 🟢 **3** | 1 | 2 | 2 | 90.0% |
| 3 | Alice Martin | 🟢 **2** | 1 | 1 | 1 | 100.0% |
| 4 | David Morin | 🟢 **2** | 1 | 1 | 1 | 100.0% |
| 5 | Eva Girard | 🟢 **2** | 1 | 1 | 1 | 80.0% |

---

## Légende

- 🔴 Score ≥ 8 : fragmentation critique
- 🟠 Score ≥ 5 : fragmentation élevée
- 🟢 Score < 5 : fragmentation normale

*Généré automatiquement par grist-org-visualizer*