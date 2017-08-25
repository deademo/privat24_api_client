import argparse

from core import Privat24API

parser = argparse.ArgumentParser(description='Interface for privat24 api')
parser.add_argument('-m', '--merchant_id', required=True, help='Merchant id from privat24')
parser.add_argument('-p', '--password', required=True, help='Password from privat24')
parser.add_argument('-c', '--card_number', required=True, help='Number of needed card')
parser.add_argument('-f', '--from_date', help='Get history from date, by default today minus 5 years')
parser.add_argument('-t', '--to_date', help='Get history to date, by default today')
parser.add_argument('-b', '--balance', action='store_true', help='Will get and show ballance of card')
parser.add_argument('-hi', '--history', action='store_true', help='Will get and show history of transactions')
parser.add_argument('-hc', '--cache_history', action='store_true', help='Will cache history of transactions')
parser.add_argument('-re', '--requests_empty', help='Will stop doing requests if got N empty transactions in a row')

def main(args):
    api = Privat24API(args.merchant_id, args.password)
    if args.balance:
        print('Current balance:', api.card_balance(args.card_number))
    if args.history or args.cache_history:
        history = list(api.history(args.card_number, from_date=args.from_date, to_date=args.to_date, stop_empty_requests=args.requests_empty))
    if args.history:
        for item in history:
            print('[{} {trantime}][{rest}] {cardamount} {description} {terminal}'.format('{}.{}.{}'.format(*item['trandate'].split('-')[::-1]), **item), flush=True)

    # print(max([(float(x['rest'].strip(' UAH')), x) for x in history], key=lambda x: x[0]))

if __name__ == '__main__':
    main(parser.parse_args())
