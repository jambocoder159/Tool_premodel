"""
CSV storage for collected price data.
"""
import csv
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from ..config import OUTPUT_DIR

logger = logging.getLogger(__name__)


@dataclass
class AlignedDataPoint:
    """Represents a single aligned data point from both sources."""
    timestamp: datetime
    btc_price: float
    yes_price: float
    no_price: float
    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float
    time_to_expiry_seconds: Optional[int]
    market_id: str


class CSVStorage:
    """Thread-safe CSV storage for price data."""

    COLUMNS = [
        "timestamp",
        "btc_price",
        "yes_price",
        "no_price",
        "yes_bid",
        "yes_ask",
        "no_bid",
        "no_ask",
        "time_to_expiry_seconds",
        "market_id",
    ]

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._current_file: Optional[Path] = None
        self._current_date: Optional[str] = None
        self._writer: Optional[csv.writer] = None
        self._file_handle = None

    def _get_filename(self, market_id: str, date: datetime) -> Path:
        """Generate filename for the given market and date."""
        date_str = date.strftime("%Y-%m-%d")
        safe_market_id = market_id[:16] if market_id else "unknown"
        return self.output_dir / f"btc_15min_{safe_market_id}_{date_str}.csv"

    def _ensure_file(self, market_id: str, timestamp: datetime) -> None:
        """Ensure the correct file is open for writing."""
        date_str = timestamp.strftime("%Y-%m-%d")

        # Check if we need to rotate files
        if self._current_date != date_str or self._current_file is None:
            self.close()

            self._current_date = date_str
            self._current_file = self._get_filename(market_id, timestamp)

            # Check if file exists (for appending vs new file)
            file_exists = self._current_file.exists()

            self._file_handle = open(self._current_file, "a", newline="")
            self._writer = csv.writer(self._file_handle)

            # Write header if new file
            if not file_exists:
                self._writer.writerow(self.COLUMNS)
                logger.info(f"Created new CSV file: {self._current_file}")

    def write(self, data: AlignedDataPoint) -> None:
        """Write a data point to CSV.

        Thread-safe operation.
        """
        with self._lock:
            self._ensure_file(data.market_id, data.timestamp)

            row = [
                data.timestamp.isoformat(),
                f"{data.btc_price:.2f}",
                f"{data.yes_price:.4f}",
                f"{data.no_price:.4f}",
                f"{data.yes_bid:.4f}",
                f"{data.yes_ask:.4f}",
                f"{data.no_bid:.4f}",
                f"{data.no_ask:.4f}",
                data.time_to_expiry_seconds or "",
                data.market_id,
            ]

            self._writer.writerow(row)
            self._file_handle.flush()

    def close(self) -> None:
        """Close the current file."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
            self._writer = None
            logger.info(f"Closed CSV file: {self._current_file}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
