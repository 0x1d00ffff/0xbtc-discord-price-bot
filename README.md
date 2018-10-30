# 0xbtc-discord-price-bot
bot to monitor/post price etc to the 0xbtc discord server

Installation:
 - copy `template_secret_info.py` to `secret_info.py` and fill in your bot's authentication settings
 - Install python 3.6+
   - For debian 9 users: Debian 9 repositories only go up to python 3.5, so to
     install the latest 3.6.x python version:
     - install prerequisites:

         sudo apt install build-essential checkinstall libreadline-gplv2-dev \
         libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev \
         libbz2-dev libffi-dev

     - `https://www.python.org/ftp/python/3.6.7/Python-3.6.7.tgz`
     - `tar xvf Python-3.6.7.tgz`
     - `cd Python-3.6.7/`
     - `./configure --enable-optimizations --with-ensurepip=install`
     - `make -j2` (or `make -j8` if you have a cpu with lots of threads)
     - `sudo make altinstall`
 - `pip3 install websocket discord beautifulsoup4 matplotlib`
 - `pip3 install web3` - should work with 4.7.2 and above
   Note for Windows Users:
   - The above command failed for me with error:
   `error: command 'C:\\Program Files (x86)\\Microsoft Visual Studio 14.0\\VC\\BIN\\link.exe' failed with exit status 1158`
   - The fix: Copy rc.exe and rcdll.dll from `C:\Program Files (x86)\Windows Kits\8.1\bin\x86` to `C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin`


Requires:
 - python3
 - websocket
 - discord
 - web3.py
 - BeautifulSoup (only if !holders command is enabled)
 - matplotlib (only if !holders command is enabled)

Todo:
 - update from async to rewrite branch of discord.py [link](https://github.com/TheTrain2000/async2rewrite)
 - update help
 - move infura URL to config file
 - generalize the command interface
 - occasionally APIs return NaN as a data point.. which is a valid float. Need
   to explicitly check for this.
 - typos/new commands
   - !pools
   - !binance (to show current listing price in usd)
   - !profit 5.6 -> show profit of 5.6gh miner
   - !orderbooks mercatox
 - Need a new 'Pairing' class to handle pairings in a more generic way. This
   will allow easier integration of BTC pairings (ie mercatox)
 - volume_eth and volume_usd are not strictly defined - sometimes it means total
   volume across all pairs (converted to eth), sometimes it means volume in eth
   only and volume_btc means volume in btc only.
 - ATH announcements
 - 24h high/low/average
 - ascii chart?
 - enable hotbit?
 - new exchanges
   - tokenjar [link](https://tokenjar.io/0xbtc)
   - tokenstore [link](https://token.store/trade/0xBTC)
   - payfair [link](https://payfair.io/?coin=0XBTC&tradeType=sell&currency=USD)
   - instex [link](https://app.instex.io/0xBTC-WETH)
   - cryptobridge (not yet)
   - ddex.io