import libvirt
from decorator import decorator
import logging
import os

from vmcelery import lib_connection, to_bool


vm_xml_dump = None


class Connection(object):

    """ Singleton class to handle connection."""

#    __metaclass__ = Singleton
    connection = None

    @classmethod
    def get(cls):
        """ Return the libvirt connection."""

        return cls.connection

    @classmethod
    def set(cls, connection):
        """ Set the libvirt connection."""

        cls.connection = connection


@decorator
def req_connection(original_function, *args, **kw):
    """Connection checking decorator for libvirt.

    If envrionment variable LIBVIRT_KEEPALIVE is set
    it will use the connection from the celery worker.

    Return the decorateed function

    """
    logging.debug("Decorator running")
    if Connection.get() is None:
        connect()
        try:
            logging.debug("Decorator calling original function")
            return_value = original_function(*args, **kw)
        finally:
            logging.debug("Finally part of decorator")
            disconnect()
        return return_value
    else:
        logging.debug("Decorator calling original \
                        function with active connection")
        return_value = original_function(*args, **kw)
        return return_value


@decorator
def wrap_libvirtError(original_function, *args, **kw):
    """ Decorator to wrap libvirt error in simple Exception.

    Return decorated function

    """
    try:
        return original_function(*args, **kw)
    except libvirt.libvirtError as e:
        logging.error(e.get_error_message())
        e_msg = e.get_error_message()
        if vm_xml_dump is not None:
            e_msg += "\n"
            e_msg += vm_xml_dump
        new_e = Exception(e.get_error_message())
        new_e.libvirtError = True
        raise new_e


@wrap_libvirtError
def connect(connection_string='qemu:///system'):
    """ Connect to the libvirt daemon.

    String is specified in the connection_string parameter
    the default is the local root.

    """
    if not to_bool(os.getenv('LIBVIRT_KEEPALIVE', "False")):
        if Connection.get() is None:
            Connection.set(libvirt.open(connection_string))
            logging.debug("Connection estabilished to libvirt.")
        else:
            logging.debug("There is already an active connection to libvirt.")
    else:
        Connection.set(lib_connection)
        logging.debug("Using celery libvirt connection connection.")


@wrap_libvirtError
def disconnect():
    """ Disconnect from the active libvirt daemon connection."""
    if os.getenv('LIBVIRT_KEEPALIVE') is None:
        if Connection.get() is None:
            logging.debug('There is no available libvirt conection.')
        else:
            Connection.get().close()
            logging.debug('Connection closed to libvirt.')
            Connection.set(None)
    else:
        logging.debug('Keepalive connection should not close.')
