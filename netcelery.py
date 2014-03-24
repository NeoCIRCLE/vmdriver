from celery import Celery
from kombu import Queue, Exchange
from socket import gethostname
from os import getenv
HOSTNAME = gethostname()
AMQP_URI = getenv('AMQP_URI')
CACHE_URI = getenv('CACHE_URI')

celery = Celery('netdriver', backend='cache',
                broker=AMQP_URI,
                include=['netdriver'])

celery.conf.update(
    CELERY_CACHE_BACKEND=CACHE_URI,
    CELERY_TASK_RESULT_EXPIRES=300,
    CELERY_QUEUES=(
        Queue(HOSTNAME + '.net', Exchange(
            'netdriver', type='direct'), routing_key='netdriver'),
    )
)
