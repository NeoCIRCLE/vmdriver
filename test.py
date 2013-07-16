#!/usr/bin/env python

import vmdriver
import logging

#Enable logging
logging.basicConfig(filename='example.log', level=logging.DEBUG)
vm_driver = vmdriver.VMDriver()
vm_driver.connect()
#vm_driver.vm_define(testvm)
print vm_driver.list_domains()
vm_driver.disconnect()
vm_driver.disconnect()
