# 0xbtc-discord-price-bot
bot to monitor/post price etc to the 0xbtc discord server

Installation:
 - copy `template_secret_info.py` to `secret_info.py` and fill in your bot's authentication settings
 - Install python 3
 - `pip3 install websocket discord`
 - `python3 main.py`

Requires:
 - python3
 - websocket
 - discord

Todo:
 - Need a new 'Pairing' class to handle pairings in a more generic way. This
   will allow easier integration of BTC pairings (ie mercatox)
 - ATH announcements
 - 24h high/low/average
 - ascii chart?
 - combine prices from multiple sources
 - new exchanges
   - tokenjar
   - tokenstore
 - ~~0xBTC - BTC ratio~~
