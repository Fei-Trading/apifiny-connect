#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
# @File    :   connect_api_demo.py
# @Desc    :   None
'''

import datetime
import hashlib
import json
import random
import ssl
import time
from urllib.parse import unquote, urlencode

import jwt
import requests
import websocket

# Ver 2.2.0
# https://doc.apifiny.com/connect/#introduction


class API_CONFIG:
    """Replace to your ACCOUNT_ID API_KEY_ID and SECRET_KEY
    """
    ACCOUNT_ID = "YOUR_ACCOUNT_ID"
    API_KEY_ID = "YOUR_API_KEY_ID"
    SECRET_KEY = "YOUR_API_SECRET_KEY"

    SYMBOL = 'BTCUSD'
    venue = 'VENUE1'  # Calling api requires specifying the name of the exchange
    # Specify the name of the exchange, subscribe to the market can subscribe to multiple exchanges
    VENUES = ["VENUE1", "VENUE2"]

    API_HTTP = "https://apibnu.apifiny.com/ac/v2"
    HOST = "https://api.apifiny.com"
    MD_WS = "wss://api.apifiny.com/md/ws/v1"
    ORDER_PUSH_WS = "wss://apibnu.apifiny.com/ac/ws/v2/asset"
    ORDER_NEW_WS = "wss://api.apifiny.com/ws/trading"


class ExchangeAPI:
    def __init__(self, base_url, account_id, api_key_id, secret_key):
        self.secret_key_id = api_key_id
        self.secret_key = secret_key
        self.account_id = account_id
        self.base_url = base_url

    def clean_none_value(self, d) -> dict:
        out = {}
        for k in d.keys():
            if d[k] is not None:
                out[k] = d[k]
        return out

    def encoded_string(self, query):
        return unquote(urlencode(query, True).replace("%40", "@"))

    def prepare_params(self, params):
        return self.encoded_string(self.clean_none_value(params))

    def gen_signature(self, params_string=None):
        digest = None
        if params_string:
            digest = hashlib.sha256(params_string.encode()).hexdigest()
        millis = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
        signature = jwt.encode({
            'accountId': self.account_id,
            'secretKeyId': self.secret_key_id,
            'digest': digest,
            'exp': millis,
        }, self.secret_key, algorithm='HS256')
        return signature.decode("utf-8")

    def generate_orderid(self):
        return self.account_id.split('-')[-1] + str(int(time.time() * 1000)) + str(random.randint(100, 999))

    def http_request(self, method, path, params=None, stream=False):

        url = self.base_url + path
        if method.lower() == 'get':
            header = None
            if params:
                params_string = self.prepare_params(params)
                header = {'signature': self.gen_signature(params_string)}
            r = requests.get(url, params=params, headers=header)

            if r.status_code == 200:
                return r.json()
            else:
                return r.text
        if method.lower() == 'post':
            params_json_string = json.dumps(params)
            header = {'Content-Type': 'application/json; charset=utf-8',
                      'signature': self.gen_signature(params_json_string)}
            r = requests.post(url, data=params_json_string, headers=header)
            if r.status_code == 200:
                return r.json()
            else:
                return r.text

    def ws_client(self, url):
        header = {"signature": self.gen_signature()}
        ssl_opt = {"cert_reqs": ssl.CERT_NONE}
        con = websocket.create_connection(url, header=header, sslopt=ssl_opt)
        while True:
            response = con.recv()
            if 'ping' in response:
                pong = response.replace('ping', 'pong')
                con.send(pong)
            print(response)

    def ws_client_order(self, msg):
        sslopt = {"cert_reqs": ssl.CERT_NONE}
        header = {"signature": self.gen_signature()}
        con = websocket.create_connection(
            API_CONFIG.ORDER_NEW_WS, header=header, sslopt=sslopt)
        con.send(json.dumps(msg))
        while True:
            print("waiting message...")
            time.sleep(2)
            response = con.recv()
            if 'ping' in response:
                pong = response.replace('ping', 'pong')
                con.send(pong)
            print(response)

    def ws_new_order(self, venue, symbol, side, price, qty, total=None, stop_type=None, trigger_price=None):
        msg = {"action": "newOrder", "data": {"orderId": "", "venue": venue, "orderInfo":
                                              {"symbol": symbol, "orderType": "LIMIT", "quantity": qty, "limitPrice": price,
                                               "orderSide": side, "timeInForce": "7", "total": total, "stopType": stop_type, "triggerPrice": trigger_price}}}
        self.ws_client_order(msg)

    def ws_cancel_order(self, oid, venue):
        msg = {"action": "cancelOrder", "data": {
            "orderId": oid, "venue": venue}}
        self.ws_client_order(msg)

    def ws_cancel_all_order(self, venue, symbol):
        msg = {"action": "cancelAllOrder", "data": {
            "venue": venue, "symbol": symbol}}
        self.ws_client_order(msg)

    def current_time_millis(self):
        return self.http_request("get", "/utils/currentTimeMillis")

    def list_currency(self):
        return self.http_request("get", f"/utils/listCurrency")

    def query_account_info(self, venue):
        return self.http_request("get", "/account/queryAccountInfo", {
            "accountId": self.account_id,
            "venue": venue
        })

    def list_venue_info(self):
        return self.http_request("get", "/utils/listVenueInfo")

    def list_symbol_info(self, venue):
        return self.http_request("get", f"/utils/listSymbolInfo")

    def list_balance(self, venue):
        return self.http_request("get", "/asset/listBalance", {
            "accountId": self.account_id,
            "venue": venue
        })

    def currency_convert(self, venue, currency, target, amount):
        return self.http_request("post", "/asset/currencyConversion", {
            "accountId": self.account_id,
            "venue": venue,
            "currency": currency,
            "amount": amount,
            "targetCurrency": target
        })

    def creat_withdraw_ticket(self, venue):
        return self.http_request("get", "/asset/createWithdrawTicket", {
            "accountId": self.account_id,
            "venue": venue
        })

    def query_address(self, venue, currency):
        return self.http_request("get", "/asset/queryAddress", {
            "accountId": self.account_id,
            "venue": venue,
            "coin": currency,
        })

    def withdraw(self, venue, currency, address, amount, ticket_id, memo=""):
        return self.http_request("post", "/asset/withdraw", {
            "accountId": self.account_id,
            "venue": venue,
            "coin": currency,
            "amount": amount,
            "address": address,
            "memo": memo,
            "ticket": ticket_id
        })

    def fiat_withdraw(self, venue, currency, amount, ticket_id, fiat_info):
        return self.http_request("post", "/asset/fiat-withdraw", {
            "accountId": self.account_id,
            "venue": venue,
            "coin": currency,
            "amount": amount,
            "ticket": ticket_id,
            "fiatInfo": fiat_info
        })

    def query_max_instant_amount(self, venue, currency):
        return self.http_request("get", "/asset/query-max-instant-amount", {
            "accountId": self.account_id,
            "venue": venue,
            "currency": currency
        })

    def transfer_between_venues(self, venue, currency, amount, target_venue):
        return self.http_request("post", "/asset/transferToVenue", {
            "accountId": self.account_id,
            "venue": venue,
            "currency": currency,
            "amount": amount,
            "targetVenue": target_venue,
        })

    def query_asset_activity_list(self, start_time, end_time, limit):
        return self.http_request("get", "/asset/queryAssetActivityList", {
            "accountId": self.account_id,
            "startTimeDate": start_time,
            "endTimeDate": end_time,
            "page": '1',
            "limit": limit
        })

    def new_order(self, order_id, symbol, order_type, quantity, limit_price, order_side, venue, time_inforce, total=None, stop_type=None, trigger_price=None):
        return self.http_request("post", "/order/newOrder", {
            "accountId": self.account_id,
            "orderId": order_id,
            "venue": venue,
            "orderInfo": {
                "symbol": symbol,
                "orderType": order_type,
                "quantity": quantity,
                "limitPrice": limit_price,
                "orderSide": order_side,
                "timeInForce": time_inforce,
                "total": total,
                "stopType": stop_type,
                "triggerPrice": trigger_price
            },
        })

    def cancel_order(self, order_id, venue):
        return self.http_request("post", "/order/cancelOrder", {
            "accountId": self.account_id,
            "venue": venue,
            "orderId": order_id,
        })

    def cancel_all_order(self, venue=None, symbol=None):
        return self.http_request("post", "/order/cancelAccountVenueAllOrder", {
            "accountId": self.account_id,
            "venue": venue,
            "symbol": symbol
        })

    def list_open_order(self):
        return self.http_request("get", "/order/listOpenOrder", {
            "accountId": self.account_id,
        })

    def query_order_info(self, order_id, venue):
        return self.http_request("get", "/order/queryOrderInfo", {
            "accountId": self.account_id,
            "venue": venue,
            "orderId": order_id,
        })

    def list_order_info(self, order_id_set):
        return self.http_request("get", "/order/listMultipleOrderInfo", {
            "accountId": self.account_id,
            "orderIdList": ','.join(order_id_set)
        })

    def list_completed_order(self, venue=None, order_status=None, limit=None, startTime=None, endTime=None):
        return self.http_request("get", "/order/listCompletedOrder", {
            "accountId": self.account_id,
            "venue": venue,
            "orderStatus": order_status,
            "limit": limit,
            'startTime': startTime,
            'endTime': endTime,
        })

    def list_filled_order(self, venue=None, order_id=None, symbol=None, start_time=None, end_time=None, limit=None):
        return self.http_request("get", "/order/listFilledOrder", {
            "accountId": self.account_id,
            "venue": venue,
            "orderId": order_id,
            "symbol": symbol,
            "limit": limit,
            "startTime": start_time,
            "endTime": end_time
        })

    def get_commission_rate(self, venue, symbol):
        return self.http_request("get", "/asset/getCommissionRate", {
            "accountId": self.account_id,
            "venue": venue,
            'symbol': symbol,
        })

    def stream_order(self):
        self.ws_client(API_CONFIG.ORDER_NEW_WS)

    def stream_balance(self):
        self.ws_client(API_CONFIG.ORDER_PUSH_WS)


if __name__ == '__main__':
    exchange_api = ExchangeAPI(
        API_CONFIG.API_HTTP, API_CONFIG.ACCOUNT_ID, API_CONFIG.API_KEY_ID, API_CONFIG.SECRET_KEY)

    # send order
    order_id = exchange_api.generate_orderid()
    res = exchange_api.new_order(
        order_id, "BTCUSDT", "LIMIT", "0.02", "100", "BUY", API_CONFIG.venue, 3)
    print(res)

    # get current time millis
    # res = exchange_api.current_time_millis()
    # print(res)

    # # list currency
    # c_res = exchange_api.list_currency()
    # print(c_res)

    # # query venue info
    # v_res = exchange_api.list_venue_info()
    # print(v_res)

    # # query symbole info
    # res = exchange_api.list_symbol_info(API_CONFIG.venue)
    # print(res)

    # # currency convert
    # res = exchange_api.currency_convert('COINBASEPRO', 'USDC', 'USD', '10')
    # print(res)

    # # query address
    # res = exchange_api.query_address(API_CONFIG.venue, 'BTC')
    # print(res)
    # address = res['result']['address']

    # # create ticket
    # res = exchange_api.creat_withdraw_ticket(API_CONFIG.venue)
    # print(res)
    # ticket = res['result']['ticket']
    # # print(json.dumps(res['result'], indent=4, sort_keys=True))

    # # withdraw lite
    # memo = ""  # if currency is eos, the value of memo is the memo field returned by queryAddressLite
    # res = exchange_api.withdraw(
    #     API_CONFIG.venue, 'BTC', address, 0.01, ticket, memo)
    # print(res)

    # # fiat_withdraw
    # fiat_info = {
    #     "routingNumber": "xxxx",
    #     "code": "xxxx",
    #             "bankName": "xxxx",
    #             "bankAddress": "xxxx",
    #             "country": "xxxx",
    #             "beneficiaryName": "xxxx",
    #             "beneficiaryNumber": "xxxx",
    #             "emailAddress": "xxxx",
    #             "phoneNumber": "xxxx"
    # }
    # res = exchange_api.fiat_withdraw(
    #     API_CONFIG.venue, 'USD', 0.01, ticket, fiat_info)
    # print(res)

    # # query_asset_activity_list_lite
    # now_time = int(time.time() * 1000)
    # begin_time = int(now_time - 3 * 24 * 3600 * 1000)
    # res = exchange_api.query_asset_activity_list(begin_time, now_time, 10)
    # print(res)

    # list open order
    # res = exchange_api.list_open_order()
    # print(res)

    # # list order info
    # res = exchange_api.list_order_info([order_id, '123'])
    # print(res)

    # # query single order
    # res = exchange_api.query_order_info(order_id, API_CONFIG.venue)
    # print(res)

    # # cancel order
    # res = exchange_api.cancel_order(order_id, API_CONFIG.venue)
    # print(res)

    # # list completed order
    # now_time = int(time.time() * 1000)
    # begin_time = int(now_time - 3 * 24 * 3600 * 1000)
    # res = exchange_api.list_completed_order(
    #     API_CONFIG.venue, "", 10, begin_time, now_time)
    # for i in res['result']:
    #     print(i['accountId'], i['orderId'], i['venue'], i['orderStatus'])
    # print(res)

    # # list filled order
    # now_time = int(time.time() * 1000)
    # begin_time = int(now_time - 3 * 24 * 3600 * 1000)
    # res = exchange_api.list_filled_order(
    #     API_CONFIG.venue, None, None, begin_time, now_time)
    # for i in res['result']:
    #     print(i['accountId'], i['orderId'], i['venue'], i['orderStatus'])
    # print(res)

    # # query account info
    # res = exchange_api.query_account_info(API_CONFIG.venue)
    # print(res)

    # # query account balance
    # res = exchange_api.list_balance(API_CONFIG.venue)
    # print(res)
    # # print(json.dumps(res['result'], indent=4, sort_keys=True))
    # for i in v_res['result']:
    #     venue = i['exchange']
    #     res = exchange_api.query_account_info(venue)
    #     res2 = exchange_api.list_balance(venue)
    #     print(i)
    #     print(res)
    #     print(res2)

    # # websocket new order
    # exchange_api.ws_new_order("GBBO", "BTCUSDT", "BUY", "30000.01", "0.001")

    # # websocket cancel order
    # exchange_api.ws_cancel_order("xxxxxx", "GBBO")

    # # websocket cancel all order
    # exchange_api.ws_cancel_all_order("GBBO", "BTCUSDT")

    # # get market data using http
    # res = requests.get(
    #     f"{API_CONFIG.HOST}/md/orderbook/v1/{API_CONFIG.SYMBOL}/{API_CONFIG.venue}")
    # print(res.json())

    # # get Consolidated Order book using http
    # res = requests.get(f"{API_CONFIG.HOST}/md/cob/v1/{API_CONFIG.SYMBOL}")
    # print(res.json())
    # Market data test
    # get market data using websocket")
    # channel：orderbook,trade,kline_1h,ticker
    # msg = {"channel": "orderbook", "symbol": 'BTCUSDT', "venues": API_CONFIG.VENUES,
    #        'collect': True, "action": "sub"}
    # Conslidated Order Book
    # msg = {"channel": "cob", "symbol": 'BTCUSDT', "action": "sub"}

    # def sub_md(message):
    #     import ssl

    #     from websocket import create_connection
    #     sslopt = {"cert_reqs": ssl.CERT_NONE}
    #     con = create_connection(API_CONFIG.MD_WS, sslopt=sslopt)
    #     con.send(json.dumps(message))
    #     while True:
    #         response = con.recv()
    #         if 'ping' in response:
    #             pong = response.replace('ping', 'pong')
    #             con.send(pong)
    #         print(response)

    # sub_md(msg)
