"""
Tool_premodel - Polymarket 15-Minute Binary Option Pricing Model

Main entry point for the pricing model and data collection system.
"""
import argparse
import asyncio
import logging
import signal
import sys

from .data import DataCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class GracefulExit:
    """Handle graceful shutdown on SIGINT/SIGTERM."""

    def __init__(self):
        self.should_exit = False
        signal.signal(signal.SIGINT, self._exit_handler)
        signal.signal(signal.SIGTERM, self._exit_handler)

    def _exit_handler(self, signum, frame):
        logger.info("Shutdown signal received...")
        self.should_exit = True


async def run_collector(debug: bool = False) -> None:
    """Run the data collector."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    graceful_exit = GracefulExit()

    print()
    print("=" * 60)
    print("  Tool_premodel - Polymarket Binary Option Data Collector")
    print("=" * 60)
    print()
    print("Collecting:")
    print("  - BTC/USDT real-time prices from Binance")
    print("  - 15-minute binary option prices from Polymarket")
    print()
    print("Output: ./output/btc_15min_*.csv")
    print()
    print("Press Ctrl+C to stop...")
    print()

    async with DataCollector() as collector:
        # Start collection in a task
        collection_task = asyncio.create_task(collector.start())

        # Monitor for shutdown
        while not graceful_exit.should_exit:
            await asyncio.sleep(0.5)

        # Cancel collection
        collection_task.cancel()
        try:
            await collection_task
        except asyncio.CancelledError:
            pass

    print()
    print("Data collection stopped.")


async def list_markets() -> None:
    """List available 15-minute BTC markets."""
    print()
    print("Searching for 15-minute BTC markets on Polymarket...")
    print()

    from .data import PolymarketClient

    client = PolymarketClient()

    try:
        markets = await client.find_btc_15min_markets()

        if not markets:
            print("No 15-minute BTC markets found.")
            return

        print(f"Found {len(markets)} market(s):")
        print()

        for i, market in enumerate(markets, 1):
            print(f"{i}. {market.question}")
            print(f"   Market ID: {market.market_id[:16]}...")
            if market.end_date:
                print(f"   Expires: {market.end_date}")
            print()

    finally:
        await client.close()


async def search_crypto_markets(query: str) -> None:
    """Search for crypto markets on Polymarket."""
    print()
    print(f"Searching for '{query}' markets on Polymarket...")
    print()

    from .data import PolymarketClient

    client = PolymarketClient()

    try:
        markets = await client.search_crypto_markets(query)

        if not markets:
            print(f"No markets found matching '{query}'.")
            return

        print(f"Found {len(markets)} market(s):")
        print()

        for i, market in enumerate(markets, 1):
            print(f"{i}. {market.question}")
            print(f"   Market ID: {market.market_id[:32]}...")
            print(f"   Yes Token: {market.yes_token_id[:32]}...")
            print(f"   No Token:  {market.no_token_id[:32]}...")
            if market.end_date:
                print(f"   Expires: {market.end_date}")
            print()

    finally:
        await client.close()


async def test_binance() -> None:
    """Test Binance WebSocket connection."""
    print()
    print("Testing Binance WebSocket connection...")
    print()

    from .data import BinanceClient

    client = BinanceClient()

    try:
        print("Connecting to Binance...")
        async for trade in client.stream_trades():
            print(f"BTC/USDT: ${trade.price:.2f} (qty: {trade.quantity:.6f})")
            # Just show 5 trades then exit
            if trade.trade_id % 5 == 0:
                break
        print()
        print("Binance connection working!")

    finally:
        await client.disconnect()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Polymarket 15-Minute Binary Option Pricing Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main collect           # Start data collection
  python -m src.main collect --debug   # With debug logging
  python -m src.main list              # List 15-minute BTC markets
  python -m src.main search bitcoin    # Search for bitcoin markets
  python -m src.main test-binance      # Test Binance connection
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Collect command
    collect_parser = subparsers.add_parser("collect", help="Start data collection")
    collect_parser.add_argument(
        "--debug", "-d", action="store_true", help="Enable debug logging"
    )

    # List command
    subparsers.add_parser("list", help="List available 15-minute BTC markets")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for crypto markets")
    search_parser.add_argument(
        "query", nargs="?", default="bitcoin", help="Search term (default: bitcoin)"
    )

    # Test Binance command
    subparsers.add_parser("test-binance", help="Test Binance WebSocket connection")

    args = parser.parse_args()

    if args.command == "collect":
        asyncio.run(run_collector(debug=args.debug))
    elif args.command == "list":
        asyncio.run(list_markets())
    elif args.command == "search":
        asyncio.run(search_crypto_markets(args.query))
    elif args.command == "test-binance":
        asyncio.run(test_binance())
    else:
        parser.print_help()
        print()
        print("Quick start:")
        print("  python -m src.main test-binance  # Test Binance connection")
        print("  python -m src.main search btc    # Search crypto markets")


if __name__ == "__main__":
    main()
