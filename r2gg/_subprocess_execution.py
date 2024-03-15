import subprocess

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
            with open(outfile, "w") as out:
                process = subprocess.Popen(
                str_args,
                stdout=out,
                stderr=subprocess.STDOUT,
            )

        else:
            process = subprocess.Popen(
                str_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            process_output, _ =  process.communicate()
            logger.info(process_output.decode("utf-8"))

        returncode = process.returncode
        if process.returncode != 0:
            error_msg = f"Invalid returncode {returncode} for subprocess '{subprocess_arg}'"
            logger.error(error_msg)
            raise RuntimeError(error_msg)


    except (OSError, subprocess.CalledProcessError) as exception:
        logger.info('Exception occured: ' + str(exception))
        logger.info('Subprocess failed')
        return False
    else:
        # no exception was raised
        logger.info('Subprocess finished')
