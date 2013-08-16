from celery import Celery
from kombu import Queue, Exchange
from socket import gethostname

HOSTNAME = gethostname()

celery = Celery('netdriver', backend='amqp',
                broker='amqp://cloud:test@10.9.1.31/vmdriver',
                include=['tasks'])

celery.conf.update(

    CELERY_QUEUES=(
        Queue(HOSTNAME + '.net', Exchange(
            'netdriver', type='direct'), routing_key='netdriver'),
    )
)
