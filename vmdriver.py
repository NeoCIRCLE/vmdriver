#!/usr/bin/env python

import libvirt
import logging


class VMDriver:
    '''Circle Virtal Machin driver main class
    '''
    connection = None

    def req_connection(original_function):
        '''Connection checking decorator for libvirt.
        '''
        def new_function(*args, **kwargs):
            if args[0].connection is None:
                logging.error("No connection to libvirt daemon.")
            else:
                return original_function(*args, **kwargs)
        return new_function

    def connect(self, connection_string='qemu:///system'):
        '''Connect to the libvirt daemon specified in the
        connection_string or the local root.
        '''
        if self.connection is None:
            self.connection = libvirt.open(connection_string)
        else:
            logging.error("There is already an active connection to libvirt.")

    @req_connection
    def disconnect(self, connection_string='qemu:///system'):
        '''Disconnect from the active libvirt daemon connection.
        '''
        self.connection.close()
        self.connection = None

    @req_connection
    def vm_define(self, vm):
        '''Define permanent virtual machine from xml
        '''
        self.connection.defineXML(vm.dump_xml())
        logging.info("Virtual machine %s is defined from xml", vm.name)

    @req_connection
    def vm_create(self, vm):
        '''Create and start non-permanent virtual machine from xml
        flags can be:
            VIR_DOMAIN_NONE = 0
            VIR_DOMAIN_START_PAUSED = 1
            VIR_DOMAIN_START_AUTODESTROY = 2
            VIR_DOMAIN_START_BYPASS_CACHE = 4
            VIR_DOMAIN_START_FORCE_BOOT = 8
        '''
        self.connection.createXML(vm.dump_xml(), libvirt.VIR_DOMAIN_NONE)
        logging.info("Virtual machine %s is created from xml", vm.name)

    @req_connection
    def list_domains(self):
        return self.connection.listDefinedDomains()

    @req_connection
    def lookupByName(self, name):
        try:
            self.connection.lookupByName(name)
        except libvirt.libvirtError as e:
            logging.error(e.get_error_message())
    #virDomainResume
