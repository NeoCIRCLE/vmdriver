import xml.etree.ElementTree as ET 



top = ET.Element('domain',attrib={'type':'kvm', 'xmlns:qemu':'http://libvirt.org/schemas/domain/qemu/1.0'})
cpu = ET.SubElement(top,'cpu')
#vcpu = 
#cputune = 

#devices =

xml_dump = ET.tostring(top)

print xml_dump

