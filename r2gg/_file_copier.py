from collections import defaultdict
from shutil import copyfile, SameFileError

def copy_file_locally(in_path, out_path):
    """
    Copie le fichies avec les chemins définis dans 'in_path' et 'out_path'

    Parameters
    ----------
    in_paths: list
        chemins sur la machine locale
    out_paths: list
        chemins sur la machine distante
    """
    try:
        copyfile(in_path, out_path)
    except SameFileError:
        print("The file " + in_path + " is already there")
    except FileNotFoundError:
        print("The file " + in_path + " was not found")
