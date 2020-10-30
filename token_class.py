

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


class Token():
    """Token info class - allows token address and decimals lookup."""
    def __init__(self, token_symbol=None):
        self._token_symbol = token_symbol

    @classmethod
    def from_symbol(cls, token_symbol):
        return cls(token_symbol)

    @classmethod
    def from_address(cls, address):
        token_symbol = get_token_name_from_address(address)
        return cls(token_symbol)

    @property
    def symbol(self):
        return self._token_symbol

    @property
    def address(self):
        return get_token_address_from_name(self._token_symbol)

    @property
    def decimals(self):
        return get_token_decimals_from_name(self._token_symbol)\



def get_token_address_from_name(name):
    try:
        return [i[1] for i in tokens if i[0].lower() == name.lower()][0]
    except IndexError:
        raise RuntimeError("Unknown name {}, need to edit token_class.py".format(name))



def get_token_name_from_address(address):
    try:
        return [i[0] for i in tokens if i[1].lower() == address.lower()][0]
    except IndexError:
        raise RuntimeError("Unknown address {}, need to edit token_class.py".format(address))



def get_token_decimals_from_name(name):
    try:
        return [i[2] for i in tokens if i[0].lower() == name.lower()][0]
    except IndexError:
        raise RuntimeError("Unknown name {}, need to edit token_class.py".format(name))



def get_token_decimals_from_address(address):
    try:
        return [i[2] for i in tokens if i[1].lower() == address.lower()][0]
    except IndexError:
        raise RuntimeError("Unknown address {}, need to edit token_class.py".format(address))



def main():
    print("0xbtc address:",
          Token.from_symbol("0xBTC").address)

    print("uni decimals:",
          Token.from_symbol("UNI").decimals)

    print("0xba100000625a3754423978a60c9317c58a424e3D symbol:",
          Token.from_address("0xba100000625a3754423978a60c9317c58a424e3D").symbol)


if __name__ == "__main__":
    main()
