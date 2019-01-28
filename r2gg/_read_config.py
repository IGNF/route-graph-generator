import json

def config_from_path(path_to_config_file):
    with open(path_to_config_file, encoding='utf-8') as config_file:
        raw_config = json.loads(config_file.read())

    normalized_config = _normalize(raw_config)
    return normalized_config

def _normalize(raw_config):
    normalized_config = raw_config
    return normalized_config
