import os
from datetime import datetime
import json
import re
import requests
import zipfile
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

def _resource_name(dataset_slug, title):
    resource_slug = re.sub(r'[\\/:"*?<>|]+', "", title.lower().replace(" ", "-"))
    return dataset_slug + "-" + resource_slug


def _is_expired_end_date(end_date):
    if not end_date:
        return False
    try:
        parts = end_date.split("-")
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 12
    except Exception:
        return False

    now = datetime.now()
    if year < now.year:
        return True
    if year == now.year and month < now.month:
        return True
    return False


def filter_transport_datasets(data, out_dir):
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "datasets_total": len(data),
        "public_transit_datasets_total": 0,
        "selected_resources_count": 0,
        "eliminated_networks": [],
    }

    datasets = [dataset for dataset in data if dataset.get("type") == "public-transit"]
    report["public_transit_datasets_total"] = len(datasets)

    offers_to_remove = []
    for dataset in datasets:
        if "agrégat_region" in dataset.get("tags", []):
            for offer in dataset.get("offers", []):
                offers_to_remove.append(offer.get("identifiant_offre"))

    filtered_datasets = []
    for dataset in datasets:
        if "agrégat_region" in dataset.get("tags", []):
            filtered_datasets.append(dataset)
            continue
        # if there is no offer, keep the dataset
        if len(dataset.get("offers")) == 0:
            filtered_datasets.append(dataset)
            continue

        all_offers_to_remove = []
        for offer in dataset.get("offers", []):
            if offer.get("identifiant_offre") in offers_to_remove:
                all_offers_to_remove.append(True)
            else:
                all_offers_to_remove.append(False)
        if all(all_offers_to_remove):
            report["eliminated_networks"].append({
                "network_name": dataset.get("slug"),
                "reason": "dataset_offer_covered_by_region_aggregate",
                "stage": "get_all_gtfs",
            })
            continue
        if len(dataset.get("sub_types", [])) == 1 and dataset.get("sub_types")[0] == "school":
            report["eliminated_networks"].append({
                "network_name": dataset.get("slug"),
                "reason": "dataset_sub_type_school_only",
                "stage": "get_all_gtfs",
            })
            continue
        filtered_datasets.append(dataset)

    list_urls = {}
    resource_updated = {}
    selected_resources = {}
    for dataset in filtered_datasets:
        dataset_slug = dataset.get("slug")
        for resource in dataset.get("resources", []):
            if resource.get("format") == "GTFS":
                resource_name = _resource_name(dataset_slug, resource.get("title", ""))
                resource_end_date = resource.get("metadata", {}).get("end_date", "2099-12-31")
                if resource.get("metadata", {}).get("issues_count", {}).get("InvalidCoordinates", 0) >= 1:
                    report["eliminated_networks"].append({
                        "network_name": resource_name,
                        "reason": "metadata_issue_invalid_coordinates",
                        "stage": "get_all_gtfs",
                    })
                    continue
                if resource.get("metadata", {}).get("issues_count", {}).get("MissingMandatoryFile", 0) >= 1:
                    report["eliminated_networks"].append({
                        "network_name": resource_name,
                        "reason": "metadata_issue_missing_mandatory_file",
                        "stage": "get_all_gtfs",
                    })
                    continue
                if resource.get("metadata", {}).get("issues_count", {}).get("InvalidShapeId", 0) >= 1:
                    report["eliminated_networks"].append({
                        "network_name": resource_name,
                        "reason": "metadata_issue_invalid_shape_id",
                        "stage": "get_all_gtfs",
                    })
                    continue
                if resource.get("metadata", {}).get("issues_count", {}).get("NoCalendar", 0) >= 1:
                    report["eliminated_networks"].append({
                        "network_name": resource_name,
                        "reason": "metadata_issue_no_calendar",
                        "stage": "get_all_gtfs",
                    })
                    continue
                if resource.get("metadata", {}).get("issues_count", {}).get("InvalidTimezone", 0) >= 1:
                    report["eliminated_networks"].append({
                        "network_name": resource_name,
                        "reason": "metadata_issue_invalid_timezone",
                        "stage": "get_all_gtfs",
                    })
                    continue
                if _is_expired_end_date(resource_end_date):
                    report["eliminated_networks"].append({
                        "network_name": resource_name,
                        "reason": "resource_expired_end_date",
                        "stage": "get_all_gtfs",
                    })
                    continue
                if resource.get("community_resource_publisher", "VINCENT_MIRAS") != "VINCENT_MIRAS":
                    report["eliminated_networks"].append({
                        "network_name": resource_name,
                        "reason": "community_resource_publisher_not_supported",
                        "stage": "get_all_gtfs",
                    })
                    continue
                if resource_name not in resource_updated:
                    resource_updated[resource_name] = resource.get("updated")
                    selected_resources[resource_name] = {
                        "updated": resource.get("updated"),
                    }
                    list_urls[resource_name] = (
                        {
                            "url": resource.get("url"),
                            "resource_name": resource_name,
                        },
                        out_dir
                    )
                else:
                    new_time = datetime.strptime(resource.get("updated"), "%Y-%m-%dT%H:%M:%S.%fZ")
                    old_time = datetime.strptime(resource_updated[resource_name], "%Y-%m-%dT%H:%M:%S.%fZ")
                    if new_time > old_time:
                        report["eliminated_networks"].append({
                            "network_name": resource_name,
                            "reason": "resource_superseded_by_newer_version",
                            "stage": "get_all_gtfs",
                        })
                        resource_updated[resource_name] = resource.get("updated")
                        selected_resources[resource_name]["updated"] = resource.get("updated")
                        list_urls[resource_name] = (
                            {
                                "url": resource.get("url"),
                                "resource_name": resource_name,
                            },
                            out_dir
                        )
                    else:
                        report["eliminated_networks"].append({
                            "network_name": resource_name,
                            "reason": "resource_older_than_selected_version",
                            "stage": "get_all_gtfs",
                        })

    report["selected_resources_count"] = len(list_urls)
    return list_urls, report


def download_and_extract(args):
    """Download and extract a single GTFS file."""
    url_info, out_dir = args
    url = url_info.get("url")
    resource_name = url_info.get("resource_name")

    response = requests.get(url)
    if response.status_code != 200:
        if response.status_code == 403:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            return {
                "resource_name": resource_name,
                "success": False,
                "reason": f"http_status_{response.status_code}",
            }

    if "text" in response.headers.get("Content-Type", ""):
        return {
            "resource_name": resource_name,
            "success": False,
            "reason": "unexpected_text_content_type",
        }

    filename = resource_name + ".zip"
    if resource_name.endswith(".zip"):
        filename = resource_name
    filepath = os.path.join(out_dir, filename)

    with open(filepath, "wb") as f:
        f.write(response.content)

    try:
        # extract the zip and remove the zip file
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            extract_path = filepath.replace('.zip', '')
            zip_ref.extractall(extract_path)

            # if there is a nested folder, move all files to the gtfs folder and remove the nested folder
            extracted_items = os.listdir(extract_path)
            if extracted_items:
                nested_folder = os.path.join(extract_path, extracted_items[0])
                if os.path.isdir(nested_folder):
                    for file in os.listdir(nested_folder):
                        os.rename(os.path.join(nested_folder, file), os.path.join(extract_path, file))
                    os.rmdir(nested_folder)
    except zipfile.BadZipFile:
        if os.path.exists(filepath):
            os.remove(filepath)
        return {
            "resource_name": resource_name,
            "success": False,
            "reason": "invalid_zip_file",
        }

    if os.path.exists(filepath):
        os.remove(filepath)
    return {
        "resource_name": resource_name,
        "success": True,
        "reason": None,
    }


def _write_get_all_report(report, out_dir):
    report_path = os.path.join(out_dir, "get_all_gtfs_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def main(out_dir, api_url="https://transport.data.gouv.fr/api/datasets"):
    response = requests.get(api_url)
    data = response.json()
    list_urls, report = filter_transport_datasets(data, out_dir)
    download_jobs = list(list_urls.values())
    os.makedirs(out_dir, exist_ok=True)
    # Download all GTFS files using multiprocessing
    with Pool(min(cpu_count(), 4)) as pool:
        download_results = list(tqdm(pool.imap_unordered(download_and_extract, download_jobs), total=len(download_jobs), desc="Downloading and extracting GTFS files"))

    report["download_attempted_count"] = len(download_jobs)
    report["download_success_count"] = sum(1 for result in download_results if result.get("success"))
    report["download_failed_count"] = report["download_attempted_count"] - report["download_success_count"]
    for result in download_results:
        if not result.get("success"):
            report["eliminated_networks"].append({
                "network_name": result.get("resource_name"),
                "reason": result.get("reason", "download_or_extract_failed"),
                "stage": "get_all_gtfs",
            })

    _write_get_all_report(report, out_dir)
    return report

if __name__ == "__main__":
    import time
    start_time = time.time()
    main("gtfs_in")
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
