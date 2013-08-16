from celery import Celery
from kombu import Queue, Exchange
from socket import gethostname
import os

HOSTNAME = gethostname()

celery = Celery('vmcelery', backend='amqp',
                broker='amqp://cloud:test@10.9.1.31/vmdriver',
                include=['tasks'])

celery.conf.update(
    CELERY_QUEUES=(
        Queue(HOSTNAME + '.vm', Exchange(
            'vmdriver', type='direct'), routing_key="vmdriver"),
    )
)

if os.getenv('LIBVIRT_KEEPALIVE') is not None:
    import libvirt
    lib_connection = libvirt.open(os.getenv('LIBVIRT_URI'))
