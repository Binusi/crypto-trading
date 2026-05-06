from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    id: str
    symbol: str
    name: str


DEFAULT_UNIVERSE: list[Asset] = [
    Asset("bitcoin", "BTC", "Bitcoin"),
    Asset("ethereum", "ETH", "Ethereum"),
    Asset("binancecoin", "BNB", "BNB"),
    Asset("solana", "SOL", "Solana"),
    Asset("ripple", "XRP", "XRP"),
    Asset("cardano", "ADA", "Cardano"),
    Asset("dogecoin", "DOGE", "Dogecoin"),
    Asset("tron", "TRX", "TRON"),
    Asset("avalanche-2", "AVAX", "Avalanche"),
    Asset("polkadot", "DOT", "Polkadot"),
    Asset("matic-network", "MATIC", "Polygon"),
    Asset("chainlink", "LINK", "Chainlink"),
    Asset("litecoin", "LTC", "Litecoin"),
    Asset("bitcoin-cash", "BCH", "Bitcoin Cash"),
    Asset("near", "NEAR", "NEAR Protocol"),
    Asset("cosmos", "ATOM", "Cosmos"),
    Asset("uniswap", "UNI", "Uniswap"),
    Asset("stellar", "XLM", "Stellar"),
    Asset("ethereum-classic", "ETC", "Ethereum Classic"),
    Asset("filecoin", "FIL", "Filecoin"),
]


BTC_ID = "bitcoin"


def by_id(asset_id: str) -> Asset | None:
    for a in DEFAULT_UNIVERSE:
        if a.id == asset_id:
            return a
    return None


def by_symbol(symbol: str) -> Asset | None:
    s = symbol.upper()
    for a in DEFAULT_UNIVERSE:
        if a.symbol == s:
            return a
    return None
