from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DepartmentSplitConfig:
    """Configuration for splitting cleaned GTFS by a GeoJSON feature."""

    output_dir: str
    geojson_file: str
    feature_name_field: str
    zipped: bool = False


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for running the full GTFS processing pipeline."""

    get_output_dir: str = "gtfs_in"
    clean_output_dir: str = "gtfs_clean"
    api_url: str = "https://transport.data.gouv.fr/api/datasets"
    clean_geojson_file: Optional[str] = "france_buffer.geojson"
    zip_clean_output: bool = False
    departement_split: Optional[DepartmentSplitConfig] = None
