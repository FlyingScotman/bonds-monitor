"""Entry point for bonds-monitor CLI."""
import sys
from pathlib import Path

from bonds_monitor.config import load_config
from bonds_monitor.engine import Engine
from bonds_monitor.providers.stubs import (
    StubAnalyticsProvider,
    StubMarketDataProvider,
    StubQuikProvider,
    StubStaticDataProvider,
)
from bonds_monitor.ui.app import BondsApp


def main():
    config_path = Path("config.yaml")
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_path)

    # Wire up providers (swap stubs with real adapters when ready)
    engine = Engine(
        quik=StubQuikProvider(),
        market_data=StubMarketDataProvider(),
        static_data=StubStaticDataProvider(),
        analytics=StubAnalyticsProvider(),
        config=config,
    )

    app = BondsApp(engine=engine, config=config)
    app.run()


if __name__ == "__main__":
    main()
