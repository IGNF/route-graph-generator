import argparse
import logging

import psycopg2

from _read_config import config_from_path

# Définition des niveaux de log
LEVELS = {
    'CRITICAL' : logging.CRITICAL,
    'ERROR' : logging.ERROR,
    'WARNING' : logging.WARNING,
    'INFO' : logging.INFO,
    'DEBUG' : logging.DEBUG
}

def configure():

    parser = argparse.ArgumentParser()
    parser.add_argument('config_file_path', type=str)
    config_path = parser.parse_args().config_file_path

    # Récupération de l'objet 'génération' qui contient toute la config
    config = config_from_path(config_path)['generation']

    # Récupération de la configuration du log
    logs_config = config_from_path( config['general']['logs']['configFile'] )

    # Gestion du fichiers de logs non spécifié
    try:
        logs_file = logs_config['filename']
    except KeyError:
        logs_file = '/dev/null'

    # Configuration du module logging
    logging.basicConfig(
        format='%(asctime)s %(message)s',
        level=LEVELS[ logs_config['level'].upper() ],
        handlers=[
            logging.FileHandler(logs_file),
            logging.StreamHandler()
        ])

    # Initialisation du logger
    logger = logging.getLogger(__name__)

    # Configuration des bases de données précisées dans la config
    db_configs = { base['id']: config_from_path(base['configFile']) for base in config['bases'] if base['type'] == 'bdd' }

    # Récupération de l'objet permettant de générer la ressource
    resource = config['resource']

    # Configuration de la bdd de travail
    work_db_config = db_configs[ config['workingSpace']['baseId'] ]

    # Récupération des paramètres de la bdd
    host = work_db_config.get('host')
    dbname = work_db_config.get('dbname')
    user = work_db_config.get('username')
    password = work_db_config.get('password')
    port = work_db_config.get('port')
    connect_args = 'host=%s dbname=%s user=%s password=%s' %(host, dbname, user, password)

    logger.info("Connecting to work database")
    connection = psycopg2.connect(connect_args)
    connection.set_client_encoding('UTF8')

    return config, resource, db_configs, connection, logger
