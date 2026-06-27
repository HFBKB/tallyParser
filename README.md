# TallyParser

TallyParser est un outil modulaire en Python conçu pour extraire, transformer et exporter les données de soumission issues de formulaires [Tally.so](https://tally.so).

> Le pipeline est divisé en 3 scripts modulaires et indépendants :  
> Script 1 : Récupération de la dernière soumission via l'API Tally.so.  
> Script 2 : Parsing et formatage du JSON par namespaces (version stable — sans téléchargement de fichiers).  
> Script 3 : Génération d'un fichier Excel structuré avec une feuille par namespace de premier niveau (à venir).

---

## 🚀 Fonctionnalités (version stable)

- **Script 1** : récupère et sauvegarde la soumission brute depuis l'API Tally.so (déjà consolidé).  
- **Script 2** : normalise le JSON brut en une structure imbriquée par *namespaces* (séparateur `|`), convertit les types basiques selon la configuration et écrit des JSON exploitables par Python. **Cette version ne télécharge ni ne modifie les URLs des fichiers**.  
- **Script 3** : (à venir) export Excel avec une feuille par namespace racine.

---