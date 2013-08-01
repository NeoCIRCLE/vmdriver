#!/usr/bin/env python

import libvirt
import logging


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


def req_connection(original_function):
    '''Connection checking decorator for libvirt.
    '''

    def new_function(*args, **kwargs):
        logging.debug("Decorator running")
        global connection
        if connection is None:
            connect()
        try:
            logging.debug("Decorator calling original function")
            return_value = original_function(*args, **kwargs)
        finally:
            logging.debug("Finally part of decorator")
            disconnect()
        return return_value
    return new_function


def connect(connection_string='qemu:///system'):
    '''Connect to the libvirt daemon specified in the
    connection_string or the local root.
    '''
    global connection
    if connection is None:
        connection = libvirt.open(connection_string)
        logging.debug("Connection estabilished to libvirt.")
    else:
        logging.error("There is already an active connection to libvirt.")


def disconnect():
    '''Disconnect from the active libvirt daemon connection.
    '''
    global connection
    if connection is None:
        logging.debug('There is no available libvirt conection.')
    else:
        connection.close()
        logging.debug('Connection closed to libvirt.')
        connection = None


@req_connection
def define(vm):
    '''Define permanent virtual machine from xml
    '''
    connection.defineXML(vm.dump_xml())
    logging.info("Virtual machine %s is defined from xml", vm.name)


@req_connection
def create(vm):
    '''Create and start non-permanent virtual machine from xml
    flags can be:
        VIR_DOMAIN_NONE = 0
        VIR_DOMAIN_START_PAUSED = 1
        VIR_DOMAIN_START_AUTODESTROY = 2
        VIR_DOMAIN_START_BYPASS_CACHE = 4
        VIR_DOMAIN_START_FORCE_BOOT = 8
    '''
    connection.createXML(vm.dump_xml(), libvirt.VIR_DOMAIN_START_PAUSED)
    logging.info("Virtual machine %s is created from xml", vm.name)


@req_connection
def delete(name):
    '''Destroy the running called 'name' virtual machine.
    '''
    domain = lookupByName(name)
    domain.destroy()


@req_connection
def list_domains():
    '''
    :return list: List of domains name in host
    '''
    domain_list = []
    for i in connection.listDomainsID():
        dom = connection.lookupByID(i)
        domain_list += dom.name()
    return domain_list


@req_connection
def lookupByName(name):
    '''Return with the requested Domain
    '''
    try:
        return connection.lookupByName(name)
    except libvirt.libvirtError as e:
        logging.error(e.get_error_message())


@req_connection
def undefine(name):
    '''Undefine an already defined virtual machine.
    If it's running it becomes transient (lsot on reboot)
    '''
    domain = lookupByName(name)
    domain.undefine()


@req_connection
def start(name):
    '''Start an already defined virtual machine.
    '''
    domain = lookupByName(name)
    domain.create()


@req_connection
def save(name, path):
    '''Stop virtual machine and save its memory to path.
    '''
    domain = lookupByName(name)
    domain.save(path)


@req_connection
def resume(name):
    '''Resume stopped virtual machines.
    '''
    domain = lookupByName(name)
    domain.resume()


@req_connection
def reset(name):
    '''Reset (power reset) virtual machine.
    '''
    domain = lookupByName(name)
    domain.reset()


@req_connection
def reboot(name):
    '''Reboot (with guest acpi support) virtual machine.
    '''
    domain = lookupByName(name)
    domain.reboot()


@req_connection
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


@req_connection
def domain_info(name):
    '''
    state   the running state, one of virDomainState
    maxmem  the maximum memory in KBytes allowed
    memory  the memory in KBytes used by the domain
    virtcpunum    the number of virtual CPUs for the domain
    cputime    the CPU time used in nanoseconds
    '''
    keys = ['state', 'maxmem', 'memory', 'virtcpunum', 'cputime']
    dom = lookupByName(name)
    values = dom.info()
    # Change state to proper ENUM
    info = dict(zip(keys, values))
    info['state'] = state_dict[info['state']]
    return info
# virDomainResume
