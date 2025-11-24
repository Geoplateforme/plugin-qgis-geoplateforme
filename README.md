# Géoplateforme - QGIS Plugin

[![License: GPLv2+](https://img.shields.io/badge/License-GPLv2+-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![flake8](https://img.shields.io/badge/linter-flake8-green)](https://flake8.pycqa.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

![logo plugin Géoplateforme pour QGIS](https://raw.githubusercontent.com/Geoplateforme/plugin-qgis-geoplateforme/refs/heads/main/geoplateforme/resources/images/logo.svg)

## 📌 Le plugin Géoplateforme pour QGIS

Le plugin **Géoplateforme** pour QGIS est conçu pour faciliter l’accès aux données et services de la Géoplateforme directement depuis QGIS.
Il s’adresse aux administrations, collectivités, bureaux d’études et acteurs privés souhaitant exploiter efficacement la donnée publique française.

### ✅ Fonctionnalités principales

- **Accès direct aux flux de la Géoplateforme** via le gestionnaire de sources de données dans QGIS.

    ![Entrée IGN dans le gestionnaire de sources de données de QGIS](https://raw.githubusercontent.com/Geoplateforme/plugin-qgis-geoplateforme/refs/heads/main/docs/static/images/PluginGPF_gestionnaire.png)

- **Configuration des géoservices** à partir de vos propres données vectorielles.
  - Services concernés : WMS, WMS-v, WMTS, TMS, WFS
  - Gestion des métadonnées de vos données.
  - Gestion des permissions et des clés d’accès pour les flux  à accès restreints sur vos données ou ceux de vos partenaires.

    ![Configuration d'un service publié](https://github.com/Geoplateforme/plugin-qgis-geoplateforme/blob/main/docs/static/images/PluginGPF_config.png?raw=true)

- **Synchronisation avec cartes.gouv.fr** pour :
  - la **découvrabilité des flux** dans le [catalogue](https://cartes.gouv.fr/catalogue/search).
  - l'accès à l'**Interface de style** pour personnaliser le rendu des données.
- **Traitements QGIS via le modeleur** (processings) pour automatiser les tâches.

    ![Exemple de traitement dans le modeleur QGIS](https://raw.githubusercontent.com/Geoplateforme/plugin-qgis-geoplateforme/refs/heads/main/docs/static/images/PluginGPF_gestionnaire.png)

- **Fédération de Plugins** :
  - *GPF Isochrone / Isodistance / Itinéraire* : calculs d’itinéraires et iso-calculs.
  - *French Locator Filter* : géocodage direct/inverse, unitaire ou en masse.
  - *QGiréférentiels* : accès aux pré-paquets diffusés par la Géoplateforme.
  - *BD TOPO® Extractor* : extraction ciblée de la BD TOPO avec stylisation à la volée.

### 🔧 Installation

Disponible via le **gestionnaire d’extensions QGIS** (extensions expérimentales) à partir de **QGIS ≥ 3.40.4**.  
Compatibilité anticipée avec **QGIS 4.0** (prévue en février 2026).

### 📖 Documentation

Vous pouvez consulter la documentation à cette adresse [documentation](https://geoplateforme.github.io/plugin-qgis-geoplateforme/)

### ▶️ Utilisation

1. Activez le plugin dans QGIS.
2. Ajoutez des couches via le gestionnaire QGIS.
3. Authentifiez-vous puis configurez vos géoservices (WMS, WFS, WMTS, TMS).
4. Exploitez les traitements dans le modeleur QGIS pour automatiser vos workflows.

----

## Crédits

Le plugin a été amorcé avec le [QGIS Plugin Templater](https://oslandia.gitlab.io/qgis/template-qgis-plugin/), conçu et financé par [l'IGN](https://www.ign.fr/particuliers) et principalement développé par [Oslandia](https://oslandia.com/).

----

## Licence

Le plugin est distribué sous les termes de la licence [`GPLv2+`](https://github.com/Geoplateforme/plugin-qgis-geoplateforme/blob/main/LICENSE).
