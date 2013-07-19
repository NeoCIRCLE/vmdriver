#!/usr/bin/env python

from subprocess import call
import logging


class NWDriver:

    def __init__():
        pass

    def ovs_command_execute(self, command):
        return_val = call(['sudo', 'ovs-vsctl', command])
        logging.info('OVS command: %s executed.', command)
        return return_val

    def nw_create(self, vm):
        pass

    def nw_delete(self, vm):
        pass
