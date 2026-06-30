import csv
from datetime import datetime
import json
import os
import pandas as pd
import geopandas as gpd
from pathlib import Path
import shutil
import zipfile
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

from .utils.file_utils import read_if_exists


def _safe_len(df):
    return int(len(df)) if df is not None else 0


def _safe_unique_count(df, column):
    if df is None or column not in df.columns:
        return 0
    return int(df[column].nunique())


def _build_counts(stops=None, trips=None, stop_times=None, calendar=None, shapes=None):
    return {
        "stops": _safe_len(stops),
        "trips": _safe_len(trips),
        "stop_times": _safe_len(stop_times),
        "services": _safe_unique_count(calendar, "service_id"),
        "shapes": _safe_unique_count(shapes, "shape_id"),
    }


def _eliminated_pct(input_count, output_count):
    if input_count <= 0:
        return 0.0
    pct = ((input_count - output_count) / input_count) * 100
    return round(max(0.0, min(100.0, pct)), 2)


def _build_elimination_metrics(input_counts, output_counts):
    return {
        "stops_eliminated_pct": _eliminated_pct(input_counts.get("stops", 0), output_counts.get("stops", 0)),
        "trips_eliminated_pct": _eliminated_pct(input_counts.get("trips", 0), output_counts.get("trips", 0)),
        "stop_times_eliminated_pct": _eliminated_pct(input_counts.get("stop_times", 0), output_counts.get("stop_times", 0)),
        "services_eliminated_pct": _eliminated_pct(input_counts.get("services", 0), output_counts.get("services", 0)),
        "shapes_eliminated_pct": _eliminated_pct(input_counts.get("shapes", 0), output_counts.get("shapes", 0)),
    }


def _calendar_expiration_date(calendar_df):
    if calendar_df is None or calendar_df.empty or "end_date" not in calendar_df.columns:
        return None
    end_dates = pd.to_datetime(calendar_df["end_date"], format="%Y%m%d", errors="coerce").dropna()
    if end_dates.empty:
        return None
    # The network expires when its latest service is no longer valid.
    return end_dates.max().strftime("%Y-%m-%d")


def _counts_from_output_dir(output_dir):
    output_dir = Path(output_dir)
    stops = read_if_exists(output_dir / "stops.txt")
    trips = read_if_exists(output_dir / "trips.txt")
    stop_times = read_if_exists(output_dir / "stop_times.txt")
    calendar = read_if_exists(output_dir / "calendar.txt")
    shapes = read_if_exists(output_dir / "shapes.txt")
    return _build_counts(stops, trips, stop_times, calendar, shapes), _calendar_expiration_date(calendar)


def _read_get_all_eliminated_networks(input_dir_global):
    report_path = Path(input_dir_global) / "get_all_gtfs_report.json"
    if not report_path.exists():
        return []
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except Exception:
        return []

    eliminated = report.get("eliminated_networks", [])
    if not isinstance(eliminated, list):
        return []

    normalized = []
    for item in eliminated:
        if not isinstance(item, dict):
            continue
        normalized.append({
            "network_name": item.get("network_name"),
            "reason": item.get("reason"),
            "stage": item.get("stage", "get_all_gtfs"),
        })
    return normalized


def _write_processing_report(results, output_dir_global, input_dir_global=None):
    sorted_results = sorted(results, key=lambda r: r["network_name"])
    network_metrics = []
    eliminated_networks = []
    expiration_candidates = []

    for result in sorted_results:
        input_counts = result.get("input_counts", _build_counts())
        output_counts = result.get("output_counts", _build_counts())
        network_expiration_date = result.get("graph_expiration_date")
        eliminated = bool(result.get("eliminated", False))
        elimination_reason = result.get("elimination_reason")

        if network_expiration_date and not eliminated:
            expiration_candidates.append(datetime.strptime(network_expiration_date, "%Y-%m-%d"))

        if eliminated:
            eliminated_networks.append({
                "network_name": result["network_name"],
                "reason": elimination_reason,
                "stage": "gtfs_clean",
            })

        network_metrics.append({
            "network_name": result["network_name"],
            "input_counts": input_counts,
            "output_counts": output_counts,
            "metrics": _build_elimination_metrics(input_counts, output_counts),
            "graph_expiration_date": network_expiration_date,
            "eliminated": eliminated,
            "elimination_reason": elimination_reason,
        })

    graph_expiration_date = None
    if expiration_candidates:
        graph_expiration_date = min(expiration_candidates).strftime("%Y-%m-%d")

    eliminated_networks.extend(_read_get_all_eliminated_networks(input_dir_global))

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "graph_expiration_date": graph_expiration_date,
        "network_metrics": network_metrics,
        "eliminated_networks": eliminated_networks,
    }

    report_path = Path(output_dir_global) / "processing_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

def hms_to_seconds(t):
    if pd.isna(t) or str(t).strip() == "":
        return None
    try:
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s
    except:
        return None

def calendar_dates_to_calendar(calendar_dates_path, output_path):
    """
    Convert calendar_dates.txt to calendar.txt format.
    Analyzes which days of the week have service for each service_id.
    """

    service_data = {}

    # Parse calendar_dates.txt and build day-of-week usage
    with open(calendar_dates_path, newline='', encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            service_id = row['service_id']
            date_str = row['date']
            exception_type = int(row.get('exception_type', '1'))

            # Only count services with exception_type=1 (service added)
            if exception_type != 1:
                continue

            if service_id not in service_data:
                service_data[service_id] = {
                    'start': None,
                    'end': None,
                    'days': {0: False, 1: False, 2: False, 3: False, 4: False, 5: False, 6: False}  # Mon-Sun
                }

            # Parse date (YYYYMMDD format)
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            # If date is in the past, skip it
            if date_obj.date() < datetime.now().date():
                continue
            day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday

            # Update day of week as having service
            service_data[service_id]['days'][day_of_week] = True

            # Track date range
            if service_data[service_id]['start'] is None or date_str < service_data[service_id]['start']:
                service_data[service_id]['start'] = date_str
            if service_data[service_id]['end'] is None or date_str > service_data[service_id]['end']:
                service_data[service_id]['end'] = date_str

    # Write calendar.txt
    with open(output_path, 'w', newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            'service_id', 'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday', 'start_date', 'end_date'
        ])
        writer.writeheader()
        for service_id, data in service_data.items():
            writer.writerow({
                'service_id': service_id,
                'monday': '1' if data['days'][0] else '0',
                'tuesday': '1' if data['days'][1] else '0',
                'wednesday': '1' if data['days'][2] else '0',
                'thursday': '1' if data['days'][3] else '0',
                'friday': '1' if data['days'][4] else '0',
                'saturday': '1' if data['days'][5] else '0',
                'sunday': '1' if data['days'][6] else '0',
                'start_date': data['start'],
                'end_date': data['end']
            })


def filter_gtfs(input_dir, output_dir, geojson_file=None, zip_output=False):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    filter_result = {
        "input_counts": _build_counts(),
        "output_counts": _build_counts(),
        "graph_expiration_date": None,
        "eliminated": False,
        "elimination_reason": None,
    }

    # Copy all files in input_dir to output_dir
    files_to_copy = [file for file in os.listdir(input_dir) if (input_dir / file).is_file()]
    has_locations_geojson = "locations.geojson" in files_to_copy

    for file in files_to_copy:
        src = input_dir / file
        dst = output_dir / file
        shutil.copy(src, dst)

    trips = read_if_exists(input_dir / "trips.txt")
    stop_times = read_if_exists(input_dir / "stop_times.txt")
    stops = read_if_exists(input_dir / "stops.txt")
    calendar = read_if_exists(input_dir / "calendar.txt")
    routes = read_if_exists(input_dir / "routes.txt")
    transfers = read_if_exists(input_dir / "transfers.txt")
    shapes_input = read_if_exists(input_dir / "shapes.txt")

    filter_result["input_counts"] = _build_counts(stops, trips, stop_times, calendar, shapes_input)

    # Parse agency pour enlever les trailing whitespaces
    agency = read_if_exists(input_dir / "agency.txt")
    if agency is not None:
        agency.to_csv(output_dir / "agency.txt", index=False)

    if has_locations_geojson:
        # GTFS flex (unsupported in Valhalla https://github.com/valhalla/valhalla/issues/5419)
        filter_result["eliminated"] = True
        filter_result["elimination_reason"] = "unsupported_gtfs_flex_locations_geojson"
        shutil.rmtree(output_dir, ignore_errors=True)
        return None, None, None, None, None, None, filter_result

    if trips is None or stop_times is None or stops is None:
        filter_result["eliminated"] = True
        filter_result["elimination_reason"] = "missing_required_files_trips_stop_times_stops"
        shutil.rmtree(output_dir, ignore_errors=True)
        return None, None, None, None, None, None, filter_result

    if calendar is None:
        filter_result["eliminated"] = True
        filter_result["elimination_reason"] = "missing_calendar"
        shutil.rmtree(output_dir, ignore_errors=True)
        return None, None, None, None, None, None, filter_result

    if 'start_pickup_drop_off_window' in stop_times.columns:
        # GTFS flex (unsupported in Valhalla https://github.com/valhalla/valhalla/issues/5419)
        #set pickup_type and drop_off_type to 0 if empty
        stop_times['pickup_type'] = stop_times['pickup_type'].fillna(0)
        stop_times['drop_off_type'] = stop_times['drop_off_type'].fillna(0)
        #remove row with pickup_type >=2 or drop_off_type >=2
        stop_times['pickup_type'] = stop_times['pickup_type'].astype(int)
        stop_times['drop_off_type'] = stop_times['drop_off_type'].astype(int)
        stop_times = stop_times[(stop_times['pickup_type'] < 2) & (stop_times['drop_off_type'] < 2)].copy()

    # Nettoyage de routes.txt pour NOIREAU (qui met un " tout seul dans le nom)
    if routes is not None and "route_long_name" in routes.columns:
        mask = routes["route_long_name"].notna()
        routes.loc[mask, "route_long_name"] = (
            routes.loc[mask, "route_long_name"]
            .str.replace('"', '', regex=False)
        )
        routes.to_csv(output_dir / "routes.txt", index=False)

    # filter out of calendar lines that have 0 for each day of week
    calendar = calendar[(calendar["monday"] == "1") | (calendar["tuesday"] == "1") |
                        (calendar["wednesday"] == "1") | (calendar["thursday"] == "1") |
                        (calendar["friday"] == "1") | (calendar["saturday"] == "1") |
                        (calendar["sunday"] == "1")]

    # Convert end_date to datetime
    calendar["enddate"] = calendar["end_date"].astype(str)
    calendar["enddate"] = calendar["enddate"].apply(
        lambda x: datetime.strptime(x, "%Y%m%d")
    )
    today = datetime.today()
    # Keep only services that haven't expired
    calendar = calendar[calendar["enddate"] >= today]
    calendar.drop(columns=["enddate"], inplace=True)

    valid_service_ids = set()
    if calendar is not None:
        valid_service_ids.update(calendar["service_id"].unique())

    filtered_trips = trips[trips["service_id"].isin(valid_service_ids)].copy()

    filtered_shapes = None
    if "shape_id" in filtered_trips.columns:
        valid_shape_ids = filtered_trips["shape_id"].unique()
        shapes = read_if_exists(input_dir / "shapes.txt")
        if shapes is not None and "shape_id" in shapes.columns:
            filtered_shapes = shapes[shapes["shape_id"].isin(valid_shape_ids)].copy()
            if "shape_dist_traveled" in filtered_shapes.columns:
                s = filtered_shapes["shape_dist_traveled"]
                filtered_shapes = filtered_shapes[s.isna() | s.eq("") | (s != s.shift(1))]
            shape_sizes = filtered_shapes.groupby("shape_id")["shape_id"].transform("size")
            filtered_shapes["shape_id_count"] = filtered_shapes.groupby("shape_id").cumcount()
            filtered_shapes = filtered_shapes[
                (shape_sizes <= 10000) |
                (filtered_shapes["shape_id_count"] % 5 == 0)
            ].copy()
            filtered_shapes.drop(columns=["shape_id_count"], inplace=True)

    valid_trip_ids = filtered_trips["trip_id"].unique()
    filtered_stop_times = stop_times[stop_times["trip_id"].isin(valid_trip_ids)].copy()

    # cap departure time to 36:24:00 (Valhalla)
    filtered_stop_times["departure_seconds"] = filtered_stop_times["departure_time"].apply(hms_to_seconds)
    mask = filtered_stop_times["departure_seconds"] > 131040
    filtered_stop_times.loc[mask, "departure_time"] = "36:24:00"
    filtered_stop_times = filtered_stop_times.drop(columns=["departure_seconds"])

    valid_stop_ids = filtered_stop_times["stop_id"].unique()
    filtered_stops = stops[stops["stop_id"].isin(valid_stop_ids)].copy()
    if "parent_station" in filtered_stops.columns:
        additional_valid_stop_ids = filtered_stops["parent_station"].unique()
        additional_filtered_stops = stops[stops["stop_id"].isin(additional_valid_stop_ids)].copy()
        filtered_stops = pd.concat([filtered_stops, additional_filtered_stops]).drop_duplicates()

    # Remove stop_timezone column from stops if it exists
    if "stop_timezone" in filtered_stops.columns:
        filtered_stops.drop(columns=["stop_timezone"], inplace=True)

    if geojson_file is not None:
      features = gpd.read_file(geojson_file)
      features = features.to_crs("EPSG:4326")
      geometry = gpd.points_from_xy(filtered_stops.stop_lon, filtered_stops.stop_lat)
      gdf = gpd.GeoDataFrame(filtered_stops, geometry=geometry, crs="EPSG:4326")
      joined = gpd.sjoin(gdf, features[["id", "geometry"]], predicate="within")
      if joined.empty:
          filter_result["eliminated"] = True
          filter_result["elimination_reason"] = "no_stops_within_filter_geometry"
          shutil.rmtree(output_dir, ignore_errors=True)
          return None, None, None, None, None, None, filter_result
      filtered_stops = joined.drop(columns=["index_right", "id", "geometry"]).copy()
      if filtered_shapes is not None:
          geometry = gpd.points_from_xy(filtered_shapes.shape_pt_lon, filtered_shapes.shape_pt_lat)
          gdf = gpd.GeoDataFrame(filtered_shapes, geometry=geometry, crs="EPSG:4326")
          joined = gpd.sjoin(gdf, features[["id", "geometry"]], predicate="within")
          filtered_shapes = joined.drop(columns=["index_right", "id", "geometry"]).copy()

    # In trips, remove the value for shape_id if it doesn't exist in filtered_shapes
    if filtered_shapes is not None and "shape_id" in filtered_trips.columns:
        valid_shape_ids = filtered_shapes["shape_id"].unique()
        filtered_trips.loc[~filtered_trips["shape_id"].isin(valid_shape_ids), "shape_id"] = ""

    filtered_transfers = None

    if transfers is not None:
        valid_from_stop_ids = set(filtered_stops["stop_id"].unique())
        valid_to_stop_ids = set(filtered_stops["stop_id"].unique())
        filtered_transfers = transfers[transfers["from_stop_id"].isin(valid_from_stop_ids) & transfers["to_stop_id"].isin(valid_to_stop_ids)].copy()
        filtered_transfers.to_csv(output_dir / "transfers.txt", index=False)

    if calendar is not None:
        calendar.to_csv(output_dir / "calendar.txt", index=False)
    if len(filtered_trips) - len(trips) != 0:
        filtered_trips.to_csv(output_dir / "trips.txt", index=False)
    filtered_stops.to_csv(output_dir / "stops.txt", index=False)
    filtered_stop_times.to_csv(output_dir / "stop_times.txt", index=False)
    if filtered_shapes is not None:
        filtered_shapes.to_csv(output_dir / "shapes.txt", index=False)

    if len(filtered_stops) == 0 or len(filtered_trips) == 0 or len(filtered_stop_times) == 0 or len(calendar) == 0:
        filter_result["eliminated"] = True
        if len(calendar) == 0:
            filter_result["elimination_reason"] = "no_active_services_in_calendar"
        elif len(filtered_stops) == 0:
            filter_result["elimination_reason"] = "no_stops_after_filtering"
        elif len(filtered_trips) == 0:
            filter_result["elimination_reason"] = "no_trips_after_filtering"
        else:
            filter_result["elimination_reason"] = "no_stop_times_after_filtering"
        shutil.rmtree(output_dir, ignore_errors=True)
        return None, None, None, None, None, None, filter_result

    filter_result["output_counts"] = _build_counts(filtered_stops, filtered_trips, filtered_stop_times, calendar, filtered_shapes)
    filter_result["graph_expiration_date"] = _calendar_expiration_date(calendar)

    if zip_output:
       zip_folder(output_dir)
       shutil.rmtree(output_dir)

    return filtered_stops, filtered_trips, filtered_stop_times, calendar, filtered_shapes, filtered_transfers, filter_result


def post_filter_stops(input_dir, stops, trips, stop_times, calendar, shapes, transfers, output_dir, zipped_input=False, zip_output=False):
    """
    inverse of filter_gtfs, to be used after filtering stops by feature
    filters stop_times, trips and calendar based on the filtered stops
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    if zipped_input:
        with zipfile.ZipFile(input_dir) as z:
            for name in z.namelist():
                if name in ["stops.txt", "trips.txt", "stop_times.txt", "calendar.txt", "shapes.txt"]:
                    continue  # handled separately
                with z.open(name) as src, open(output_dir / name, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    else:
        # Copy all files in input_dir to output_dir
        files_to_copy = [file for file in os.listdir(input_dir) if (input_dir / file).is_file()]
        for file in files_to_copy:
            if file not in ["trips.txt", "stops.txt", "stop_times.txt", "calendar.txt", "shapes.txt"]:
                src = input_dir / file
                dst = output_dir / file
                shutil.copy(src, dst)


    if trips is None or stop_times is None or stops is None:
        raise RuntimeError("Missing required GTFS files (trips, stop_times, stops)")

    if calendar is None:
        raise RuntimeError("No calendar.txt found")

    valid_stop_ids = stops["stop_id"].unique()
    filtered_stop_times = stop_times[stop_times["stop_id"].isin(valid_stop_ids)].copy()
    filtered_stop_times.to_csv(output_dir / "stop_times.txt", index=False)
    if transfers is not None:
        valid_from_stop_ids = set(stops["stop_id"].unique())
        valid_to_stop_ids = set(stops["stop_id"].unique())
        filtered_transfers = transfers[transfers["from_stop_id"].isin(valid_from_stop_ids) & transfers["to_stop_id"].isin(valid_to_stop_ids)].copy()
        filtered_transfers.to_csv(output_dir / "transfers.txt", index=False)

    valid_trip_ids = filtered_stop_times["trip_id"].unique()
    filtered_trips = trips[trips["trip_id"].isin(valid_trip_ids)].copy()
    filtered_trips.to_csv(output_dir / "trips.txt", index=False)

    if "shape_id" in filtered_trips.columns:
        valid_shape_ids = filtered_trips["shape_id"].unique()
        shapes = read_if_exists(input_dir / "shapes.txt")
        if shapes is not None and "shape_id" in shapes.columns:
            filtered_shapes = shapes[shapes["shape_id"].isin(valid_shape_ids)].copy()
            filtered_shapes.to_csv(output_dir / "shapes.txt", index=False)

    valid_service_ids = filtered_trips["service_id"].unique()
    calendar = calendar[calendar["service_id"].isin(valid_service_ids)].copy()
    calendar.to_csv(output_dir / "calendar.txt", index=False)

    if zip_output:
       zip_folder(output_dir)
       shutil.rmtree(output_dir)



def zip_folder(folder_path):
    zip_path = f"{folder_path}.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)


def process_job(job):
    input_dir, output_dir_global, geojson_file, zip_output = job
    output_dir = Path(output_dir_global) / input_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)
    default_result = {
        "network_name": input_dir.name,
        "input_counts": _build_counts(),
        "output_counts": _build_counts(),
        "graph_expiration_date": None,
        "eliminated": True,
        "elimination_reason": "processing_error",
    }

    try:
        stops = read_if_exists(input_dir / "stops.txt")
        trips = read_if_exists(input_dir / "trips.txt")
        stop_times = read_if_exists(input_dir / "stop_times.txt")
        calendar = read_if_exists(input_dir / "calendar.txt")
        shapes = read_if_exists(input_dir / "shapes.txt")
        default_result["input_counts"] = _build_counts(stops, trips, stop_times, calendar, shapes)

        calendar_dates_path = Path(input_dir) / "calendar_dates.txt"
        calendar_path = Path(input_dir) / "calendar.txt"
        calendars_path = Path(input_dir) / "calendars.txt"
        if calendars_path.exists():
            calendars_path.rename(calendar_path)

        if calendar_path.exists():
            is_empty_calendar = False
            with open(calendar_path, newline='', encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                # if calendar has no rows, remove it
                if len(list(reader)) == 0:
                    is_empty_calendar = True
            if is_empty_calendar:
                calendar_path.unlink()

        if calendar_dates_path.is_file() and not calendar_path.is_file():
            calendar_dates_to_calendar(calendar_dates_path, calendar_path)

        if calendar_dates_path.exists():
            calendar_dates_path.unlink()

        filter_output = output_dir
        if geojson_file is not None:
            filter_output = Path(output_dir_global) / "temp" / input_dir.name

        stops, trips, stop_times, calendar, shapes, transfers, filter_result = filter_gtfs(input_dir, filter_output, geojson_file, zip_output)
        if geojson_file is not None and stops is not None:
            stops.to_csv(output_dir / "stops.txt", index=False)
            post_filter_stops(filter_output, stops, trips, stop_times, calendar, shapes, transfers, output_dir)
            shutil.rmtree(filter_output)
            output_counts, graph_expiration_date = _counts_from_output_dir(output_dir)
            filter_result["output_counts"] = output_counts
            filter_result["graph_expiration_date"] = graph_expiration_date

        return {
            "network_name": input_dir.name,
            **filter_result,
        }
    except Exception as exc:
        default_result["elimination_reason"] = f"processing_error: {str(exc)}"
        shutil.rmtree(output_dir, ignore_errors=True)
        temp_output = Path(output_dir_global) / "temp" / input_dir.name
        if temp_output.exists():
            shutil.rmtree(temp_output, ignore_errors=True)
        return default_result


def main(input_dir_global, output_dir_global, geojson_file=None, zip_output=False):
    jobs = []
    for input_path in list(Path(input_dir_global).iterdir()):
        if input_path.is_dir():
            jobs.append((input_path, output_dir_global, geojson_file, zip_output))

    with Pool(min(cpu_count(), 4)) as pool:
        results = list(tqdm(pool.imap_unordered(process_job, jobs), total=len(jobs), desc="Cleaning GTFS feeds"))
    if geojson_file is not None:
        temp_dir = Path(output_dir_global) / "temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    parent = Path(output_dir_global)
    for subdir in parent.iterdir():
        if subdir.is_dir() and not any(subdir.iterdir()):
            subdir.rmdir()

    _write_processing_report(results, output_dir_global, input_dir_global)


if __name__ == "__main__":
    GTFS_FOLDER = "gtfs_in"
    OUTPUT_FOLDER = "gtfs_clean"
    import time
    start_time = time.time()
    main(GTFS_FOLDER, OUTPUT_FOLDER, "france_buffer.geojson", zip_output=False)
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
