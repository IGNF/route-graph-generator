import csv
from pathlib import Path
from multiprocessing import Pool, cpu_count, Lock
from tqdm import tqdm

ID_COLUMNS = {
    "agency_id","stop_id","route_id","trip_id",
    "service_id","shape_id","fare_id","zone_id"
}

REF_COLUMNS = {
    "stop_id","route_id","trip_id","service_id",
    "shape_id","from_stop_id","to_stop_id"
}

GTFS_REQUIRED_FIELDS = {
    "agency.txt": [
        "agency_id",
        "agency_name",
        "agency_url",
        "agency_timezone"
    ],

    "stops.txt": [
        "stop_id",
        "stop_name",
        "stop_lat",
        "stop_lon"
    ],

    "routes.txt": [
        "route_id",
        "route_type",
        "route_short_name"
    ],

    "trips.txt": [
        "route_id",
        "service_id",
        "trip_id"
    ],

    "stop_times.txt": [
        "trip_id",
        "arrival_time",
        "departure_time",
        "stop_id",
        "stop_sequence"
    ],

    "calendar.txt": [
        "service_id",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "start_date",
        "end_date"
    ]
}

# Global lock for file writing
_write_lock = None


def prefix_value(prefix, value):
    if not value:
        value = ""
    return f"{prefix}{value}"


def process_job(job):
    file_path, prefix, output_file_name, output_dir = job

    with open(file_path, newline='', encoding="utf-8-sig") as fin:
        reader = csv.DictReader(fin)
        output_path = Path(output_dir) / output_file_name

        # Process all rows first
        rows_to_write = []
        for row in reader:
            row.pop(None, None)
            filtered = {}
            for col in GTFS_REQUIRED_FIELDS[file_path.name]:
                if col == "agency_id" and not row.get(col):
                    row[col] = prefix
                if col == "end_date" and not row.get(col):
                    row[col] = "20291231"
                if col == "route_short_name" and not row.get(col):
                    if row.get("route_long_name"):
                        row[col] = row.get("route_long_name")
                    else:
                        row[col] = row.get("route_id")
                val = row[col]
                if col in ID_COLUMNS or col in REF_COLUMNS:
                    val = prefix_value(prefix, val)
                filtered[col] = val
            rows_to_write.append(filtered)

        # Write all rows with lock protection
        with _write_lock:
            with open(output_path, "a", newline='', encoding="utf-8") as fout:
                writer = csv.DictWriter(
                    fout,
                    fieldnames=GTFS_REQUIRED_FIELDS[file_path.name]
                )
                for filtered_row in rows_to_write:
                    writer.writerow(filtered_row)


def initialize_output_files_in_dir(output_dir):
    """Create output files with headers only in the target directory."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for file_name, fields in GTFS_REQUIRED_FIELDS.items():
        output_path = output_dir / file_name
        with open(output_path, "w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

def init_pool(lock):
    """Initialize worker processes with the shared lock."""
    global _write_lock
    _write_lock = lock


def merge_gtfs(input_dir="gtfs", output_dir="gtfs_merged/france_entiere", max_workers=None):
    """Merge multiple GTFS folders into a single GTFS directory with prefixed ids."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    initialize_output_files_in_dir(output_dir)

    jobs = []
    i = 0
    for folder in input_dir.iterdir():
        if not folder.is_dir():
            continue
        prefix = f"{i}_"
        i += 1
        for file_name in GTFS_REQUIRED_FIELDS.keys():
            file_path = folder / file_name
            if file_path.exists():
                jobs.append((file_path, prefix, file_name, output_dir))

    # Create a lock for file writing
    worker_count = max_workers if max_workers is not None else cpu_count()
    lock = Lock()
    with Pool(worker_count, initializer=init_pool, initargs=(lock,)) as pool:
        list(tqdm(pool.imap_unordered(process_job, jobs), total=len(jobs), desc="Processing files"))


def main(input_dir="gtfs", output_dir="gtfs_merged/france_entiere", max_workers=None):
    merge_gtfs(input_dir=input_dir, output_dir=output_dir, max_workers=max_workers)

if __name__ == "__main__":
    import time
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
