from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for running the full GTFS processing pipeline."""

    get_output_dir: str = "gtfs_in"
    clean_output_dir: str = "gtfs_clean"
    api_url: str = "https://transport.data.gouv.fr/api/datasets"
    clean_geojson_file: Optional[str] = "france_buffer.geojson"
    zip_clean_output: bool = False
