#!/usr/bin/env python

import libvirt
import vm
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
        '''
        self.connection.createXML(vm.dump_xml())
        logging.info("Virtual machine %s is created from xml", vm.name)

    @req_connection
    def list_domains(self):
        return self.connection.listDefinedDomains()

#Create VM
a = vm.VMNetwork(name="vm-88", mac="02:00:00:00:00:00")
b = vm.VMDisk(name="asd", source='/asdasd/adasds/asd')
testvm = vm.VMInstance(name="Thisthename", vcpu="1",
                       memory_max="2048",
                       disk_list=[a],
                       network_list=[b])
