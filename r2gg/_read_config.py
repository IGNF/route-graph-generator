import json

def config_from_path(path_to_config_file):
    """
    Retourne une configuration (normalisée) à partir d'un chemin vers une configuration JSON

    Parameters
    ----------
    path_to_config_file: str

    Returns
    -------
    dict
        configuration normalisée
    """
    with open(path_to_config_file, encoding='utf-8') as config_file:
        raw_config = json.loads(config_file.read())

    return _normalize(raw_config)

def _normalize(raw_config):
    """
    TODO
    Normalise une configuration

    Parameters
    ----------
    raw_config: dict

    Returns
    -------
    dict
        configuration normalisée
    """
    normalized_config = raw_config
    return normalized_config
