- Description :

Vérification des couches vectorielles avant intégration dans l'entrepôt.

- Paramètres :

| Entrée           | Paramètre          | Description                                                |
|------------------|--------------------|------------------------------------------------------------|
| Couches vectorielles à vérifier | `INPUT_LAYERS`  | Couches vectorielles à vérifier. |

- Sorties :

| Sortie                             | Paramètre                           | Description                    |
|------------------------------------|-------------------------------------|--------------------------------|
| Code de résultat | `RESULT_CODE`        | Code de résultat. 0 si aucun problème |

Le code de résultat est fourni sous forme de flags:

```python
class ResultCode(IntFlag):
    """
    https://docs.python.org/fr/3/library/enum.html#intflag
    """

    VALID = 0
    CRS_MISMATCH = 1
    INVALID_LAYER_NAME = 2
    INVALID_FILE_NAME = 4
    INVALID_FIELD_NAME = 8
    INVALID_LAYER_TYPE = 16
    INVALID_GEOMETRY = 32
    NO_FEATURES = 64
```

La présence d'un type d'erreur peut être vérifié via python :

```python
if CheckLayerAlgorithm.ResultCode.CRS_MISMATCH in result_code:
    print("Les CRS des couches ne sont pas tous identiques")
```

Pour les vérifications de géométrie, le processing QGIS [`qgis:checkvalidity`](https://docs.qgis.org/3.40/fr/docs/user_manual/processing_algs/qgis/vectorgeometry.html#check-validity) est utilisé avec la méthode QGIS.

Nom du traitement : `geoplateforme:check_layers`
