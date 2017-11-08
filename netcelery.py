""" Celery module for libvirt RPC calls. """
from celery import Celery
from kombu import Queue, Exchange
from os import getenv

from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-n", "--hostname", dest="hostname",
                    help="Define the full queue name with"
                    "with priority", metavar="hostname.queue.priority")
(args, unknwon_args) = parser.parse_known_args()
HOSTNAME = vars(args).pop("hostname")
if HOSTNAME is None:
    raise Exception("You must define hostname as -n <hostname> or "
                    "--hostname=<hostname>.\n"
                    "Hostname format must be hostname.module.priority.")

AMQP_URI = getenv('AMQP_URI')


def to_bool(value):
    return value.lower() in ("true", "yes", "y", "t")


lib_connection = None
native_ovs = False

if to_bool(getenv('LIBVIRT_KEEPALIVE', "False")):
    import libvirt
    lib_connection = libvirt.open(getenv('LIBVIRT_URI'))
if to_bool(getenv('NATIVE_OVS', "False")):
    native_ovs = True

VXLAN_MTU = getenv('VXLAN_MTU', '1450')

celery = Celery('netcelery',
                broker=AMQP_URI,
                include=['netdriver'])

celery.conf.update(
    CELERY_RESULT_BACKEND='amqp',
    CELERY_TASK_RESULT_EXPIRES=300,
    CELERY_QUEUES=(
        Queue(HOSTNAME, Exchange(
            'netdriver', type='direct'), routing_key="netdriver"),
    )
)
