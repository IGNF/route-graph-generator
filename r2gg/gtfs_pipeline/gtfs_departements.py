import shutil
import zipfile
from pathlib import Path
import os
import geopandas as gpd
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

from .gtfs_clean import post_filter_stops
from .utils.file_utils import read_if_exists
from .utils.geom_utils import get_gtfs_geometry

GLOBAL_FEATURES = None


def process_job(job):
    gtfs, geom, feature_folder, feature_name_field, zipped = job
    if geom is None:
        return

    features_sindex = GLOBAL_FEATURES.sindex
    possible_matches_idx = list(features_sindex.intersection(geom))
    possible_features = GLOBAL_FEATURES.iloc[possible_matches_idx]

    if zipped:
        with zipfile.ZipFile(gtfs) as z:
            stops = read_if_exists(z.open("stops.txt"))
            trips = read_if_exists(z.open("trips.txt"))
            stop_times = read_if_exists(z.open("stop_times.txt"))
            calendar = read_if_exists(z.open("calendar.txt"))
            transfers = read_if_exists(z.open("transfers.txt"))
            try:
                shapes = read_if_exists(z.open("shapes.txt"))
            except KeyError:
                shapes = None
    else:
        stops = read_if_exists(gtfs / "stops.txt")
        trips = read_if_exists(gtfs / "trips.txt")
        stop_times = read_if_exists(gtfs / "stop_times.txt")
        calendar = read_if_exists(gtfs / "calendar.txt")
        shapes = read_if_exists(gtfs / "shapes.txt")
        transfers = read_if_exists(gtfs / "transfers.txt")

    geometry = gpd.points_from_xy(stops.stop_lon, stops.stop_lat)
    gdf = gpd.GeoDataFrame(stops, geometry=geometry, crs="EPSG:4326")
    joined = gpd.sjoin(gdf, possible_features[[feature_name_field, "geometry"]], predicate="within")
    if joined.empty:
        return
    groups = joined.groupby(feature_name_field)

    # Check intersection with each feature
    for code_dep, group in groups:
        filtered_stops = group.drop(columns=["geometry", "index_right", feature_name_field])
        if filtered_stops.empty:
            continue
        folder = Path(feature_folder) / code_dep
        dst = folder / gtfs.stem
        dst.mkdir(parents=True, exist_ok=True)
        filtered_stops.to_csv(dst / "stops.txt", index=False)
        post_filter_stops(gtfs, filtered_stops, trips, stop_times, calendar, shapes, transfers, dst, zipped_input=zipped, zip_output=zipped)


def init_worker(features):
    global GLOBAL_FEATURES
    GLOBAL_FEATURES = features


def copy_gtfs_to_feature(gtfs_folder, feature_folder, geojson_file, feature_name_field, zipped=False):
    features = gpd.read_file(geojson_file)
    features = features.to_crs("EPSG:4326")

    if zipped:
        gtfs_list = list(Path(gtfs_folder).glob("*.zip"))
    else:
        gtfs_list = list(Path(gtfs_folder).iterdir())

    jobs = []
    for gtfs in gtfs_list:
        gtfs_geom = get_gtfs_geometry(gtfs, zipped=zipped)
        jobs.append((gtfs, gtfs_geom, feature_folder, feature_name_field, zipped))

    with Pool(min(cpu_count(), 4), initializer=init_worker, initargs=(features,)) as pool:
        list(tqdm(pool.imap_unordered(process_job, jobs), total=len(jobs), desc="Extracting GTFS per departement"))

    for folder in os.listdir(feature_folder):
        if folder.startswith("temp_"):
            shutil.rmtree(Path(feature_folder) / folder)


if __name__ == "__main__":
    import time
    GTFS_FOLDER = "gtfs_clean"
    GEOJSON_FILE = "buffered_departements.geojson"
    OUTPUT_FOLDER = "gtfs_deps"
    FEATURE_NAME_FIELD = "code"
    start_time = time.time()
    copy_gtfs_to_feature(GTFS_FOLDER, OUTPUT_FOLDER, GEOJSON_FILE, FEATURE_NAME_FIELD, zipped=False)
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
