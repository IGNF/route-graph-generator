import os
import shutil


def export_gtfs_reports(config, resource, gtfs_in_dir, gtfs_clean_dir, logger):
    """Export GTFS recap files to valhalla output directories.

    Reports are copied next to each source valhalla configuration file so they can be
    uploaded by the caller (e.g. pivot) alongside valhalla artifacts.
    """

    work_dir = config["workingSpace"]["directory"]
    report_files = [
        os.path.join(gtfs_clean_dir, "processing_report.json"),
        os.path.join(gtfs_in_dir, "get_all_gtfs_report.json"),
    ]

    # Keep backward compatibility with previous location for processing_report.
    processing_report = report_files[0]
    if os.path.exists(processing_report):
        output_report = os.path.join(work_dir, "processing_report.json")
        shutil.copyfile(processing_report, output_report)
        logger.info("GTFS processing report exported to: " + output_report)

    target_dirs = set()
    for source in resource.get("sources", []):
        if source.get("type") != "valhalla":
            continue
        source_storage = source.get("storage") or {}
        source_config = source_storage.get("config")
        if source_config:
            target_dirs.add(os.path.dirname(source_config) or ".")

    for target_dir in target_dirs:
        os.makedirs(target_dir, exist_ok=True)
        for report_path in report_files:
            if not os.path.exists(report_path):
                continue
            output_path = os.path.join(target_dir, os.path.basename(report_path))
            shutil.copyfile(report_path, output_path)
            logger.info("GTFS report exported to: " + output_path)
