import socket
import logging


logger = logging.getLogger(__name__)


def get_priviliged_queue_name():
    hostname = socket.gethostname()
    logger.debug("Checking for vmdriver priviliged queue %s.vm.priv",
                 hostname)
    queue_name = hostname + '.vm.priv'
    return queue_name
