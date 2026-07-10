from pathlib import Path
import geopandas as gpd
import zipfile
from .file_utils import read_if_exists

def get_gtfs_geometry(gtfs_folder, zipped=False):
    """
    Returns a shapely geometry representing GTFS coverage
    using stops.txt
    """

    try:
        if zipped:
            with zipfile.ZipFile(gtfs_folder, 'r') as zip_ref:
                if "stops.txt" not in zip_ref.namelist():
                    return None
                with zip_ref.open('stops.txt') as f:
                    stops = read_if_exists(f)
        else:
            stops_path = Path(gtfs_folder) / "stops.txt"
            if not stops_path.exists():
                return None
            stops = read_if_exists(stops_path)

        if stops is None or "stop_lat" not in stops.columns or "stop_lon" not in stops.columns:
            return None

        geometry = gpd.points_from_xy(stops.stop_lon, stops.stop_lat)
        gdf = gpd.GeoDataFrame(stops, geometry=geometry, crs="EPSG:4326")

        return gdf.total_bounds

    except Exception as e:
        print(f"Error processing {gtfs_folder}: {e}")
        return None
