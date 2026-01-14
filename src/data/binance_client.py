"""
Binance WebSocket client for real-time BTC/USDT price streaming.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

import websockets
from websockets.exceptions import ConnectionClosed

from ..config import (
    BINANCE_WS_URL,
    MAX_RECONNECT_ATTEMPTS,
    RECONNECT_DELAY,
)

logger = logging.getLogger(__name__)


@dataclass
class TradeData:
    """Represents a single trade from Binance."""
    timestamp: datetime
    price: float
    quantity: float
    trade_id: int


class BinanceClient:
    """WebSocket client for Binance BTC/USDT trade stream."""

    def __init__(self, url: str = BINANCE_WS_URL):
        self.url = url
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_count = 0
        self._last_price: Optional[float] = None

    @property
    def last_price(self) -> Optional[float]:
        """Get the most recent BTC price."""
        return self._last_price

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        logger.info(f"Connecting to Binance WebSocket: {self.url}")
        self._ws = await websockets.connect(self.url)
        self._reconnect_count = 0
        logger.info("Connected to Binance WebSocket")

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("Disconnected from Binance WebSocket")

    def _parse_trade(self, data: dict) -> TradeData:
        """Parse trade message from Binance.

        Binance trade stream format:
        {
            "e": "trade",     # Event type
            "E": 123456789,   # Event time (ms)
            "s": "BTCUSDT",   # Symbol
            "t": 12345,       # Trade ID
            "p": "95000.00",  # Price
            "q": "0.001",     # Quantity
            "T": 123456789,   # Trade time (ms)
            ...
        }
        """
        timestamp = datetime.fromtimestamp(data["T"] / 1000)
        price = float(data["p"])
        quantity = float(data["q"])
        trade_id = data["t"]

        self._last_price = price

        return TradeData(
            timestamp=timestamp,
            price=price,
            quantity=quantity,
            trade_id=trade_id,
        )

    async def stream_trades(self) -> AsyncGenerator[TradeData, None]:
        """Stream real-time trades from Binance.

        Yields TradeData objects as they arrive.
        Auto-reconnects on disconnect.
        """
        self._running = True

        while self._running:
            try:
                if not self._ws:
                    await self.connect()

                async for message in self._ws:
                    if not self._running:
                        break

                    data = json.loads(message)
                    if data.get("e") == "trade":
                        yield self._parse_trade(data)

            except ConnectionClosed as e:
                logger.warning(f"Binance WebSocket disconnected: {e}")
                self._ws = None

                if self._reconnect_count < MAX_RECONNECT_ATTEMPTS:
                    self._reconnect_count += 1
                    logger.info(
                        f"Reconnecting ({self._reconnect_count}/{MAX_RECONNECT_ATTEMPTS})..."
                    )
                    await asyncio.sleep(RECONNECT_DELAY)
                else:
                    logger.error("Max reconnect attempts reached")
                    break

            except Exception as e:
                logger.error(f"Binance WebSocket error: {e}")
                self._ws = None
                await asyncio.sleep(RECONNECT_DELAY)

    async def get_current_price(self) -> Optional[float]:
        """Get the current BTC price (blocking until first trade received)."""
        async for trade in self.stream_trades():
            return trade.price
        return None
