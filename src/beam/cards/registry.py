"""In-memory index of metric cards under a metrics/ directory."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

from .loader import load_card
from .model import MetricCard

_DEFAULT_METRICS_DIR = Path(__file__).resolve().parents[3] / "metrics"


class Registry:
    """Discover every metric card under metrics_dir and look them up by id."""

    def __init__(self, metrics_dir: Path | str = _DEFAULT_METRICS_DIR) -> None:
        self.metrics_dir = Path(metrics_dir)
        self._cards: dict[tuple[str, str], MetricCard] = {}
        self._versions: dict[str, list[str]] = defaultdict(list)
        self._load_all()

    def _load_all(self) -> None:
        for card_path in sorted(self.metrics_dir.glob("*/v*.yaml")):
            card = load_card(card_path)
            self._cards[(card.id, card.version)] = card
            self._versions[card.id].append(card.version)
        for versions in self._versions.values():
            versions.sort()

    def get(self, id: str, version: str | None = None) -> MetricCard:
        """Return a metric card by id. Defaults to the latest version."""
        if id not in self._versions:
            raise KeyError(f"no metric card with id {id!r}")
        if version is None:
            version = self._versions[id][-1]
        if (id, version) not in self._cards:
            raise KeyError(f"no version {version!r} for metric card {id!r}")
        return self._cards[(id, version)]

    def list_ids(self) -> list[str]:
        return sorted(self._versions.keys())

    def list_versions(self, id: str) -> list[str]:
        if id not in self._versions:
            raise KeyError(f"no metric card with id {id!r}")
        return list(self._versions[id])

    def __len__(self) -> int:
        return len(self._cards)

    def __iter__(self) -> Iterator[MetricCard]:
        yield from self._cards.values()
