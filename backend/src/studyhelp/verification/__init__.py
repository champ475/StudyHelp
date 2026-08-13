"""Registers every topic's verifier against the shared registry. Adding a
topic means adding one import + one `registry.register(...)` line here —
the pipeline that calls `interface.registry.get(topic).verify_step()` never
changes (ARCHITECTURE.md D1, D21)."""

from studyhelp.verification.interface import registry
from studyhelp.verification.topics.subtraction_borrowing.verifier import (
    SubtractionBorrowingVerifier,
)

registry.register(SubtractionBorrowingVerifier())

__all__ = ["registry"]
