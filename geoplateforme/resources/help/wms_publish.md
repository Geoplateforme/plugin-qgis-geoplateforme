- Description :

Publication de base de données vectorielle en service WMS-VECTOR.

- Paramètres :

| Entrée           | Paramètre          | Description                                                |
|------------------|--------------------|------------------------------------------------------------|
| Identifiant de l'entrepôt    | `DATASTORE`        | Identifiant de l'entrepôt utilisé pour la création de la livraison.  |
| Identifiant de la base de données vectorielle | `STORED_DATA`      | Identifiant de la base de données vectorielle. |
| Nom de la publication | `NAME`      | Nom de la publication. |
| Nom technique de la publication | `LAYER_NAME`      | Nom technique de la publication. |
| Titre de la publication | `TITLE`      | Titre de la publication. |
| Résumé de la publication | `ABSTRACT`      | Résumé de la publication. |
| Mot clé de la publication | `KEYWORDS`      | Mot clé de la publication. |
| JSON pour les relations | `RELATIONS`      | JSON pour les relations. Example : `[{"name" : nom_couche, "style": <chemin fichier .sld de style>, "ftl": <chemin fichier .ftl de style>}]`.  |
| Url attribution | `URL_ATTRIBUTION`      | Url attribution |
| Titre attribution | `URL_TITLE`      | Titre attribution |
| Tags à ajouter | `TAGS`  | List de tags à importer. Format `"clé 1,valeur 1;clé 2,valeur 2;..;clé n,valeur n"` |

- Sorties :

| Sortie                             | Paramètre                           | Description                    |
|------------------------------------|-------------------------------------|--------------------------------|
| Identifiant de la publication | `OFFERING_ID`        | Identifiant de la publication  |

Nom du traitement : `geoplateforme:wms_publish`
