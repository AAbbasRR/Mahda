from __future__ import absolute_import

import datetime
import os

from . import settings

from celery import Celery
from celery.signals import worker_ready
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mahda_test.settings')

app = Celery('mahda_test', broker=settings.cache_backend, backend=settings.cache_backend)

app.conf.result_expires = datetime.timedelta(seconds=15)

app.config_from_object('django.conf:settings', namespace='CELERY')

app.uses_utc_timezone()

app.conf.beat_schedule = {
    "get_currency_paird_data": {
        'task': 'app_WebSocket.tasks.get_binance_currenypairs',
        'schedule': crontab(minute=0, hour=0)
    },
    "get_last_candle_1m": {
        'task': 'app_WebSocket.tasks.get_binance_chart',
        'schedule': crontab(minute='*/1')
    }
}
app.autodiscover_tasks()


@worker_ready.connect
def at_start(sender, **k):
    with sender.app.connection() as conn:
        sender.app.send_task('app_WebSocket.tasks.get_binance_currenypairs', connection=conn)
