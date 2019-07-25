import os

def convert_paths(config, resource, output_dirs):
    """
    Convertit un les chemins d'input d'une resource en chemin d'outputs
    Avec effets de bords : modifie la ressource passée en argument

    Retourne 2 tableaux de même taille, le premier correspond aux fichiers initiaux (input) et le
    second aux fichiers de sortie, afin de pouvoir réaliser la copie avec la focntion _file_copier.copy_files()

    Parameters
    ----------
    resource: dict
        dictionnaire correspondant à une resource
    output_dirs: dict
        mapping vers les répertoires de sortie. Doit contenir les clefs :
        Pour pgrouting : dbConfigDir, profileDir, resourceDir
        Pour osrm : dataDir, profileDir, resourceDir

    Returns
    -------
    in_paths: list
        liste des chemins initiaux des fichiers
    out_paths: list
        liste des chemis convertis
    """
    in_paths = []
    out_paths = []

    resource_type = resource["type"]
    if resource_type == "pgr":
        in_paths.append(resource["topology"]["storage"]["base"]["dbConfig"])
        resource["topology"]["storage"]["base"]["dbConfig"] = _convert_path(resource["topology"]["storage"]["base"]["dbConfig"], output_dirs["dbConfigDir"])
        out_paths.append(resource["topology"]["storage"]["base"]["dbConfig"])

    elif resource_type == "osrm":
        in_paths.append(resource["topology"]["storage"]["file"])
        resource["topology"]["storage"]["file"] = _convert_path(resource["topology"]["storage"]["file"], output_dirs["dataDir"])
        out_paths.append(resource["topology"]["storage"]["file"])

    for source in resource["sources"]:
        if source["type"] == "pgr":
            in_paths.append(source["storage"]["dbConfig"])
            source["storage"]["dbConfig"] = _convert_path(source["storage"]["dbConfig"], output_dirs["dbConfigDir"])
            out_paths.append(source["storage"]["dbConfig"])
        elif source["type"] == "osrm":
            in_paths.append(source["storage"]["file"])
            source["storage"]["file"] = _convert_path(source["storage"]["file"], output_dirs["dataDir"])
            out_paths.append(source["storage"]["file"])

        in_paths.append(source["cost"]["compute"]["storage"]["file"])
        source["cost"]["compute"]["storage"]["file"] = _convert_path(source["cost"]["compute"]["storage"]["file"], output_dirs["profileDir"])
        out_paths.append(source["cost"]["compute"]["storage"]["file"])
        in_paths.append(source["cost"]["configuration"]["storage"]["file"])
        source["cost"]["configuration"]["storage"]["file"] = _convert_path(source["cost"]["configuration"]["storage"]["file"], output_dirs["profileDir"])
        out_paths.append(source["cost"]["configuration"]["storage"]["file"])

    in_paths.append(config["outputs"]["configuration"]["storage"]["file"])
    config["outputs"]["configuration"]["storage"]["file"] = _convert_path(config["outputs"]["configuration"]["storage"]["file"], output_dirs["resourceDir"])
    out_paths.append(config["outputs"]["configuration"]["storage"]["file"])

    return in_paths, out_paths


def _convert_path(in_path, out_dir):
    """
    Convertit un chemin de fichier

    Parameters
    ----------
    in_path: str
        chemin initial
    out_dir: str
        dossier de sortie
    """
    out_path = out_dir
    filename = os.path.basename(in_path)
    out_path += filename

    return out_path
