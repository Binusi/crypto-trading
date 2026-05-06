from pydantic import BaseModel


class AssetInfo(BaseModel):
    id: str
    symbol: str
    name: str
