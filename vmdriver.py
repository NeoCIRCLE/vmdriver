#!/usr/bin/env python

import libvirt
import logging


connection = None


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
    return connection.listDefinedDomains()


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
# virDomainResume
