from celery import Celery
from kombu import Queue, Exchange
from socket import gethostname
from os import getenv
HOSTNAME = gethostname()
AMQP_URI = getenv('AMQP_URI')


celery = Celery('netdriver', backend='amqp',
                broker=AMQP_URI,
                include=['netdriver'])

celery.conf.update(

    CELERY_QUEUES=(
        Queue(HOSTNAME + '.net', Exchange(
            'netdriver', type='direct'), routing_key='netdriver'),
    )
)
