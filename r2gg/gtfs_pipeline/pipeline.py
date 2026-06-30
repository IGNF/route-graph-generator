from . import get_all_gtfs
from . import gtfs_clean
from . import gtfs_departements
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

    if config.departement_split is not None:
        gtfs_departements.copy_gtfs_to_feature(
            config.clean_output_dir,
            config.departement_split.output_dir,
            config.departement_split.geojson_file,
            config.departement_split.feature_name_field,
            config.departement_split.zipped,
        )
