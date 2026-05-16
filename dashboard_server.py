"""
dashboard_server.py

HTTP + WebSocket serwer (aiohttp):
- serwuje dashboard.html pod http://localhost:8080/
- emituje dane bloków i metryki wydajności przez ws://localhost:8080/ws
- śledzi latencję, throughput i rozmiar przetworzonych danych

Wszystkie obliczenia i pobieranie danych z bloków są w business_logic_layer.py.
Ten plik zajmuje się wyłącznie transportem danych do przeglądarki.
"""

import asyncio
import json
import logging
import sys
import time
from collections import deque
from pathlib import Path

from aiohttp import web
import aiohttp

from access_layer import BlockchainAccess
from business_logic_layer import BlockchainLogic
from config import ConnConfig, AppConfig
from filters import HighValueFilter, HighFeeFilter, GasPriceFilter, FailedTransactionFilter, TokenTransferFilter, AddressFilter, ContractInteractionFilter, WhaleTransactionFilter, FrequentSenderFilter
from reporting_layer import ConsoleReporter


HOST = "localhost"
PORT = 8080
MAX_BLOCKS = 100

block_history: deque[dict] = deque(maxlen=MAX_BLOCKS)
connected_clients: set[web.WebSocketResponse] = set()

logger = logging.getLogger("Dashboard")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


# ─── Metryki wydajności ────────────────────────────────────────────────────────

class PerformanceTracker:
    """
    Agreguje metryki na podstawie gotowych danych z block_data.
    Żadnych obliczeń — tylko zbieranie i statystyki.
    """

    def __init__(self):
        self.latencies: deque[float] = deque(maxlen=50)
        self.block_timestamps: deque[float] = deque(maxlen=60)
        self.tx_counts: deque[int] = deque(maxlen=60)
        self.bytes_total: int = 0
        self.total_blocks: int = 0
        self.total_txs: int = 0
        self.start_time: float = time.monotonic()

    def record(self, block_data: dict) -> None:
        """Przyjmuje gotowy block_data z BlockchainLogic i akumuluje metryki."""
        now = time.monotonic()
        latency = block_data.get("fetch_latency_ms", 0)
        tx_count = block_data.get("transactions_count", 0)
        size = block_data.get("size_bytes", 0)

        self.latencies.append(latency)
        self.block_timestamps.append(now)
        self.tx_counts.append(tx_count)
        self.bytes_total += size
        self.total_blocks += 1
        self.total_txs += tx_count

    def snapshot(self) -> dict:
        now = time.monotonic()
        uptime_s = now - self.start_time

        cutoff = now - 60
        recent_blocks = sum(1 for t in self.block_timestamps if t >= cutoff)
        recent_txs = sum(
            tx for t, tx in zip(self.block_timestamps, self.tx_counts)
            if t >= cutoff
        )

        lats = list(self.latencies)
        avg_lat  = round(sum(lats) / len(lats), 1) if lats else 0
        min_lat  = round(min(lats), 1) if lats else 0
        max_lat  = round(max(lats), 1) if lats else 0
        last_lat = round(lats[-1], 1) if lats else 0

        return {
            "latency_avg_ms":     avg_lat,
            "latency_min_ms":     min_lat,
            "latency_max_ms":     max_lat,
            "latency_last_ms":    last_lat,
            "latency_history":    lats[-20:],
            "blocks_per_min":     recent_blocks,
            "txs_per_min":        recent_txs,
            "total_blocks":       self.total_blocks,
            "total_txs":          self.total_txs,
            "bytes_processed_mb": round(self.bytes_total / (1024 * 1024), 3),
            "uptime_s":           round(uptime_s),
        }


perf = PerformanceTracker()


# ─── Broadcast ────────────────────────────────────────────────────────────────

async def broadcast(message: dict) -> None:
    if not connected_clients:
        return
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
    """
    Rozszerza ConsoleReporter wyłącznie o wysyłanie danych do dashboardu.
    Nie wykonuje żadnych obliczeń — wszystkie dane przychodzą gotowe
    z BlockchainLogic.process_block_data().
    """

    def report_block(self, block_data: dict, iteration) -> None:
        super().report_block(block_data, iteration)

        perf.record(block_data)

        block_history.append(block_data)

        loop = asyncio.get_event_loop()
        loop.create_task(broadcast({"type": "block", "data": block_data}))
        loop.create_task(broadcast({"type": "perf",  "data": perf.snapshot()}))


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
    logger.info(f"WS client connected ({len(connected_clients)} total)")

    await ws.send_str(json.dumps({
        "type": "history",
        "data": list(block_history),
        "perf": perf.snapshot(),
    }))

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.ERROR:
            logger.warning(f"WS error: {ws.exception()}")
            break

    connected_clients.discard(ws)
    logger.info(f"WS client disconnected ({len(connected_clients)} total)")
    return ws


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    conn_cfg = ConnConfig()
    app_cfg  = AppConfig()
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

    app = web.Application()
    app.router.add_get("/",   handle_index)
    app.router.add_get("/ws", handle_ws)
    app.router.add_static("/", path=Path(__file__).parent, name='static')

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    logger.info(f"Dashboard → http://{HOST}:{PORT}/")

    await logic.fetch_latest_blocks()

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