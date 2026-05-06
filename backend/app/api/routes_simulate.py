from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.logging import get_logger
from app.data.binance import BinanceProvider
from app.data.universe import DEFAULT_UNIVERSE
from app.ml.model import LightGBMModel
from app.schemas.simulate import SimulateRequest, SimulateResponse
from app.simulation.simulator import Simulator

router = APIRouter(tags=["simulate"])
log = get_logger(__name__)


@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    if not settings.model_path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Model not found at {settings.model_path}. "
                "Train it first with: python -m app.ml.train"
            ),
        )

    universe = DEFAULT_UNIVERSE
    if req.universe:
        wanted = {s.upper() for s in req.universe}
        universe = [a for a in DEFAULT_UNIVERSE if a.symbol.upper() in wanted]
        if not universe:
            raise HTTPException(status_code=400, detail="No supported assets in universe override.")

    provider = BinanceProvider()
    model = LightGBMModel.load(settings.model_path)
    sim = Simulator(provider=provider, model=model, universe=universe, settings=settings)

    threshold = req.confidence_threshold if req.confidence_threshold is not None else settings.confidence_threshold

    log.info("simulate.start", start=str(req.start_date), end=str(req.end_date), capital=req.starting_capital)
    result = sim.run(
        start_date=req.start_date,
        end_date=req.end_date,
        starting_capital=req.starting_capital,
        confidence_threshold=threshold,
    )
    log.info("simulate.done", ending_value=result.ending_value, n_trades=result.summary.n_trades)
    return result
