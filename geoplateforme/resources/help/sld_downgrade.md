- Description :

Mise à jour fichier .sld pour passer d'une version 1.1.0 à 1.0.0.

- Paramètres :

| Entrée           | Paramètre          | Description                                                |
|------------------|--------------------|------------------------------------------------------------|
| Fichier en entrée    | `FILE_PATH`        | Fichier .sld en entrée, au format 1.1.0.  |
| Vérification du format .sld 1.1.0 en entrée    | `CHECK_INPUT`        | Option pour ajouter une vérification du fichier en entrée. S'il n'est pas compatible avec la version 1.1.0, le traitement est arreté. |
| Vérification du format .sld 1.0.0 en sortie    | `CHECK_OUTPUT`        | Option pour ajouter une vérification du fichier en sortie. S'il n'est pas compatible avec la version 1.0.0, le traitement est arreté. |

- Sorties :

| Sortie                             | Paramètre                           | Description                    |
|------------------------------------|-------------------------------------|--------------------------------|
| Fichier en sortie | `OUTPUT`        | Fichier .sld converti au format 1.0.0  |

Nom du traitement : `geoplateforme:sld_downgrade`
