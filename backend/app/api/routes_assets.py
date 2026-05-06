from fastapi import APIRouter

from app.data.universe import DEFAULT_UNIVERSE
from app.schemas.assets import AssetInfo

router = APIRouter(tags=["assets"])


@router.get("/assets", response_model=list[AssetInfo])
def list_assets() -> list[AssetInfo]:
    return [AssetInfo(id=a.id, symbol=a.symbol, name=a.name) for a in DEFAULT_UNIVERSE]
