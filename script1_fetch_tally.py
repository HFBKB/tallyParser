import os
import yaml
import json
import requests

def load_config(config_path):
    """Charge les paramètres depuis le fichier YAML dédié."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def fetch_latest_submission(api_key, form_id):
    """
    Récupère la dernière soumission d'un formulaire via l'API Tally.
    """
    url = f"https://api.tally.so/forms/{form_id}/submissions?limit=1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"Requête vers Tally.so pour le formulaire : {form_id}...")
    response = requests.get(url, headers=headers)
    
    response.raise_for_status() 
    return response.json()

def save_json(data, file_path):
    """Sauvegarde le dictionnaire python en fichier JSON."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Données sauvegardées avec succès dans : {file_path}")

def main():
    config_path = os.path.join("config", "script1.yaml")

    try:
        config = load_config(config_path)
        api_key = config['tally']['api_key']
        form_id = config['tally']['form_id']
        output_path = config['output']['file_path']

        # 1. Récupération des données
        data = fetch_latest_submission(api_key, form_id)

        # Vérification sur la bonne clé 'submissions'
        if not data.get('submissions') or len(data['submissions']) == 0:
            print("Aucune soumission trouvée pour ce formulaire.")
            return

        # 2. Sauvegarde pour le Script 2
        save_json(data, output_path)

    except FileNotFoundError:
        print(f"Erreur : Le fichier de configuration '{config_path}' est introuvable.")
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la communication avec l'API Tally : {e}")
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")

if __name__ == "__main__":
    main()