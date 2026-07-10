import argparse

from .config import PipelineConfig
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run GTFS processing pipeline")
    parser.add_argument("--get-output-dir", default="gtfs_in")
    parser.add_argument("--clean-output-dir", default="gtfs_clean")
    parser.add_argument("--clean-geojson-file", default="france_buffer.geojson")
    parser.add_argument("--zip-clean-output", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    cfg = PipelineConfig(
        get_output_dir=args.get_output_dir,
        clean_output_dir=args.clean_output_dir,
        clean_geojson_file=args.clean_geojson_file,
        zip_clean_output=args.zip_clean_output,
    )
    run_pipeline(cfg)


if __name__ == "__main__":
    main()
