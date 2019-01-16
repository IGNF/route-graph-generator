import argparse
import logging
import sys

import psycopg2 as pg

from _read_config import config_from_path

levels = {
	'CRITICAL' : logging.CRITICAL,
    'ERROR' : logging.ERROR,
    'WARNING' : logging.WARNING,
    'INFO' : logging.INFO,
    'DEBUG' : logging.DEBUG
}

parser = argparse.ArgumentParser()
parser.add_argument('config_file_path', type=str)
config_path = parser.parse_args().config_file_path

config = config_from_path(config_path)['generation']

logs_config = config_from_path( config['general']['logs']['configFile'] )

try:
	logs_file = logs_config['filename']
except KeyError:
	logs_file = '/dev/null'

logging.basicConfig(
	format='%(asctime)s %(message)s',
	level=levels[ logs_config['level'].upper() ],
	handlers=[
        logging.FileHandler(logs_file),
        logging.StreamHandler()
    ])

db_configs = { base['id']: config_from_path(base['configFile']) for base in config['bases'] if base['type'] == 'bdd' }

source_config = db_configs[ config['resource']['topology']['mapping']['source']['baseId'] ]

host = source_config.get('host')
dbname = source_config.get('dbname')
user = source_config.get('username')
password = source_config.get('password')
connect_args = 'host=%s dbname=%s user=%s password=%s' %(host, dbname, user, password)

resource = config['resource']
