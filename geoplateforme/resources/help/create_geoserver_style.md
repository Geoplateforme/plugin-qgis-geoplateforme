- Description :

Ajout d'un fichier de style .sld en tant que fichier static GEOSERVER-STYLE dans l'entrepôt.

- Paramètres :

| Entrée           | Paramètre          | Description                                                |
|------------------|--------------------|------------------------------------------------------------|
| Identifiant de l'entrepôt    | `DATASTORE`        | Identifiant de l'entrepôt utilisé pour la création de la donnée statique.  |
| Chemin vers le fichier .sld à ajouter    | `FILE_PATH`        | Chemin vers le fichier .sld à ajouter. (support uniquement du format 1.0.0) |
| Nom de la donnée statique    | `NAME`        | Nom de la donnée statique |
| Description    | `DESCRIPTION`        | Description de la donnée statique (optionnel) |

- Sorties :

| Sortie                             | Paramètre                           | Description                    |
|------------------------------------|-------------------------------------|--------------------------------|
| Identifiant de la donnée statique crée | `ID_STATIC`        | Identifiant de la donnée statique crée  |

Attention, seuls les fichiers .sld au format 1.0.0 sont actuellement supportés par la Géoplateforme.

Nom du traitement : `geoplateforme:create_geoserver_style`
