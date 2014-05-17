import lxml.etree as ET

from os import getenv

NATIVE_OVS = getenv('NATIVE_OVS') == 'True'

# VM Instance class


class VMInstance:
    name = None
    arch = None
    vm_type = None
    os_boot = None
    vcpu = None
    cpu_share = None
    memory_max = None
    network_list = list()
    disk_list = list()
    graphics = dict
    raw_data = None

    def __init__(self,
                 name,
                 vcpu,
                 memory_max,
                 memory=None,
                 emulator='/usr/bin/kvm',
                 cpu_share=100,
                 arch="x86_64",
                 boot_menu=False,
                 vm_type="test",
                 network_list=None,
                 disk_list=None,
                 graphics=None,
                 acpi=True,
                 raw_data="",
                 boot_token="",
                 seclabel_type="dynamic",
                 seclabel_mode="apparmor"):
        '''Default Virtual Machine constructor
        name    - unique name for the instance
        vcpu    - nubmer of processors
        memory_max  - maximum virtual memory (actual memory maybe add late)
        memory
        cpu_share   - KVM process priority (0-100)
        arch        - libvirt arch parameter default x86_64
        os_boot     - boot device default hd
        vm_type     - hypervisor type default kvm
        network_list    - VMNetwork list
        disk_list   - VMDIsk list
        graphics    - Dict that keys are: type, listen, port, passwd
        acpi        - True/False to enable acpi
        seclabel_type - libvirt security label type
        seclabel_mode - libvirt security mode (selinux, apparmor)
        '''
        self.name = name
        self.emulator = emulator
        self.vcpu = vcpu
        self.cpu_share = cpu_share
        self.memory_max = memory_max
        if memory is None:
            self.memory = memory_max
        else:
            self.memory = memory
        self.arch = arch
        self.boot_menu = boot_menu
        self.vm_type = vm_type
        self.network_list = network_list
        self.disk_list = disk_list
        self.graphics = graphics
        self.acpi = acpi
        self.raw_data = raw_data
        self.seclabel_type = seclabel_type
        self.seclabel_mode = seclabel_mode
        self.boot_token = boot_token

    @classmethod
    def deserialize(cls, desc):
        desc['disk_list'] = [VMDisk.deserialize(d) for d in desc['disk_list']]
        desc['network_list'] = [VMNetwork.deserialize(
            n) for n in desc['network_list']]
        return cls(**desc)

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
        ET.SubElement(xml_top, 'vcpu').text = str(self.vcpu)
        ET.SubElement(xml_top, 'memory').text = str(self.memory_max)
        ET.SubElement(xml_top, 'currentMemory').text = str(self.memory)
        # Cpu tune
        cputune = ET.SubElement(xml_top, 'cputune')
        ET.SubElement(cputune, 'shares').text = str(self.cpu_share)
        # Os specific options
        os = ET.SubElement(xml_top, 'os')
        ET.SubElement(os, 'type', attrib={'arch': self.arch}).text = "hvm"
        ET.SubElement(os, 'bootmenu', attrib={
                      'enable': "yes" if self.boot_menu else "no"})
        # Devices
        devices = ET.SubElement(xml_top, 'devices')
        ET.SubElement(devices, 'emulator').text = self.emulator
        for disk in self.disk_list:
            devices.append(disk.build_xml())
        for network in self.network_list:
            devices.append(network.build_xml())
        # Serial console
        serial = ET.SubElement(devices,
                               'console',
                               attrib={'type': 'unix'})
        ET.SubElement(serial,
                      'target',
                      attrib={'port': '0'})
        ET.SubElement(serial,
                      'source',
                      attrib={'mode': 'bind',
                              'path': '/var/lib/libvirt/serial/%s'
                              % self.name})
        # Console/graphics section
        if self.graphics is not None:
            ET.SubElement(devices,
                          'graphics',
                          attrib={
                              'type': self.graphics['type'],
                              'listen': self.graphics['listen'],
                              'port': str(self.graphics['port']),
                              # 'passwd': self.graphics['passwd'],
                              # TODO: Add this as option
                          })
            ET.SubElement(devices,
                          'input',
                          attrib={
                              'type': 'tablet',
                              'bus': 'usb', })
        # Features (TODO: features as list)
        features = ET.SubElement(xml_top, 'features')
        if self.acpi:
            ET.SubElement(features, 'acpi')
        # Building raw data into xml
        if self.raw_data:
            xml_top.append(ET.fromstring(self.raw_data))
        # Security label
        ET.SubElement(xml_top, 'seclabel', attrib={
            'type': self.seclabel_type,
            'mode': self.seclabel_mode
        })
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
                 source,
                 disk_type="file",
                 disk_device="disk",
                 driver_name="qemu",
                 driver_type="qcow2",
                 driver_cache="none",
                 target_device="vda"):
        self.source = source
        self.disk_type = disk_type
        self.disk_device = disk_device
        self.driver_name = driver_name
        self.driver_type = driver_type
        self.driver_cache = driver_cache
        self.target_device = target_device

    @classmethod
    def deserialize(cls, desc):
        return cls(**desc)

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
    ipv4            -- the IPv4 address of virtual machine (Flow control)
    ipv6            -- the IPv6 address of virtual machine (Flow controlo)
    vlan            -- Port VLAN configuration
    network_type    -- need to be "ethernet" by default
    model           -- available models in libvirt
    QoS             -- CIRCLE QoS class?
    comment         -- Any comment
    managed         -- Apply managed flow rules for spoofing prevent
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
    ipv4 = None
    ipv6 = None
    managed = False

    def __init__(self,
                 name,
                 mac,
                 bridge="cloud",
                 ipv4=None,
                 ipv6=None,
                 network_type=None,
                 virtual_port=None,
                 model='virtio',
                 QoS=None,
                 vlan=0,
                 managed=False):
        self.name = name
        self.bridge = bridge
        self.mac = mac
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.model = model
        if not network_type:
            if NATIVE_OVS:
                self.network_type = 'bridge'
                self.virtual_port = 'openvswitch'
            else:
                self.network_type = 'ethernet'
                self.virtual_port = virtual_port
        else:
            self.network_type = network_type
            self.virtual_port = virtual_port
        self.QoS = QoS
        self.vlan = vlan
        self.managed = managed

    @classmethod
    def deserialize(cls, desc):
        return cls(**desc)

    # XML dump
    def build_xml(self):
        xml_top = ET.Element('interface', attrib={'type': self.network_type})
        if self.vlan > 0 and self.network_type == "bridge":
            xml_vlan = ET.SubElement(xml_top, 'vlan')
            ET.SubElement(xml_vlan, 'tag', attrib={'id': str(self.vlan)})
        if self.network_type == "bridge":
            ET.SubElement(xml_top, 'source', attrib={'bridge': self.bridge})
        if self.network_type == "ethernet":
            ET.SubElement(xml_top, 'script', attrib={'path': self.script_exec})
        if self.virtual_port is not None:
            ET.SubElement(xml_top, 'virtualport',
                          attrib={'type': self.virtual_port})
        ET.SubElement(xml_top, 'target', attrib={'dev': self.name})
        ET.SubElement(xml_top, 'mac', attrib={'address': self.mac})
        ET.SubElement(xml_top, 'model', attrib={'type': self.model})
        ET.SubElement(xml_top, 'rom', attrib={'bar': 'off'})
        return xml_top

    def dump_xml(self):
        return ET.tostring(self.build_xml(), encoding='utf8',
                           method='xml',
                           pretty_print=True)