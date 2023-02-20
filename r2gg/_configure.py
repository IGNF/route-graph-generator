import argparse
import logging
import os

import psycopg2

from r2gg._read_config import config_from_path

# Définition des niveaux de log
LEVELS = {
    'CRITICAL' : logging.CRITICAL,
    'ERROR' : logging.ERROR,
    'WARNING' : logging.WARNING,
    'INFO' : logging.INFO,
    'DEBUG' : logging.DEBUG
}

def configure():
    """
    Fonction de lecture du fichier de configuration passé en argument

    Returns
    -------
    config: dict
        dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
    resource: dict
        dictionnaire correspondant à la resource décrite dans le fichier passé en argument
    db_configs: dict
        dictionnaire correspondant aux configurations des bdd
    connection: psycopg2.connection
        connection à la bdd de travail
    logger: logging.Logger
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file_path', type=str)
    args = parser.parse_args()
    config_path = args.config_file_path

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
    logger.info("Log initialized")

    # Todo : Créer une fonction qui vérifie la configuration
    db_configs = {}
    # Configuration des bases de données précisées dans la config
    for base in config['bases']:
        if base['type'] == 'bdd':
            db_configs[ base['id'] ] = config_from_path(base['configFile'])
            db_configs[base['id']].update({"schema":base['schema']})

    # Récupération de l'objet permettant de générer la ressource
    resource = config['resource']

    # Création de l'espace de travail
    if not os.path.exists(config['workingSpace']['directory']):
        os.makedirs(config['workingSpace']['directory'])

    return config, resource, db_configs, logger

def connect_working_db(config, db_configs, logger):
    """
    Fonction de connexion à la BDD de travail

    Parameters
    ----------
    config: dict
        dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
    db_configs: dict
        dictionnaire correspondant aux configurations des bdd
    logger: logging.Logger
    Returns
    -------
    connection: psycopg2.connection
        connection à la bdd de travail

    """

    # Configuration de la bdd de travail
    work_db_config = db_configs[ config['workingSpace']['baseId'] ]

    # Récupération des paramètres de la bdd
    host = work_db_config.get('host')
    dbname = work_db_config.get('database')
    user = work_db_config.get('user')
    password = work_db_config.get('password')
    port = work_db_config.get('port')
    connect_args = 'host=%s dbname=%s user=%s password=%s port=%s' %(host, dbname, user, password, port)

    logger.info("Connecting to work database")
    connection = psycopg2.connect(connect_args)
    connection.set_client_encoding('UTF8')

    return connection

def disconnect_working_db(connection, logger):
    """
    Fonction de connexion à la BDD de travail

    Parameters
    ----------
    connection: psycopg2.connection
        connection à la bdd de travail
    logger: logging.Logger
    """

    connection.close()
    logger.info("Connection to work database closed")