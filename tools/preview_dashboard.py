"""Preview local del dashboard web sin arrancar el bot completo."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bot


def _preview_portfolio_snapshot():
    """Datos neutros para preview local sin depender de APIs ni wallet real."""
    return {
        "cash": None,
        "cash_ok": False,
        "active": [],
        "resolved_won": [],
        "dead": [],
        "active_value": 0.0,
        "resolved_value": 0.0,
        "portfolio_total": 0.0,
        "api_error": "preview-local-disabled",
    }


def main():
    host = os.getenv("PREVIEW_HOST", "127.0.0.1")
    port = int(os.getenv("PREVIEW_PORT", "8080"))

    # La preview local no necesita auth para revisar la UI.
    bot.DASHBOARD_USER = ""
    bot.DASHBOARD_PASSWORD = ""
    bot.DASHBOARD_REFRESH_SEC = int(os.getenv("PREVIEW_REFRESH_SEC", "300"))

    if os.getenv("PREVIEW_DISABLE_PORTFOLIO", "1") != "0":
        bot._get_portfolio_and_positions = _preview_portfolio_snapshot

    app = bot.create_dashboard_app()
    print(f"Dashboard preview: http://{host}:{port}/")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
