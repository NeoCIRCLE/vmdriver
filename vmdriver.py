import libvirt
import logging
import os
import sys
from vm import VMInstance
from decorator import decorator
from vmcelery import celery, lib_connection

sys.path.append(os.path.dirname(os.path.basename(__file__)))

connection = None

state_dict = {0: 'NOSTATE',
              1: 'RUNNING',
              2: 'BLOCKED',
              3: 'PAUSED',
              4: 'SHUTDOWN',
              5: 'SHUTOFF',
              6: 'CRASHED',
              7: 'PMSUSPENDED'
              }


@decorator
def req_connection(original_function, *args, **kw):
    '''Connection checking decorator for libvirt.

       If envrionment variable LIBVIRT_KEEPALIVE is set
       it will use the connection from the celery worker.
    '''
    logging.debug("Decorator running")
    global connection
    if connection is None:
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
    try:
        return original_function(*args, **kw)
    except libvirt.libvirtError as e:
        logging.error(e.get_error_message())
        new_e = Exception(e.get_error_message())
        new_e.libvirtError = True
        raise new_e


@celery.task
@wrap_libvirtError
def connect(connection_string='qemu:///system'):
    '''Connect to the libvirt daemon specified in the
    connection_string or the local root.
    '''
    global connection
    if os.getenv('LIBVIRT_KEEPALIVE') is None:
        if connection is None:
            connection = libvirt.open(connection_string)
            logging.debug("Connection estabilished to libvirt.")
        else:
            logging.debug("There is already an active connection to libvirt.")
    else:
        connection = lib_connection
        logging.debug("Using celery libvirt connection connection.")


@celery.task
@wrap_libvirtError
def disconnect():
    '''Disconnect from the active libvirt daemon connection.
    '''
    global connection
    if os.getenv('LIBVIRT_KEEPALIVE') is None:
        if connection is None:
            logging.debug('There is no available libvirt conection.')
        else:
            connection.close()
            logging.debug('Connection closed to libvirt.')
            connection = None
    else:
        logging.debug('Keepalive connection should not close.')


@celery.task
@req_connection
@wrap_libvirtError
def define(vm):
    '''Define permanent virtual machine from xml
    '''
    connection.defineXML(vm.dump_xml())
    logging.info("Virtual machine %s is defined from xml", vm.name)


@celery.task
@req_connection
@wrap_libvirtError
def create(vm_desc):
    '''Create and start non-permanent virtual machine from xml
    flags can be:
        VIR_DOMAIN_NONE = 0
        VIR_DOMAIN_START_PAUSED = 1
        VIR_DOMAIN_START_AUTODESTROY = 2
        VIR_DOMAIN_START_BYPASS_CACHE = 4
        VIR_DOMAIN_START_FORCE_BOOT = 8
    '''
    vm = VMInstance.deserialize(vm_desc)
    # Setting proper hypervisor
    vm.vm_type = os.getenv("HYPERVISOR_TYPE", "test")
    # Emulating DOMAIN_START_PAUSED FLAG behaviour on test driver
    if vm.vm_type == "test":
        connection.createXML(
            vm.dump_xml(), libvirt.VIR_DOMAIN_NONE)
        domain = lookupByName(vm.name)
        domain.suspend()
    # Real driver create
    else:
            connection.createXML(
                vm.dump_xml(), libvirt.VIR_DOMAIN_START_PAUSED)
            logging.info("Virtual machine %s is created from xml", vm.name)
    return domain_info(vm.name)


@celery.task
@req_connection
@wrap_libvirtError
def shutdown(name):
    '''Shutdown virtual machine (need ACPI support).
    '''
    domain = lookupByName(name)
    domain.shutdown()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def delete(name):
    '''Destroy the running called 'name' virtual machine.
    '''
    domain = lookupByName(name)
    domain.destroy()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def list_domains():
    '''
    :return list: List of domains name in host
    '''
    domain_list = []
    for i in connection.listDomainsID():
        dom = connection.lookupByID(i)
        domain_list.append(dom.name())
    return domain_list


@celery.task
@req_connection
@wrap_libvirtError
def lookupByName(name):
    '''Return with the requested Domain
    '''
    return connection.lookupByName(name)


@celery.task
@req_connection
@wrap_libvirtError
def undefine(name):
    '''Undefine an already defined virtual machine.
    If it's running it becomes transient (lsot on reboot)
    '''
    domain = lookupByName(name)
    domain.undefine()


@celery.task
@req_connection
@wrap_libvirtError
def start(name):
    '''Start an already defined virtual machine.
    '''
    domain = lookupByName(name)
    domain.create()


@celery.task
@req_connection
@wrap_libvirtError
def suspend(name):
    '''Stop virtual machine and keep memory in RAM.
    '''
    domain = lookupByName(name)
    domain.suspend()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def save(name, path):
    '''Stop virtual machine and save its memory to path.
    '''
    domain = lookupByName(name)
    domain.save(path)


@celery.task
@req_connection
@wrap_libvirtError
def restore(path, name):
    '''Restore a saved virtual machine
    from the memory image stored at path.'''
    connection.restore(path)
    return domain_info(name)


@celery.task
@req_connection
@wrap_libvirtError
def resume(name):
    '''Resume stopped virtual machines.
    '''
    domain = lookupByName(name)
    domain.resume()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def reset(name):
    '''Reset (power reset) virtual machine.
    '''
    domain = lookupByName(name)
    domain.reset()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def reboot(name):
    '''Reboot (with guest acpi support) virtual machine.
    '''
    domain = lookupByName(name)
    domain.reboot()
    return _parse_info(domain.info())


@celery.task
@req_connection
@wrap_libvirtError
def node_info():
    ''' Get info from Host as dict:
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
    '''
    keys = ['model', 'memory', 'cpus', 'mhz',
            'nodes', 'sockets', 'cores', 'threads']
    values = connection.getInfo()
    return dict(zip(keys, values))


def _parse_info(values):
    '''Parse libvirt domain info into dict'''
    keys = ['state', 'maxmem', 'memory', 'virtcpunum', 'cputime']
    info = dict(zip(keys, values))
    # Change state to proper ENUM
    info['state'] = state_dict[info['state']]
    return info


@celery.task
@req_connection
@wrap_libvirtError
def domain_info(name):
    '''
    state   the running state, one of virDomainState
    maxmem  the maximum memory in KBytes allowed
    memory  the memory in KBytes used by the domain
    virtcpunum    the number of virtual CPUs for the domain
    cputime    the CPU time used in nanoseconds
    '''
    dom = lookupByName(name)
    return _parse_info(dom.info())


@celery.task
@req_connection
@wrap_libvirtError
def network_info(name, network):
    '''
    rx_bytes
    rx_packets
    rx_errs
    rx_drop
    tx_bytes
    tx_packets
    tx_errs
    tx_drop
    '''
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
    ''' Sending linux key_code to the name vm
        key_code can be optained from linux_keys.py
        e.x: linuxkeys.KEY_RIGHTCTRL
    '''
    domain = lookupByName(name)
    domain.sendKey(libvirt.VIR_KEYCODE_SET_LINUX, 100, [key_code], 1, 0)


def _stream_handler(stream, buf, opaque):
    fd = opaque
    os.write(fd, buf)


@celery.task
@req_connection
@wrap_libvirtError
def screenshot(name, path):
    """Save screenshot of virtual machine
        to the path as name-screenshot.ppm
    """
    # Import linuxkeys to get defines
    import linuxkeys
    # Connection need for the stream object
    global connection
    domain = lookupByName(name)
    # Send key to wake up console
    domain.sendKey(libvirt.VIR_KEYCODE_SET_LINUX,
                   100, [linuxkeys.KEY_RIGHTCTRL], 1, 0)
    # Create Stream to get data
    stream = connection.newStream(0)
    # Take screenshot accessible by stream (return mimetype)
    domain.screenshot(stream, 0, 0)
    # Get file to save data (TODO: send on AMQP?)
    try:
        fd = os.open(path + "/" + name + "-screenshot.ppm",
                     os.O_WRONLY | os.O_TRUNC | os.O_CREAT, 0o644)
        # Save data with handler
        stream.recvAll(_stream_handler, fd)
    finally:
        stream.finish()
        os.close(fd)


@celery.task
@req_connection
@wrap_libvirtError
def migrate(name, host, live=False):
    '''Migrate domain to host'''
    flags = libvirt.VIR_MIGRATE_PEER2PEER
    if live:
        flags = flags | libvirt.VIR_MIGRATE_LIVE
    domain = lookupByName(name)
    domain.migrateToURI(
        duri="qemu+tcp://" + host + "/system",
        flags=flags,
        dname=name,
        bandwidth=0)
    #return _parse_info(domain.info())
