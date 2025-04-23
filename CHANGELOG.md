# CHANGELOG

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

<!--

Unreleased

## version_tag - YYYY-DD-mm

### Added

### Changed

### Removed

-->

## 0.2.0-beta1 - 2025-04-23

* feature(auth): Add OAuth2 authentication by @Ducarouge in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/2>
* feature(dasboard) : add combobox to filter datastore by dataset  by @Ducarouge in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/7>
* feature(dashboard): add new UI to fit IGNGPF-4830 by @Ducarouge in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/8>
* feature(packaging): include oAuth credentials from GH Actions secrets during packaging steps by @Guts in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/14>
* feature(vector db): restore vector db creation wizard by @jmkerloch in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/16>
* refactor(network): Nettoyage et refactoring du Network Manager by @Ducarouge in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/6>
* refactor(stored data): optimize stored data for better load by @Ducarouge in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/9>
* refactor(upload): refactor upload to optimize and use network manager by @Ducarouge in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/10>
* fix(auth): make QGIS auth configuration map JSON compliant before loading it as JSON by @Guts in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/13>
* fix(ci): fix packaged plugin and repository was missing in documentation by @Guts in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/11>
* fix(init): plg_settings.qgis_auth_id can be None and so have no length by @Guts in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/12>
* fix(quality): apply Qt6 migration script by @Guts in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/4>
* fix(user): fix community without user  by @Ducarouge in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/18>
* update(plugin): cleanup, remove and rename from geotuileur to geoplateforme by @Guts in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/1>
* update(tooling): replace black with ruff formatter by @Guts in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/3>
* update(tooling): set ruff as Python formatter in VS Code by @Guts in <https://github.com/Geoplateforme/plugin-qgis-geoplateforme/pull/5>

## 0.1.0 - 2025-04-10

* First release
* Generated with the [QGIS Plugins templater](https://oslandia.gitlab.io/qgis/template-qgis-plugin/)
