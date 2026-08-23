// Topic -> diagram renderer dispatch table (mirrors the backend's
// verifier/analogy registries: one entry per topic, looked up by the exact
// topic string `verification/__init__.py` registers, never a giant
// if/else). Every one of the 14 topics has an entry — the 7 light-check
// topics deliberately share `QuestionCardDiagram`, a scoped-down honest
// fallback, since their `given` has no structured numeric data to draw a
// real geometric/numeric diagram from (see that module's docstring).

import { AreaPerimeterDiagram } from "./AreaPerimeterDiagram";
import { DecimalsDiagram } from "./DecimalsDiagram";
import { FractionsDiagram } from "./FractionsDiagram";
import { LcmHcfDiagram } from "./LcmHcfDiagram";
import { MeasurementDiagram } from "./MeasurementDiagram";
import { MultiplicationDivisionDiagram } from "./MultiplicationDivisionDiagram";
import { QuestionCardDiagram } from "./QuestionCardDiagram";
import { SubtractionDiagram } from "./SubtractionDiagram";
import type { DiagramRenderer } from "./types";

export const DIAGRAM_REGISTRY: Record<string, DiagramRenderer> = {
  subtraction_with_borrowing: SubtractionDiagram,
  fractions_addition: FractionsDiagram,
  lcm_hcf: LcmHcfDiagram,
  decimals: DecimalsDiagram,
  area_perimeter: AreaPerimeterDiagram,
  multiplication_division: MultiplicationDivisionDiagram,
  measurement: MeasurementDiagram,
  shapes_angles: QuestionCardDiagram,
  how_many_squares: QuestionCardDiagram,
  symmetry: QuestionCardDiagram,
  patterns: QuestionCardDiagram,
  mapping: QuestionCardDiagram,
  boxes_sketches: QuestionCardDiagram,
  smart_charts: QuestionCardDiagram,
};

export function getDiagramRenderer(topic: string): DiagramRenderer | undefined {
  return DIAGRAM_REGISTRY[topic];
}
