from celery import shared_task

from channels.layers import get_channel_layer

from asgiref.sync import async_to_sync

from mahda_test import settings

import requests as api
import redis
import json


@shared_task
def get_binance_currenypairs():
    redis_cache = redis.StrictRedis(host=settings.Redis_host, port=settings.Redis_port, db=settings.Redis_db)  # config redis system cache
    binance_url = "https://api1.binance.com/api/v3/ticker/price"
    response = api.get(binance_url).json()
    currency_pairs = [item["symbol"] for item in response]
    redis_cache.set("currencypairs", json.dumps(currency_pairs))


@shared_task
def get_binance_chart():
    channel = get_channel_layer()
    redis_cache = redis.StrictRedis(host=settings.Redis_host, port=settings.Redis_port, db=settings.Redis_db)  # config redis system cache
    try:
        users_request = json.loads(redis_cache.get("usersrequest"))
        if len(users_request) >= 1:
            binance_url = "https://api1.binance.com/api/v3/klines"
            for currency_pair in users_request:
                print(currency_pair)
                response = api.get(binance_url, params={"symbol": currency_pair, "interval": "1m"}).json()
                close_price = response[0][4]
                lowest_price = list(filter(lambda item: float(item) > float(close_price), users_request[currency_pair]))
                for price in lowest_price:
                    for channel_name in users_request[currency_pair][price]:
                        async_to_sync(channel.send)(
                            channel_name,
                            {
                                "type": "send.to.user",
                                "message": {
                                    "status": True,
                                    "result": {
                                        "currency_pair": currency_pair,
                                        "target_price": price,
                                        "now_price": close_price,
                                        "price_type": "lowset",
                                        "timestamp": response[0][6]
                                    }
                                }
                            }
                        )
                higher_price = list(filter(lambda item: float(item) < float(close_price), users_request[currency_pair]))
                for price in higher_price:
                    for channel_name in users_request[currency_pair][price]:
                        async_to_sync(channel.send)(
                            channel_name,
                            {
                                "type": "send.to.user",
                                "message": {
                                    "status": True,
                                    "result": {
                                        "currency_pair": currency_pair,
                                        "target_price": price,
                                        "now_price": close_price,
                                        "price_type": "higher",
                                        "timestamp": response[0][6]
                                    }
                                }
                            }
                        )
    except json.decoder.JSONDecodeError:
        pass
