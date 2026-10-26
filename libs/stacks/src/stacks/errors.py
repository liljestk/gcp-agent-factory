"""The one error type the CLI reports: anything that stops the matrix from being trustworthy."""

from __future__ import annotations


class StacksError(Exception):
    """The catalog, a module reference or the diff can't be read safely.

    The pipeline fails closed on this error: an unknown change must never look like no change.
    """
