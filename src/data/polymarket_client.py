"""
Polymarket CLOB API client for 15-minute binary option prices.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import aiohttp

from ..config import POLYMARKET_CLOB_URL, POLYMARKET_POLL_INTERVAL

# Gamma API for market discovery
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Represents a Polymarket binary option market."""
    market_id: str
    condition_id: str
    question: str
    yes_token_id: str
    no_token_id: str
    end_date: Optional[datetime] = None


@dataclass
class PriceData:
    """Price data for a binary option market."""
    timestamp: datetime
    market_id: str
    yes_price: float
    no_price: float
    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float
    time_to_expiry_seconds: Optional[int] = None


class PolymarketClient:
    """REST client for Polymarket CLOB API."""

    def __init__(self, base_url: str = POLYMARKET_CLOB_URL):
        self.base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None
        self._current_market: Optional[MarketData] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make HTTP GET request to CLOB API."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Polymarket API error: {e}")
            raise

    async def get_markets(self) -> List[Dict]:
        """Get list of available markets."""
        response = await self._request("/markets")
        # API returns {"data": [...], ...} or just a list
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response if isinstance(response, list) else []

    async def get_midpoint(self, token_id: str) -> float:
        """Get midpoint price for a token."""
        data = await self._request("/midpoint", params={"token_id": token_id})
        return float(data.get("mid", 0))

    async def get_price(self, token_id: str, side: str = "buy") -> float:
        """Get current price for a token.

        Args:
            token_id: The token ID to get price for
            side: 'buy' or 'sell'
        """
        data = await self._request(
            "/price", params={"token_id": token_id, "side": side}
        )
        return float(data.get("price", 0))

    async def get_orderbook(self, token_id: str) -> Dict:
        """Get order book for a token.

        Returns dict with 'bids' and 'asks' lists.
        Each bid/ask has 'price' and 'size'.
        """
        return await self._request("/book", params={"token_id": token_id})

    async def find_btc_15min_markets(self) -> List[MarketData]:
        """Find active 15-minute BTC binary option markets.

        Searches for:
        1. BTC Up/Down 15-minute markets (btc-updown-15m-*)
        2. Markets with "Bitcoin 15 minutes" style questions
        """
        # First try the Gamma API for BTC updown markets
        updown_markets = await self.find_btc_updown_markets()
        if updown_markets:
            return updown_markets

        # Fallback: search CLOB API for keyword matches
        markets = await self.get_markets()
        btc_markets = []

        for market in markets:
            question = market.get("question", "").lower()

            # Check if market matches BTC 15-min criteria
            is_btc = any(kw in question for kw in ["bitcoin", "btc"])
            is_15min = any(kw in question for kw in ["15 min", "15min", "15-min"])

            if is_btc and is_15min:
                try:
                    end_date = None
                    if market.get("end_date_iso"):
                        end_date = datetime.fromisoformat(
                            market["end_date_iso"].replace("Z", "+00:00")
                        )

                    tokens = market.get("tokens", [])
                    yes_token = next(
                        (t for t in tokens if t.get("outcome") == "Yes"), None
                    )
                    no_token = next(
                        (t for t in tokens if t.get("outcome") == "No"), None
                    )

                    if yes_token and no_token:
                        btc_markets.append(
                            MarketData(
                                market_id=market.get("condition_id", ""),
                                condition_id=market.get("condition_id", ""),
                                question=market.get("question", ""),
                                yes_token_id=yes_token.get("token_id", ""),
                                no_token_id=no_token.get("token_id", ""),
                                end_date=end_date,
                            )
                        )
                except Exception as e:
                    logger.warning(f"Error parsing market: {e}")
                    continue

        return btc_markets

    async def find_btc_updown_markets(self) -> List[MarketData]:
        """Find active BTC Up/Down 15-minute markets via Gamma API.

        These markets have slug format: btc-updown-15m-{timestamp}
        Outcomes are "Up" and "Down" (not Yes/No).

        Returns:
            List of active BTC updown markets, sorted by expiry (soonest first)
        """
        session = await self._get_session()
        url = f"{POLYMARKET_GAMMA_URL}/events"

        try:
            params = {"active": "true", "closed": "false", "limit": 200}
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                events = await response.json()

            markets = []
            now = datetime.now().astimezone()

            for event in events:
                slug = event.get("slug", "").lower()

                # Match btc-updown-15m-* pattern
                if not ("btc-updown" in slug and "15m" in slug):
                    continue

                for m in event.get("markets", []):
                    clob_token_ids = m.get("clobTokenIds", [])

                    # Parse outcomes - could be string "["Up", "Down"]" or list
                    outcomes_raw = m.get("outcomes", [])
                    if isinstance(outcomes_raw, str):
                        import json
                        try:
                            outcomes = json.loads(outcomes_raw)
                        except json.JSONDecodeError:
                            outcomes = []
                    else:
                        outcomes = outcomes_raw

                    if len(clob_token_ids) < 2 or len(outcomes) < 2:
                        continue

                    # Find Up/Down token indices
                    up_idx = next(
                        (i for i, o in enumerate(outcomes) if o.lower() == "up"),
                        0
                    )
                    down_idx = next(
                        (i for i, o in enumerate(outcomes) if o.lower() == "down"),
                        1
                    )

                    up_token = clob_token_ids[up_idx] if up_idx < len(clob_token_ids) else ""
                    down_token = clob_token_ids[down_idx] if down_idx < len(clob_token_ids) else ""

                    if not up_token or not down_token:
                        continue

                    # Parse end date
                    end_date = None
                    end_date_str = m.get("endDate") or m.get("endDateIso")
                    if end_date_str:
                        try:
                            end_date = datetime.fromisoformat(
                                end_date_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass

                    # Skip expired markets
                    if end_date and end_date < now:
                        continue

                    markets.append(
                        MarketData(
                            market_id=m.get("conditionId", ""),
                            condition_id=m.get("conditionId", ""),
                            question=m.get("question", ""),
                            yes_token_id=up_token,  # Up = Yes equivalent
                            no_token_id=down_token,  # Down = No equivalent
                            end_date=end_date,
                        )
                    )

            # Sort by expiry time (soonest first)
            markets.sort(key=lambda m: m.end_date or datetime.max.replace(tzinfo=None))

            if markets:
                logger.info(f"Found {len(markets)} BTC updown 15m market(s)")

            return markets

        except Exception as e:
            logger.error(f"Error finding BTC updown markets: {e}")
            return []

    def set_market(self, market: MarketData) -> None:
        """Set the current market to track."""
        self._current_market = market
        logger.info(f"Tracking market: {market.question}")

    async def get_current_prices(self) -> Optional[PriceData]:
        """Get current prices for the tracked market.

        Returns None if no market is set.
        """
        if not self._current_market:
            logger.warning("No market set for price tracking")
            return None

        market = self._current_market
        timestamp = datetime.now()

        try:
            # Get order books for both tokens
            yes_book = await self.get_orderbook(market.yes_token_id)
            no_book = await self.get_orderbook(market.no_token_id)

            # Extract best bid/ask prices
            yes_bids = yes_book.get("bids", [])
            yes_asks = yes_book.get("asks", [])
            no_bids = no_book.get("bids", [])
            no_asks = no_book.get("asks", [])

            yes_bid = float(yes_bids[0]["price"]) if yes_bids else 0.0
            yes_ask = float(yes_asks[0]["price"]) if yes_asks else 1.0
            no_bid = float(no_bids[0]["price"]) if no_bids else 0.0
            no_ask = float(no_asks[0]["price"]) if no_asks else 1.0

            # Midpoint prices
            yes_price = (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else 0.5
            no_price = (no_bid + no_ask) / 2 if no_bid and no_ask else 0.5

            # Calculate time to expiry
            time_to_expiry = None
            if market.end_date:
                delta = market.end_date - timestamp
                time_to_expiry = max(0, int(delta.total_seconds()))

            return PriceData(
                timestamp=timestamp,
                market_id=market.market_id,
                yes_price=yes_price,
                no_price=no_price,
                yes_bid=yes_bid,
                yes_ask=yes_ask,
                no_bid=no_bid,
                no_ask=no_ask,
                time_to_expiry_seconds=time_to_expiry,
            )

        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return None

    async def stream_prices(self, interval: float = POLYMARKET_POLL_INTERVAL):
        """Stream prices at regular intervals.

        Yields PriceData objects at the specified interval.
        """
        while True:
            prices = await self.get_current_prices()
            if prices:
                yield prices
            await asyncio.sleep(interval)

    async def search_crypto_markets(self, query: str = "bitcoin") -> List[MarketData]:
        """Search for crypto markets using the Gamma API.

        Args:
            query: Search term (e.g., 'bitcoin', 'btc', 'ethereum')

        Returns:
            List of matching MarketData objects
        """
        session = await self._get_session()
        url = f"{POLYMARKET_GAMMA_URL}/events"

        try:
            params = {"active": "true", "closed": "false", "limit": 100}
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                events = await response.json()

            markets = []
            query_lower = query.lower()

            for event in events:
                title = event.get("title", "").lower()
                event_matches = query_lower in title
                event_markets = event.get("markets", [])

                for m in event_markets:
                    # Search both event title and individual market questions
                    question = m.get("question", "").lower()
                    if not event_matches and query_lower not in question:
                        continue

                    # Get token IDs from clobTokenIds field
                    clob_token_ids = m.get("clobTokenIds", [])
                    outcomes = m.get("outcomes", [])

                    # Need at least 2 tokens for Yes/No binary market
                    if len(clob_token_ids) < 2:
                        continue

                    # Determine which token is Yes and which is No
                    # Usually: first token is "No", second is "Yes"
                    # Or check outcomes list for explicit names
                    if outcomes and len(outcomes) >= 2:
                        # Find Yes/No indices
                        yes_idx = next(
                            (i for i, o in enumerate(outcomes) if o.lower() == "yes"),
                            1  # Default to second token
                        )
                        no_idx = 1 - yes_idx if yes_idx in [0, 1] else 0
                    else:
                        # Default: first=No, second=Yes
                        yes_idx, no_idx = 1, 0

                    yes_token_id = clob_token_ids[yes_idx] if yes_idx < len(clob_token_ids) else ""
                    no_token_id = clob_token_ids[no_idx] if no_idx < len(clob_token_ids) else ""

                    if not yes_token_id or not no_token_id:
                        continue

                    end_date = None
                    if m.get("endDateIso"):
                        try:
                            end_date = datetime.fromisoformat(
                                m["endDateIso"].replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass

                    markets.append(
                        MarketData(
                            market_id=m.get("conditionId", ""),
                            condition_id=m.get("conditionId", ""),
                            question=m.get("question", ""),
                            yes_token_id=yes_token_id,
                            no_token_id=no_token_id,
                            end_date=end_date,
                        )
                    )

            return markets

        except Exception as e:
            logger.error(f"Error searching crypto markets: {e}")
            return []

    @staticmethod
    def create_market(
        market_id: str,
        question: str,
        yes_token_id: str,
        no_token_id: str,
        end_date: Optional[datetime] = None,
    ) -> MarketData:
        """Create a MarketData object from manual input.

        Use this when you know the market/token IDs from the Polymarket UI.

        Args:
            market_id: The condition ID of the market
            question: Description of the market
            yes_token_id: Token ID for the Yes outcome
            no_token_id: Token ID for the No outcome
            end_date: Optional expiry datetime

        Returns:
            MarketData object ready for tracking
        """
        return MarketData(
            market_id=market_id,
            condition_id=market_id,
            question=question,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            end_date=end_date,
        )
