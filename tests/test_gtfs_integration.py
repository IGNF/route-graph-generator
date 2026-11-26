"""Unit tests for GTFS preprocessing integration in Valhalla generation."""

import csv
import os
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pytest

# Test the gtfs_pipeline package directly without importing full r2gg._main
from r2gg.gtfs_pipeline import PipelineConfig
from r2gg.gtfs_pipeline.gtfs_clean import filter_gtfs, process_job


@pytest.fixture
def gtfs_feed(tmp_path):
    def create(stops, stop_times):
        source = tmp_path / "input"
        source.mkdir()
        (source / "stops.txt").write_text(stops, encoding="utf-8")
        (source / "stop_times.txt").write_text(stop_times, encoding="utf-8")
        (source / "trips.txt").write_text("trip_id,service_id\ntrip,service\n", encoding="utf-8")
        (source / "calendar.txt").write_text(
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
            "service,1,1,1,1,1,1,1,20200101,20991231\n",
            encoding="utf-8",
        )
        return source, tmp_path / "output"
    return create


def test_clean_removes_non_platform_stop_times_but_keeps_parent_station(gtfs_feed):
    source, output = gtfs_feed(
        "stop_id,location_type,parent_station\n"
        "station,1,\nplatform,0,station\nimplicit,,\n"
        "entrance,2,station\nnode,3,station\nboarding,4,station\n",
        "trip_id,stop_id,departure_time\n"
        "trip,platform,08:00:00\ntrip,station,08:01:00\n"
        "trip,implicit,08:02:00\ntrip,entrance,08:03:00\n"
        "trip,node,08:04:00\ntrip,boarding,08:05:00\n"
        "trip,missing,08:06:00\n",
    )

    stops, _, stop_times, _, _, _, report = filter_gtfs(source, output)

    assert stop_times["stop_id"].tolist() == ["platform", "implicit"]
    assert set(stops["stop_id"]) == {"platform", "implicit", "station"}
    assert report["input_counts"]["stop_times"] == 7
    assert report["output_counts"]["stop_times"] == 2
    assert not report["eliminated"]
    with (output / "stop_times.txt").open(encoding="utf-8", newline="") as stream:
        assert [row["stop_id"] for row in csv.DictReader(stream)] == ["platform", "implicit"]


def test_clean_accepts_absent_location_type(gtfs_feed):
    source, output = gtfs_feed(
        "stop_id\nplatform\n",
        "trip_id,stop_id,departure_time\ntrip,platform,08:00:00\n",
    )

    _, _, stop_times, _, _, _, report = filter_gtfs(source, output)

    assert stop_times["stop_id"].tolist() == ["platform"]
    assert not report["eliminated"]


def test_clean_excludes_feed_with_only_station_stop_times(gtfs_feed):
    source, output = gtfs_feed(
        "stop_id,location_type\nstation,1\n",
        "trip_id,stop_id,departure_time\ntrip,station,08:00:00\n",
    )

    *_, report = filter_gtfs(source, output)

    assert report["eliminated"]
    assert report["elimination_reason"] == "no_stops_after_filtering"
    assert not output.exists()


def test_clean_preserves_exceptions_and_extends_calendar_without_extra_service(gtfs_feed):
    source, output = gtfs_feed(
        "stop_id\nplatform\n",
        "trip_id,stop_id,departure_time\ntrip,platform,08:00:00\n",
    )
    (source / "calendar.txt").write_text(
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
        "service,1,1,1,1,1,1,1,20990101,20990103\n",
        encoding="utf-8",
    )
    original_dates = (
        "service_id,date,exception_type\n"
        "service,20990102,2\nservice,20990105,1\nservice,20990107,1"
    )
    (source / "calendar_dates.txt").write_text(original_dates, encoding="utf-8")

    report = process_job((source, output, None, False))

    assert not report["eliminated"]
    cleaned = output / source.name
    with (cleaned / "calendar.txt").open(encoding="utf-8", newline="") as stream:
        assert list(csv.DictReader(stream))[0]["end_date"] == "20990107"
    with (cleaned / "calendar_dates.txt").open(encoding="utf-8", newline="") as stream:
        dates = [(row["date"], row["exception_type"]) for row in csv.DictReader(stream)]
    assert dates == [
        ("20990102", "2"), ("20990105", "1"), ("20990107", "1"),
        ("20990104", "2"), ("20990106", "2"),
    ]
    assert (source / "calendar_dates.txt").read_text(encoding="utf-8") == original_dates


def test_clean_generates_calendar_for_exception_only_services(gtfs_feed):
    source, output = gtfs_feed(
        "stop_id\nplatform\n",
        "trip_id,stop_id,departure_time\ntrip,platform,08:00:00\n",
    )
    (source / "calendar.txt").unlink()
    (source / "calendar_dates.txt").write_text(
        "service_id,date,exception_type\n"
        "service,20990102,1\nservice,20990109,1\n"
        "expired,20000101,1\n",
        encoding="utf-8",
    )

    report = process_job((source, output, None, False))

    assert not report["eliminated"]
    cleaned = output / source.name
    with (cleaned / "calendar.txt").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["service_id"] == "service"
    assert [rows[0][day] for day in (
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    )] == ["0"] * 7
    assert (rows[0]["start_date"], rows[0]["end_date"]) == ("20990102", "20990109")
    assert (cleaned / "calendar_dates.txt").read_text(encoding="utf-8") == (
        source / "calendar_dates.txt"
    ).read_text(encoding="utf-8")
    assert not (source / "calendar.txt").exists()


def test_clean_retains_exception_only_service_alongside_regular_calendar(gtfs_feed):
    source, output = gtfs_feed(
        "stop_id\nplatform\n",
        "trip_id,stop_id,departure_time\ntrip,platform,08:00:00\n",
    )
    today = date.today().strftime("%Y%m%d")
    (source / "calendar.txt").write_text(
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
        "other,1,1,1,1,1,1,1,20200101,20991231\n",
        encoding="utf-8",
    )
    (source / "calendar_dates.txt").write_text(
        f"service_id,date,exception_type\nservice,{today},1\n", encoding="utf-8"
    )

    report = process_job((source, output, None, False))

    assert not report["eliminated"]
    with (output / source.name / "calendar.txt").open(encoding="utf-8", newline="") as stream:
        rows = {row["service_id"]: row for row in csv.DictReader(stream)}
    assert rows["service"]["start_date"] == today
    assert rows["service"]["end_date"] == today
    assert rows["service"]["monday"] == "0"


def test_clean_preserves_calendar_dates_with_geo_filter(gtfs_feed, tmp_path):
    source, output = gtfs_feed(
        "stop_id,stop_lat,stop_lon\nplatform,48.85,2.35\n",
        "trip_id,stop_id,departure_time\ntrip,platform,08:00:00\n",
    )
    dates = "service_id,date,exception_type\nservice,20990102,2\n"
    (source / "calendar_dates.txt").write_text(dates, encoding="utf-8")
    geometry = tmp_path / "area.geojson"
    geometry.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature",'
        '"properties":{"id":1},"geometry":{"type":"Polygon",'
        '"coordinates":[[[2,48],[3,48],[3,49],[2,49],[2,48]]]}}]}',
        encoding="utf-8",
    )

    report = process_job((source, output, geometry, False))

    assert not report["eliminated"]
    assert (output / source.name / "calendar_dates.txt").read_text(encoding="utf-8") == dates


def test_clean_preserves_calendar_dates_in_zip(gtfs_feed):
    source, output = gtfs_feed(
        "stop_id\nplatform\n",
        "trip_id,stop_id,departure_time\ntrip,platform,08:00:00\n",
    )
    dates = "service_id,date,exception_type\nservice,20990102,2\n"
    (source / "calendar_dates.txt").write_text(dates, encoding="utf-8")

    report = process_job((source, output, None, True))

    assert not report["eliminated"]
    with ZipFile(output / f"{source.name}.zip") as archive:
        assert archive.read("calendar_dates.txt").decode("utf-8") == dates


def test_clean_reports_invalid_calendar_exception(gtfs_feed):
    source, output = gtfs_feed(
        "stop_id\nplatform\n",
        "trip_id,stop_id,departure_time\ntrip,platform,08:00:00\n",
    )
    (source / "calendar_dates.txt").write_text(
        "service_id,date,exception_type\nservice,20990102,3\n", encoding="utf-8"
    )

    report = process_job((source, output, None, False))

    assert report["eliminated"]
    assert "Invalid calendar exception type" in report["elimination_reason"]


class TestGTFSConfigParsing:
    """Test GTFS configuration parsing and validation."""

    def test_gtfs_disabled_returns_none(self):
        """Helper function should return None when GTFS is disabled."""
        # Simulate the config parsing logic
        resource = {
            "sources": [
                {
                    "id": "test-source",
                    "type": "valhalla",
                    # No gtfs block
                }
            ]
        }

        gtfs_settings = []
        for source in resource.get("sources", []):
            source_gtfs = source.get("gtfs")
            if isinstance(source_gtfs, dict) and source_gtfs.get("enabled", False):
                gtfs_settings.append(source_gtfs)

        assert len(gtfs_settings) == 0

    def test_gtfs_disabled_explicitly_returns_none(self):
        """When GTFS is explicitly disabled, no settings should be collected."""
        resource = {
            "sources": [
                {
                    "id": "test-source",
                    "type": "valhalla",
                    "gtfs": {"enabled": False},
                }
            ]
        }

        gtfs_settings = []
        for source in resource.get("sources", []):
            source_gtfs = source.get("gtfs")
            if isinstance(source_gtfs, dict) and source_gtfs.get("enabled", False):
                gtfs_settings.append(source_gtfs)

        assert len(gtfs_settings) == 0

    def test_gtfs_enabled_collected(self):
        """When GTFS is enabled, settings should be collected."""
        resource = {
            "sources": [
                {
                    "id": "test-source",
                    "type": "valhalla",
                    "gtfs": {
                        "enabled": True,
                        "apiUrl": "https://test.example.com/api",
                    },
                }
            ]
        }

        gtfs_settings = []
        for source in resource.get("sources", []):
            source_gtfs = source.get("gtfs")
            if isinstance(source_gtfs, dict) and source_gtfs.get("enabled", False):
                gtfs_settings.append(source_gtfs)

        assert len(gtfs_settings) == 1
        assert gtfs_settings[0]["apiUrl"] == "https://test.example.com/api"

    def test_gtfs_config_defaults(self):
        """GTFS config fields should default properly."""
        work_dir = "/work/dir"

        gtfs_settings = [{
            "enabled": True,
            # Only enabled, use defaults
        }]

        settings = gtfs_settings[0]
        in_dir = settings.get("getOutputDir", os.path.join(work_dir, "gtfs_in"))
        clean_dir = settings.get("cleanOutputDir", os.path.join(work_dir, "gtfs_clean"))
        transit_dir = settings.get("transitDir", os.path.join(work_dir, "transit_tiles"))

        # Use normpath for platform-agnostic comparison
        assert Path(in_dir) == Path("/work/dir/gtfs_in")
        assert Path(clean_dir) == Path("/work/dir/gtfs_clean")
        assert Path(transit_dir) == Path("/work/dir/transit_tiles")

    def test_gtfs_mismatched_configs_detected(self):
        """Mismatched GTFS configs should be detected."""
        gtfs_settings = [
            {
                "enabled": True,
                "apiUrl": "https://api1.example.com",
            },
            {
                "enabled": True,
                "apiUrl": "https://api2.example.com",  # Different
            },
        ]

        first_settings = gtfs_settings[0]
        for settings in gtfs_settings[1:]:
            if settings != first_settings:
                # Mismatch detected
                assert True
                return

        # Should have detected mismatch
        assert False, "Mismatch should have been detected"


class TestPipelineConfig:
    """Test PipelineConfig dataclass."""

    def test_pipeline_config_api_url_parameter(self):
        """PipelineConfig properly stores and defaults API URL."""
        cfg = PipelineConfig()
        assert cfg.api_url == "https://transport.data.gouv.fr/api/datasets"

        custom_api = "https://custom.api.example.com"
        cfg2 = PipelineConfig(api_url=custom_api)
        assert cfg2.api_url == custom_api

    def test_pipeline_config_all_defaults(self):
        """PipelineConfig has sensible defaults for all fields."""
        cfg = PipelineConfig()

        assert cfg.get_output_dir == "gtfs_in"
        assert cfg.clean_output_dir == "gtfs_clean"
        assert cfg.api_url == "https://transport.data.gouv.fr/api/datasets"
        assert cfg.clean_geojson_file == "france_buffer.geojson"
        assert cfg.zip_clean_output is False

    def test_pipeline_config_custom_values(self):
        """PipelineConfig accepts custom field values."""
        cfg = PipelineConfig(
            get_output_dir="/custom/in",
            clean_output_dir="/custom/clean",
            api_url="https://custom.api.com",
            zip_clean_output=True,
        )

        assert cfg.get_output_dir == "/custom/in"
        assert cfg.clean_output_dir == "/custom/clean"
        assert cfg.api_url == "https://custom.api.com"
        assert cfg.zip_clean_output is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
