import osmium
import os
import time

class _PBFWriter(osmium.SimpleHandler):
    def __init__(self, writer):
        osmium.SimpleHandler.__init__(self)
        self.writer = writer
    def node(self, n):
        self.writer.add_node(n)
    def way(self, w):
        self.writer.add_way(w)
    def relation(self, r):
        self.writer.add_relation(r)

def osm_to_pbf(in_path, out_path, logger):
    """
    Fonction de conversion depuis un fichier .osm vers un fichier .osm.pbf

    Parameters
    ----------
    in_path: str
        chemin du fichier .osm en entrée
    out_path: str
        chemin du fichier .osm.pbf en entrée
    logger: logging.Logger
    """

    logger.info("Writing pbf file: {} from osm file {}".format(out_path, in_path))
    start_time = time.time()
    if os.path.exists(out_path):
      os.remove(out_path)
    writer = osmium.SimpleWriter(out_path)
    handler = _PBFWriter(writer)
    handler.apply_file(in_path)
    os.remove(in_path)
    end_time = time.time()
    logger.info("PBF writing done. Elapsed time : %s seconds." %(end_time - start_time))
