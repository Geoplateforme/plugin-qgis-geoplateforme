# Guide d'utilisation

L'extension Géoplateforme vous permet de publier vos données sur cartes.gouv.fr via la Géoplateforme directement depuis QGIS.

Elle est constituée d'un ensemble de traitements QGIS et d'interface graphique pour leur utilisation et la visualisation des données disponibles sur cartes.gouv.fr.

La recherche des données sur la Géoplateforme est intégrée dans le [Gestionnaire des sources de données de QGIS](https://docs.qgis.org/3.40/fr/docs/user_manual/managing_data_source/opening_data.html#provider-based-loading-tools).

## Menu

Le menu de l'extension permet d'afficher les différents outils disponibles.

![Menu plugin](../static/images/plugin_menu.png "Menu plugin")

Vous pouvez aussi afficher l'aide en ligne et les paramètres de l'extension.

:::{note}
Le menu peut changer selon les plugins référencés installés. Voir [la page dédiée](../external_plugins/integration.md).
:::

## Barre d'outils

Les actions de l'extension Géoplateforme sont aussi disponibles via les barres d'outils de QGIS.

![Barre d'outils plugin](../static/images/plugin_toolbar.png "Barre d'outils plugin")

Si vous n'êtes pas encore connecté, seule l'action de connection est disponible.

![Barre d'outils plugin déconnecté](../static/images/plugin_toolbar_disconnected.png "Barre d'outils plugin déconnecté")

----

## Connexion

Pour certaines fonctionnalités, il est nécessaire de s'authentifier à la Géoplateforme via le bouton suivant :

![Bouton connexion](../static/images/connect_button.png "Bouton connexion")

Si vous n'êtes pas déjà connecté vous pouvez demander une connection sur cartes.gouv.fr via le bouton correspondant.

![Interface connection](../static/images/authentication_widget.png "Interface connection")

Vous serez redirigé vers la plateforme de connection de cartes.gouv.fr.

![Connection cartes.gouv.fr](../static/images/cartes_gouv_connection.png "Connection cartes.gouv.fr")

Si vous êtes déjà connecté, des informations sur l'utilisateur courant sont affichées :

![Interface utilisateur](../static/images/user_widget.png "Interface utilisateur")

Vous pouvez vous déconnecter ou visualiser les identifiants des entrepôts disponibles.

----

## Gestionnaire des sources de données

La recherche des données sur la Géoplateforme est intégrée dans le [Gestionnaire des sources de données de QGIS](https://docs.qgis.org/3.40/fr/docs/user_manual/managing_data_source/opening_data.html#provider-based-loading-tools).

![Données Géoplateforme](../static/images/data_provider_widget.png "Données Géoplateforme")

2 modes de recherche sont disponibles

- Recherche simple : la recherche est effectuée sur le texte défini par l'utilisateur
- Recherche avancée : la recherche est effectué selon des critères précis (titre, nom de couche, visibilité, ...)

![Recherche avancée](../static/images/advanced_search.png "Recherche avancée")

Une fois la donnée sélectionnée vous pouvez l'ajouter à vos couches QGIS via le bouton `Ajouter`.

Si la donnée est privée vous pouvez sélectionner une configuration d'authentification de QGIS.

![Recherche avancée](../static/images/private_service_load.png "Recherche avancée")

----

## Tableau de bord

Le tableau de bord peut être affiché via le bouton suivant :

![Bouton dashboard](../static/images/dashboard_button.png "Bouton dashboard")

Voici un aperçu de l'interface graphique disponible :

![Interface dashboard](../static/images/dashboard_widget.png "Interface dashboard")

Vous pouvez trouver:

1. Des composants pour choisir l'entrepôt et la fiche de données visualisée
2. Un ensemble d'onglet affichant les informations de la fiche de donnée

Les onglets disponibles sont:

- Métadonnées
- Données
- Services
- Document (fonctionnalité en attente de développement).
- Permissions

### Création d'une fiche de donnée

La création d'une nouvelle fiche est effectuée via le bouton `Nouvelle fiche`.

![Nouvelle fiche](../static/images/create_dataset_widget.png "Nouvelle fiche")

Vous pouvez choisir les données à importer via le bouton `...`.

Une nouvelle interface est affichée.

![Sélection couche](../static/images/upload_layer_selection.png "Sélection couche").

Vous pourrez y sélectionner les couches disponibles dans QGIS et ajouter un fichier depuis la barre d'outils à droite.

Une fois les fichiers sélectionné vous pouvez cliquer sur la flèche de retour ou OK pour afficher la liste des données à importer.

![Liste couche](../static/images/upload_layer_list.png "Liste couche").

Si cela est possible, le CRS de la donnée est affichée et la liste des couches contenues dans les GPKG est affichée.

En cas de divergence de CRS un avertissement est affiché.

![Divergence CRS](../static/images/upload_layer_crs_mismatch.png "Divergence CRS").

Vous pouvez choisir de lancer une vérification locale des données avant de lancer l'intégration. Ceci est possible via l'option `Validation de la donnée avant envoi`. Le processing QGIS [`qgis:checkvalidity`](https://docs.qgis.org/3.40/fr/docs/user_manual/processing_algs/qgis/vectorgeometry.html#check-validity) est utilisé avec la méthode QGIS.

Il est nécessaire de définir les tables contenant des géométries multi. Le plugin va automatiquement définir ces tables en fonction des couches sélectionnées. Il est parfois possible que la définition automatique ne donne pas les bonnes tables. Vous pouvez indiquer les tables concernées par leurs noms séparés par des virgules.

Une fois vos fichiers et couches sélectionnés vous pouvez lancer l'intégration dans la Géoplateforme avec le bouton `Soumettre`.

Une fenêtre est affichée pour afficher les différentes étapes de la livraison.

Il n'est pas possible de la fermer tant que les données ne sont pas disponibles sur l'entrepôt.

![Attente livraison](../static/images/upload_wait_for_data.png "Attente livraison").

Vous pourrez ensuite voir les étapes de vérification en cours dans l'entrepôt.

![Liste vérification](../static/images/upload_checks.png "Liste vérification").

Si vous fermez la fenêtre avant la fin des vérifications, le traitement pour l'intégration des données en base ne sera pas lancée. Un message vous averti que le traitement devra être lancé ultérieurement.

![Attente vérification](../static/images/upload_wait_check.png "Attente vérification").

### Données

Cet onglet contient l'ensemble des données associées à la fiche de données courante.

![Interface données](../static/images/data_tab.png "Interface données")

4 tableaux sont disponibles:

- Livraisons
- Base de données vecteur
- Pyramides de tuiles vectorielles
- Pyramides de tuiles raster

Lors de la sélection d'une ligne du tableau, un panneau est affiché à droite pour décrire la donnée sélectionnée.

Les actions disponibles dépendent du type de la donnée sélectionnée.

Vous pouvez ajouter des données à la fiche de données via le bouton `Ajouter des données`.

#### Livraisons

![Panneau livraison](../static/images/upload_widget.png "Panneau livraison").

Le panneau des livraisons permet d'afficher les détails des données livrées. Le bouton `Charger rapport de génération` vous permet de récupérer les logs pour l'ensemble des traitements et vérifications effectués pour la livraison.

2 actions sont disponibles pour les livraisons :

- `Suppression` : demande de suppression de la livraison. Les bases de données vecteur créées depuis la livraison ne sont pas supprimées.
- `Génération base de données vectorielle` : demande du lancement du traitement pour la génération d'une base de données vecteur.

#### Bases de données vecteur

![Panneau base de données vecteur](../static/images/vector_db_widget.png "Panneau base de données vecteur").

Le panneau des bases de données vecteur permet d'afficher les détails des bases livrées. Le bouton `Charger rapport de génération` vous permet de récupérer les logs pour l'ensemble des traitements et vérifications effectués pour la base de données.

4 actions sont disponibles pour les bases de données vecteur :

- `Suppression` : demande de suppression de la base de données.
- `Génération tuile` : demande de génération de tuiles vectorielles
- `Publication WFS` : demande de publication WFS
- `Publication WMS-Vecteur` : demande de publication WMS-Vecteur

##### Génération de tuiles vectorielles

Les paramètres nécessaires à la génération de tuiles vectorielles sont définis via plusieurs pages. Vous pouvez à tout moment revenir à la page précédente via la flèche de retour située en haut à gauche (sous Windows) ou via le bouton retour situé à coté du bouton suivant (sous Linux).

![Première page génération de tuiles vectorielles](../static/images/vector_tiles_init_page.png "Première page génération de tuiles vectorielles").

Vous devez définir un nom et les niveaux de zoom à utiliser.

![Seconde page génération de tuiles vectorielles](../static/images/vector_tiles_tables.png "Seconde page génération de tuiles vectorielles").

Vous devez sélectionner les tables et attributs à utiliser.

![Troisième page génération de tuiles vectorielles](../static/images/vector_tiles_tippecanoe.png "Troisième page génération de tuiles vectorielles").

Vous devez sélectionner l'option de généralisation à appliquer.

La génération est ensuite lancée dans la géoplateforme.

![Génération de tuiles vectorielles](../static/images/vector_tiles_generation.png "Génération de tuiles vectorielles").

Vous pouvez fermer la fenêtre pendant la génération.

##### Publication WFS

Les paramètres nécessaires à la publication WFS sont définis via plusieurs pages. Vous pouvez à tout moment revenir à la page précédente via la flèche de retour située en haut à gauche (sous Windows) ou via le bouton retour situé à coté du bouton suivant (sous Linux).

![Première page publication WFS](../static/images/publish_wfs_table_selection.png "Première page publication WFS").

Vous devez définir les tables nécessaires au service. Le titre de la table et le résumé sont obligatoires pour chaque table utilisée.

Vous devez sélectionner au moins une table.

![Description service](../static/images/publish_service_description.png "Description service").

Tout les paramètres sont obligatoires.

Le nom technique doit être unique pour tout les services de l'entrepôt utilisé.

Si c'est le cas, une erreur sera remontée lors de la publication et vous pourrez revenir à cette page pour le modifier.

![Publication métadonnée](../static/images/publish_metadata.png "Publication métadonnée").

Cette page vous permet de créer ou de mettre à jour la métadonnée associée au jeu de données. La métadonnée est unique pour tout les services du jeu de donnée.

Si des paramètres sont manquants, ils sont indiqués en rouge dans l'interface.

![Publication restriction](../static/images/publish_restriction.png "Publication restriction").

Vous pouvez choisir de restreindre l'accès au service.

![Publication](../static/images/publish_page.png "Publication").

La publication est ensuite effectuée sur la Géoplateforme.

Une fois le service publié, la métadonnée doit être créée ou mise à jour. Il n'est pas possible de fermer la page pendant ces traitements.

![Publication attente métadonnée](../static/images/publish_wait_metadata.png "Publication attente métadonnée").

Le service créé est automatiquement sélectionné dans le tableau de bord après la fermeture de la fenêtre de publication.

##### Publication WMS-Vecteur

Les paramètres nécessaires à la publication WMS-Vecteur sont définis via plusieurs pages. Vous pouvez à tout moment revenir à la page précédente via la flèche de retour située en haut à gauche (sous Windows) ou via le bouton retour situé à coté du bouton suivant (sous Linux).

![Première page publication WMS-Vecteur](../static/images/publish_wms_vector_table_selection.png "Première page publication WMS-Vecteur").

Vous devez définir les tables nécessaires au service.

Vous devez sélectionner au moins une table.

Un fichier de style .sld doit être défini pour chaque table. Ce fichier peut être sélectionné depuis votre ordinateur ou créer depuis une couche chargée dans QGIS.

Attention, seul le format SLD 1.0.0 est supporté par la Géoplateforme. Un outils de conversion est disponible dans les traitements QGIS (conversion partielle, toutes les symbologies ne sont pas supportées).

Si vous sélectionnez une couche chargée dans QGIS, un export du style courant au format SLD est effectuée (version 1.1.0) puis l'outil de conversion est appelé pour produire un fichier au format 1.0.0.

![Description service](../static/images/publish_service_description.png "Description service").

Tout les paramètres sont obligatoires.

Le nom technique doit être unique pour tout les services de l'entrepôt utilisé.

Si c'est le cas, une erreur sera remontée lors de la publication et vous pourrez revenir à cette page pour le modifier.

![Publication métadonnée](../static/images/publish_metadata.png "Publication métadonnée").

Cette page vous permet de créer ou de mettre à jour la métadonnée associée au jeu de données. La métadonnée est unique pour tout les services du jeu de donnée.

Si des paramètres sont manquants, ils sont indiqués en rouge dans l'interface.

![Publication restriction](../static/images/publish_restriction.png "Publication restriction").

Vous pouvez choisir de restreindre l'accès au service.

![Publication](../static/images/publish_page.png "Publication").

La publication est ensuite effectuée sur la Géoplateforme.

Une fois le service publié, la métadonnée doit être créée ou mise à jour. Il n'est pas possible de fermer la page pendant ces traitements.

![Publication attente métadonnée](../static/images/publish_wait_metadata.png "Publication attente métadonnée").

Le service créé est automatiquement sélectionné dans le tableau de bord après la fermeture de la fenêtre de publication.

#### Pyramides de tuiles vectorielles

![Panneau pyramides vectorielles](../static/images/pyr_vector_widget.png "Panneau pyramides vectorielles").

Le panneau des pyramides de tuiles vectorielles permet d'afficher les détails des pyramides livrées. Le bouton `Charger rapport de génération` vous permet de récupérer les logs pour l'ensemble des traitements et vérifications effectués.

2 actions sont disponibles pour les pyramides de tuiles vectorielles :

- `Suppression` : demande de suppression de la pyramide.
- `Publication wms-tms` : demande de publication WMS-TMS

##### Publication WMS-TMS

Les paramètres nécessaires à la publication WMS-TMS sont définis via plusieurs pages. Vous pouvez à tout moment revenir à la page précédente via la flèche de retour située en haut à gauche (sous Windows) ou via le bouton retour situé à coté du bouton suivant (sous Linux).

![Description service](../static/images/publish_service_description.png "Description service").

Tout les paramètres sont obligatoires.

Le nom technique doit être unique pour tout les services de l'entrepôt utilisé.

Si c'est le cas, une erreur sera remontée lors de la publication et vous pourrez revenir à cette page pour le modifier.

![Publication métadonnée](../static/images/publish_metadata.png "Publication métadonnée").

Cette page vous permet de créer ou de mettre à jour la métadonnée associée au jeu de données. La métadonnée est unique pour tout les services du jeu de donnée.

Si des paramètres sont manquants, ils sont indiqués en rouge dans l'interface.

![Publication restriction](../static/images/publish_restriction.png "Publication restriction").

Vous pouvez choisir de restreindre l'accès au service.

![Publication](../static/images/publish_page.png "Publication").

La publication est ensuite effectuée sur la Géoplateforme.

Une fois le service publié, la métadonnée doit être créée ou mise à jour. Il n'est pas possible de fermer la page pendant ces traitements.

![Publication attente métadonnée](../static/images/publish_wait_metadata.png "Publication attente métadonnée").

Le service créé est automatiquement sélectionné dans le tableau de bord après la fermeture de la fenêtre de publication.

#### Pyramides de tuiles raster

![Panneau pyramides raster](../static/images/pyr_raster_widget.png "Panneau pyramides raster").

Le panneau des pyramides de tuiles raster permet d'afficher les détails des pyramides livrées. Le bouton `Charger rapport de génération` vous permet de récupérer les logs pour l'ensemble des traitements et vérifications effectués.

3 actions sont disponibles pour les pyramides de tuiles vectorielles :

- `Suppression` : demande de suppression de la pyramide.
- `Publication WMS-Raster` : demande de publication WMS-Raster
- `Publication WMTS-TMS` : demande de publication WMTS-TMS

##### Publication WMS-Raster

Les paramètres nécessaires à la publication WMS-Raster sont définis via plusieurs pages. Vous pouvez à tout moment revenir à la page précédente via la flèche de retour située en haut à gauche (sous Windows) ou via le bouton retour situé à coté du bouton suivant (sous Linux).

![Description service](../static/images/publish_service_description.png "Description service").

Tout les paramètres sont obligatoires.

Le nom technique doit être unique pour tout les services de l'entrepôt utilisé.

Si c'est le cas, une erreur sera remontée lors de la publication et vous pourrez revenir à cette page pour le modifier.

![Publication métadonnée](../static/images/publish_metadata.png "Publication métadonnée").

Cette page vous permet de créer ou de mettre à jour la métadonnée associée au jeu de données. La métadonnée est unique pour tout les services du jeu de donnée.

Si des paramètres sont manquants, ils sont indiqués en rouge dans l'interface.

![Publication restriction](../static/images/publish_restriction.png "Publication restriction").

Vous pouvez choisir de restreindre l'accès au service.

![Publication](../static/images/publish_page.png "Publication").

La publication est ensuite effectuée sur la Géoplateforme.

Une fois le service publié, la métadonnée doit être créée ou mise à jour. Il n'est pas possible de fermer la page pendant ces traitements.

![Publication attente métadonnée](../static/images/publish_wait_metadata.png "Publication attente métadonnée").

Le service créé est automatiquement sélectionné dans le tableau de bord après la fermeture de la fenêtre de publication.

##### Publication WMTS-TMS

Les paramètres nécessaires à la publication WMTS-TMS sont définis via plusieurs pages. Vous pouvez à tout moment revenir à la page précédente via la flèche de retour située en haut à gauche (sous Windows) ou via le bouton retour situé à coté du bouton suivant (sous Linux).

![Description service](../static/images/publish_service_description.png "Description service").

Tout les paramètres sont obligatoires.

Le nom technique doit être unique pour tout les services de l'entrepôt utilisé.

Si c'est le cas, une erreur sera remontée lors de la publication et vous pourrez revenir à cette page pour le modifier.

![Publication métadonnée](../static/images/publish_metadata.png "Publication métadonnée").

Cette page vous permet de créer ou de mettre à jour la métadonnée associée au jeu de données. La métadonnée est unique pour tout les services du jeu de donnée.

Si des paramètres sont manquants, ils sont indiqués en rouge dans l'interface.

![Publication restriction](../static/images/publish_restriction.png "Publication restriction").

Vous pouvez choisir de restreindre l'accès au service.

![Publication](../static/images/publish_page.png "Publication").

La publication est ensuite effectuée sur la Géoplateforme.

Une fois le service publié, la métadonnée doit être créée ou mise à jour. Il n'est pas possible de fermer la page pendant ces traitements.

![Publication attente métadonnée](../static/images/publish_wait_metadata.png "Publication attente métadonnée").

Le service créé est automatiquement sélectionné dans le tableau de bord après la fermeture de la fenêtre de publication.

### Services

Cet onglet contient l'ensemble des services disponibles pour le jeu de données sélectionné.

Lors de la sélection d'un service, un panneau est affiché à droite pour décrire le service sélectionné.

![Panneau service](../static/images/publish_wms_vector_table_selection.png "Panneau service").

2 actions sont toujours disponibles :

- `Dépublication` : demande la dépublication du service
- `Charger` : charge le service dans QGIS

D'autres fonctionnalités peuvent être affichées selon le service sélectionné

- gestion des styles
- gestion des permission
- génération de tuiles raster

#### Gestion des styles

Pour les services WFS et WMS-Vecteur, il est possible d'ajouter des fichiers de styles.

![Styles](../static/images/services_styles_widget.png "Styles")

Lors de la demande d'ajout vous pourrez choisir le nom du style et le fichier de style à utiliser.

Au format .sld pour les services WFS :

![Création style sld](../static/images/services_create_style_sld.png "Création style sld")

Au format .json mapbox pour les services WMS-Vecteur :

![Création style mapbox](../static/images/services_create_style_mapbox.png "Création style mapbox")

#### Gestions des permissions

Pour les services fermés, il est possible d'ajouter une permission.

Un tableau affiche les permissions associées à ce service et il est possible d'ajouter une permission.

Pour la création et la mise à jour des permissions, veuillez vous référer au chapitre des Permissions.

----

### Métadonnée

Cet onglet contient la métadonnée associée à la fiche de donnée.

Cette métadonnée est unique pour tout les services de la fiche de donnée. Elle est mise à jour à chaque publication ou dépublication d'un service.

Aucune métadonnée n'est publié tant qu'un service n'a pas été publié.

![Interface métadonnée](../static/images/metadata_widget.png "Interface métadonnée").

Une fois les modifications effectués, il est nécessaire d'appuyer sur le bouton `Mise à jour` pour lancer la mise à jour de la métadonnée dans la Géoplateforme.

### Permission

Cet onglet contient toutes les permissions accordées pour cet entrepot.

![Interface permissions](../static/images/permissions_tab.png "Interface permissions").

Il est possible d'ajouter une permission avec le bouton `Créer une permission`.

![Permissions](../static/images/permissions_widget.png "Permissions")

La fenêtre de création vous permet de définir :

- le nom de la permission (license)
- à qui la permission est accordée (des communautés ou des utilisateurs)
- sa date d'expiration (optionnel)
- les services auxquels cette permission donne accès

![Création permissions](../static/images/permission_creation_widget.png "Création permission")

Lors de la sélection d'une permission, un panneau complémentaire est affiché à droite du tableau des permissions.

![Panneau permissions](../static/images/permissions_panel.png "Panneau permission")

Vous pouvez modifier la permission en appuyant sur le bouton `Modifier`.

Le contenu du panneau peut être modifié et vous pouvez sélectionner les services pour la permission.

Il est nécessaire d'appuyer sur le bouton `Sauvegarder` pour valider les modifications.

Vous pouvez aussi supprimer la permission sélectionné avec le bouton `Supprimer`.

## Clés d'accès

Pour l'utilisation de service privé vous aurez besoin de créer des clés d'accès pour la Géoplateforme.

L'interface de gestion des clés d'accès peut être affichée via le bouton suivant :

![Bouton clés](../static/images/key_button.png "Bouton clés")

Voici un aperçu de l'interface graphique disponible :

![Interface clés](../static/images/key_widget.png "Interface clés")

Lors de la sélection d'une clé, un panneau est affiché à droite du tableau.

Vous pouvez modifier la clé en appuyant sur le bouton `Modifier`.

Le contenu du panneau peut être modifié et vous pouvez sélectionner les services pour la clé.

Il est nécessaire d'appuyer sur le bouton `Sauvegarder` pour valider les modifications.

Vous pouvez aussi supprimer la clé sélectionnée avec le bouton `Supprimer`.

### Ajouter une clé d'accès

![Ajout clé](../static/images/key_creation.png "Ajout clé")

Vous pouvez choisir parmis 3 types de clés:

- Basique

Vous devez défini un nom d'utilisateur et un mot de passe. Attention, le nom d'utilisateur doit être unique dans la Géoplateforme.

![Clé déjà utilisée](../static/images/key_user_exists.png "Clé déjà utilisée")

- Hash

Une valeur de hash sera calculé automatiquement par la Géoplateforme et pourra être utilisée comme paramètre complémentaire pour les requêtes vers la Géoplateforme.

- Oauth2

Votre compte Géoplateforme sera utilisé pour l'authentification. Vous ne pouvez avoir qu'une seule clé de type Oauth2.

Pour les clés de type Basique et Hash, après la création vous aurez la possibilité de créer une configuration d'authentification QGIS associée à cette clé.

![Ajout clé](../static/images/key_auth_creation.png "Ajout clé")

## Réglages

Les réglages utilisés par l'extension sont disponibles depuis le menu :

![Paramètres extension](../static/images/plugin_settings.png "Paramètres extension")

### Variables d'environnement

Ces paramètres peuvent être définis via des variables d'environnement. Ceci permet une configuration de l'extension directement par la Direction des Systèmes d'Information (DSI).

Le tableau suivant reprend les paramètres disponibles avec la variable d'environnement associée et la valeur par défaut:

|Paramètre                         | Variable d'environnement                                | Valeur par défaut                          |
|----------------------------------|---------------------------------------------------------|--------------------------------------------|
|URL requête API Géoplateforme     | `QGIS_GEOPLATEFORME_URL_API_ENTREPOT` | `https://data.geopf.fr/api/`        |
|URL requête API de recherche Géoplateforme     | `QGIS_GEOPLATEFORME_URL_API_SEARCH` | `https://data.geopf.fr/recherche/api`        |
|Identifiant des entrepôts de type bac à sable     | `QGIS_GEOPLATEFORME_SANDBOX_DATASTORE_IDS_STR` | `122b878c-aad8-4507-87b2-465e664467d3,87e1beb6-ee07-4adc-8449-6a925dc28949`        |
|Identifiant des traitement de création de pyramides raster depuis WMS-Vecteur     | `QGIS_GEOPLATEFORME_RASTER_TILES_FROM_WMS_VECTOR_PROCESSING_IDS_STR` | `6a54dc92-fc93-4c8e-9f02-046bf889550e,2e56e7ba-552b-49b8-abcf-563184dd8c55`        |
|Identifiant des traitement de création de pyramides raster depuis WMS-Vecteur     | `QGIS_GEOPLATEFORME_VECTOR_DB_GENERATION_PROCESSING_IDS_STR` | `0de8c60b-9938-4be9-aa36-9026b77c3c96, 5a348542-61a7-4289-a950-8544bb0ce2b8`        |
|Identifiant des traitement de création de pyramides vectorielles     | `QGIS_GEOPLATEFORME_VECTOR_TILE_GENERATION_PROCESSING_IDS_STR` | `0de8c60b-9938-4be9-aa36-9026b77c3c96, 5a348542-61a7-4289-a950-8544bb0ce2b8`        |
