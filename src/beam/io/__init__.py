"""Adapters that read benchmark output into a tool by metric score table."""

from .csv import read_csv

__all__ = ["read_csv"]
