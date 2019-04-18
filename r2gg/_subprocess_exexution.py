import subprocess

def subprocess_exexution(args, logger):
    try:
        str_args = [str(arg) for arg in args]
        logger.info('Subprocess: \"' + " ".join(str_args) + '\"')
        process = subprocess.Popen(
            str_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        process_output, _ =  process.communicate()
        logger.info(process_output.decode("utf-8"))

    except (OSError, subprocess.CalledProcessError) as exception:
        logger.info('Exception occured: ' + str(exception))
        logger.info('Subprocess failed')
        return False
    else:
        # no exception was raised
        logger.info('Subprocess finished')
