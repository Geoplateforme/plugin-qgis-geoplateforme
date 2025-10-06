import pytest
from osgeo import gdal, osr
from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.tools.check_layer import CheckLayerAlgorithm
from tests.qgis.processings.conftest import QgsProcessingFeedBackTest

INVALID_CHARS = CheckLayerAlgorithm.get_invalid_characters()


@pytest.fixture()
def alg() -> QgsProcessingAlgorithm:
    """
    Retrieve algorithm to be tested from processing registry

    Returns: QgsProcessingAlgorithm

    """
    algo_str = f"{GeoplateformeProvider().id()}:{CheckLayerAlgorithm().name()}"
    alg = QgsApplication.processingRegistry().algorithmById(algo_str)
    assert alg is not None
    return alg


def create_shape_file(
    tmpdir,
    filename: str,
    layer_name: str,
    crs_auth_id: str = None,
    fields: QgsFields = None,
    add_feature: bool = True,
) -> QgsVectorLayer:
    layer_path = tmpdir / filename

    if fields is None:
        fields = QgsFields()
    if crs_auth_id is None:
        crs_auth_id = "EPSG:4326"

    QgsVectorFileWriter(
        str(layer_path),
        "UTF-8",
        fields,
        QgsWkbTypes.Type.Point,
        QgsCoordinateReferenceSystem(crs_auth_id),
        "ESRI Shapefile",
    )
    layer = QgsVectorLayer(str(layer_path), layer_name, "ogr")

    if add_feature:
        layer.startEditing()
        feat = QgsFeature()
        feat.setFields(fields)
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        layer.addFeature(feat)

        assert layer.commitChanges()

    assert layer.crs().authid() == crs_auth_id
    return layer


def test_no_input(alg: QgsProcessingAlgorithm):
    """
    Check no error is raised when no input is provided

    Args:
        alg: pytest fixture to get QgsProcessingAlgorithm
    """
    params = {CheckLayerAlgorithm.INPUT_LAYERS: []}
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    result, success = alg.run(params, context, feedback)
    assert success

    result_code = result[CheckLayerAlgorithm.RESULT_CODE]
    assert result_code == CheckLayerAlgorithm.ResultCode.VALID


def test_valid_layers(alg: QgsProcessingAlgorithm, tmpdir):
    """
    Check return code in case of valid layers

    Args:
        alg: pytest fixture to get QgsProcessingAlgorithm
        tmpdir: pytest fixture to get temporary directory
    """

    params = {
        CheckLayerAlgorithm.INPUT_LAYERS: [
            create_shape_file(tmpdir, "vect_1.shp", "vect_1"),
            create_shape_file(tmpdir, "vect_2.shp", "vect_2"),
            create_shape_file(tmpdir, "vect_2.shp", "vect_3"),
        ]
    }
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedBackTest()
    result, success = alg.run(params, context, feedback)
    assert success

    result_code = result[CheckLayerAlgorithm.RESULT_CODE]
    assert result_code == CheckLayerAlgorithm.ResultCode.VALID


def test_crs_mismatch(alg: QgsProcessingAlgorithm, tmpdir):
    """
    Check return code in case of crs mismatch

    Args:
        alg: pytest fixture to get QgsProcessingAlgorithm
        tmpdir: pytest fixture to get temporary directory
    """

    params = {
        CheckLayerAlgorithm.INPUT_LAYERS: [
            create_shape_file(tmpdir, "vect_4326.shp", "vect_4326", "EPSG:4326"),
            create_shape_file(tmpdir, "vect_4143.shp", "vect_4143", "EPSG:4143"),
            create_shape_file(tmpdir, "vect_3857.shp", "vect_3857", "EPSG:3857"),
        ]
    }
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedBackTest()
    result, success = alg.run(params, context, feedback)
    assert success

    result_code = result[CheckLayerAlgorithm.RESULT_CODE]
    assert result_code == CheckLayerAlgorithm.ResultCode.CRS_MISMATCH

    expected_warnings = [
        "- [KO] vect_4143 : invalid CRS EPSG:4143. Expected EPSG:4326",
        "- [KO] vect_3857 : invalid CRS EPSG:3857. Expected EPSG:4326",
    ]
    assert expected_warnings == feedback.warnings


def test_invalid_layer_name(alg: QgsProcessingAlgorithm, tmpdir):
    """
    Check return code in case of invalid layer name

    Args:
        alg: pytest fixture to get QgsProcessingAlgorithm
        tmpdir: pytest fixture to get temporary directory
    """

    params = {
        CheckLayerAlgorithm.INPUT_LAYERS: [
            create_shape_file(tmpdir, "valid.shp", "valid"),
            create_shape_file(tmpdir, "invalid_1.shp", "inva&lid"),
            create_shape_file(tmpdir, "invalid_2.shp", "inva'lid"),
            create_shape_file(tmpdir, "invalid_3.shp", 'inva"lid'),
            create_shape_file(tmpdir, "invalid_4.shp", "inva<lid"),
            create_shape_file(tmpdir, "invalid_5.shp", "inva>lid"),
        ]
    }
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedBackTest()
    result, success = alg.run(params, context, feedback)
    assert success

    result_code = result[CheckLayerAlgorithm.RESULT_CODE]
    assert result_code == CheckLayerAlgorithm.ResultCode.INVALID_LAYER_NAME
    expected_warnings = [
        f"- [KO] invalid layer name for inva&lid. Please remove any special character ({INVALID_CHARS})",
        f"- [KO] invalid layer name for inva'lid. Please remove any special character ({INVALID_CHARS})",
        f'- [KO] invalid layer name for inva"lid. Please remove any special character ({INVALID_CHARS})',
        f"- [KO] invalid layer name for inva<lid. Please remove any special character ({INVALID_CHARS})",
        f"- [KO] invalid layer name for inva>lid. Please remove any special character ({INVALID_CHARS})",
    ]
    assert expected_warnings == feedback.warnings


def test_invalid_filename(alg: QgsProcessingAlgorithm, tmpdir):
    """
    Check return code in case of invalid filename

    Args:
        alg: pytest fixture to get QgsProcessingAlgorithm
        tmpdir: pytest fixture to get temporary directory
    """

    layers = [
        {"layer_name": "file_1", "file_name": "inva&lid.shp"},
        {"layer_name": "file_2", "file_name": "inva'lid.shp"},
        {"layer_name": "file_3", "file_name": 'inva"lid.shp'},
        {"layer_name": "file_4", "file_name": 'inva"lid.shp'},
        {"layer_name": "file_5", "file_name": "inva<lid.shp"},
        {"layer_name": "file_6", "file_name": "inva>lid.shp"},
    ]

    layer_list = [
        create_shape_file(tmpdir, layer["file_name"], layer["layer_name"])
        for layer in layers
    ]

    params = {CheckLayerAlgorithm.INPUT_LAYERS: layer_list}
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedBackTest()
    result, success = alg.run(params, context, feedback)
    assert success

    result_code = result[CheckLayerAlgorithm.RESULT_CODE]
    assert result_code == CheckLayerAlgorithm.ResultCode.INVALID_FILE_NAME

    expected_warnings = []
    for layer in layers:
        file_path = str(tmpdir / layer["file_name"])
        expected_warnings.append(
            f"- [KO] invalid file name for {file_path}. Please remove any special character ({INVALID_CHARS})"
        )
    assert expected_warnings == feedback.warnings


def test_invalid_field_name(alg: QgsProcessingAlgorithm, tmpdir):
    """
    Check return code in case of invalid field name

    Args:
        alg: pytest fixture to get QgsProcessingAlgorithm
        tmpdir: pytest fixture to get temporary directory
    """

    layers = [
        {
            "layer_name": "file_1",
            "file_name": "invalid_field_1.shp",
            "field_names": ["inva&lid"],
        },
        {
            "layer_name": "file_2",
            "file_name": "invalid_field_2.shp",
            "field_names": ["inva'lid"],
        },
        {
            "layer_name": "file_3",
            "file_name": "invalid_field_3.shp",
            "field_names": ['inva"lid'],
        },
        {
            "layer_name": "file_4",
            "file_name": "invalid_field_4.shp",
            "field_names": ['inva"lid'],
        },
        {
            "layer_name": "file_5",
            "file_name": "invalid_field_5.shp",
            "field_names": ["inva<lid"],
        },
        {
            "layer_name": "file_6",
            "file_name": "invalid_field_6.shp",
            "field_names": ["inva>lid"],
        },
        {
            "layer_name": "file_7",
            "file_name": "invalid_field_7.shp",
            "field_names": ["inva>lid", "inva<lid"],
        },
    ]

    layer_list = []
    for layer in layers:
        fields = QgsFields()
        for field in layer["field_names"]:
            fields.append(QgsField(field, QVariant.String))
        layer_list.append(
            create_shape_file(
                tmpdir, layer["file_name"], layer["layer_name"], "EPSG:4326", fields
            )
        )

    params = {CheckLayerAlgorithm.INPUT_LAYERS: layer_list}
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedBackTest()
    result, success = alg.run(params, context, feedback)
    assert success

    result_code = result[CheckLayerAlgorithm.RESULT_CODE]
    assert result_code == CheckLayerAlgorithm.ResultCode.INVALID_FIELD_NAME

    expected_warnings = []
    for layer in layers:
        layer_name = layer["layer_name"]
        for field in layer["field_names"]:
            expected_warnings.append(
                f"- [KO] invalid layer field name {field} for {layer_name}. Please remove any special character ({INVALID_CHARS})"
            )
    assert expected_warnings == feedback.warnings


def create_raster_file(tmpdir, filename: str) -> str:
    fn = str(tmpdir / filename)

    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(fn, xsize=10, ysize=10, bands=1, eType=gdal.GDT_Float32)

    # Dummy minimal optional values
    geot = [500000, 10, 0, 4600000, 0, -10]
    ds.SetGeoTransform(geot)
    srs = osr.SpatialReference()
    srs.SetUTM(12, 1)
    srs.SetWellKnownGeogCS("NAD83")
    ds.SetProjection(srs.ExportToWkt())

    return fn


def test_invalid_layer_type(alg: QgsProcessingAlgorithm, tmpdir):
    """
    Check return code in case of invalid layer type

    Args:
        alg: pytest fixture to get QgsProcessingAlgorithm
        tmpdir: pytest fixture to get temporary directory
    """
    filepath = create_raster_file(tmpdir, "raster.tif")
    params = {CheckLayerAlgorithm.INPUT_LAYERS: filepath}
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedBackTest()
    result, success = alg.run(params, context, feedback)
    assert success

    result_code = result[CheckLayerAlgorithm.RESULT_CODE]
    assert result_code == CheckLayerAlgorithm.ResultCode.INVALID_LAYER_TYPE

    expected_warnings = [
        "- [KO] invalid layer type for raster. Only QgsVectorLayer are supported."
    ]
    assert expected_warnings == feedback.warnings


def test_empty_layers(alg: QgsProcessingAlgorithm, tmpdir):
    """
    Check return code in case of empty layers

    Args:
        alg: pytest fixture to get QgsProcessingAlgorithm
        tmpdir: pytest fixture to get temporary directory
    """

    params = {
        CheckLayerAlgorithm.INPUT_LAYERS: [
            create_shape_file(tmpdir, "vect_1.shp", "vect_1", add_feature=False),
        ]
    }
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedBackTest()
    result, success = alg.run(params, context, feedback)
    assert success

    result_code = result[CheckLayerAlgorithm.RESULT_CODE]
    assert result_code == CheckLayerAlgorithm.ResultCode.NO_FEATURES
