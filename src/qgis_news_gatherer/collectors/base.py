# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Base collector class for all data sources."""

from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from rich.console import Console

from qgis_news_gatherer.config import ReportConfig, settings


# Pictographic emoji ranges that render via Noto Color Emoji at full glyph
# size in WeasyPrint. Strip them from user-supplied content to keep inline
# card layouts intact. Pure-text symbols (©, ™, arrows, geometric shapes
# without VS16) are left alone.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric shapes ext
    "\U0001F800-\U0001F8FF"  # supplemental arrows-c
    "\U0001F900-\U0001F9FF"  # supplemental symbols & pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols & pictographs ext-a
    "\U00002600-\U000026FF"  # miscellaneous symbols (sun, star, etc.)
    "\U00002700-\U000027BF"  # dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicators (flags)
    "\ufe0f"  # VS16 emoji presentation selector
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    """Remove pictographic/color emoji from a string."""
    return _EMOJI_RE.sub("", text)


@dataclass
class NewsItem:
    """A single news item from any source."""

    title: str
    url: str | None = None
    description: str | None = None
    date: date_type | None = None
    author: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "date": self.date.isoformat() if self.date else None,
            "author": self.author,
            "category": self.category,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class CollectorResult:
    """Result from a collector."""

    section_name: str
    section_title: str
    items: list[NewsItem] = field(default_factory=list)
    error: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return True if collection succeeded."""
        return self.error is None

    @property
    def has_items(self) -> bool:
        """Return True if there are items."""
        return len(self.items) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "section_name": self.section_name,
            "section_title": self.section_title,
            "items": [item.to_dict() for item in self.items],
            "error": self.error,
            "warnings": self.warnings,
            "success": self.success,
            "item_count": len(self.items),
        }


class BaseCollector(ABC):
    """Base class for all data collectors."""

    section_name: str = "base"
    section_title: str = "Base"

    def __init__(self, config: ReportConfig, console: Console | None = None):
        self.config = config
        self.console = console or Console()
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.request_timeout),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "BaseCollector":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def log_verbose(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.config.verbose:
            self.console.print(f"[dim]{self.section_name}: {message}[/dim]")

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        self.console.print(f"[yellow]Warning ({self.section_name}): {message}[/yellow]")

    def log_error(self, message: str) -> None:
        """Log an error message."""
        self.console.print(f"[red]Error ({self.section_name}): {message}[/red]")

    def is_in_month(self, item_date: date_type | datetime | None) -> bool:
        """Check if a date falls within the target month."""
        if item_date is None:
            return False
        if isinstance(item_date, datetime):
            item_date = item_date.date()
        return self.config.month_start() <= item_date <= self.config.month_end()

    def _cache_path(self) -> Path:
        """Get the cache file path for this collector + month."""
        month_str = self.config.target_month.strftime("%Y-%m")
        cache_dir = settings.cache_dir / month_str
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{self.section_name}.json"

    def _cache_is_valid(self) -> bool:
        """Check if cache exists and is less than 24h old."""
        path = self._cache_path()
        if not path.exists():
            return False
        age_seconds = (datetime.now().timestamp() - path.stat().st_mtime)
        max_age = settings.cache_ttl_hours * 3600
        return age_seconds < max_age

    def _save_cache(self, result: CollectorResult) -> None:
        """Save a CollectorResult to the cache."""
        try:
            path = self._cache_path()
            path.write_text(json.dumps(result.to_dict(), default=str, indent=2))
            self.log_verbose(f"Cached result to {path}")
        except Exception as e:
            self.log_verbose(f"Failed to write cache: {e}")

    def _load_cache(self) -> CollectorResult | None:
        """Load a CollectorResult from the cache."""
        try:
            path = self._cache_path()
            data = json.loads(path.read_text())
            items = []
            for item_data in data.get("items", []):
                item_date = None
                if item_data.get("date"):
                    try:
                        item_date = date_type.fromisoformat(item_data["date"])
                    except (ValueError, TypeError):
                        pass
                items.append(NewsItem(
                    title=item_data.get("title", ""),
                    url=item_data.get("url"),
                    description=item_data.get("description"),
                    date=item_date,
                    author=item_data.get("author"),
                    category=item_data.get("category"),
                    tags=item_data.get("tags", []),
                    metadata=item_data.get("metadata", {}),
                ))
            result = CollectorResult(
                section_name=data.get("section_name", self.section_name),
                section_title=data.get("section_title", self.section_title),
                items=items,
                error=data.get("error"),
                warnings=data.get("warnings", []),
            )
            self.log_verbose(f"Loaded {len(items)} items from cache")
            return result
        except Exception as e:
            self.log_verbose(f"Failed to read cache: {e}")
            return None

    @abstractmethod
    async def collect(self) -> CollectorResult:
        """Collect data from the source. Must be implemented by subclasses."""
        pass

    async def safe_collect(self, force: bool = False) -> CollectorResult:
        """Safely collect data, using cache when available.

        Args:
            force: If True, bypass cache and fetch fresh data.
        """
        # Try cache first
        if not force and self._cache_is_valid():
            cached = self._load_cache()
            if cached is not None:
                return cached

        try:
            result = await self.collect()
            # Cache successful results
            if result.success:
                self._save_cache(result)
            return result
        except httpx.HTTPError as e:
            self.log_error(f"HTTP error: {e}")
            # Fall back to stale cache on error
            cached = self._load_cache()
            if cached is not None:
                self.log_verbose("Using stale cache after HTTP error")
                cached.warnings.append(f"Using cached data (fetch failed: {e})")
                return cached
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                error=f"HTTP error: {e}",
            )
        except asyncio.TimeoutError:
            self.log_error("Request timed out")
            cached = self._load_cache()
            if cached is not None:
                cached.warnings.append("Using cached data (request timed out)")
                return cached
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                error="Request timed out",
            )
        except Exception as e:
            self.log_error(f"Unexpected error: {e}")
            cached = self._load_cache()
            if cached is not None:
                cached.warnings.append(f"Using cached data (error: {e})")
                return cached
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                error=f"Unexpected error: {e}",
            )
