from unittest.mock import MagicMock, patch

from r2gg._main import valhalla_convert


def _build_resource(tmp_path):
    return {
        "type": "valhalla",
        "sources": [
            {
                "id": "test-source",
                "storage": {
                    "dir": str(tmp_path / "tiles"),
                    "tar": str(tmp_path / "tiles.tar"),
                    "config": str(tmp_path / "valhalla.json"),
                },
            }
        ],
    }


def test_valhalla_convert_uses_top_level_logging_flags(tmp_path):
    """valhalla_build_config must be called with the top-level --logging-*
    flags (supported by pyvalhalla) rather than the nonexistent
    --mjolnir-logging-* ones, which made the command exit with return code 2."""
    config = {"workingSpace": {"directory": str(tmp_path)}}
    resource = _build_resource(tmp_path)
    # Le fichier OSM PBF doit exister pour que valhalla_convert ne tente pas de le convertir
    (tmp_path / "test-source.osm.pbf").touch()

    logger = MagicMock()

    with patch("r2gg._main.subprocess_execution") as mocked_subprocess_execution, \
            patch("time.sleep"):
        valhalla_convert(config, resource, logger)

    build_config_calls = [
        call for call in mocked_subprocess_execution.call_args_list
        if call.args[0][0] == "valhalla_build_config"
    ]
    assert len(build_config_calls) == 1
    build_config_args = build_config_calls[0].args[0]

    assert "--logging-type" in build_config_args
    assert "--logging-file-name" in build_config_args
    assert "--mjolnir-logging-type" not in build_config_args
    assert "--mjolnir-logging-file-name" not in build_config_args
    assert "--mjolnir-timezone" in build_config_args


def test_valhalla_convert_builds_timezone_database_once(tmp_path):
    """The timezone database is built via valhalla_build_timezones so mjolnir
    can resolve stop timezones instead of warning for every single stop."""
    config = {"workingSpace": {"directory": str(tmp_path)}}
    resource = _build_resource(tmp_path)
    (tmp_path / "test-source.osm.pbf").touch()

    logger = MagicMock()

    with patch("r2gg._main.subprocess_execution") as mocked_subprocess_execution, \
            patch("time.sleep"):
        valhalla_convert(config, resource, logger)

    timezone_calls = [
        call for call in mocked_subprocess_execution.call_args_list
        if call.args[0] == ["python", "-m", "valhalla_build_timezones"]
    ]
    assert len(timezone_calls) == 1
    assert timezone_calls[0].kwargs["outfile"] == str(tmp_path / "tz_world.sqlite")
