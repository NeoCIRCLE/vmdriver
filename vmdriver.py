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
        '''Return with the requested Domain
        '''
        try:
            return self.connection.lookupByName(name)
        except libvirt.libvirtError as e:
            logging.error(e.get_error_message())

    @req_connection
    def vm_undefine(self, name):
        '''Undefine an already defined virtual machine.
        If it's running it becomes transient (lsot on reboot)
        '''
        vm = self.lookupByName(name)
        try:
            vm.undefine()
        except:
            logging.error('Can not get VM with name %s', name)

    @req_connection
    def vm_start(self, name):
        '''Start an already defined virtual machine.
        '''
        vm = self.lookupByName(name)
        vm.create()

    @req_connection
    def vm_save(self, name, path):
        '''Stop virtual machine and save its memory to path.
        '''
        vm = self.lookupByName(name)
        vm.save(path)

    def vm_resume(self, name):
        '''Resume stopped virtual machines.
        '''
        vm = self.lookupByName(name)
        vm.resume()

    def vm_reset(self, name):
        '''Reset (power reset) virtual machine.
        '''
        vm = self.lookupByName(name)
        vm.reset()

    def vm_reboot(self, name):
        '''Reboot (with guest acpi support) virtual machine.
        '''
        vm = self.lookupByName(name)
        vm.reboot()
    #virDomainResume
