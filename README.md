# 0xbtc-discord-price-bot
Bot to monitor/post price etc to the 0xbtc discord server ([link to the discord](https://discord.gg/rQbhv7u))

\[[How to add an exchange](#adding-an-exchange)\] \[[How to add a command](#adding-a-command)\]

##### Installation:

1. Clone this repository
2. Install python 3.8. Other versions may work also, but I have not tested them.
3. run `pip3 install -r requirements.txt`
   - For for Windows Users: This command failed for me with error:
   `error: command 'C:\\Program Files (x86)\\Microsoft Visual Studio 14.0\\VC\\BIN\\link.exe' failed with exit status 1158`
   - The fix: Copy rc.exe and rcdll.dll from `C:\Program Files (x86)\Windows Kits\8.1\bin\x86` to `C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin`
4. copy `template_secret_info.py` to `secret_info.py` and fill in your bot's authentication settings
5. edit `configuration.py`
6. (Optional) edit `exchanges` list at the end of `main.py`
7. (Optional) run `python3 /path/to/price-bot/ --self_test`
8. run `python3 /path/to/price-bot/`

##### Adding an Exchange:
1. Create a new file for the exchange in exchanges/, a good idea is to copy + 
   paste one - for example `mercatox.py`
2. Edit the class name, properties and `_update()` fn to work for the exchange
3. (Optional) Test the new exchange file: 

        cd 0xbtc-discord-price-bot
        python -m exchanges.mercatox

4. Edit `exchanges/__init__.py` to import the new class
5. Add an entry to the MultiExchangeManager init at the bottom of `main.py`

##### Adding a Command:
1. If the command is simple and always returns the same string, you can skip
   to step 3.
2. Edit `command_handlers.py` and create a new function to do something. Copy
   an existing function to get the correct prototype. Typically the function
   names start with the prefix `cmd_`, and they always return a string - either
   a good response or an explicit error message.
3. Edit `configuration.py` and add a new entry to GLOBAL_COMMANDS or
   TRADING_COMMANDS that references your new function. If its a string only 
   command, a string can be used in place of a function name.

##### Requires:
 - python3
 - discord
 - web3.py
 - BeautifulSoup (only if !holders command is enabled)
 - matplotlib (only if !holders command is enabled)

##### How to update uniswap-python

        cd 0xbtc-discord-price-bot
        rm -rf uniswap
        git clone https://github.com/uniswap-python/uniswap-python.git /tmp/uniswap-python
        cp -r /tmp/uniswap-python/uniswap .

##### Bugs:
 - bot creates the 'databases' folder in a location relative to the current
   directory, rather than the location of the bot code
 - occasionally APIs return NaN as a data point.. which is a valid float. Need
   to explicitly check for this.

##### Todo:
 - merge quickswap.py and uniswap_v2.py. They are the same except the use of different
   RPC urls (MATIC_NODE_URL vs ETHEREUM_NODE_URL), token class (Token vs MaticToken),
   and blocktime (SECONDS_PER_MATIC_BLOCK vs SECONDS_PER_ETH_BLOCK).
 - replace web3 with aioethereum to fix the "heartbeat blocked for 10 seconds..." errors
 - a memoized web3 implementation would likely reduce overall traffic. Each time the
   APIs need updating, clear the memo and run all updates with the same web3 instance.
 - at boot the !status commands shows all exchanges as OK. it should show "not yet
   updated" until the first update is done
 - modify background_update so that it updates all exchanges independently, that way
   a single slow api call does not delay others
 - add a timeout on background_update so >30 second updates are logged and cancelled
 - add resfinex (link)[https://docs.resfinex.com/guide/rest.html]
 - add exponential backoff to `_update()` of the the APIs so things like rate 
   limiting are handled automatically. This would probably require modification
   of some commands which treat data older than the update rate as invalid.
 - at some level, wrap handle_global_command and handle_global_command in try
   blocks which call logging.exception to report unexpected exceptions in
   command handlers
 - switch from etherscan to bloxy.info for holders chart data source. this
   probably also means moving the holders chart functionality into the token
   library
 - update ping times for !status in background_update
 - make configuration text-based so it does not need python imports
 - generalize command categories (currently only trading and global)
 - new commands
   - !binance (to show current listing price in usd)
   - !orderbooks mercatox
   - !liquidity
   - !apy (can show apy in dex pools for last 24h using liquidity * fee calc)
 - Need a new 'Pairing' class to handle pairings in a more generic way. This
   will allow easier integration of BTC pairings (ie mercatox)
 - volume_eth and volume_usd are not strictly defined - sometimes it means total
   volume across all pairs (converted to eth), sometimes it means volume in eth
   only and volume_btc means volume in btc only.
 - go through code and use token_class.py everywhere it should be used
 - enable hotbit?
 - new exchanges
   - tokenjar [link](https://tokenjar.io/0xbtc)
   - tokenstore [link](https://token.store/trade/0xBTC)
   - Page down ~~payfair [link](https://payfair.io/?coin=0XBTC&tradeType=sell&currency=USD)~~
   - instex [link](https://app.instex.io/0xBTC-WETH)
   - cryptobridge (not yet)
   - ddex.io
   - Rootrex
   - Altilly (CEX) [link](https://www.altilly.com/market/0xBTC_ETH)
   - fatbtc (CEX) [link](https://fatbtc.com/trading?currency=0XBTC%2FUSDT&freetab=2)
   - vether pools - future
