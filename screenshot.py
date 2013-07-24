#!/usr/bin/env python

import libvirt
import os
# pip install pillow
from PIL import Image


def handler(stream, buf, opaque):
    fd = opaque
    os.write(fd, buf)

uri = "qemu:///system"
vmname = "ubuntu"
filename = "screenshot.ppm"
connection = libvirt.open(uri)
domain = connection.lookupByName(vmname)


# Sendkey
# Keys described in /usr/include/linux/input.h
domain.sendKey(libvirt.VIR_KEYCODE_SET_LINUX, 100, [97],1, 0)

stream = connection.newStream(0)
mimetype = domain.screenshot(stream, 0, 0)
print "mimetype:", mimetype
fd = os.open(filename, os.O_WRONLY | os.O_TRUNC | os.O_CREAT, 0o644)
stream.recvAll(handler, fd)

Image.open("screenshot.ppm").save("screenshot.png")
