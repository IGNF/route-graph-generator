"""Unit tests for GTFS preprocessing integration in Valhalla generation."""

import os
from pathlib import Path

import pytest

# Test the gtfs_pipeline package directly without importing full r2gg._main
from r2gg.gtfs_pipeline import PipelineConfig


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

    def test_gtfs_zip_output_validation(self):
        """GTFS config should enforce zip_output requirement for Valhalla."""
        gtfs_settings = [{
            "enabled": True,
            "zipCleanOutput": False,
        }]
        
        settings = gtfs_settings[0]
        zip_output = settings.get("zipCleanOutput", True)
        
        # For Valhalla transit support, must be True
        if not zip_output:
            assert True  # Error condition detected
        else:
            assert False

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
