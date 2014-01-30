""" CIRCLE driver for Open vSwitch. """
import subprocess
import logging

from netcelery import celery
from os import getenv
from vm import VMNetwork

driver = getenv("HYPERVISOR_TYPE", "test")


@celery.task
def create(network):
    """ Create a network port. """
    port_create(VMNetwork.deserialize(network))


@celery.task
def delete(network):
    """ Delete a network port. """
    port_delete(VMNetwork.deserialize(network))


def add_tuntap_interface(if_name):
    """ For testing purpose only adding tuntap interface. """
    subprocess.call(['sudo', 'ip', 'tuntap', 'add', 'mode', 'tap', if_name])


def del_tuntap_interface(if_name):
    """ For testing purpose only deleting tuntap interface. """
    subprocess.call(['sudo', 'ip', 'tuntap', 'del', 'mode', 'tap', if_name])


def ovs_command_execute(command):
    """ Execute OpenVSwitch commands.

    command -   List of strings
    return  -   Command output

    """
    command = ['sudo', 'ovs-vsctl'] + command
    return_val = subprocess.call(command)
    logging.info('OVS command: %s executed.', command)
    return return_val


def ofctl_command_execute(command):
    """ Execute OpenVSwitch flow commands.

    command -   List of strings
    return  -   Command output

    """
    command = ['sudo', 'ovs-ofctl'] + command
    return_val = subprocess.call(command)
    logging.info('OVS flow command: %s executed.', command)
    return return_val


def build_flow_rule(
        in_port=None,
        dl_src=None,
        protocol=None,
        nw_src=None,
        ipv6_src=None,
        tp_dst=None,
        priority=None,
        actions=None):
    """
    Generate flow rule from the parameters.

    in_port     - Interface flow-port number
    dl_src      - Source mac addsress (virtual interface)
    protocol    - Protocol for the rule like ip,ipv6,arp,udp,tcp
    nw_src      - Source network IP(v4)
    ipv6_src    - Source network IP(v6)
    tp_dst      - Destination port
    priority    - Rule priority
    actions     - Action for the matching rule

    return - Open vSwitch compatible flow rule.

    """
    flow_rule = ""
    if in_port is None:
        raise AttributeError("Parameter in_port is mandantory")
    parameters = [('in_port=%s', in_port),
                  ('dl_src=%s', dl_src),
                  ('%s', protocol),
                  ('nw_src=%s', nw_src),
                  ('ipv6_src=%s', ipv6_src),
                  ('tp_dst=%s', tp_dst),
                  ('priority=%s', priority),
                  ('actions=%s', actions)]
    # Checking for values if not None making up rule list
    rule = [p1 % p2 for (p1, p2) in parameters if p2 is not None]
    # Generate rule string with comas, except the last item
    for i in rule[:-1]:
        flow_rule += i + ","
    flow_rule += rule[-1]
    return flow_rule


def set_port_vlan(network_name, vlan):
    """ Setting vlan for interface named net_name. """

    cmd_list = ['set', 'Port', network_name, 'tag=' + str(vlan)]
    ovs_command_execute(cmd_list)


def add_port_to_bridge(network_name, bridge):
    """ Add bridge to network_name. """
    cmd_list = ['add-port', bridge, network_name]
    ovs_command_execute(cmd_list)


def del_port_from_bridge(network_name):
    """ Delete network_name port. """
    ovs_command_execute(['del-port', network_name])


def mac_filter(network, port_number, remove=False):
    """ Apply/Remove mac filtering rule for network. """
    if not remove:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   priority="40000", actions="normal")
        ofctl_command_execute(["add-flow", network.bridge, flow_cmd])
    else:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac)
        ofctl_command_execute(["del-flows", network.bridge, flow_cmd])


def ban_dhcp_server(network, port_number, remove=False):
    """ Apply/Remove dhcp-server ban rule to network. """
    if not remove:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="udp", tp_dst="68",
                                   priority="43000", actions="drop")
        ofctl_command_execute(["add-flow", network.bridge, flow_cmd])
    else:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="udp", tp_dst="68")
        ofctl_command_execute(["del-flows", network.bridge, flow_cmd])


def ipv4_filter(network, port_number, remove=False):
    """ Apply/Remove ipv4 filter rule to network.  """
    if not remove:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="ip", nw_src=network.ipv4,
                                   priority=42000, actions="normal")
        ofctl_command_execute(["add-flow", network.bridge, flow_cmd])
    else:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="ip", nw_src=network.ipv4)
        ofctl_command_execute(["del-flows", network.bridge, flow_cmd])


def ipv6_filter(network, port_number, remove=False):
    """ Apply/Remove ipv6 filter rule to network.  """
    if not remove:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="ipv6", ipv6_src=network.ipv6,
                                   priority=42000, actions="normal")
        ofctl_command_execute(["add-flow", network.bridge, flow_cmd])
    else:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="ipv6", ipv6_src=network.ipv6)
        ofctl_command_execute(["del-flows", network.bridge, flow_cmd])


def arp_filter(network, port_number, remove=False):
    """ Apply/Remove arp filter rule to network. """
    if not remove:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="arp", nw_src=network.ipv4,
                                   priority=41000, actions="normal")
        ofctl_command_execute(["add-flow", network.bridge, flow_cmd])
    else:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="arp", nw_src=network.ipv4)
        ofctl_command_execute(["del-flows", network.bridge, flow_cmd])


def enable_dhcp_client(network, port_number, remove=False):
    """ Apply/Remove allow dhcp-client rule to network. """
    if not remove:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="udp", tp_dst="67",
                                   priority="40000", actions="normal")
        ofctl_command_execute(["add-flow", network.bridge, flow_cmd])
    else:
        flow_cmd = build_flow_rule(in_port=port_number, dl_src=network.mac,
                                   protocol="udp", tp_dst="67")
        ofctl_command_execute(["del-flows", network.bridge, flow_cmd])


def disable_all_not_allowed_trafic(network, port_number, remove=False):
    """ Apply/Remove explicit deny all not allowed network. """
    if not remove:
        flow_cmd = build_flow_rule(in_port=port_number,
                                   priority="30000", actions="drop")
        ofctl_command_execute(["add-flow", network.bridge, flow_cmd])
    else:
        flow_cmd = build_flow_rule(in_port=port_number)
        ofctl_command_execute(["del-flows", network.bridge, flow_cmd])


def port_create(network):
    """ Adding port to bridge apply rules and pull up interface. """
    # For testing purpose create tuntap iface
    if driver == "test":
        add_tuntap_interface(network.name)

    # Create the port for virtual network
    add_port_to_bridge(network.name, network.bridge)
    # Set VLAN parameter for tap interface
    set_port_vlan(network.name, network.vlan)

    # Clear all old rules
    clear_port_rules(network)

    # Getting network FlowPortNumber
    port_number = get_fport_for_network(network)

    # Set Flow rules to avoid mac or IP spoofing
    if network.managed:
        # Allow traffic from fource MAC and IP
        ban_dhcp_server(network, port_number)
        ipv4_filter(network, port_number)
        ipv6_filter(network, port_number)
        arp_filter(network, port_number)
        enable_dhcp_client(network, port_number)
    else:
        # Allow all traffic from source MAC address
        mac_filter(network, port_number)
    # Explicit deny all other traffic
    disable_all_not_allowed_trafic(network, port_number)
    pull_up_interface(network)


def port_delete(network):
    """ Remove port from bridge and remove rules from flow database. """
    # Getting network FlowPortNumber
    port_number = get_fport_for_network(network)

    # Clear network rules - debuggin 1 by 1 delete
    #if network.managed:
    #    ban_dhcp_server(network, port_number, remove=True)
    #    ipv4_filter(network, port_number, remove=True)
    #    ipv6_filter(network, port_number, remove=True)
    #    arp_filter(network, port_number, remove=True)
    #    enable_dhcp_client(network, port_number, remove=True)
    #else:
    #    mac_filter(network, port_number, remove=True)
    clear_port_rules(network)

    # Explicit deny all other traffic
    disable_all_not_allowed_trafic(network, port_number, remove=True)

    # Delete port
    del_port_from_bridge(network.name)

    # For testing purpose dele tuntap iface
    if driver == "test":
        del_tuntap_interface(network.name)


def clear_port_rules(network):
    """ Clear all rules for a port. """
    port_number = get_fport_for_network(network)
    flow_cmd = build_flow_rule(in_port=port_number)
    ofctl_command_execute(["del-flows", network.bridge, flow_cmd])


def pull_up_interface(network):
    """ Pull up interface named network.

    return command output

    """
    command = ['sudo', 'ip', 'link', 'set', 'up', network.name]
    return_val = subprocess.call(command)
    logging.info('IP command: %s executed.', command)
    return return_val


def get_fport_for_network(network):
    """ Return the OpenFlow port number for a given network.

    Example: ovs-vsctl get Interface vm-88 ofport

    return stripped output string

    """
    output = subprocess.check_output(
        ['sudo', 'ovs-vsctl', 'get', 'Interface', network.name, 'ofport'])
    return str(output).strip()
