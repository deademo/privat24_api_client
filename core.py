import datetime
from dateutil.relativedelta import relativedelta
import diskcache
import hashlib
import lxml.etree
import re
import requests
import urllib.parse


class cache_type:
    NO_CACHE = 0
    DISK_CACHE = 1


class Privat24API:

    def __init__(self, id, password, cache=cache_type.DISK_CACHE):
        self.id = id
        self.password = password
        self.balance_url = 'https://api.privatbank.ua/p24api/balance'
        self.transaction_url = 'https://api.privatbank.ua/p24api/rest_fiz'

        self.cache_dir = 'privat24requests'
        if cache == cache_type.DISK_CACHE:
            self.cache = diskcache.Cache(self.cache_dir)
        elif cache == cache_type.NO_CACHE:
            self.cache = None

        self.cached_rate = {}

    def signature(self, data):
        seed = (data+self.password).encode('utf-8')
        md5 = hashlib.md5(seed).hexdigest().encode('utf-8')
        signature = hashlib.sha1(md5).hexdigest()

        return signature

    def merchant_xml(self, signature):
        return """<merchant>
            <id>{}</id>
            <signature>{}</signature>
        </merchant>""".format(self.id, signature)

    def make_request(self, url, payload='', force_reload=False, method=requests.post):

        h = hashlib.md5()
        h.update(url.encode('utf-8'))
        h.update(payload.encode('utf-8'))
        key = h.hexdigest()

        h = hashlib

        if self.cache is None or key not in self.cache or force_reload:
            args = [url]
            if payload:
                args.append(payload)
            response = method(*args)
            if self.cache is not None:
                self.cache[key] = response
        else:
            response = self.cache[key]

        return response


    def card_balance(self, card_number):
        data = """<oper>cmt</oper>
            <wait>0</wait>
            <test>0</test>
            <payment id="">
                <prop name="cardnum" value="{card}" />
                <prop name="country" value="UA" />
            </payment>""".format(card=card_number)

        merchant_xml = self.merchant_xml(self.signature(data))
        xml = """<?xml version="1.0" encoding="UTF-8"?>
            <request version="1.0">
                {merchant}
                <data>{data}</data>
            </request>""".strip().format(merchant=merchant_xml, data=data)
        
        response = self.make_request(self.balance_url, xml)
        
        # print(response.text)
        doc = lxml.etree.fromstring(response.text.encode('utf-8'))
        try:
            balance = float(doc.xpath('./data/info/cardbalance/av_balance/text()')[0])
        except:
            balance = 0
        return balance

    def history(self, card_number, from_date=None, to_date=None, step=15, stop_empty_requests=None, show_progress=True):
        if from_date is None:
            from_date = datetime.datetime.now().replace(year=datetime.datetime.now().year-5)
        elif isinstance(from_date, str):
            from_date = datetime.datetime.strptime(from_date, '%d.%m.%Y')
        if to_date is None:
            to_date = datetime.datetime.now()
        elif isinstance(to_date, str):
            to_date = datetime.datetime.strptime(to_date, '%d.%m.%Y')

        dates_list = []
        current_from_date = from_date
        while current_from_date <= to_date:
            current_to_date = current_from_date + datetime.timedelta(days=step)
            if current_to_date >= to_date:
                current_to_date = to_date
            dates_list.append((current_from_date, current_to_date))
            current_from_date = current_from_date + datetime.timedelta(days=step+1)
        dates_list = list(sorted(dates_list, key=lambda x: x[0], reverse=True))

        empty_in_row = 0
        for index, (from_date, to_date) in enumerate(dates_list):
            current_from_date = from_date.strftime('%d.%m.%Y')
            current_to_date = to_date.strftime('%d.%m.%Y')
            if show_progress:
                print('[{}/{}] Doing request for date {} - {}'.format(index+1, len(dates_list), current_from_date, current_to_date), flush=True, end='')
            data = """<oper>cmt</oper>
                <wait>0</wait>
                <test>0</test>
                <payment id="">
                    <prop name="sd" value="{from_date}" />
                    <prop name="ed" value="{to_date}" />
                    <prop name="card" value="{card}" />
                </payment>""".format(card=card_number, 
                                     from_date=current_from_date, 
                                     to_date=current_to_date)

            merchant_xml = self.merchant_xml(self.signature(data))
            xml = """<?xml version="1.0" encoding="UTF-8"?>
                <request version="1.0">
                    {merchant}
                    <data>{data}</data>
                </request>""".strip().format(merchant=merchant_xml, data=data)
            
            response = self.make_request(self.transaction_url, xml)
            doc = lxml.etree.fromstring(response.text.encode('utf-8'))
            # print(response.text)
            result = [{x: item.get(x) for x in item.keys()} 
                      for item in doc.xpath('./data/info/statements/statement')]
            if show_progress:
                print(' ... found {} transactions'.format(len(result)), flush=True)
            for item in result:
                yield item

            if stop_empty_requests is not None and empty_in_row >= int(stop_empty_requests):
                if show_progress:
                    print('Stop requests, because found {} empty requests in a row'.format(empty_in_row))
                break

            if len(result) == 0:
                empty_in_row += 1
            else:
                empty_in_row

    def exchange_rate(self, date=None, currency='USD'):
        if date is None:
            date = datetime.datetime.now()
        elif isinstance(date, str):
            date = datetime.datetime.strptime(date, '%d.%m.%Y')

        while True:
            url = 'https://api.privatbank.ua/p24api/exchange_rates?date={}'.format(date.strftime('%d.%m.%Y'))
            response = self.make_request(url, method=requests.get)
            data = lxml.etree.fromstring(response.text.encode('utf-8'))
            if not len(data.xpath('.//exchangerate')):
                date = date + relativedelta(days=-1)
                continue
            else:
                break

        needed_exchange_rate = data.xpath('.//exchangerate[@baseCurrency="UAH" and @currency="{}"]/@saleRateNB'.format(currency))[0]
        return float(needed_exchange_rate)

    def get_income_per_month(self, history, currency=None, month_range=None):
        month_to_income = {}
        for item in history:
            if item['cardamount'].startswith('-'):
                continue

            date = datetime.datetime.strptime(item['trandate'], '%Y-%m-%d')
            key = date.strftime('%Y-%m')
            value = float(item['cardamount'].split(' ')[0])

            if currency:
                exchange_rate = self.exchange_rate(datetime.datetime.strptime(key, '%Y-%m').strftime('%d.%m.%Y'))
                value /= exchange_rate

            if key not in month_to_income:
                month_to_income[key] = 0
            month_to_income[key] += value

        if month_range:
            buffer_month_to_income = {}
            max_key = max([datetime.datetime.strptime(x, '%Y-%m') for x in month_to_income]).strftime('%Y-%m')
            min_key = min([datetime.datetime.strptime(x, '%Y-%m') for x in month_to_income]).strftime('%Y-%m')
            for key, value in month_to_income.items():
                date = datetime.datetime.strptime(key, '%Y-%m')

                needed_values = [value]
                for i in range(1, int(month_range)+1):
                    for side in (1, -1):
                        current_key = (date + relativedelta(months=1*side)).strftime('%Y-%m')
                        if current_key in month_to_income:
                            needed_values.append(month_to_income[current_key])

                buffer_month_to_income[key] = sum(needed_values)/len(needed_values)
            month_to_income = buffer_month_to_income

        return month_to_income