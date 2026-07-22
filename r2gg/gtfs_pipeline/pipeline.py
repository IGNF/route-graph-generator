from . import get_all_gtfs
from . import gtfs_clean
from .config import PipelineConfig


def run_pipeline(config: PipelineConfig) -> None:
    """Run the end-to-end GTFS ingestion and cleaning pipeline."""
    get_all_gtfs.main(config.get_output_dir, api_url=config.api_url)
    gtfs_clean.main(
        config.get_output_dir,
        config.clean_output_dir,
        config.clean_geojson_file,
        config.zip_clean_output,
    )
