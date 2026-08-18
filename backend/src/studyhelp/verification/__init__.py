"""Registers every topic's verifier against the shared registry. Adding a
topic means adding one import + one `registry.register(...)` line here —
the pipeline that calls `interface.registry.get(topic).verify_step()` never
changes (ARCHITECTURE.md D1, D21)."""

from studyhelp.verification.interface import registry
from studyhelp.verification.topics._light_check.base import LightCheckVerifier
from studyhelp.verification.topics.area_perimeter.verifier import AreaPerimeterVerifier
from studyhelp.verification.topics.decimals.verifier import DecimalsVerifier
from studyhelp.verification.topics.fractions_addition.verifier import FractionsAdditionVerifier
from studyhelp.verification.topics.lcm_hcf.verifier import LcmHcfVerifier
from studyhelp.verification.topics.measurement.verifier import MeasurementVerifier
from studyhelp.verification.topics.multiplication_division.verifier import (
    MultiplicationDivisionVerifier,
)
from studyhelp.verification.topics.subtraction_borrowing.verifier import (
    SubtractionBorrowingVerifier,
)

registry.register(SubtractionBorrowingVerifier())
registry.register(FractionsAdditionVerifier())
registry.register(LcmHcfVerifier())
registry.register(DecimalsVerifier())
registry.register(AreaPerimeterVerifier())
registry.register(MultiplicationDivisionVerifier())
registry.register(MeasurementVerifier())

# The 7 "light-check" chapters (Phase F, ARCHITECTURE.md D20/D47's Phase-0
# audit) share one verifier class (_light_check/base.py) — recognition/
# visual/interpretive tasks with a single free-text `answer` field, not a
# multi-field DAG procedure.
for _light_check_topic in (
    "shapes_angles",
    "how_many_squares",
    "symmetry",
    "patterns",
    "mapping",
    "boxes_sketches",
    "smart_charts",
):
    registry.register(LightCheckVerifier(topic=_light_check_topic))

__all__ = ["registry"]
