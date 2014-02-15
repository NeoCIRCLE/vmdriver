""" Driver for libvirt. """
import libvirt
import logging
import os
import sys
import socket
import json
from decorator import decorator

from psutil import NUM_CPUS, virtual_memory, cpu_percent

from celery.contrib.abortable import AbortableTask

from vm import VMInstance
from vmcelery import celery, lib_connection

sys.path.append(os.path.dirname(os.path.basename(__file__)))


state_dict = {0: 'NOSTATE',
              1: 'RUNNING',
              2: 'BLOCKED',
              3: 'PAUSED',
              4: 'SHUTDOWN',
              5: 'SHUTOFF',
              6: 'CRASHED',
              7: 'PMSUSPENDED'
              }


# class Singleton(type):
#
#    """ Singleton class."""
#
#    _instances = {}
#
#    def __call__(cls, *args, **kwargs):
#        if cls not in cls._instances:
#            cls._instances[cls] = super(Singleton, cls).__call__(*args,
#                                                                 **kwargs)
#        return cls._instances[cls]


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
        new_e = Exception(e.get_error_message())
        new_e.libvirtError = True
        raise new_e


@wrap_libvirtError
def connect(connection_string='qemu:///system'):
    """ Connect to the libvirt daemon.

    String is specified in the connection_string parameter
    the default is the local root.

    """
    if os.getenv('LIBVIRT_KEEPALIVE') is None:
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


@celery.task
@req_connection
@wrap_libvirtError
def define(vm):
    """ Define permanent virtual machine from xml. """
    Connection.get().defineXML(vm.dump_xml())
    logging.info("Virtual machine %s is defined from xml", vm.name)


@celery.task
@req_connection
@wrap_libvirtError
def create(vm_desc):
    """ Create and start non-permanent virtual machine from xml.

    Return the domain info dict.
    flags can be:
        VIR_DOMAIN_NONE = 0
        VIR_DOMAIN_START_PAUSED = 1
        VIR_DOMAIN_START_AUTODESTROY = 2
        VIR_DOMAIN_START_BYPASS_CACHE = 4
        VIR_DOMAIN_START_FORCE_BOOT = 8

    """
    vm = VMInstance.deserialize(vm_desc)
    # Setting proper hypervisor
    vm.vm_type = os.getenv("HYPERVISOR_TYPE", "test")
    xml = vm.dump_xml()
    logging.info(xml)
    # Emulating DOMAIN_START_PAUSED FLAG behaviour on test driver
    if vm.vm_type == "test":
        Connection.get().createXML(
            xml, libvirt.VIR_DOMAIN_NONE)
        domain = lookupByName(vm.name)
        domain.suspend()
    # Real driver create
    else:
        Connection.get().createXML(
            vm.dump_xml(), libvirt.VIR_DOMAIN_START_PAUSED)
        logging.info("Virtual machine %s is created from xml", vm.name)
    # context
    try:
        sock = socket.create_connection(('127.0.0.1', 1235), 3)
        data = {'boot_token': vm.boot_token,
                'socket': '/var/lib/libvirt/serial/%s' % vm.name}
        sock.sendall(json.dumps(data))
        sock.close()
    except socket.error:
        logging.error('Unable to connect to context server')
    return domain_info(vm.name)


class shutdown(AbortableTask):
    """ Shutdown virtual machine (need ACPI support).
    Return When domain is missiing.
    This job is abortable:
        AbortableAsyncResult(id="<<jobid>>").abort()
    """
    time_limit = 120

    @req_connection
    def run(self, **kwargs):
        from time import sleep
        name = kwargs['name']
        try:
            domain = lookupByName(name)
            domain.shutdown()
            while True:
                try:
                    Connection.get().lookupByName(name)
                except libvirt.libvirtError as e:
                    if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                        return
                    else:
                        raise
                else:
                    if self.is_aborted(**kwargs):
                        logging.info("Shutdown aborted on vm: %s", name)
                        return
                    sleep(5)
        except libvirt.libvirtError as e:
            new_e = Exception(e.get_error_message())
            new_e.libvirtError = True
            raise new_e


@celery.task
@req_connection
@wrap_libvirtError
def delete(name):
    """ Destroy the running called 'name' virtual machine. """
    domain = lookupByName(name)
    domain.destroy()


@celery.task
@req_connection
@wrap_libvirtError
def list_domains():
    """ List the running domains.

    :return list: List of domains name in host.

    """
    domain_list = []
    for i in Connection.get().listDomainsID():
        dom = Connection.get().lookupByID(i)
        domain_list.append(dom.name())
    return domain_list


@celery.task
@req_connection
@wrap_libvirtError
def list_domains_info():
    """ List the running domains.

    :return list: List of domains info dict.

    """
    domain_list = []
    for i in Connection.get().listDomainsID():
        dom = Connection.get().lookupByID(i)
        domain_dict = _parse_info(dom.info())
        domain_dict['name'] = dom.name()
        domain_list.append(domain_dict)
    return domain_list


@celery.task
@req_connection
@wrap_libvirtError
def lookupByName(name):
    """ Return with the requested Domain. """
    return Connection.get().lookupByName(name)


@celery.task
@req_connection
@wrap_libvirtError
def undefine(name):
    """ Undefine an already defined virtual machine.

    If it's running it becomes transient (lost on reboot)

    """
    domain = lookupByName(name)
    domain.undefine()


@celery.task
@req_connection
@wrap_libvirtError
def start(name):
    """ Start an already defined virtual machine."""

    domain = lookupByName(name)
    domain.create()


@celery.task
@req_connection
@wrap_libvirtError
def suspend(name):
    """ Stop virtual machine and keep memory in RAM.

    Return the domain info dict.

    """

    domain = lookupByName(name)
    domain.suspend()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def save(name, path):
    """ Stop virtual machine and save its memory to path. """

    domain = lookupByName(name)
    domain.save(path)


@celery.task
@req_connection
@wrap_libvirtError
def restore(name, path):
    """ Restore a saved virtual machine.

    Restores the virtual machine from the memory image
    stored at path.
    Return the domain info dict.

    """
    Connection.get().restore(path)
    return domain_info(name)


@celery.task
@req_connection
@wrap_libvirtError
def resume(name):
    """ Resume stopped virtual machines.

    Return the domain info dict.

    """

    domain = lookupByName(name)
    domain.resume()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def reset(name):
    """ Reset (power reset) virtual machine.

    Return the domain info dict.

    """

    domain = lookupByName(name)
    domain.reset()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def reboot(name):
    """ Reboot (with guest acpi support) virtual machine.

    Return the domain info dict.

    """
    domain = lookupByName(name)
    domain.reboot()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def node_info():
    """ Get info from Host as dict.

    Return dict:

    model   string indicating the CPU model
    memory  memory size in kilobytes
    cpus    the number of active CPUs
    mhz     expected CPU frequency
    nodes    the number of NUMA cell, 1 for unusual NUMA
             topologies or uniform memory access;
             check capabilities XML for the actual NUMA topology
    sockets  number of CPU sockets per node if nodes > 1,
             1 in case of unusual NUMA topology
    cores    number of cores per socket, total number of
             processors in case of unusual NUMA topolog
    threads  number of threads per core, 1 in case of unusual numa topology

    """

    keys = ['model', 'memory', 'cpus', 'mhz',
            'nodes', 'sockets', 'cores', 'threads']
    values = Connection.get().getInfo()
    return dict(zip(keys, values))


def _parse_info(values):
    """ Parse libvirt domain info into dict.

    Return the info dict.

    """

    keys = ['state', 'maxmem', 'memory', 'virtcpunum', 'cputime']
    info = dict(zip(keys, values))
    # Change state to proper ENUM
    info['state'] = state_dict[info['state']]
    return info


@celery.task
@req_connection
@wrap_libvirtError
def domain_info(name):
    """ Get the domain info from libvirt.

    Return the domain info dict:
    state   the running state, one of virDomainState
    maxmem  the maximum memory in KBytes allowed
    memory  the memory in KBytes used by the domain
    virtcpunum    the number of virtual CPUs for the domain
    cputime    the CPU time used in nanoseconds

    """
    dom = lookupByName(name)
    return _parse_info(dom.info())


@celery.task
@req_connection
@wrap_libvirtError
def network_info(name, network):
    """ Return the network info dict.

    rx_bytes
    rx_packets
    rx_errs
    rx_drop
    tx_bytes
    tx_packets
    tx_errs
    tx_drop

    """
    keys = ['rx_bytes', 'rx_packets', 'rx_errs', 'rx_drop',
            'tx_bytes', 'tx_packets', 'tx_errs', 'tx_drop']
    dom = lookupByName(name)
    values = dom.interfaceStats(network)
    info = dict(zip(keys, values))
    return info


@celery.task
@req_connection
@wrap_libvirtError
def send_key(name, key_code):
    """ Sending linux key_code to the name vm.

    key_code can be optained from linux_keys.py
    e.x: linuxkeys.KEY_RIGHTCTRL

    """
    domain = lookupByName(name)
    domain.sendKey(libvirt.VIR_KEYCODE_SET_LINUX, 100, [key_code], 1, 0)


def _stream_handler(stream, buf, opaque):
    opaque.write(buf)


@celery.task
@req_connection
@wrap_libvirtError
def screenshot(name):
    """Save screenshot of virtual machine.
    Returns a ByteIO object that contains the screenshot in png format.
    """
    from io import BytesIO
    from PIL import Image
    # Import linuxkeys to get defines
    import linuxkeys
    # Connection need for the stream object
    domain = lookupByName(name)
    # Send key to wake up console
    domain.sendKey(libvirt.VIR_KEYCODE_SET_LINUX,
                   100, [linuxkeys.KEY_RIGHTCTRL], 1, 0)
    # Create Stream to get data
    stream = Connection.get().newStream(0)
    # Take screenshot accessible by stream (return mimetype)
    domain.screenshot(stream, 0, 0)
    # Get file to save data (send on AMQP?)
    fd = BytesIO()
    try:
        # Save data with handler
        stream.recvAll(_stream_handler, fd)
    finally:
        stream.finish()
    #Convert ppm to png
    #Seek to the beginning of the stream
    fd.seek(0)
    # Get the image
    image = BytesIO()
    ppm = Image.open(fd)
    ppm.save(image, format='PNG')
    return image


@celery.task
@req_connection
@wrap_libvirtError
def migrate(name, host, live=False):
    """ Migrate domain to host. """
    flags = libvirt.VIR_MIGRATE_PEER2PEER
    if live:
        flags = flags | libvirt.VIR_MIGRATE_LIVE
    domain = lookupByName(name)
    domain.migrateToURI(
        duri="qemu+tcp://" + host + "/system",
        flags=flags,
        dname=name,
        bandwidth=0)
    # return _parse_info(domain.info())


@celery.task
def ping():
    return True


@celery.task
def get_core_num():
    return NUM_CPUS


@celery.task
def get_ram_size():
    return virtual_memory().total


@celery.task
def get_node_metrics():
    result = {}
    result['cpu.usage'] = cpu_percent(0)
    result['memory.usage'] = virtual_memory().percent
    return result
