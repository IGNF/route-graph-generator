from setuptools import setup

setup (
    name = 'r2gg',
    version = '1.1.2',
    entry_points = {
            'console_scripts': [
                'r2gg-populate_pivot=r2gg:populate_pivot',
                'r2gg-pivot2pgrouting=r2gg:pivot2pgrouting',
                'r2gg-pivot2osm=r2gg:pivot2osm',
                'r2gg-osm2osrm=r2gg:osm2osrm'
            ]
    }
)
