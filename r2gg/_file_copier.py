from collections import defaultdict
from shutil import copyfile, SameFileError



def copy_files_locally(in_paths, out_paths):
    """
    Copie les fichiers avec les chemins définis dans 'in_paths' et 'out_paths'

    Parameters
    ----------
    in_paths: list
        chemins sur la machine locale
    out_paths: list
        chemins sur la machine distante
    """
    for in_path, out_path in zip(in_paths, out_paths):
        try:
            copyfile(in_path, out_path)
        except SameFileError:
            print("The file " + in_path + " is already there")
        except FileNotFoundError:
            print("The file " + in_path + " was not found")
        except IsADirectoryError:
            print(in_path + " is a directory (probably valhalla tile dir). Ignored")
