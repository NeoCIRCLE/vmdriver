import libvirt
import sys

# Open libvirt connection (local)
connection = libvirt.open(None)

# XML sample for testing
xml_sample = '''
<domain type='kvm' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
        <name>one-2273</name>
        <vcpu>1</vcpu>
        <cputune>
                <shares>512</shares>
        </cputune>
        <memory>1048576</memory>
        <os>
                <type arch='x86_64'>hvm</type>
                <boot dev='hd'/>
        </os>
        <devices>
                <emulator>/usr/bin/kvm</emulator>
                <disk type='file' device='disk'>
                        <source file='/datastore/0/2273/disk.0'/>
                        <target dev='vda'/>
                        <driver name='qemu' type='qcow2' cache='default'/>
                </disk>
                <disk type='file' device='cdrom'>
                        <source file='/datastore/0/2273/disk.1'/>
                        <target dev='hda'/>
                        <readonly/>
                        <driver name='qemu' type='raw'/>
                </disk>
                <interface type='bridge'>
                        <source bridge='cloud'/>
                        <mac address='02:00:0a:09:01:2d'/>
                        <model type='virtio'/>
                </interface>
                <graphics type='vnc' listen='0.0.0.0' port='8173' passwd='usxdfmnkfk'/>
        </devices>
        <features>
                <acpi/>
        </features>
        <cpu><topology sockets='1' cores='1' threads='1'/></cpu>
</domain>
'''

if connection == None:
    print "Fail to connect to libvirt daemon."
    sys.exit(1)
try
    names = connection.listDefinedDomains()
    print names
    connection.defineXML(xml_sample)
    print connection.listDefinedDomains()
#    conn.undefineXML()
