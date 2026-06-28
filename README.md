# TallyParser

> TallyParser est un outil modulaire en Python conçu pour extraire, transformer et exporter les données de soumission issues de formulaires Tally.so.  
> Le pipeline est divisé en 3 scripts modulaires et indépendants :

TallyParser transforme les soumissions Tally.so en artefacts exploitables (JSON normalisés, fichiers Excel structurés) via un pipeline modulaire et configurable.

---

## 🚀 Fonctionnalités principales

- **Script 1 — Récupération**  
  Récupère la dernière soumission via l'API Tally.so et sauvegarde le JSON brut localement.

- **Script 2 — Parsing & Normalisation**  
  Télécharge les objets référencés (pièces jointes), normalise la structure JSON par *namespaces* (séparateur `|`), convertit les types basiques selon la configuration et produit des JSON prêts à être consommés par d'autres outils.

- **Script 3 — Export Excel**  
  Exporte les JSON normalisés vers un fichier Excel structuré :
  - Une **feuille** par namespace racine (clé de premier niveau sous `data`).
  - Chaque **sous‑objet** non‑primitif devient un **tableau séparé** dans la feuille parent.
  - Les tableaux sont écrits les uns sous les autres, séparés par des lignes vides configurables.
  - Formatage pilotable depuis `./config/script3.yaml` : police, tailles, couleurs (titres, lignes, bordures), remplissage, bordures horizontales, masquage de la grille, etc.
  - Option **feuille d'index** (activée par défaut) listant tous les tableaux créés.



