# Plugin Géoplateforme pour QGIS

[![License: GPLv2+](https://img.shields.io/badge/License-GPLv2+-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![flake8](https://img.shields.io/badge/linter-flake8-green)](https://flake8.pycqa.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

![logo plugin Géoplateforme pour QGIS](https://raw.githubusercontent.com/Geoplateforme/plugin-qgis-geoplateforme/refs/heads/main/geoplateforme/resources/images/logo.svg)

Le plugin **Géoplateforme** pour QGIS est conçu pour faciliter l’accès aux données et services de la Géoplateforme directement depuis QGIS.
Il s’adresse aux administrations, collectivités, bureaux d’études et acteurs privés souhaitant exploiter efficacement la donnée publique française.

![Vue de la suite de plugins Géoplateforme dans QGIS](https://github.com/Geoplateforme/plugin-qgis-geoplateforme/blob/main/docs/static/images/qgis_all_inclusive_plugins.png?raw=true)

🚀 Pour l'essayer, vous pouvez l'installer directement depuis le [dépôt officiel des plugins QGIS](https://plugins.qgis.org/plugins/geoplateforme/).

## ✅ Principales fonctionnalités

- **Accès direct aux flux de la Géoplateforme** via le gestionnaire de sources de données dans QGIS.

    ![Entrée IGN dans le gestionnaire de sources de données de QGIS](https://raw.githubusercontent.com/Geoplateforme/plugin-qgis-geoplateforme/refs/heads/main/docs/static/images/plugin_data_source_provider.png)

- **Configuration des géoservices** à partir de vos propres données vectorielles.
  - Services concernés : WMS, WMS-v, WMTS, TMS, WFS
  - Gestion des métadonnées de vos données.
  - Gestion des permissions et des clés d’accès pour les flux  à accès restreints sur vos données ou ceux de vos partenaires.

    ![Configuration d'un service publié](https://github.com/Geoplateforme/plugin-qgis-geoplateforme/blob/main/docs/static/images/plugin_entrepot_donnees_configuration_service.png?raw=true)

- **Synchronisation avec cartes.gouv.fr** pour :
  - la **découvrabilité des flux** dans le [catalogue](https://cartes.gouv.fr/catalogue/search).
  - l'accès à l'**Interface de style** pour personnaliser le rendu des données.
- **Traitements QGIS via le modeleur** (processings) pour automatiser les tâches.

    ![Exemple de traitement dans le modeleur QGIS](https://video.osgeo.org/w/baDmkJ3HCtmWrASkCLGVho)

### Fédération de plugins

Le plugin se présente également comme une **fédération de plugins** spécialisés pour des usages spécifiques autour des données et services de la Géoplateforme :

- *GPF Isochrone / Isodistance / Itinéraire* : calculs d’itinéraires et iso-calculs
- *French Locator Filter* : géocodage direct/inverse, unitaire ou en masse
- *QGiréférentiels* : accès aux pré-paquets diffusés par la Géoplateforme
- *BD TOPO® Extractor* : extraction ciblée de la BD TOPO avec stylisation à la volée

![QGIS - Installation des plugins liés](https://geoplateforme.github.io/plugin-qgis-geoplateforme/_images/qgis_install_subplugins.png)

Pour plus d'informations sur l'intégration des plugins tiers, [consulter cette page de la documentation](https://geoplateforme.github.io/plugin-qgis-geoplateforme/external_plugins/integration.html).

----

## 📖 Documentation

Vous pouvez consulter la documentation à cette adresse [documentation](https://geoplateforme.github.io/plugin-qgis-geoplateforme/)

----

## Crédits

Le plugin a été amorcé avec le [QGIS Plugin Templater](https://oslandia.gitlab.io/qgis/template-qgis-plugin/) en repartant sur les bases du [plugin Géotuileur](https://gitlab.com/Oslandia/qgis/ign-geotuileur) entre avril et décembre 2025.  

Il a été conçu et financé par [l'IGN](https://www.ign.fr/particuliers) et principalement développé par [Oslandia](https://oslandia.com/).

----

## Licence

Le plugin est distribué sous les termes de la licence [`GPLv2+`](https://github.com/Geoplateforme/plugin-qgis-geoplateforme/blob/main/LICENSE).
