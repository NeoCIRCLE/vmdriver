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
        for network in vm.network_list:
            self.port_create(network)
        pass

    def nw_delete(self, vm):
        pass

    def port_create(self, network):
        '''
        add-port BRIDGE PORT
        set Port vnet18 tag=9
        add-flow cloud in_port=245,dl_src=02:00:0a:09:01:8a,udp,tp_dst=68,priority=43000,actions=drop".
        add-flow cloud in_port=245,dl_src=02:00:0a:09:01:8a,ip,nw_src=10.9.1.138,priority=42000,actions=normal".
        add-flow cloud in_port=245,dl_src=02:00:0a:09:01:8a,ipv6,ipv6_src=2001:738:2001:4031:9:1:138:0/112,priority=42000,actions=normal".
        add-flow cloud in_port=245,dl_src=02:00:0a:09:01:8a,arp,nw_src=10.9.1.138,priority=41000,actions=normal".
        add-flow cloud in_port=245,dl_src=02:00:0a:09:01:8a,udp,tp_dst=67,priority=40000,actions=normal".
        add-flow cloud in_port=245,priority=39000,actions=drop".
        '''
        self.ovs_command_execute('')
        self.ovs_command_execute('')
        self.ovs_command_execute('')
        self.ovs_command_execute('')
        self.ovs_command_execute('')
        self.ovs_command_execute('')
        self.ovs_command_execute('')
