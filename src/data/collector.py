"""
Unified data collector combining Binance and Polymarket data.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from .binance_client import BinanceClient
from .polymarket_client import PolymarketClient, MarketData
from .storage import CSVStorage, AlignedDataPoint
from ..config import COLLECTION_INTERVAL

logger = logging.getLogger(__name__)


class DataCollector:
    """Collects and aligns data from Binance and Polymarket."""

    def __init__(self):
        self.binance = BinanceClient()
        self.polymarket = PolymarketClient()
        self.storage = CSVStorage()
        self._running = False
        self._current_market: Optional[MarketData] = None

    async def discover_market(self) -> Optional[MarketData]:
        """Find an active 15-minute BTC market to track."""
        logger.info("Searching for 15-minute BTC markets on Polymarket...")

        markets = await self.polymarket.find_btc_15min_markets()

        if not markets:
            logger.warning("No 15-minute BTC markets found")
            return None

        # Select market closest to expiry but still active
        now = datetime.now()
        active_markets = [
            m for m in markets
            if m.end_date is None or m.end_date > now
        ]

        if not active_markets:
            logger.warning("No active 15-minute BTC markets found")
            return None

        # Sort by expiry time (soonest first)
        active_markets.sort(
            key=lambda m: m.end_date or datetime.max
        )

        selected = active_markets[0]
        logger.info(f"Selected market: {selected.question}")

        return selected

    async def _collect_binance_prices(self) -> None:
        """Background task to collect Binance prices."""
        async for trade in self.binance.stream_trades():
            if not self._running:
                break
            # Price is stored in self.binance.last_price

    async def _collect_aligned_data(self) -> None:
        """Main collection loop - aligns data at 1-second intervals."""
        logger.info("Starting aligned data collection...")

        while self._running:
            try:
                # Get current BTC price from Binance
                btc_price = self.binance.last_price

                if btc_price is None:
                    logger.debug("Waiting for Binance price...")
                    await asyncio.sleep(0.5)
                    continue

                # Get Polymarket prices
                poly_prices = await self.polymarket.get_current_prices()

                if poly_prices is None:
                    logger.debug("Waiting for Polymarket prices...")
                    await asyncio.sleep(0.5)
                    continue

                # Create aligned data point
                data_point = AlignedDataPoint(
                    timestamp=datetime.now(),
                    btc_price=btc_price,
                    yes_price=poly_prices.yes_price,
                    no_price=poly_prices.no_price,
                    yes_bid=poly_prices.yes_bid,
                    yes_ask=poly_prices.yes_ask,
                    no_bid=poly_prices.no_bid,
                    no_ask=poly_prices.no_ask,
                    time_to_expiry_seconds=poly_prices.time_to_expiry_seconds,
                    market_id=poly_prices.market_id,
                )

                # Write to storage
                self.storage.write(data_point)

                logger.debug(
                    f"Collected: BTC=${btc_price:.2f}, "
                    f"Yes={poly_prices.yes_price:.4f}, "
                    f"No={poly_prices.no_price:.4f}, "
                    f"TTX={poly_prices.time_to_expiry_seconds}s"
                )

                # Check if market has expired
                if (
                    poly_prices.time_to_expiry_seconds is not None
                    and poly_prices.time_to_expiry_seconds <= 0
                ):
                    logger.info("Market expired, searching for new market...")
                    new_market = await self.discover_market()
                    if new_market:
                        self._current_market = new_market
                        self.polymarket.set_market(new_market)
                    else:
                        logger.warning("No new market found, continuing...")

                await asyncio.sleep(COLLECTION_INTERVAL)

            except Exception as e:
                logger.error(f"Collection error: {e}")
                await asyncio.sleep(1)

    async def start(self, market: Optional[MarketData] = None) -> None:
        """Start data collection.

        Args:
            market: Optional specific market to track.
                   If None, will auto-discover.
        """
        self._running = True

        # Discover or set market
        if market:
            self._current_market = market
        else:
            self._current_market = await self.discover_market()

        if self._current_market:
            self.polymarket.set_market(self._current_market)
        else:
            logger.warning("Starting without Polymarket market (BTC-only mode)")

        # Start collection tasks
        binance_task = asyncio.create_task(self._collect_binance_prices())
        collection_task = asyncio.create_task(self._collect_aligned_data())

        logger.info("Data collection started")

        try:
            await asyncio.gather(binance_task, collection_task)
        except asyncio.CancelledError:
            logger.info("Collection tasks cancelled")

    async def stop(self) -> None:
        """Stop data collection."""
        logger.info("Stopping data collection...")
        self._running = False

        await self.binance.disconnect()
        await self.polymarket.close()
        self.storage.close()

        logger.info("Data collection stopped")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False
