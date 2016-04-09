import rados
import rbd
import os

from privcelery import celery


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


@celery.task
def write_to_ceph_block_device(poolname, diskname):
    diskname = str(diskname)
    path = "/tmp/" + diskname
    statinfo = os.stat(path)
    disk_size = statinfo.st_size
    with open(path, "rb") as f:
        with CephConnection(str(poolname)) as conn:
            rbd_inst = rbd.RBD()
            try:
                rbd_inst.create(conn.ioctx, diskname, disk_size)
            except rbd.ImageExists:
                rbd_inst.remove(conn.ioctx, diskname)
                rbd_inst.create(conn.ioctx, diskname, disk_size)

            try:
                with rbd.Image(conn.ioctx, diskname) as image:
                    offset = 0
                    data = f.read(4096)
                    while data:
                        offset += image.write(data, offset)
                        data = f.read(4096)
            except:
                rbd_inst.remove(conn.ioctx, diskname)
                raise


@celery.task
def read_from_ceph_block_device(poolname, diskname):
    diskname = str(diskname)
    path = "/tmp/" + diskname
    try:
        with open(path, "wb") as f:
            with CephConnection(str(poolname)) as conn:
                with rbd.Image(conn.ioctx, diskname) as image:
                    offset = 0
                    size = image.size()
                    while offset < size - 4096:
                        data = image.read(offset, 4096)
                        f.write(data)
                        offset += 4096
                    data = image.read(offset, size - offset)
                    f.write(data)
                rbd_inst = rbd.RBD()
                rbd_inst.remove(conn.ioctx, diskname)
    except:
        with CephConnection(str(poolname)) as conn:
            rbd_inst = rbd.RBD()
            rbd_inst.remove(conn.ioctx, diskname)
        remove_temp_file(path)
        raise


@celery.task
def remove_temp_file(path):
    os.unlink(path)
