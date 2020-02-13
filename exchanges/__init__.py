from .multi_exchange_manager import MultiExchangeManager

from .coinmarketcap import CoinMarketCapAPI
# 2/12/20 removed enclaves. blocks all usa traffic.
#from .enclavesdex import EnclavesAPI
# 2/12/20 removed forkdelta. need a new api since livecoinwatch stopped tracking it.
#from .forkdelta import ForkDeltaAPI
from .mercatox import MercatoxAPI
#from .hotbit import HotbitAPI
from .idex import IDEXAPI
#2/12/20 removed ethex, they might be out of business. homepage says check later.
#from .ethex import EthexAPI
#2/12/20 removed coinexchange. homepage says closed.
#from .coinexchange import CoinExchangeAPI
from .uniswap import UniswapAPI
#2/12/20 removed merklex. seems to have rebranded to nitrade.
#from .merklex import MerkleXAPI
from .zxchange import ZxchangeAPI
