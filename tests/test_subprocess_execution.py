from unittest.mock import MagicMock, patch

import pytest

from r2gg._subprocess_execution import subprocess_execution


def test_stream_output_logs_before_process_finishes():
    logger = MagicMock()
    process = MagicMock(returncode=None)

    def output_lines():
        yield b"Extracting\n"
        logger.info.assert_any_call("Extracting")
        process.wait.assert_not_called()
        yield b"\n"
        yield b"Finished \xff\n"

    def finish():
        process.returncode = 0

    process.stdout = output_lines()
    process.wait.side_effect = finish
    with patch("r2gg._subprocess_execution.subprocess.Popen", return_value=process):
        subprocess_execution(["osrm-extract", "graph.osm"], logger, stream_output=True)

    process.communicate.assert_not_called()
    process.wait.assert_called_once()
    logger.info.assert_any_call("Finished \ufffd")
    logger.info.assert_any_call("Subprocess finished")


def test_stream_output_reports_failure():
    logger = MagicMock()
    process = MagicMock(returncode=1)
    process.stdout = iter([b"Extraction failed\n"])
    with patch("r2gg._subprocess_execution.subprocess.Popen", return_value=process):
        with pytest.raises(RuntimeError, match="Invalid returncode 1"):
            subprocess_execution(["osrm-extract"], logger, stream_output=True)

    logger.info.assert_any_call("Extraction failed")
    logger.error.assert_called_once()


def test_default_output_still_groups_repeated_lines():
    logger = MagicMock()
    process = MagicMock(returncode=0)
    process.communicate.return_value = (b"Tile 1\nTile 2\n", None)
    with patch("r2gg._subprocess_execution.subprocess.Popen", return_value=process):
        subprocess_execution(["valhalla_build_tiles"], logger)

    process.communicate.assert_called_once()
    logger.info.assert_any_call("Tile 1 (repeated 2 times)")
