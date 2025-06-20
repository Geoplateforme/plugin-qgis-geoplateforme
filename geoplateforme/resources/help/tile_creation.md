- Description :

Création de tuiles vectorielles depuis une base de données vectorielles.

- Paramètres :

| Entrée           | Paramètre          | Description                                                |
|------------------|--------------------|------------------------------------------------------------|
| Identifiant de l'entrepôt    | `DATASTORE`        | Identifiant de l'entrepôt utilisé pour la création de la livraison.  |
| Nom des tuiles en sortie | `STORED_DATA_NAME`  | Nom des tuiles en sortie. |
| Identifiant de la base de données vectorielles | `VECTOR_DB_STORED_DATA_ID`      | Identifiant de la base de données vectorielles. |
| Option tippecanoe | `TIPPECANOE_OPTIONS`      | Options tippecanoe. |
| JSON pour la composition | `COMPOSITION`      | JSON pour la composition. Example : `[{"layer" : nom_couche, "table": nom_table, "filter":filter_str, "top_level": "2", "bottom_level": "10"}]`. |
| Niveau bas pour la pyramide | `BOTTOM_LEVEL`      | Niveau bas pour la pyramide, valeur entre 1 et 21 |
| Niveau haut pour la pyramide | `TOP_LEVEL`      | Niveau haut pour la pyramide, valeur entre 1 et 21 |
| Zone de moissonnage | `BBOX`      | Zone de moissonnage (optionnel) |
| Tags à ajouter | `TAGS`  | List de tags à importer. Format `"clé 1,valeur 1;clé 2,valeur 2;..;clé n,valeur n"` |
| Attendre la fin de la génération  ? | `WAIT_FOR_GENERATION` | Option pour attendre la fin de la génération avant de sortir du traitement, permet de vérifier si les tuiles vectorielles ont été correctement générées. (Désactivée par défaut) |

- Sorties :

| Sortie                             | Paramètre                           | Description                    |
|------------------------------------|-------------------------------------|--------------------------------|
| Identifiant des tuiles vectorielles créés | `CREATED_STORED_DATA_ID`        | Identifiant des tuiles vectorielles créés  |
| Identifiant de l'exécution du traitement | `PROCESSING_EXEC_ID`        | Identifiant de l'exécution du traitement  |

Nom du traitement : `geoplateforme:tile_creation`
