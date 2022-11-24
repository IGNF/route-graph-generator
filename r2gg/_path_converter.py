import os

def convert_path(in_path, out_dir, subdir=""):
    """
    Convertit un chemin de fichier

    Parameters
    ----------
    in_path: str
        chemin initial
    out_dir: str
        dossier de sortie
    """
    out_path = out_dir
    filename = os.path.basename(in_path)

    return os.path.join(out_path, subdir, filename)
