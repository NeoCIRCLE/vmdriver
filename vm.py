#!/usr/bin/env python
import lxml.etree as ET

# VM Instance class


class VMInstance:
    name = None
    arch = None
    vm_type = None
    arch = None
    os_boot = None
    vcpu = None
    cpu_share = None
    memory_max = None
    network_list = list()
    disk_list = list()
    graphics = dict
    context = dict

    def __init__(self,
                 name,
                 vcpu,
                 memory_max,
                 cpu_share="100",
                 arch="x86_64",
                 os_boot="hd",
                 vm_type="kvm",
                 network_list=None,
                 disk_list=None,
                 context=None,
                 graphics=None,
                 acpi=True):
        '''Default Virtual Machine constructor
        name    - unique name for the instance
        vcpu    - nubmer of processors
        memory_max  - maximum virtual memory (actual memory maybe add late)
        cpu_share   - KVM process priority (0-100)
        arch        - libvirt arch parameter default x86_64
        os_boot     - boot device default hd
        vm_type     - hypervisor type default kvm
        network_list    - VMNetwork list
        disk_list   - VMDIsk list
        context  -   Key-Value pars (not used)
        graphics    - Dict that keys are: type, listen, port, passwd
        acpi        - True/False to enable acpi
        '''
        self.name = name
        self.vcpu = vcpu
        self.cpu_share = cpu_share
        self.memory_max = memory_max
        self.arch = arch
        self.os_boot = os_boot
        self.vm_type = vm_type
        self.network_list = network_list
        self.disk_list = disk_list
        self.conext = context
        self.graphics = graphics
        self.acpi = acpi

    def build_xml(self):
        '''Return the root Element Tree object
        '''
        ET.register_namespace(
            'qemu', 'http://libvirt.org/schemas/domain/qemu/1.0')
        xml_top = ET.Element(
            'domain',
            attrib={
                'type': self.vm_type
            })
        # Basic virtual machine paramaters
        ET.SubElement(xml_top, 'name').text = self.name
        ET.SubElement(xml_top, 'vcpu').text = self.vcpu
        ET.SubElement(xml_top, 'memory').text = self.memory_max
        # Cpu tune
        cputune = ET.SubElement(xml_top, 'cputune')
        ET.SubElement(cputune, 'shares').text = self.cpu_share
        # Os specific options
        os = ET.SubElement(xml_top, 'os')
        ET.SubElement(os, 'type', attrib={'arch': self.arch}).text = "hvm"
        ET.SubElement(os, 'boot', attrib={'dev': self.os_boot})
        # Devices
        devices = ET.SubElement(xml_top, 'devices')
        ET.SubElement(devices, 'emulator').text = '/usr/bin/kvm'
        for disk in self.disk_list:
            devices.append(disk.build_xml())
        for network in self.network_list:
            devices.append(network.build_xml())
        # Console/graphics section
        if self.graphics is not None:
            ET.SubElement(devices,
                          'graphics',
                          attrib={
                              'type': self.graphics['type'],
                              'listen': self.graphics['listen'],
                              'port': self.graphics['port'],
                              'passwd': self.graphics['passwd'],
                          })
        # Features
        features = ET.SubElement(xml_top, 'features')
        if self.acpi:
            ET.SubElement(features, 'acpi')
        return xml_top

    def dump_xml(self):
        return ET.tostring(self.build_xml(),
                           encoding='utf8',
                           method='xml',
                           pretty_print=True)


class VMDisk:

    '''Virtual MAchine disk representing class
    '''
    name = None
    source = None
    disk_type = None
    disk_device = None
    driver_name = None
    driver_type = None
    driver_cache = None
    target_device = None

    def __init__(self,
                 name,
                 source,
                 disk_type="file",
                 disk_device="disk",
                 driver_name="qemu",
                 driver_type="qcow2",
                 driver_cache="default",
                 target_device="vda"):
        self.name = name
        self.source = source
        self.disk_type = disk_type
        self.disk_device = disk_device
        self.driver_name = driver_name
        self.driver_type = driver_type
        self.driver_cache = driver_cache
        self.target_device = target_device

    def build_xml(self):
        xml_top = ET.Element('disk',
                             attrib={'type': self.disk_type,
                                     'device': self.disk_device})
        ET.SubElement(xml_top, 'source',
                      attrib={self.disk_type: self.source})
        ET.SubElement(xml_top, 'target',
                      attrib={'dev': self.target_device})
        ET.SubElement(xml_top, 'driver',
                      attrib={
                          'name': self.driver_name,
                          'type': self.driver_type,
                          'cache': self.driver_cache})
        return xml_top

    def dump_xml(self):
        return ET.tostring(self.build_xml(),
                           encoding='utf8',
                           method='xml',
                           pretty_print=True)


class VMNetwork:

    ''' Virtual Machine network representing class
    name            -- network device name
    bridge          -- bridg for the port
    mac             -- the MAC address of the quest interface
    vlan            -- Port VLAN configuration
    network_type    -- need to be "ethernet" by default
    model           -- available models in libvirt
    QoS             -- CIRCLE QoS class?
    comment         -- Any comment
    script          -- Executable network script /bin/true by default
    '''
    # Class attributes
    name = None
    bridge = None
    network_type = None
    mac = None
    model = None
    QoS = None
    script_exec = '/bin/true'
    comment = None
    vlan = 0

    def __init__(self,
                 name,
                 bridge,
                 mac,
                 network_type='ethernet',
                 model='virtio',
                 QoS=None,
                 vlan=0):
        self.name = name
        self.bridge = bridge
        self.network_type = network_type
        self.mac = mac
        self.model = model
        self.QoS = QoS
        self.vlan = vlan

    # XML dump
    def build_xml(self):
        xml_top = ET.Element('interface', attrib={'type': self.network_type})
        ET.SubElement(xml_top, 'target', attrib={'dev': self.name})
        ET.SubElement(xml_top, 'mac', attrib={'address': self.mac})
        ET.SubElement(xml_top, 'model', attrib={'type': self.model})
        ET.SubElement(xml_top, 'script', attrib={'path': self.script_exec})
        return xml_top

    def dump_xml(self):
        return ET.tostring(self.build_xml(), encoding='utf8',
                           method='xml', pretty_print=True)
