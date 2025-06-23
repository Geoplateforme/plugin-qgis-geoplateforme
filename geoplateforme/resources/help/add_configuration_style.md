- Description :

Ajout d'un fichier de style pour une configuration de service.

Une annexe est créée dans l'entrepôt et est ensuite référencée dans la balise `extra` de la configuration.

- Paramètres :

| Entrée           | Paramètre          | Description                                                |
|------------------|--------------------|------------------------------------------------------------|
| Identifiant de l'entrepôt    | `DATASTORE_ID`        | Identifiant de l'entrepôt  |
| Identifiant de la configuration    | `CONFIGURATION_ID`        | Identifiant de la configuration  |
| Fichier de style  | `STYLE_FILE_PATH`        | Fichier de style |
| Nom du style  | `STYLE_NAME`        | Nom du style|
| Nom du jeu de données  | `DATASET_NAME`        | Nom du jeu de données. |

- Sorties :

| Sortie                             | Paramètre                           | Description                    |
|------------------------------------|-------------------------------------|--------------------------------|
| Identifiant de l'annexe créée | `CREATED_ANNEXE_ID`        | Identifiant de l'annexe créée. |

Nom du traitement : `geoplateforme:add_configuration_style`
