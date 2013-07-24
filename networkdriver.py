#!/usr/bin/env python

import subprocess
import logging


def ovs_command_execute(command):
    '''Execute OpenVSwitch commands
    command -   List of strings
    '''
    command = ['sudo', 'ovs-vsctl'] + command
    return_val = subprocess.call(command)
    logging.info('OVS command: %s executed.', command)
    return return_val


def ofctl_command_execute(command):
    '''Execute OpenVSwitch flow commands
    command -   List of strings
    '''
    command = ['sudo', 'ovs-ofctl'] + command
    return_val = subprocess.call(command)
    logging.info('OVS flow command: %s executed.', command)
    return return_val


def create(vm):
    for network in vm.network_list:
        port_create(network)


def delete(vm):
    for network in vm.network_list:
        port_delete(network)


def build_flow_rule():


def ban_dhcp_server(network, port_number):
    cmd_list = ['add-flow', network.bridge,
                'in_port=%(port_number)s,dl_src=%(mac)s,udp,tp_dst=68,\
                        priority=43000,actions=drop' % {
                'port_number': port_number, 'mac': network.mac}]
    return cmd_list


def port_create(network):
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
    cmd_list = ['add-port', network.bridge, network.name]
    ovs_command_execute(cmd_list)

    # Set VLAN parameter for tap interface
    cmd_list = ['set', 'Port', network.name, 'tag='+str(network.vlan)]
    ovs_command_execute(cmd_list)

    # Getting network FlowPortNumber
    port_number = get_fport_for_network(network)

    # Set Flow rules to avoid mac or IP spoofing
    # Set flow rule 1 (dhcp server ban)
    ofctl_command_execute(ban_dhcp_server(network, port_number))
    # Set flow rules 2 (ipv4 filter)
    cmd_list = ['add-flow', network.bridge,
                'in_port=%(port_number)s,dl_src=%(mac)s,ip,\
                        nw_src=%(ipv4)s,priority=42000,actions=normal' % {
        'port_number': port_number,
        'mac': network.mac, 'ipv4': network.ipv4}]
    ofctl_command_execute(cmd_list)

    # Set flow rules 3 (ipv6 filter)
    cmd_list = ['add-flow', network.bridge,
                'in_port=%(port_number)s,dl_src=%(mac)s,ipv6,\
                        ipv6_src=%(ipv6)s,priority=42000,actions=normal' % {
        'port_number': port_number,
        'mac': network.mac, 'ipv6': network.ipv6}]
    ofctl_command_execute(cmd_list)

    # Set flow rules 4 (enabling arp)
    cmd_list = ['add-flow', network.bridge,
                'in_port=%(port_number)s,dl_src=%(mac)s,arp,\
                        nw_src=%(ipv4)s,priority=41000,actions=normal' % {
        'port_number': port_number,
        'mac': network.mac, 'ipv4': network.ipv4}]
    ofctl_command_execute(cmd_list)

    # Set flow rules 5 (enabling arp)
    cmd_list = ['add-flow', network.bridge,
                'in_port=%(port_number)s,dl_src=%(mac)s,udp,tp_dst=67,\
                        priority=40000,actions=normal' % {
                'port_number': port_number, 'mac': network.mac}]
    ofctl_command_execute(cmd_list)

    # Set flow rule 6 (disable other protocols)
    cmd_list = ['add-flow', network.bridge,
                'in_port=%(port_number)s,priority=39000,actions=drop' % {
                    'port_number': port_number}]
    ofctl_command_execute(cmd_list)


def port_delete(network):

    # Getting network FlowPortNumber
    port_number = get_fport_for_network(network)

    # Delete flow
    cmd_list = ['del-flows', network.bridge,
                'in_port=%(port_number)s,dl_src=%(mac)s,udp,tp_dst=68' % {
                'port_number': port_number, 'mac': network.mac}]
    ofctl_command_execute(cmd_list)

    # Delete port
    # cmd_list = ['del-port', network.name]
    # ovs_command_execute(cmd_list)


def get_fport_for_network(network):
    '''Returns the OpenFlow port number for a given network
    cmd: ovs-vsctl get Interface vm-88 ofport
    '''
    output = subprocess.check_output(
        ['sudo', 'ovs-vsctl', 'get', 'Interface', network.name, 'ofport'])
    return output
