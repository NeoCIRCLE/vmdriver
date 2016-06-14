import rados
import rbd
import os
import subprocess
import libvirt
import lxml.etree as ET
from base64 import b64decode
import logging

from util import req_connection, wrap_libvirtError, Connection

logger = logging.getLogger(__name__)

DUMP_SIZE_LIMIT = int(os.getenv("DUMP_SIZE_LIMIT", 20 * 1024 ** 3))  # 20GB


class CephConnection:

    def __init__(self, pool_name, ceph_config=None):

        self.pool_name = pool_name
        self.ceph_config = ceph_config
        self.cluster = None
        self.ioctx = None

    def __enter__(self):
        try:
            if self.ceph_config is None:
                self.ceph_config = os.getenv("CEPH_CONFIG",
                                             "/etc/ceph/ceph.conf")
            self.cluster = rados.Rados(conffile=self.ceph_config)
            self.cluster.connect(timeout=2)
            self.ioctx = self.cluster.open_ioctx(self.pool_name)
        except rados.InterruptedOrTimeoutError as e:
            raise Exception(e)

        return self

    def __exit__(self, type, value, traceback):

        self.ioctx.close()
        self.cluster.shutdown()


def sudo(*args):
    subprocess.check_output(["/bin/sudo"] + list(args))


def map_rbd(ceph_path, local_path):
    try:
        sudo("/bin/rbd", "map", ceph_path)
    except:
        sudo("/bin/rbd", "unmap", local_path)
        sudo("/bin/rbd", "map", ceph_path)


def save(domain, poolname, diskname):
    diskname = str(diskname)
    poolname = str(poolname)
    ceph_path = os.path.join(poolname, diskname)
    local_path = os.path.join("/dev/rbd", ceph_path)
    disk_size = DUMP_SIZE_LIMIT

    with CephConnection(poolname) as conn:
        rbd_inst = rbd.RBD()
        try:
            rbd_inst.create(conn.ioctx, diskname, disk_size)
        except rbd.ImageExists:
            rbd_inst.remove(conn.ioctx, diskname)
            rbd_inst.create(conn.ioctx, diskname, disk_size)
        try:
            map_rbd(ceph_path, local_path)
            domain.save(local_path)
        except:
            rbd_inst.remove(conn.ioctx, diskname)
            raise
        finally:
            sudo("/bin/rbd", "unmap", local_path)


def restore(connection, poolname, diskname):
    diskname = str(diskname)
    poolname = str(poolname)
    ceph_path = os.path.join(poolname, diskname)
    local_path = os.path.join("/dev/rbd", ceph_path)

    map_rbd(ceph_path, local_path)
    connection.restore(local_path)
    sudo("/bin/rbd", "unmap", local_path)
    with CephConnection(poolname) as conn:
        rbd_inst = rbd.RBD()
        rbd_inst.remove(conn.ioctx, diskname)


def generate_secret_xml(user):
    xml = ET.Element(
        "secret",
        attrib={
            "ephemeral": "no",
            "private": "no",
        })
    ET.SubElement(xml, "description").text = "CEPH passpharse for " + user
    usage = ET.SubElement(xml, "usage", attrib={"type": "ceph"})
    ET.SubElement(usage, "name").text = user
    return ET.tostring(xml,
                       encoding='utf8',
                       method='xml',
                       pretty_print=True)


@req_connection
@wrap_libvirtError
def find_secret(user):
    conn = Connection.get()
    try:
        return conn.secretLookupByUsage(
            libvirt.VIR_SECRET_USAGE_TYPE_CEPH, user)
    except libvirt.libvirtError as e:
        if e.get_error_code() == libvirt.VIR_ERR_NO_SECRET:
            return None
        raise


@req_connection
@wrap_libvirtError
def create_secret(user, secretkey):
    xml = generate_secret_xml(user)
    conn = Connection.get()
    secret = conn.secretDefineXML(xml)
    decoded_key = b64decode(secretkey)
    secret.setValue(decoded_key)
    logger.info("Secret generated with uuid: '%s'", secret.UUIDString())
    return secret


@wrap_libvirtError
def delete_secret(user):
    secret = find_secret(user)
    if secret is not None:
        secret.undefine()
        logger.info("Secret with uuid: '%s' deleted", secret.UUIDString())


def check_secret(user, secretkey):
    secret = find_secret(user)
    if secret is None:
        secret = create_secret(user, secretkey)

    return secret.UUIDString()
