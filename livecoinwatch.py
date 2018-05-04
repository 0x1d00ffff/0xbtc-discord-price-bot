"""

data = 
{'data': [{
    '__v': 0,
   '_id': '5ae231e61bf2276634e771d5',
   'active': True,
   'base': '0xBTC',
   'exchange': 'ForkDelta',
   'last': 0.594567000066063,
   'lastq': 660.6300000000001,
   'outlier': False,
   'quote': 'ETH',
   'rate': 0.0009000000001,
   'url': 'https://forkdelta.github.io/#!/trade/0xBTC-ETH',
   'usd': 0.594567000066063,
   'usdq': 660.6300000000001,
   'volume': 20153.666549554204,
   'volumep': 100,
   'volumepq': 0.0007236425477855652}],


"""

try:
    from urllib.request import urlopen
except:
    from urllib import urlopen

import json

import pprint

_SERVER_URL = "https://www.livecoinwatch.com/api"

def get_coin_price(coin_symbol):
    method = "/coin/{}".format(coin_symbol)

    response = urlopen(_SERVER_URL+method, timeout=10.0)
    data = json.loads(response.read())

    #pprint.pprint(data)
    
    last_price_in_usd = data['data'][0]['usd']
    last_price_in_eth = data['data'][0]['rate']
    last_eth_price = data['data'][0]['lastq']

    return last_price_in_usd, last_price_in_eth, last_eth_price


if __name__ == "__main__":
    price = get_coin_price('0xBTC')
    print('0xbtc price', price)

    price = get_coin_price('BTC')
    print('btc price', price)