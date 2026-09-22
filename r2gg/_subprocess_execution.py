import re
import subprocess
from collections import Counter, OrderedDict

# Substitue les nombres pour regrouper les lignes qui ne diffèrent que par un identifiant/compteur
_NUMBER_RE = re.compile(r"\d+")


def _log_subprocess_output(output, logger):
    """
    Journalise la sortie d'un sous-processus en évitant de répéter des lignes quasi identiques
    (ex: un message de progression loggé une fois par tuile/gare, sur des milliers d'occurrences).
    Chaque type de ligne n'est loggé qu'une fois, avec le nombre total d'occurrences.
    """
    lines = [line for line in output.splitlines() if line.strip()]

    first_line_by_pattern = OrderedDict()
    occurrences = Counter()
    for line in lines:
        pattern = _NUMBER_RE.sub("#", line)
        occurrences[pattern] += 1
        first_line_by_pattern.setdefault(pattern, line)

    for pattern, line in first_line_by_pattern.items():
        count = occurrences[pattern]
        if count > 1:
            logger.info(line + f" (repeated {count} times)")
        else:
            logger.info(line)


def subprocess_execution(args, logger, outfile = None):
    """
    Exécute un sous-processus (commande système)

    Parameters
    ----------
    args: [str]
        arguments pour l'exécution d'un sous-processus, avec en premier argument
        le nom de la commande

    logger: logging.Logger
    """
    try:
        str_args = [str(arg) for arg in args]
        subprocess_arg = " ".join(str_args)
        logger.info('Subprocess: \"' + subprocess_arg + '\"')
        if outfile is not None:
            # stderr est capturé séparément (et non fusionné dans le fichier) car
            # certaines commandes (ex: valhalla_build_timezones) écrivent des données
            # binaires sur stdout : les mélanger avec les messages de progression de
            # stderr corromprait le fichier de sortie.
            with open(outfile, "w") as out:
                process = subprocess.Popen(
                str_args,
                stdout=out,
                stderr=subprocess.PIPE,
            )
            _, process_stderr = process.communicate()
            if process_stderr:
                _log_subprocess_output(process_stderr.decode("utf-8"), logger)

        else:
            process = subprocess.Popen(
                str_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            process_output, _ =  process.communicate()
            _log_subprocess_output(process_output.decode("utf-8"), logger)

        # Wait for process stop
        while process.returncode is None:
            process.wait()

        if process.returncode != 0:
            error_msg = f"Invalid returncode {process.returncode} for subprocess '{subprocess_arg}'"
            logger.error(error_msg)
            raise RuntimeError(error_msg)


    except (OSError, subprocess.CalledProcessError) as exception:
        logger.info('Exception occured: ' + str(exception))
        logger.info('Subprocess failed')
        return False
    else:
        # no exception was raised
        logger.info('Subprocess finished')
