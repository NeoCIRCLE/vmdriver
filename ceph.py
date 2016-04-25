import rados
import rbd
import os
import subprocess


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
    ceph_path = "%s/%s" % (poolname, diskname)
    local_path = "/dev/rbd/" + ceph_path
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


def restore(connection, poolname, diskname):
    diskname = str(diskname)
    poolname = str(poolname)
    local_path = "/dev/rbd/%s/%s" % (poolname, diskname)

    connection.restore(local_path)
    sudo("/bin/rbd", "unmap", local_path)
    with CephConnection(poolname) as conn:
        rbd_inst = rbd.RBD()
        rbd_inst.remove(conn.ioctx, diskname)
