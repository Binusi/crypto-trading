from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=("settings_",))

    model_path: Path = BACKEND_ROOT / "models" / "latest.pkl"
    data_cache_dir: Path = BACKEND_ROOT / "data_cache"

    cors_origins: str = "*"

    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    coingecko_request_delay_s: float = 2.5

    initial_train_end: str = "2021-12-31"
    walk_forward_block_days: int = 90
    sim_retrain_every_days: int = 30

    confidence_threshold: float = 0.10
    top_k: int = 5
    cash_reserve_frac: float = 0.10
    max_asset_weight: float = 0.30
    transaction_cost: float = 0.0010
    min_trade_frac: float = 0.005
    cooldown_days: int = 2

    history_years: int = 5

    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
