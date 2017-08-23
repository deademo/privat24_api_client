import argparse

from core import Privat24API

parser = argparse.ArgumentParser(description='Interface for privat24 api')
parser.add_argument('-m', '--merchant_id', required=True, help='Merchant id from privat24')
parser.add_argument('-p', '--password', required=True, help='Password from privat24')
parser.add_argument('-c', '--card_number', required=True, help='Number of needed card')


def main(args):
    api = Privat24API(args.merchant_id, args.password)
    print(api.card_balance(args.card_number))
    history = api.history(args.card_number)
    for item in history:
        print('[{} {trantime}][{rest}] {cardamount} {description} {terminal}'.format('{}.{}.{}'.format(*item['trandate'].split('-')[::-1]), **item), flush=True)

    # print(max([(float(x['rest'].strip(' UAH')), x) for x in history], key=lambda x: x[0]))

if __name__ == '__main__':
    main(parser.parse_args())
