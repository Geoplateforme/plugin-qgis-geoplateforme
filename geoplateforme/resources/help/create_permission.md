- Description :

Création d'une permission dans l'entrepôt.

Cette permission pourra ensuite être associée à une clé d'un utilisateur pour permettre l'accès à des services privées.

- Paramètres :

| Entrée           | Paramètre          | Description                                                |
|------------------|--------------------|------------------------------------------------------------|
| Identifiant de l'entrepôt    | `DATASTORE`        | Identifiant de l'entrepôt utilisé.  |
| Nom de la permission  | `LICENCE`        | Nom de la permission. |
| Type de permission  | `PERMISSION_TYPE`        | Type de permission. Valeurs possibles : "ACCOUNT", "COMMUNITY"|

| Identifiants des offres  | `OFFERINGS`        | Identifiants des offres. Valeurs séparées par des virgules (,) |
| Identifiants des utilisateurs ou communautés  | `USER_OR_COMMUNITIES`        | Identifiants des utilisateurs ou communautés. Valeurs séparées par des virgules (,) |
| Date de fin de la permission | `END_DATE`        | Date de fin de la permission (Optionnel). |
| Authentification forte  | `ONLY_OAUTH`        | Authentification forte (compatible uniquement avec clé OAUTH). |

- Sorties :

| Sortie                             | Paramètre                           | Description                    |
|------------------------------------|-------------------------------------|--------------------------------|
| Identifiants des permissions créés | `CREATED_PERMISSIONS_ID`        | Identifiants des permissions créés  |

Nom du traitement : `geoplateforme:create_permission`
