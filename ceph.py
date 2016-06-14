import rados
import rbd
import os
import subprocess
import libvirt
import lxml.etree as ET
from base64 import b64decode
import logging
import re
import json

from util import req_connection, wrap_libvirtError, Connection


logger = logging.getLogger(__name__)

DUMP_SIZE_LIMIT = int(os.getenv("DUMP_SIZE_LIMIT", 20 * 1024 ** 3))  # 20GB

mon_regex = re.compile(r"^\[(?P<address>.+)\]\:(?P<port>\d+).*$")


class CephConfig:

    def __init__(self, user=None, config_path=None, keyring_path=None):

        self.user = user
        self.config_path = config_path
        self.keyring_path = keyring_path

        if user is None:
            self.user = "admin"
        if config_path is None:
            self.config_path = os.getenv("CEPH_CONFIG",
                                         "/etc/ceph/ceph.conf")
        if keyring_path is None:
            default_keyring = "/etc/ceph/ceph.client.%s.keyring" % self.user
            self.keyring_path = os.getenv("CEPH_KEYRING", default_keyring)

    def cmd_args(self):
        return ["--keyring", self.keyring_path,
                "--id", self.user,
                "--conf", self.config_path]


class CephConnection:

    def __init__(self, pool_name, conf=None):

        self.pool_name = pool_name
        self.conf = conf

        if conf is None:
            self.conf = CephConfig()

        self.cluster = None
        self.ioctx = None

    def __enter__(self):
        try:
            self.cluster = rados.Rados(
                conffile=self.conf.config_path,
                conf=dict(keyring=self.conf.keyring_path))
            timeout = os.getenv("CEPH_TIMEOUT", 2)
            self.cluster.connect(timeout=timeout)
            self.ioctx = self.cluster.open_ioctx(self.pool_name)
        except rados.InterruptedOrTimeoutError as e:
            raise Exception(e)

        return self

    def __exit__(self, type, value, traceback):

        self.ioctx.close()
        self.cluster.shutdown()


def sudo(*args):
    subprocess.check_output(["/bin/sudo"] + list(args))


def unmap_rbd(conf, local_path):
    sudo("/bin/rbd", "unmap", local_path, *conf.cmd_args())


def map_rbd(conf, ceph_path, local_path):
    try:
        sudo("/bin/rbd", "map", ceph_path, *conf.cmd_args())
    except:
        unmap_rbd(conf, local_path)
        sudo("/bin/rbd", "map", ceph_path, *conf.cmd_args())


def get_secret_key(conf, user):
    return subprocess.check_output((["/bin/ceph",
                                     "auth", "print-key", "client.%s" % user]
                                    + conf.cmd_args()))


def parse_endpoint(mon):
    m = mon_regex.match(mon["addr"])
    return (m.group("address"), m.group("port"))


def _get_endpoints(conf):
    output = subprocess.check_output((["/bin/ceph",
                                       "mon", "dump", "--format=json"]
                                      + conf.cmd_args()))
    mon_data = json.loads(output)
    mons = mon_data["mons"]
    return map(parse_endpoint, mons)


def get_endpoints(user):
    conf = CephConfig(user=user)
    return _get_endpoints(conf)


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
            map_rbd(conn.conf, ceph_path, local_path)
            domain.save(local_path)
        except:
            rbd_inst.remove(conn.ioctx, diskname)
            raise
        finally:
            unmap_rbd(conn.conf, local_path)


def restore(connection, poolname, diskname):
    diskname = str(diskname)
    poolname = str(poolname)
    ceph_path = os.path.join(poolname, diskname)
    local_path = os.path.join("/dev/rbd", ceph_path)

    map_rbd(connection.conf, ceph_path, local_path)
    connection.restore(local_path)
    unmap_rbd(connection.conf, local_path)
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
def create_secret(user):
    conf = CephConfig()
    secretkey = get_secret_key(conf, user)

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


def check_secret(user):
    secret = find_secret(user)
    if secret is None:
        secret = create_secret(user)

    return secret.UUIDString()
