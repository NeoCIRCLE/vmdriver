""" Celery module for libvirt RPC calls. """
from celery import Celery
from kombu import Queue, Exchange
from socket import gethostname
from os import getenv


HOSTNAME = gethostname()
AMQP_URI = getenv('AMQP_URI')


lib_connection = None

celery = Celery('vmcelery', backend='amqp',
                broker=AMQP_URI,
                include=['vmdriver'])

celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES=300,
    CELERY_QUEUES=(
        Queue(HOSTNAME + '.vm', Exchange(
            'vmdriver', type='direct'), routing_key="vmdriver"),
        # Queue(HOSTNAME + '.monitor', Exchange(
        #    'monitor', type='direct'), routing_key="monitor"),
    )
)

if getenv('LIBVIRT_KEEPALIVE') is not None:
    import libvirt
    lib_connection = libvirt.open(getenv('LIBVIRT_URI'))
