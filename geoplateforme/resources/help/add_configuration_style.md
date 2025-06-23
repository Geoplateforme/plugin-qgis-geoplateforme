- Description :

Ajout d'un fichier de style pour une configuration de service.

Une annexe est créée dans l'entrepôt et est ensuite référencée dans la balise `extra` de la configuration.

- Paramètres :

| Entrée           | Paramètre          | Description                                                |
|------------------|--------------------|------------------------------------------------------------|
| Identifiant de l'entrepôt    | `DATASTORE_ID`        | Identifiant de l'entrepôt  |
| Identifiant de la configuration    | `CONFIGURATION_ID`        | Identifiant de la configuration  |
| Nom du style  | `STYLE_NAME`        | Nom du style|
| Nom du jeu de données  | `DATASET_NAME`        | Nom du jeu de données. |
| Fichier(s) de style  | `STYLE_FILE_PATHS`        | Fichier(s) de style. Valeurs séparées par des , |
| Nom(s) couche  | `LAYER_STYLE_NAMES`        | Nom(s) de couche pour style. Valeurs séparées par des , (optionnel)|

Si les noms de couche sont définis, le nombre de fichiers de style doit être identique au nombre de couche.

- Sorties :

| Sortie                             | Paramètre                           | Description                    |
|------------------------------------|-------------------------------------|--------------------------------|
| Identifiants des annexes créées | `CREATED_ANNEXE_IDS`        | Identifiants des annexes créées. Valeurs séparées par des ,|

Nom du traitement : `geoplateforme:add_configuration_style`
