import argparse

from .config import DepartmentSplitConfig, PipelineConfig
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run GTFS processing pipeline")
    parser.add_argument("--get-output-dir", default="gtfs_in")
    parser.add_argument("--clean-output-dir", default="gtfs_clean")
    parser.add_argument("--clean-geojson-file", default="france_buffer.geojson")
    parser.add_argument("--zip-clean-output", action="store_true")
    parser.add_argument("--deps-output-dir", default=None)
    parser.add_argument("--deps-geojson-file", default=None)
    parser.add_argument("--deps-feature-name-field", default=None)
    parser.add_argument("--deps-zipped", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    dep_cfg = None
    if args.deps_geojson_file and args.deps_feature_name_field and args.deps_output_dir:
        dep_cfg = DepartmentSplitConfig(
            output_dir=args.deps_output_dir,
            geojson_file=args.deps_geojson_file,
            feature_name_field=args.deps_feature_name_field,
            zipped=args.deps_zipped,
        )

    cfg = PipelineConfig(
        get_output_dir=args.get_output_dir,
        clean_output_dir=args.clean_output_dir,
        clean_geojson_file=args.clean_geojson_file,
        zip_clean_output=args.zip_clean_output,
        departement_split=dep_cfg,
    )
    run_pipeline(cfg)


if __name__ == "__main__":
    main()
