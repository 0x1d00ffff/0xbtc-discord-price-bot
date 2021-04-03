
# token name, token address, token decimals
tokens = (
    ("UNI",   "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", 18),
    ("KIWI",  "0x2BF91c18Cd4AE9C2f2858ef9FE518180F7B5096D", 8),
    ("SHUF",  "0x3A9FfF453d50D4Ac52A6890647b823379ba36B9E", 18),
    ("LINK",  "0x514910771AF9Ca656af840dff83E8264EcF986CA", 18),
    ("DAI",   "0x6B175474E89094C44Da98b954EedeAC495271d0F", 18),
    ("MATIC", "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0", 18),
    ("USDC",  "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", 6),
    ("0xBTC", "0xB6eD7644C69416d67B522e20bC294A9a9B405B31", 8),
    ("GRT",   "0xb83Cd8d39462B761bb0092437d38b37812dd80A2", 18),
    ("BAL",   "0xba100000625a3754423978a60c9317c58a424e3D", 18),
    ("DUST",  "0xbCa3C97837A39099eC3082DF97e28CE91BE14472", 8),
    ("WETH",  "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 18),
    ("DONUT", "0xC0F9bD5Fa5698B6505F643900FFA515Ea5dF54A9", 18),
    ("USDT",  "0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
)

# token name, token address, token decimals
matic_tokens = (
    ("WMATIC", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", 18),
    ("maWETH", "0x20D3922b4a1A8560E1aC99FBA4faDe0c849e2142", 18),
    ("USDC",   "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", 6),
    ("KIWI",   "0x578360AdF0BbB2F10ec9cEC7EF89Ef495511ED5f", 8),
    ("0xBTC",  "0x71B821aa52a49F32EEd535fCA6Eb5aa130085978", 8),
    ("WETH",   "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619", 18),
    ("QUICK",  "0x831753DD7087CaC61aB5644b308642cc1c33Dc13", 18),
    ("DAI",    "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063", 18),
    ("SWAM",   "0x94C18174840F80D49d59DC3a1742aF0B884A8184", 18),
    ("maUSDC", "0x9719d867A500Ef117cC201206B8ab51e794d3F82", 6),
    ("USDT",   "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", 6),
)

class NoTokenMatchError(Exception):
    pass

class Token():
    """Token info class - allows token address and decimals lookup."""
    _token_definitions = tokens

    def __init__(self, token_symbol=None):
        self._token_symbol = token_symbol

    @classmethod
    def from_symbol(cls, token_symbol):
        return cls(token_symbol=token_symbol)

    @classmethod
    def from_address(cls, address):
        token_symbol = get_token_name_from_address(cls._token_definitions, address)
        return cls(token_symbol=token_symbol)

    @property
    def symbol(self):
        return self._token_symbol

    @property
    def address(self):
        return get_token_address_from_name(self._token_definitions, self._token_symbol)

    @property
    def decimals(self):
        return get_token_decimals_from_name(self._token_definitions, self._token_symbol)


class MaticToken(Token):
    _token_definitions = matic_tokens

    """Token info class for Matic tokens."""
    def __init__(self, token_symbol=None):
        super().__init__(token_symbol=token_symbol)


def get_token_address_from_name(token_definitions, name):
    try:
        return [i[1] for i in token_definitions if i[0].lower() == name.lower()][0]
    except IndexError:
        raise NoTokenMatchError("Unknown name {}, need to edit token_class.py".format(name))


def get_token_name_from_address(token_definitions, address):
    try:
        return [i[0] for i in token_definitions if i[1].lower() == address.lower()][0]
    except IndexError:
        raise NoTokenMatchError("Unknown address {}, need to edit token_class.py".format(address))


def get_token_decimals_from_name(token_definitions, name):
    try:
        return [i[2] for i in token_definitions if i[0].lower() == name.lower()][0]
    except IndexError:
        raise NoTokenMatchError("Unknown name {}, need to edit token_class.py".format(name))


def get_token_decimals_from_address(token_definitions, address):
    try:
        return [i[2] for i in token_definitions if i[1].lower() == address.lower()][0]
    except IndexError:
        raise NoTokenMatchError("Unknown address {}, need to edit token_class.py".format(address))


def main():
    print("0xbtc address:",
          Token.from_symbol("0xBTC").address)

    print("uni decimals:",
          Token.from_symbol("UNI").decimals)

    print("0xba100000625a3754423978a60c9317c58a424e3D symbol:",
          Token.from_address("0xba100000625a3754423978a60c9317c58a424e3D").symbol)

    print("0xbtc address on matic:",
          MaticToken.from_symbol("0xBTC").address)


if __name__ == "__main__":
    main()
