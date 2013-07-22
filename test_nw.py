#!/usr/bin/env python
import networkdriver
import vm
import logging
import vmdriver

logging.basicConfig(filename='example.log', level=logging.DEBUG)

graphics = {'type': 'vnc', 'listen':
            '0.0.0.0', 'port': '6300', 'passwd': 'asd'}
a = vm.VMDisk(name="ubuntu", source='/home/tarokkk/ubuntu.qcow')
b = vm.VMNetwork(name="vm-88", bridge='cloud',
                 mac="02:00:0a:09:01:8a", ipv4='10.9.1.138',
                 ipv6='2001:738:2001:4031:9:1:138:0/112')
testvm = vm.VMInstance(name="ubuntu", vcpu="1",
                       memory_max="131072",
                       disk_list=[a],
                       network_list=[b],
                       graphics=graphics)

#Creating vm
vm_driver = vmdriver.VMDriver()
vm_driver.connect()
#vm_driver.vm_create(testvm)

#Enabling network
network = networkdriver.NWDriver()
#network.nw_create(testvm)

network.nw_delete(testvm)
vm_driver.vm_delete(testvm)

vm_driver.disconnect()
