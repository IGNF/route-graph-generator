import json
import importlib.util
from pathlib import Path

import requests


REPORT_EXPORT_PATH = (
    Path(__file__).resolve().parent.parent
    / "r2gg"
    / "gtfs_pipeline"
    / "report_export.py"
)
REPORT_EXPORT_SPEC = importlib.util.spec_from_file_location(
    "r2gg_gtfs_report_export",
    str(REPORT_EXPORT_PATH),
)
REPORT_EXPORT_MODULE = importlib.util.module_from_spec(REPORT_EXPORT_SPEC)
REPORT_EXPORT_SPEC.loader.exec_module(REPORT_EXPORT_MODULE)
export_gtfs_reports = REPORT_EXPORT_MODULE.export_gtfs_reports

GET_ALL_GTFS_PATH = (
    Path(__file__).resolve().parent.parent
    / "r2gg"
    / "gtfs_pipeline"
    / "get_all_gtfs.py"
)
GET_ALL_GTFS_SPEC = importlib.util.spec_from_file_location(
    "r2gg_gtfs_pipeline_get_all_gtfs",
    str(GET_ALL_GTFS_PATH),
)
GET_ALL_GTFS_MODULE = importlib.util.module_from_spec(GET_ALL_GTFS_SPEC)
GET_ALL_GTFS_SPEC.loader.exec_module(GET_ALL_GTFS_MODULE)
download_and_extract = GET_ALL_GTFS_MODULE.download_and_extract


class _DummyLogger:
    def info(self, _msg):
        return None


def test_export_gtfs_reports_to_valhalla_output(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    gtfs_in_dir = tmp_path / "gtfs_in"
    gtfs_clean_dir = tmp_path / "gtfs_clean"
    valhalla_out_dir = tmp_path / "s3_output"

    gtfs_in_dir.mkdir()
    gtfs_clean_dir.mkdir()
    valhalla_out_dir.mkdir()

    get_all_report = gtfs_in_dir / "get_all_gtfs_report.json"
    processing_report = gtfs_clean_dir / "processing_report.json"

    get_all_report.write_text(json.dumps({"download_success_count": 12}), encoding="utf-8")
    processing_report.write_text(json.dumps({"dropped_providers": 3}), encoding="utf-8")

    config = {
        "workingSpace": {
            "directory": str(work_dir),
        }
    }
    resource = {
        "sources": [
            {
                "type": "valhalla",
                "storage": {
                    "config": str(valhalla_out_dir / "valhalla.json"),
                },
            }
        ]
    }

    export_gtfs_reports(
        config,
        resource,
        str(gtfs_in_dir),
        str(gtfs_clean_dir),
        _DummyLogger(),
    )

    assert (valhalla_out_dir / "get_all_gtfs_report.json").is_file()
    assert (valhalla_out_dir / "processing_report.json").is_file()
    # Backward compatibility: also exported in working directory root.
    assert (work_dir / "processing_report.json").is_file()


def test_download_and_extract_returns_failure_on_redirect_loop(monkeypatch, tmp_path):
    def raise_too_many_redirects(_url, **_kwargs):
        raise requests.exceptions.TooManyRedirects("Exceeded 30 redirects")

    monkeypatch.setattr("requests.get", raise_too_many_redirects)

    result = download_and_extract(({"url": "https://example.com/gtfs.zip", "resource_name": "test-resource"}, str(tmp_path)))

    assert result == {
        "resource_name": "test-resource",
        "success": False,
        "reason": "redirect_loop",
    }
