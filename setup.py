from setuptools import setup

setup (
    name = 'r2gg',
    version = '0.0.1',
    entry_points = {
            'console_scripts': [
                'r2gg:populate_pivot=r2gg:populate_pivot',
                'r2gg:pivot2pgrouting=r2gg:pivot2pgrouting',
                'r2gg:pivot2osrm=r2gg:pivot2osrm'
            ]
    }
)
