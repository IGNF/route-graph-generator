from setuptools import setup

setup (
    name = 'r2gg',
    version = '1.2.2-DEVELOP',
    entry_points = {
            'console_scripts': [
                'r2gg-sql2pivot=r2gg:sql2pivot',
                'r2gg-pivot2pgrouting=r2gg:pivot2pgrouting',
                'r2gg-pivot2osm=r2gg:pivot2osm',
                'r2gg-osm2osrm=r2gg:osm2osrm',
                'r2gg-osm2valhalla=r2gg:osm2valhalla',
                'r2gg-road2config=r2gg:road2config'
            ]
    }
)
