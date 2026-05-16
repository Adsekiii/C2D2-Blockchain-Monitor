"""
dashboard_server.py

Uruchamia prosty HTTP + WebSocket serwer (aiohttp) który:
- serwuje dashboard.html pod http://localhost:8080/
- emituje dane bloków w czasie rzeczywistym przez WebSocket ws://localhost:8080/ws
- zna historię ostatnich 100 bloków (ringbuffer)
- integruje się z istniejącym BlockchainLogic poprzez hook na reporter

Użycie:
    python dashboard_server.py
lub razem z main.py – patrz komentarze w main.py
"""

import asyncio
import json
import logging
import os
from collections import deque
from pathlib import Path

from aiohttp import web
import aiohttp

from access_layer import BlockchainAccess
from business_logic_layer import BlockchainLogic
from config import ConnConfig, AppConfig
from filters import HighValueFilter, HighFeeFilter, GasPriceFilter, FailedTransactionFilter, TokenTransferFilter, AddressFilter, ContractInteractionFilter, WhaleTransactionFilter, FrequentSenderFilter
from reporting_layer import ConsoleReporter


# ─── Config ───────────────────────────────────────────────────────────────────

HOST = "localhost"
PORT = 8080
MAX_BLOCKS = 100

# ─── Shared state ─────────────────────────────────────────────────────────────

block_history: deque[dict] = deque(maxlen=MAX_BLOCKS)
connected_clients: set[web.WebSocketResponse] = set()

logger = logging.getLogger("Dashboard")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# ─── Broadcasting ─────────────────────────────────────────────────────────────

async def broadcast(message: dict) -> None:
    dead = set()
    payload = json.dumps(message)
    for ws in connected_clients:
        try:
            await ws.send_str(payload)
        except Exception:
            dead.add(ws)
    connected_clients.difference_update(dead)


# ─── Reporter bridge ──────────────────────────────────────────────────────────

class DashboardReporter(ConsoleReporter):
    """Rozszerza ConsoleReporter o wysyłanie danych bloków do dashboardu."""

    def report_block(self, block_data: dict, iteration) -> None:
        super().report_block(block_data, iteration)

        entry = {
            "number": block_data["number"],
            "hash": block_data["hash"],
            "transactions_count": block_data["transactions_count"],
        }
        block_history.append(entry)

        asyncio.get_event_loop().create_task(
            broadcast({"type": "block", "data": entry})
        )


# ─── HTTP handlers ────────────────────────────────────────────────────────────

async def handle_index(request: web.Request) -> web.Response:
    html_path = Path(__file__).parent / "dashboard.html"
    if not html_path.exists():
        return web.Response(text="dashboard.html not found", status=404)
    return web.Response(
        text=html_path.read_text(encoding="utf-8"),
        content_type="text/html",
    )


async def handle_ws(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_clients.add(ws)
    logger.info(f"Client connected. Total: {len(connected_clients)}")

    # Wyślij historię od razu po połączeniu
    await ws.send_str(json.dumps({
        "type": "history",
        "data": list(block_history),
    }))

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.ERROR:
            logger.warning(f"WS error: {ws.exception()}")
            break

    connected_clients.discard(ws)
    logger.info(f"Client disconnected. Total: {len(connected_clients)}")
    return ws


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    conn_cfg = ConnConfig()
    app_cfg = AppConfig()
    reporter = DashboardReporter()

    access = BlockchainAccess(conn_cfg, app_cfg)
    reporter.report_connection_status(access.is_connected())

    if not access.is_connected():
        logger.error("Cannot connect to blockchain. Check your API key.")
        return

    logic = BlockchainLogic(
        access,
        reporter,
        app_cfg,
        filters=[GasPriceFilter(0.03)],
    )

    # HTTP + WS server
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/ws", handle_ws)
    app.router.add_static("/", path=Path(__file__).parent, name='static')

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    logger.info(f"Dashboard available at http://{HOST}:{PORT}/")

    # Pobierz historyczne bloki, potem subskrybuj nowe
    last_block = await logic.fetch_latest_blocks()

    try:
        await logic.subscribe_new_heads()
    except KeyboardInterrupt:
        pass
    finally:
        reporter.print_final_summary()
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
