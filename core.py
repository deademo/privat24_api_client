import requests
import diskcache
import hashlib
import lxml.etree
import re
import urllib.parse
import datetime

class Privat24API:

    def __init__(self, id, password):
        self.id = id
        self.password = password
        self.balance_url = 'https://api.privatbank.ua/p24api/balance'
        self.transaction_url = 'https://api.privatbank.ua/p24api/rest_fiz'

        self.cache = diskcache.Cache('privat24requests')

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

    def make_request(self, url, payload, force_reload=False):

        h = hashlib.md5()
        h.update(url.encode('utf-8'))
        h.update(payload.encode('utf-8'))
        key = h.hexdigest()

        h = hashlib

        if key not in self.cache or force_reload:
            response = requests.post(url, payload)
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
            balance = float(doc.xpath('./data/info/cardbalance/balance/text()')[0])
        except:
            balance = 0
        return balance

    def history(self, card_number, from_date=None, to_date=None, step=15):
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
            current_to_date = current_from_date + datetime.timedelta(days=15)
            if current_to_date >= to_date:
                current_to_date = to_date
            dates_list.append((current_from_date, current_to_date))
            current_from_date = current_from_date + datetime.timedelta(days=16)
        dates_list = list(sorted(dates_list, key=lambda x: x[0], reverse=True))

        for index, (from_date, to_date) in enumerate(dates_list):
            current_from_date = from_date.strftime('%d.%m.%Y')
            current_to_date = to_date.strftime('%d.%m.%Y')
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
            print(' ... found {} transactions'.format(len(result)), flush=True)
            for item in result:
                yield item
