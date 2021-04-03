# Interface for fetching prices for online exchanges
#
# Initialize MultiExchangeManager with a list of exchange objects to aggregate prices.
#

from .multi_exchange_manager import MultiExchangeManager

from .coinmarketcap import CoinMarketCapAPI
# 2/12/20 removed enclaves. blocks all usa traffic.
#from .enclavesdex import EnclavesAPI
# 2/12/20 removed forkdelta. need a new api since livecoinwatch stopped tracking it.
from .forkdelta import ForkDeltaAPI
# 9/06/20 added balancer
from .balancer import BalancerAPI
from .mercatox import MercatoxAPI
#from .hotbit import HotbitAPI
from .idex import IDEXAPI
from .livecoinwatch import LiveCoinWatchAPI
#2/12/20 removed ethex, they might be out of business. homepage says check later.
#from .ethex import EthexAPI
#2/12/20 removed coinexchange. homepage says closed.
#from .coinexchange import CoinExchangeAPI
# 9/10/20 remove uniswap v1. All liquidity (except $200) has moved to v2
#from .uniswap_v1 import Uniswapv1API
from .uniswap_v2 import Uniswapv2API
#2/12/20 removed merklex. seems to have rebranded to nitrade.
#from .merklex import MerkleXAPI
from .zxchange import ZxchangeAPI
# 9/22/20 added swapmatic
from .swapmatic import SwapmaticAPI
# 4/03/21 added quickswap
from .quickswap import QuickSwapAPI
