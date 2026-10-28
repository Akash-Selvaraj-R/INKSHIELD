"""Deterministic rule engine (M3 Python port of the M1/M2 engine).

Knowledge -> Rules -> Engine -> Findings. ``compile_rules`` turns selected
knowledge records into executable rules (the Rules layer); ``run_engine``
executes them against content. Policy information lives only in the
knowledge base — this engine contains no NOVA-specific phrases, limits,
or evidence. Every finding cites evidence resolved from the selected
knowledge; nothing is ever fabricated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional, Pattern

from app.services.knowledge import (
    NOVA_KNOWLEDGE_BASE,
    KnowledgeBase,
    KnowledgeBundle,
    ProhibitedClaim,
)

# Generic detection patterns for unverified market superlatives (pattern
# mechanics, not policy). Only bundles that authorize the "superlative"
# rule kind contribute evidence for these checks.
_SUPERLATIVE_PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
    (
        "fastest-best",
        re.compile(
            r"\b(?:the\s+)?(?:fastest|best)\s+(?:ai\s+)?(?:engine|platform)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "number-one",
        re.compile(r"[#\uff03]\s*1\s+(?:ai\s+)?(?:engine|platform)\b", re.IGNORECASE),
    ),
)
_SUPERLATIVE_EXPLANATION = (
    "Superlatives imply an unverified market comparison that the approved "
    "knowledge base does not substantiate."
)

_QUANTITATIVE_BOUND_PATTERN = re.compile(
    r"up\s+to\s+(\d+(?:[.,]\d+)?)\s*%\s*([a-z]+)", re.IGNORECASE
)


@dataclass(frozen=True)
class EngineEvidence:
    """A citable knowledge reference backing a finding."""

    source: str
    section: str
    text: str


@dataclass(frozen=True)
class EngineFinding:
    """A rule violation produced by the engine, in reading order."""

    id: str
    rule_id: str
    category: str
    severity: str
    title: str
    submitted_text: str
    explanation: str
    suggested_correction: str
    confidence: int
    evidence: tuple[EngineEvidence, ...]


@dataclass(frozen=True)
class _Rule:
    """A rule compiled from knowledge, ready to run against content."""

    id: str
    pattern: Pattern[str]
    category: str
    severity: str
    title: str
    explanation: str
    confidence: int
    evidence: tuple[EngineEvidence, ...]
    correction: Callable[[re.Match[str]], str]
    # Optional guard: only accept matches that satisfy it (e.g. a value
    # above the approved bound).
    accept: Optional[Callable[[re.Match[str]], bool]] = None


@dataclass(frozen=True)
class _CompiledRules:
    quantitative: tuple[_Rule, ...]
    prohibited: tuple[_Rule, ...]
    superlatives: tuple[_Rule, ...]
    terminology: tuple[_Rule, ...]


@dataclass(frozen=True)
class _RuleMatch:
    start: int
    end: int
    rule_id: str
    category: str
    severity: str
    title: str
    explanation: str
    submitted_text: str
    suggested_correction: str
    confidence: int
    evidence: tuple[EngineEvidence, ...]


def _superlative_correction(match: re.Match[str]) -> str:
    text = re.sub(
        r"\b(?:the\s+)?(?:fastest|best)\b\s*", "an ", match.group(0), flags=re.IGNORECASE
    )
    text = re.sub(r"[#\uff03]\s*1\s+", "an ", text, flags=re.IGNORECASE)
    return re.sub(r"\b(?:engine|platform)\b", "infrastructure", text, flags=re.IGNORECASE)


def _parse_quantitative_bound(claim_text: str) -> Optional[tuple[float, str]]:
    """Parse an approved quantitative bound from a claim such as
    "Up to 30% faster inference."."""
    match = _QUANTITATIVE_BOUND_PATTERN.search(claim_text)
    if not match:
        return None
    try:
        maximum = float(match.group(1).replace(",", "."))
    except ValueError:
        return None
    return maximum, match.group(2).lower()


def _resolve_prohibited_evidence(
    knowledge: KnowledgeBase, bundle: KnowledgeBundle, claim: ProhibitedClaim
) -> EngineEvidence:
    """Evidence for a prohibited claim, resolved strictly from selected knowledge:
    1. the record referenced by ``evidence_ref`` (when that source is selected),
    2. else the bundle's policy chunk,
    3. else the prohibited claim record itself.
    """
    if claim.evidence_ref:
        source_id, record_id = claim.evidence_ref
        ref_bundle = next(
            (b for b in knowledge.bundles if b.source.id == source_id), None
        )
        if ref_bundle:
            fact = next((f for f in ref_bundle.product_facts if f.id == record_id), None)
            if fact:
                return EngineEvidence(
                    source=ref_bundle.source.name, section=fact.section, text=fact.text
                )
    if bundle.chunks:
        policy = bundle.chunks[0]
        return EngineEvidence(
            source=bundle.source.name, section=policy.section, text=policy.text
        )
    return EngineEvidence(
        source=bundle.source.name, section=claim.section, text=claim.text
    )


def _compile_quantitative_rules(
    bundle: KnowledgeBundle,
) -> list[_Rule]:
    """Approved claims => quantitative bounds derived from the claim text itself."""
    rules: list[_Rule] = []
    source_name = bundle.source.name
    for claim in bundle.approved_claims:
        bound = _parse_quantitative_bound(claim.text)
        if not bound:
            continue
        maximum, metric = bound

        def accept(match: re.Match[str], maximum: float = maximum) -> bool:
            try:
                value = float(match.group(1).replace(",", "."))
            except ValueError:
                return False
            return value > maximum

        rules.append(
            _Rule(
                id=f"quantitative-{claim.id}",
                pattern=re.compile(
                    rf"(\d+(?:[.,]\d+)?)\s*%\s*{re.escape(metric)}\b(?:\s+\w+)?",
                    re.IGNORECASE,
                ),
                category="CLAIM",
                severity="CRITICAL",
                title="Unsupported performance claim",
                explanation=(
                    "The submitted performance claim exceeds the maximum approved "
                    f"quantitative claim in the brand knowledge base "
                    f"(up to {maximum:g}% {metric})."
                ),
                confidence=96,
                evidence=(
                    EngineEvidence(source=source_name, section=claim.section, text=claim.text),
                ),
                correction=lambda match, claim_text=claim.text: claim_text,
                accept=accept,
            )
        )
    return rules


def _compile_prohibited_rules(
    knowledge: KnowledgeBase, bundle: KnowledgeBundle
) -> list[_Rule]:
    """Prohibited claims => literal phrase matches with resolved evidence."""
    rules: list[_Rule] = []
    for claim in bundle.prohibited_claims:
        rules.append(
            _Rule(
                id=f"prohibited-{claim.id}",
                pattern=re.compile(rf"\b{re.escape(claim.text)}\b", re.IGNORECASE),
                category="CLAIM",
                severity=claim.severity or "HIGH",
                title=claim.title or "Prohibited claim",
                explanation=claim.explanation
                or (
                    "This phrase is listed as prohibited in the brand knowledge base "
                    f"({claim.section}). Remove it or replace it with approved, "
                    "substantiated wording."
                ),
                confidence=claim.confidence or 90,
                evidence=(_resolve_prohibited_evidence(knowledge, bundle, claim),),
                correction=lambda match, claim=claim: claim.suggested_correction
                or "Replace with an approved, substantiated statement.",
            )
        )
    return rules


def _compile_superlative_rules(bundle: KnowledgeBundle) -> list[_Rule]:
    """Brand rules: sources authorized for superlatives contribute their
    policy chunk as evidence."""
    if "superlative" not in bundle.rule_kinds or not bundle.chunks:
        return []
    brand_chunk = bundle.chunks[0]
    evidence = (
        EngineEvidence(
            source=bundle.source.name, section=brand_chunk.section, text=brand_chunk.text
        ),
    )
    return [
        _Rule(
            id=f"superlative-{pattern_id}-{bundle.source.id}",
            pattern=pattern,
            category="TERMINOLOGY",
            severity="HIGH",
            title="Unverified market superlative",
            explanation=_SUPERLATIVE_EXPLANATION,
            confidence=94,
            evidence=evidence,
            correction=_superlative_correction,
        )
        for pattern_id, pattern in _SUPERLATIVE_PATTERNS
    ]


def _compile_terminology_rules(bundle: KnowledgeBundle) -> list[_Rule]:
    """Terminology: rules with a prohibited phrase; evidence is the
    bundle's terminology chunk."""
    if not bundle.chunks:
        return []
    term_chunk = bundle.chunks[0]
    evidence = (
        EngineEvidence(
            source=bundle.source.name, section=term_chunk.section, text=term_chunk.text
        ),
    )
    rules: list[_Rule] = []
    for rule in bundle.terminology_rules:
        if not rule.prohibited:
            continue
        approved = rule.approved
        rules.append(
            _Rule(
                id=f"terminology-{rule.id}",
                pattern=re.compile(
                    rf"\b{re.escape(rule.prohibited)}\b(?:\s+(\w+))?", re.IGNORECASE
                ),
                category="TERMINOLOGY",
                severity=rule.severity or "MEDIUM",
                title="Unapproved terminology",
                explanation=rule.explanation
                or (
                    f"\u201c{rule.prohibited}\u201d is not approved terminology in this "
                    f"knowledge base. Use \u201c{approved}\u201d instead."
                ),
                confidence=rule.confidence or 90,
                evidence=evidence,
                correction=lambda match, approved=approved: (
                    f"{approved} {match.group(1)}" if match.group(1) else approved
                ),
            )
        )
    return rules


def compile_rules(knowledge: KnowledgeBase) -> _CompiledRules:
    """Rules layer: compile the selected knowledge into executable rules.

    Records without citable evidence produce no rule (evidence-first).
    """
    quantitative: list[_Rule] = []
    prohibited: list[_Rule] = []
    superlatives: list[_Rule] = []
    terminology: list[_Rule] = []

    for bundle in knowledge.bundles:
        quantitative.extend(_compile_quantitative_rules(bundle))
        prohibited.extend(_compile_prohibited_rules(knowledge, bundle))
        superlatives.extend(_compile_superlative_rules(bundle))
        terminology.extend(_compile_terminology_rules(bundle))

    return _CompiledRules(
        quantitative=tuple(quantitative),
        prohibited=tuple(prohibited),
        superlatives=tuple(superlatives),
        terminology=tuple(terminology),
    )


def _collect(content: str, rule: _Rule) -> list[_RuleMatch]:
    """Collect every non-empty match of the rule's pattern in ``content``,
    keeping only matches accepted by the rule's guard."""
    matches: list[_RuleMatch] = []
    for match in rule.pattern.finditer(content):
        if match.end() == match.start():
            continue
        if rule.accept and not rule.accept(match):
            continue
        matches.append(
            _RuleMatch(
                start=match.start(),
                end=match.end(),
                rule_id=rule.id,
                category=rule.category,
                severity=rule.severity,
                title=rule.title,
                explanation=rule.explanation,
                submitted_text=match.group(0),
                suggested_correction=rule.correction(match),
                confidence=rule.confidence,
                evidence=rule.evidence,
            )
        )
    return matches


def _run_group(content: str, rules: tuple[_Rule, ...]) -> list[_RuleMatch]:
    return [match for rule in rules for match in _collect(content, rule)]


def run_engine(
    content: str, knowledge: KnowledgeBase = NOVA_KNOWLEDGE_BASE
) -> list[EngineFinding]:
    """Run every deterministic rule compiled from ``knowledge`` against ``content``.

    Rule groups are evaluated in priority order (quantitative claims,
    prohibited absolutes, superlatives, terminology). A later match that
    overlaps an already-accepted span is suppressed, so a phrase such as
    "fastest AI engine" yields a single superlative finding instead of a
    duplicate terminology hit. Findings are returned in reading order with
    sequential IDs from INK-0042. Defaults to the complete seeded NOVA
    knowledge base.
    """
    rules = compile_rules(knowledge)
    candidates: list[_RuleMatch] = [
        *_run_group(content, rules.quantitative),
        *_run_group(content, rules.prohibited),
        *_run_group(content, rules.superlatives),
        *_run_group(content, rules.terminology),
    ]

    accepted: list[_RuleMatch] = []
    for candidate in candidates:
        overlaps = any(
            candidate.start < previous.end and previous.start < candidate.end
            for previous in accepted
        )
        if overlaps:
            continue
        accepted.append(candidate)

    accepted.sort(key=lambda item: (item.start, item.rule_id))
    return [
        EngineFinding(
            id=f"INK-{index + 42:04d}",
            rule_id=match.rule_id,
            category=match.category,
            severity=match.severity,
            title=match.title,
            submitted_text=match.submitted_text,
            explanation=match.explanation,
            suggested_correction=match.suggested_correction,
            confidence=match.confidence,
            evidence=match.evidence,
        )
        for index, match in enumerate(accepted)
    ]
