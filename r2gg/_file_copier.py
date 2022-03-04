from paramiko import SSHClient
from scp import SCPClient
from collections import defaultdict
from shutil import copyfile, SameFileError

def copy_files_with_ssh(in_paths, out_paths, ssh_config):
    """
    Copie les fichiers depuis l'hôte avec les chemins définis dans 'in_paths' vers une machine distante
    dans les chemins définis dans 'out_paths' via la connection ssh définie dans ssh_config

    Parameters
    ----------
    in_paths: list
        chemins sur la machine locale
    out_paths: list
        chemins sur la machine distante
    ssh_config: dict
        configuration de la connection ssh
        contient au moins un champ hostname, et si possible les champs port, username, password
    """

    # Passage en defaultdict pour la gestion des champs facultatifs et valeurs par défaut
    ssh_config = defaultdict(bool, ssh_config)

    hostname = ssh_config["hostname"]
    port = ssh_config["port"] or 22
    username = ssh_config["username"] or None
    password = ssh_config["password"] or None

    ssh = SSHClient()
    ssh.load_system_host_keys()

    ssh.connect(hostname, port=port, username=username, password=password)

    with SCPClient(ssh.get_transport()) as scp:
        for in_path, out_path in zip(in_paths, out_paths):
            scp.put(in_path, out_path)

    ssh.close()

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
