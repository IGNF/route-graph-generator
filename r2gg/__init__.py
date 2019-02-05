from _configure import configure
from _main import execute

__version__ = "0.0.1"

def main():
    config, resource, db_configs, connection, logger = configure()
    execute(config, resource, db_configs, connection, logger)

if __name__ == '__main__':
    main()
