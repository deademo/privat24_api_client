import argparse
import datetime
from dateutil.relativedelta import relativedelta
import os
import shutil

from core import Privat24API, cache_type

parser = argparse.ArgumentParser(description='Interface for privat24 api')

parser.add_argument('-m', '--merchant_id', required=True, help='Merchant id from privat24')
parser.add_argument('-p', '--password', required=True, help='Password from privat24')
parser.add_argument('-c', '--card_number', required=True, help='Number of needed card')

parser.add_argument('-f', '--from_date', help='Get history from date, by default today minus 5 years')
parser.add_argument('-t', '--to_date', help='Get history to date, by default today')

parser.add_argument('-hi', '--history', action='store_true', help='Will get and show history of transactions')
parser.add_argument('-re', '--requests_empty', help='Will stop doing requests if got N empty transactions in a row')
parser.add_argument('-hp', '--hide_progress', action='store_true', help='Will hide history receiving progress')
parser.add_argument('-nc', '--no_cache', action='store_true', help='Will disable cache')
parser.add_argument('-rc', '--remove_cache', action='store_true', help='Will destroy current cache')

parser.add_argument('-b', '--balance', action='store_true', help='Will get and show ballance of card')
parser.add_argument('-mb', '--max_balance', action='store_true', help='Will show day when was card max ballance')

parser.add_argument('-rm', '--report_per_mounth', action='store_true', help='Will shop card income per month')
parser.add_argument('-rmr', '--report_per_month_range', help='Will calculate average considering +N mounth before and after', default=0)

parser.add_argument('-cu', '--currency', help='Set currency of values, by default currency of card')

def main(args):
    api = Privat24API(args.merchant_id, args.password, cache=cache_type.NO_CACHE if args.no_cache else cache_type.DISK_CACHE)
    if args.remove_cache:
        shutil.rmtree(api.cache_dir)
    if args.history or args.max_balance or args.report_per_mounth:
        history = list(api.history(args.card_number, from_date=args.from_date, to_date=args.to_date, stop_empty_requests=args.requests_empty, show_progress=not args.hide_progress))

    if args.history:
        for item in history:
            print('[{} {trantime}][{rest}] {cardamount} {description} {terminal}'.format('{}.{}.{}'.format(*item['trandate'].split('-')[::-1]), **item), flush=True)

    if args.report_per_mounth:
        month_to_income = api.get_income_per_month(history, args.currency, args.report_per_month_range)

        for key, value in month_to_income.items():
            print('{date} - {value:,.2f}'.format(date=key, value=value))

    if args.balance:
        print('Current balance: {:,}'.format(api.card_balance(args.card_number)))

    if args.max_balance:
        max_ballance = max([(float(x['rest'].split(' ')[0]), x) for x in history], key=lambda x: x[0])
        print('Max card balance {:,} was {}'.format(max_ballance[0], max_ballance[1]['trandate']))

if __name__ == '__main__':
    main(parser.parse_args())
