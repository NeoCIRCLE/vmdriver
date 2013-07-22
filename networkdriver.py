#!/usr/bin/env python

import subprocess
import logging
import re


class NWDriver:

    def __init__(self):
        pass

    def ovs_command_execute(self, command):
        '''Execute OpenVSwitch commands
        command -   List of strings
        '''
        return_val = subprocess.call(['sudo', 'ovs-vsctl'] + command)
        logging.info('OVS command: %s executed.', command)
        return return_val

    def nw_create(self, vm):
        for network in vm.network_list:
            self.port_create(network)

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
        # Create the port for virtual network
        cmd_list = ['add_port', network.bridge, network.name]
        self.ovs_command_execute(cmd_list)

        # Set VLAN parameter for tap interface
        cmd_list = ['set', 'Port', network.name, network.vlan]
        self.ovs_command_execute(cmd_list)

        # Getting network FlowPortNumber
        port_number = self.get_port_number(network)

        # Set Flow rules to avoid mac or IP spoofing
        # Set flow rule 1 (dhcp server ban)
        cmd_list = ['add-flow', network.bridge,
                    'in_port=%(port_number)s,dl_src=%(mac)s,udp,tp_dst=68,\
                            priority=43000,actions=drop' % {
                    'port_number': port_number, 'mac': network.mac}]
        self.ovs_command_execute(cmd_list)

        # Set flow rules 2 (ipv4 filter)
        cmd_list = ['add-flow', network.bridge,
                    'in_port=%(port_number)s,dl_src=%(mac)s,ip,\
                            nw_src=%(ipv4)s,priority=42000,actions=normal' % {
            'port_number': port_number,
            'mac': network.mac, 'ipv4': network.ipv4}]
        self.ovs_command_execute(cmd_list)

        # Set flow rules 3 (ipv6 filter)
        cmd_list = ['add-flow', network.bridge,
                    'in_port=%(port_number)s,dl_src=%(mac)s,ipv6,\
                            nw_src=%(ipv6)s,priority=42000,actions=normal' % {
            'port_number': port_number,
            'mac': network.mac, 'ipv6': network.ipv6}]
        self.ovs_command_execute(cmd_list)

        # Set flow rules 4 (enabling arp)
        cmd_list = ['add-flow', network.bridge,
                    'in_port=%(port_number)s,dl_src=%(mac)s,arp,\
                            nw_src=%(ipv4)s,priority=41000,actions=normal' % {
            'port_number': port_number,
            'mac': network.mac, 'ipv4': network.ipv4}]
        self.ovs_command_execute(cmd_list)

        # Set flow rules 5 (enabling arp)
        cmd_list = ['add-flow', network.bridge,
                    'in_port=%(port_number)s,dl_src=%(mac)s,udp,tp_dst=67,\
                            priority=40000,actions=normal' % {
                    'port_number': port_number, 'mac': network.mac}]
        self.ovs_command_execute(cmd_list)

        # Set flow rule 6 (disable other protocols)
        cmd_list = ['add-flow', network.bridge,
                    'in_port=%(port_number)s,priority=39000,actions=drop' % {
                        'port_number': port_number}]
        self.ovs_command_execute(cmd_list)

    def get_port_number(self, network):
        '''Returns the OpenFlow port number for a given network
        '''
        output = subprocess.check_output(
            ['ovs-ofctl', 'dump-ports', network.bridge, network.name])
        return re.search('port ([0-9]+)', output).group(1)