"""Scan pipeline and in-memory scan store (M3).

Validate -> select knowledge sources -> run the deterministic rule engine
-> summarize -> score -> completed scan. There is no database: scans live
in an in-memory store that lasts for the current server process only.
"""

from __future__ import annotations

import threading
from typing import Sequence
from uuid import uuid4

from app.rules.engine import EngineFinding, run_engine
from app.schemas.scan import Evidence, Finding, ScanResponse, ScanSummary, Severity
from app.services.knowledge import select_knowledge

# Fixed per-severity penalties used by the deterministic compliance score.
SEVERITY_WEIGHT: dict[Severity, int] = {
    Severity.CRITICAL: 15,
    Severity.HIGH: 10,
    Severity.MEDIUM: 5,
    Severity.LOW: 2,
}


def summarize_findings(findings: Sequence[Finding]) -> ScanSummary:
    """Tally findings by severity into the ScanSummary shape."""
    counts = {severity: 0 for severity in Severity}
    for finding in findings:
        counts[finding.severity] += 1
    return ScanSummary(
        total_findings=len(findings),
        critical=counts[Severity.CRITICAL],
        high=counts[Severity.HIGH],
        medium=counts[Severity.MEDIUM],
        low=counts[Severity.LOW],
    )


def calculate_compliance_score(summary: ScanSummary) -> int:
    """Deterministic compliance score: start at 100, subtract a fixed
    weight per finding by severity, clamped to [0, 100]. Zero findings => 100."""
    penalty = (
        summary.critical * SEVERITY_WEIGHT[Severity.CRITICAL]
        + summary.high * SEVERITY_WEIGHT[Severity.HIGH]
        + summary.medium * SEVERITY_WEIGHT[Severity.MEDIUM]
        + summary.low * SEVERITY_WEIGHT[Severity.LOW]
    )
    return max(0, min(100, 100 - penalty))


def _next_scan_id() -> str:
    return f"scan_{uuid4().hex[:12]}"


def _to_finding(engine_finding: EngineFinding) -> Finding:
    return Finding(
        id=engine_finding.id,
        category=engine_finding.category,
        severity=Severity(engine_finding.severity),
        title=engine_finding.title,
        submitted_text=engine_finding.submitted_text,
        explanation=engine_finding.explanation,
        suggested_correction=engine_finding.suggested_correction,
        confidence=engine_finding.confidence,
        evidence=[
            Evidence(source=evidence.source, section=evidence.section, text=evidence.text)
            for evidence in engine_finding.evidence
        ],
    )


def scan_content(content: str, knowledge_sources: Sequence[str] = ()) -> ScanResponse:
    """Run the full scan pipeline: select knowledge, run the engine,
    summarize and score. Unknown knowledge source ids are ignored by the
    selection layer, so no evidence is ever fabricated."""
    knowledge = select_knowledge(knowledge_sources)
    findings = [_to_finding(item) for item in run_engine(content, knowledge)]
    summary = summarize_findings(findings)
    return ScanResponse(
        id=_next_scan_id(),
        status="completed",
        compliance_score=calculate_compliance_score(summary),
        summary=summary,
        findings=findings,
        content=content,
    )


class ScanStore:
    """Thread-safe in-memory store for scans in the current process."""

    def __init__(self) -> None:
        self._scans: list[ScanResponse] = []
        self._lock = threading.Lock()

    def add(self, scan: ScanResponse) -> ScanResponse:
        with self._lock:
            self._scans.append(scan)
        return scan

    def list(self) -> list[ScanResponse]:
        with self._lock:
            return list(self._scans)
