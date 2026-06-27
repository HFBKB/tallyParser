# TallyParser

TallyParser est un outil modulaire en Python conçu pour extraire, transformer et exporter les données de soumission issues de formulaires [Tally.so](https://tally.so).

## 🚀 Fonctionnalités

Le pipeline est divisé en 3 scripts modulaires et indépendants :
- **Script 1** : Récupération de la dernière soumission via l'API Tally.so.
- **Script 2** : *(À venir)* Parsing et formatage du JSON par namespaces.
- **Script 3** : *(À venir)* Génération d'un fichier Excel structuré avec une feuille par namespace de premier niveau.

## 📁 Architecture

```text
tallyParser/
├── .gitignore
├── README.md
├── config/
│   └── script1.yaml        # Configuration propre à chaque script
├── data/
│   └── raw_submission.json # Données brutes (ignoré par Git)
└── script1_fetch_tally.py  # Scripts d'exécution
```

## 🛠️ Prérequis

- Python 3.8+
- Un environnement virtuel (recommandé) sous VSCode

## ⚙️ Installation

1. Cloner le dépôt :
   ```bash
   git clone <ton_url_git>
   cd tallyParser
   ```

2. Créer et activer l'environnement virtuel :
   ```bash
   # Sous Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate

   # Sous Windows
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Installer les dépendances :
   ```bash
   pip install requests pyyaml
   ```

## 🔑 Configuration

Chaque script utilise un fichier de configuration `.yaml` dédié situé dans le dossier `config/`. 
*Note : Le dossier `config/` est ignoré par Git pour ne pas versionner les clés API.*

Exemple pour `config/script1.yaml` :
```yaml
tally:
  api_key: "TA_CLE_API"
  form_id: "TON_FORM_ID"

output:
  file_path: "data/raw_submission.json"
```

## 🚀 Utilisation

Pour lancer la récupération des données :
```bash
python script1_fetch_tally.py
```
Les données brutes seront sauvegardées dans `data/raw_submission.json`.