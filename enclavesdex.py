import socket
import websocket
import json
import pprint

try:
    from urllib.request import urlopen
except:
    from urllib import urlopen

"""

{'addr': '0xb6ed7644c69416d67b522e20bc294a9a9b405b31',
 'amountEther': '22230538924500000',
 'amountToken': '3293413174',
 'change': '-0.13460428979858716137',
 'priceEnclaves': '0.000675',
 'volumeEnclavesEther': '17921353316879564600',
 'volumeEther': '21737691009396312760'},

"""

def wei_to_ether(amount_in_wei):
    return int(amount_in_wei) / 1000000000000000000.0

class EnclavesAPI():
    def __init__(self):
        self.websocket_url = "ws://app.enclaves.io:80/socket.io/?EIO=3&transport=websocket";

        self.oxbtc_volume_usd = None
        self.oxbtc_price_eth = None
        self.oxbtc_24h_change = None

    def update(self):
        print('connecting to', self.websocket_url)

        ws = websocket.create_connection(self.websocket_url)
        print('connected')
        # TMP forks read session id etc first so we do the same
        #print('rcv')
        result = ws.recv()
        #print('result:')
        pprint.pprint(result)
        #print('rcv')
        result = ws.recv()
        #print('result:')
        #pprint.pprint(result)
        #request miner data
        ws.send('42["getTokens"]')
        result = ws.recv()
        #print('result:')
        #pprint.pprint(result)
        all_data = json.loads(result[2:])
        #pprint.pprint(all_data)
        tokens = all_data[1]['tokens']
        for token in tokens:
            if token['addr'] == '0xb6ed7644c69416d67b522e20bc294a9a9b405b31':
                self.oxbtc_price_eth = float(token['priceEnclaves'])
                self.oxbtc_volume_eth = wei_to_ether(token['volumeEther'])
                self.oxbtc_24h_change = float(token['change'])


        pprint.pprint(all_data)

if __name__ == "__main__":
    e = EnclavesAPI()

    e.update()
    print(e.oxbtc_price_eth)
    print(e.oxbtc_volume_eth)
    print(e.oxbtc_24h_change)