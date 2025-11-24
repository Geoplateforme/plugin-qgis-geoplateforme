# Géoplateforme - QGIS Plugin
[![License: GPLv2+](https://img.shields.io/badge/License-GPLv2+-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

[![flake8](https://img.shields.io/badge/linter-flake8-green)](https://flake8.pycqa.org/)

## 📌 Le plugin Qgis Geoplateforme
Le plugin **Géoplateforme** pour QGIS est conçu pour faciliter l’accès aux données et services de la Géoplateforme directement depuis QGIS. 
Il s’adresse aux administrations, collectivités, bureaux d’études et acteurs privés souhaitant exploiter efficacement la donnée publique française.

### ✅ Fonctionnalités principales
- **Accès direct aux flux de la Géoplateforme** via le gestionnaire de sources de données dans QGIS. 
- **Configuration des géoservices** à partir de vos propres données vectorielles.
    - Services concernés : WMS, WMS-v, WMTS, TMS, WFS
    - Gestion des métadonnées de vos données.
    - Gestion des permissions et des clés d’accès pour les flux  à accès restreints sur vos données ou ceux de vos partenaires.
- **Synchronisation avec cartes.gouv.fr** pour :
    - la **découvrabilité des flux** dans le [catalogue](https://cartes.gouv.fr/catalogue/search).
    - l'accès à l'**Interface de style** pour personnaliser le rendu des données.
- **Traitements QGIS via le modeleur** (processings) pour automatiser les tâches.
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
    <img src="/docs/static/images/PluginGPF_gestionnaire.png" alt="Gestionnaire de couches" width="600" />
3. Authentifiez-vous puis configurez vos géoservices (WMS, WFS, WMTS, TMS).
   <img src="/docs/static/images/PluginGPF_config.png" alt="Tableau de bord" width="600" />
4. Exploitez les traitements dans le modeleur Qgis pour automatiser vos workflows.

---
### Plugin

| Cookiecutter option | Picked value |
| :------------------ | :----------: |
| Plugin name | Géoplateforme |
| Plugin name slugified | geoplateforme |
| Plugin name class (used in code) | Geoplateforme |
| Plugin description short | Tirer parti de la puissance de la Géoplateforme directement depuis QGIS ! |
| Plugin description long | Connectez-vous avec votre compte cartes.gouv.fr, accédez à votre communauté, publiez vos données sous forme de services hébergés sur la Géoplateforme de l'IGN. |
| Plugin tags | Géoplateforme, France, Géoservices, téléversement, publication, Entrepôt, IGN |
| Plugin icon | <img src="geoplateforme/resources/images/logo.svg" alt="Icône" width="200" /> |
| Plugin with processing provider | True |
| Author organization | IGN & Oslandia |
| Author email | <geoplateforme@ign.fr> |
| Minimum QGIS version | 3.40 |
| Maximum QGIS version | 3.99 |
| Support Qt6 | True |
| Git repository URL | <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/> |
| Git default branch | main |
| License | GPLv2+ |
| Python linter | Flake8 |
| CI/CD platform | GitHub |
| Publish to <https://plugins.qgis.org> using CI/CD | True |
| IDE | VSCode |


### Tooling

This project is configured with the following tools:

- [Black](https://black.readthedocs.io/en/stable/) to format the code without any existential question
- [iSort](https://pycqa.github.io/isort/) to sort the Python imports

Code rules are enforced with [pre-commit](https://pre-commit.com/) hooks.  
Static code analisis is based on: Flake8

See also: [contribution guidelines](CONTRIBUTING.md).

## CI/CD

Plugin is linted, tested, packaged and published with GitHub.

If you mean to deploy it to the [official QGIS plugins repository](https://plugins.qgis.org/), remember to set your OSGeo credentials (`OSGEO_USER_NAME` and `OSGEO_USER_PASSWORD`) as environment variables in your CI/CD tool.

### Documentation

The documentation is generated using Sphinx and is automatically generated through the CI and published on Pages.

- homepage: <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/>
- repository: <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/>
- tracker: <https://github.com/Geoplateforme/plugin-qgis-geoplateforme//issues/>

----


## License

Distributed under the terms of the [`GPLv2+` license](LICENSE).
