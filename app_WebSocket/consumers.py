from channels.generic.websocket import AsyncWebsocketConsumer

from mahda_test import settings

import redis
import json


class OrderPrice(AsyncWebsocketConsumer):
    redis_cache = redis.StrictRedis(host=settings.Redis_host, port=settings.Redis_port, db=settings.Redis_db)  # config redis system cache

    async def connect(self):
        await self.accept()
        await self.send_message(True, "connect...")

    async def disconnect(self, code):
        if self.redis_cache.exists(f"{self.channel_name}_request"):
            users_request = json.loads(self.redis_cache.get("usersrequest"))
            user_channel = json.loads(self.redis_cache.get(f"{self.channel_name}_request"))
            for currency_pair in user_channel:
                for price in user_channel[currency_pair]:
                    if len(users_request[currency_pair][price]) > 1:
                        users_request[currency_pair][price].remove(self.channel_name)
                    else:
                        users_request[currency_pair].pop(price)
                if len(users_request[currency_pair]) == 0:
                    users_request.pop(currency_pair)
            self.redis_cache.set("usersrequest", json.dumps(users_request))
            self.redis_cache.delete(f"{self.channel_name}_request")

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                text_data_json = json.loads(text_data)
                if "currency_pair" in text_data_json:
                    if "target_price" in text_data_json and type(text_data_json['target_price']) in [float, int]:
                        currencies = json.loads(self.redis_cache.get("currencypairs"))
                        if text_data_json['currency_pair'].upper() in currencies:
                            try:
                                users_request = json.loads(self.redis_cache.get("usersrequest"))
                                users_request[text_data_json['currency_pair'].upper()][str(text_data_json['target_price'])].append(self.channel_name)
                            except TypeError:
                                users_request = {text_data_json['currency_pair'].upper(): {str(text_data_json['target_price']): [self.channel_name]}}
                            except KeyError as error:
                                print(error)
                                print(str(text_data_json['target_price']))
                                if str(error).split("'")[1] == text_data_json['currency_pair'].upper():
                                    users_request[text_data_json['currency_pair'].upper()] = {str(text_data_json['target_price']): [self.channel_name]}
                                elif str(error).split("'")[1] == str(text_data_json['target_price']):
                                    users_request[text_data_json['currency_pair'].upper()][str(text_data_json['target_price'])] = [self.channel_name]
                            self.redis_cache.set("usersrequest", json.dumps(users_request))
                            if self.redis_cache.exists(f"{self.channel_name}_request"):
                                user_channel = json.loads(self.redis_cache.get(f"{self.channel_name}_request"))
                                try:
                                    user_channel[text_data_json['currency_pair'].upper()].append(str(text_data_json['target_price']))
                                except KeyError:
                                    user_channel[text_data_json['currency_pair'].upper()] = [str(text_data_json['target_price'])]
                            else:
                                user_channel = {text_data_json['currency_pair'].upper(): [str(text_data_json['target_price'])]}
                            self.redis_cache.set(f"{self.channel_name}_request", json.dumps(user_channel))
                            self.redis_cache.expire(f"{self.channel_name}_request", 36000)
                            await self.send_message(True, "Successfully done")
                        else:
                            await self.send_message(False, f"not found {text_data_json['currency_pair']} in database")
                    else:
                        await self.send_message(False, "target_price is required and should not be Null or Blank and should be Number")
                else:
                    await self.send_message(False, "currency_pair is required and should not be Null or Blank")
            except json.decoder.JSONDecodeError:
                if text_data.upper() == "PING":
                    await self.send_message(True, "PONG")

    async def send_message(self, status, message):
        await self.send(json.dumps({
            "status": status,
            "message": message
        }))

    async def send_to_user(self, event):
        await self.send(json.dumps(event['message']))
