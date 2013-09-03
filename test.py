#!/usr/bin/env python

import vm
import vmdriver
#import logging
from nose.tools import raises

graphics = {'type': 'vnc', 'listen':
            '0.0.0.0', 'port': '6300', 'passwd': 'asd'}
a = vm.VMNetwork(name="vm-88", mac="02:00:00:00:00:00")
b = vm.VMDisk(name="asd", source='/asdasd/adasds/asd')
testvm = vm.VMInstance(name="Thisthename", vcpu="1",
                       memory_max="2048",
                       disk_list=[a],
                       network_list=[b],
                       graphics=graphics)

netdict = {'name': "vm-88", 'mac': "02:00:00:00:00:00"}
diskdict = {'name': "asd", 'source': '/asdasd/adasds/asd'}
vmdict = {
    'name': "Thisthename",
    'vcpu': 1,
    'memory_max': 2048,
    'disk_list': [diskdict],
    'network_list': [netdict],
    'graphics': graphics
}

print vm.VMNetwork.deserialize(netdict).dump_xml()
print vm.VMDisk.deserialize(diskdict).dump_xml()


asd = vm.VMInstance.deserialize(vmdict)
print asd.dump_xml()

# Enable logging
#logging.basicConfig(filename='example.log', level=logging.DEBUG)
#print testvm.dump_xml()
#vm_driver = vmdriver.VMDriver()
#vm_driver.connect()
#vm_driver.vm_define(testvm)
#print '%(name)s defined.' % {'name': testvm.name}
#for i in vm_driver.list_domains():
#    print i
#    #vm_driver.vm_start(i)
#    vm_driver.vm_undefine(i)
#    print '%(name)s undefined.' % {'name': i}
#vm_driver.disconnect()


@raises(AttributeError)
def test_vm_create_with_None():
    vm_driver = vmdriver.VMDriver()
    vm_driver.connect()
    vm_driver.vm_create(None)
