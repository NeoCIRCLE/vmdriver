from celery import Celery

celery = Celery('tasks', backend='amqp', broker='amqp://cloud:test@10.9.1.31/vmdriver')
