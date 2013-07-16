#!/usr/bin/env python

import vm
import vmdriver
import logging
from nose.tools import raises
a = vm.VMNetwork(name="vm-88", mac="02:00:00:00:00:00")
b = vm.VMDisk(name="asd", source='/asdasd/adasds/asd')
testvm = vm.VMInstance(name="Thisthename", vcpu="1",
                       memory_max="2048",
                       disk_list=[a],
                       network_list=[b])

# Enable logging
logging.basicConfig(filename='example.log', level=logging.DEBUG)
vm_driver = vmdriver.VMDriver()
vm_driver.connect()
# vm_driver.vm_define(None)
vm_driver.lookupByName("asdasd")
print vm_driver.list_domains()
vm_driver.disconnect()
vm_driver.disconnect()


@raises(AttributeError)
def test_vm_create_with_None():
    vm_driver = vmdriver.VMDriver()
    vm_driver.connect()
    vm_driver.vm_create(None)
