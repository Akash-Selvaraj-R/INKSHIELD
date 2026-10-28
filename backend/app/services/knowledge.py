"""Seeded NOVA demo knowledge (M3 Python port of the M2 knowledge model).

Architecture: Knowledge Sources -> Knowledge Rules -> Rule Engine -> Findings.
This module is the first layer: the seeded NOVA demo knowledge.

Policy information lives here exactly once:
- approved quantitative limits come from approved claim texts,
- prohibited phrases come from prohibited claim records,
- approved/prohibited terminology comes from terminology rules,
- brand (superlative) rules are authorized by a bundle's rule kinds.

The rule engine compiles these records; it never hardcodes NOVA policy.
All knowledge is in-memory seed data (no database in M3). Records are
frozen dataclasses, so selections can share instances safely.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

# Rule families a knowledge source can authorize (e.g. superlative checks
# need brand-guideline evidence).
RuleKind = str  # only "superlative" exists today


@dataclass(frozen=True)
class KnowledgeSource:
    """A selectable knowledge source registered in the demo catalog."""

    id: str
    name: str
    type: str
    content: str
    section: str
    status: str
    updated_at: str


@dataclass(frozen=True)
class KnowledgeChunk:
    """A quoted policy/terminology passage used as citable evidence."""

    id: str
    source_id: str
    text: str
    section: str


@dataclass(frozen=True)
class ApprovedClaim:
    """An approved claim; quantitative bounds are parsed from its text."""

    id: str
    text: str
    section: str


@dataclass(frozen=True)
class TerminologyRule:
    """Approved terminology; when a prohibited phrase is set it drives a rule."""

    id: str
    approved: str
    section: str
    prohibited: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[int] = None
    explanation: Optional[str] = None


@dataclass(frozen=True)
class ProductFact:
    """An approved product fact, citable as replacement evidence."""

    id: str
    text: str
    section: str


@dataclass(frozen=True)
class ProhibitedClaim:
    """A prohibited phrase; optional metadata customizes the finding."""

    id: str
    text: str
    section: str
    severity: Optional[str] = None
    confidence: Optional[int] = None
    title: Optional[str] = None
    explanation: Optional[str] = None
    suggested_correction: Optional[str] = None
    # Cross-reference to another knowledge record (source_id, record_id)
    # used as evidence when that source is selected.
    evidence_ref: Optional[tuple[str, str]] = None


@dataclass(frozen=True)
class KnowledgeBundle:
    """All knowledge owned by one selectable KnowledgeSource."""

    source: KnowledgeSource
    rule_kinds: tuple[RuleKind, ...] = ()
    chunks: tuple[KnowledgeChunk, ...] = ()
    approved_claims: tuple[ApprovedClaim, ...] = ()
    terminology_rules: tuple[TerminologyRule, ...] = ()
    product_facts: tuple[ProductFact, ...] = ()
    prohibited_claims: tuple[ProhibitedClaim, ...] = ()


@dataclass(frozen=True)
class KnowledgeBase:
    """The knowledge view consumed by the rule engine."""

    bundles: tuple[KnowledgeBundle, ...] = ()


SECURITY_EXPLANATION = (
    "Absolute security guarantees cannot be substantiated and are prohibited by policy."
)
SECURITY_CORRECTION = "Built for enterprise AI workloads."


def _source(
    source_id: str,
    name: str,
    type_: str,
    content: str,
    section: str,
    status: str,
    updated_at: str,
) -> KnowledgeSource:
    return KnowledgeSource(
        id=source_id,
        name=name,
        type=type_,
        content=content,
        section=section,
        status=status,
        updated_at=updated_at,
    )


# The complete seeded NOVA demo knowledge base.
NOVA_KNOWLEDGE_BASE = KnowledgeBase(
    bundles=(
        # Approved claims — the source of approved quantitative limits.
        KnowledgeBundle(
            source=_source(
                "claims",
                "Product Claims",
                "Approved Claim",
                "\u201cUp to 30% faster inference.\u201d",
                "\u00a74.2",
                "Approved",
                "Oct 24, 2026",
            ),
            approved_claims=(
                ApprovedClaim(
                    id="claim-faster-inference",
                    text="Up to 30% faster inference.",
                    section="\u00a74.2",
                ),
            ),
        ),
        # Terminology — approved and prohibited terms.
        KnowledgeBundle(
            source=_source(
                "terms",
                "Terminology",
                "Approved Term",
                "NOVA Cloud",
                "\u00a73.1",
                "Approved",
                "Oct 22, 2026",
            ),
            chunks=(
                KnowledgeChunk(
                    id="chunk-terms-approved",
                    source_id="terms",
                    text="NOVA Cloud \u00b7 AI infrastructure \u00b7 inference platform",
                    section="\u00a73.1",
                ),
            ),
            terminology_rules=(
                TerminologyRule(
                    id="term-nova-ai",
                    approved="NOVA Cloud",
                    prohibited="NOVA AI",
                    section="\u00a73.1",
                    severity="MEDIUM",
                    confidence=97,
                    explanation=(
                        "This product name is not in the approved terminology set "
                        "for customer-facing content."
                    ),
                ),
                TerminologyRule(
                    id="term-ai-infrastructure",
                    approved="AI infrastructure",
                    prohibited="AI engine",
                    section="\u00a73.1",
                    severity="MEDIUM",
                    confidence=95,
                    explanation=(
                        "\u201cAI engine\u201d is not approved terminology. Use "
                        "\u201cAI infrastructure\u201d or \u201cinference platform\u201d instead."
                    ),
                ),
                TerminologyRule(
                    id="term-inference-platform",
                    approved="inference platform",
                    section="\u00a73.1",
                ),
            ),
        ),
        # Brand guidelines — authorize superlative checks with citable evidence.
        KnowledgeBundle(
            source=_source(
                "guidelines",
                "Brand Guidelines",
                "Voice Rule",
                "Precise \u00b7 Technical \u00b7 Confident",
                "\u00a71.1",
                "Approved",
                "Oct 20, 2026",
            ),
            rule_kinds=("superlative",),
            chunks=(
                KnowledgeChunk(
                    id="chunk-brand-voice",
                    source_id="guidelines",
                    text=(
                        "Precise \u00b7 Technical \u00b7 Confident. NOVA is an AI infrastructure "
                        "company. Avoid unsupported market superlatives such as "
                        "\u201cfastest AI engine\u201d, \u201cbest AI platform\u201d, "
                        "\u201c#1 AI platform\u201d."
                    ),
                    section="\u00a71.3",
                ),
            ),
        ),
        # Prohibited claims — the prohibited phrase list plus policy evidence.
        KnowledgeBundle(
            source=_source(
                "prohibited",
                "Prohibited Claims",
                "Policy",
                "\u201c100% uptime\u201d",
                "\u00a75.4",
                "Active",
                "Oct 19, 2026",
            ),
            chunks=(
                KnowledgeChunk(
                    id="chunk-prohibited-absolute",
                    source_id="prohibited",
                    text=(
                        "Absolute claims (e.g. \u201c100% uptime\u201d, \u201c100% secure\u201d, "
                        "\u201czero latency\u201d) are prohibited; cite approved measured facts instead."
                    ),
                    section="\u00a75.4",
                ),
            ),
            prohibited_claims=(
                ProhibitedClaim(
                    id="prohibit-uptime",
                    text="100% uptime",
                    section="\u00a75.4",
                    severity="HIGH",
                    confidence=99,
                    title="Prohibited absolute availability claim",
                    explanation=(
                        "Absolute availability claims are prohibited. Use the approved "
                        "platform availability figure instead."
                    ),
                    suggested_correction="99.9% platform availability.",
                    evidence_ref=("facts", "fact-availability"),
                ),
                ProhibitedClaim(
                    id="prohibit-secure-percent",
                    text="100% secure",
                    section="\u00a75.4",
                    severity="HIGH",
                    confidence=98,
                    title="Prohibited absolute security claim",
                    explanation=SECURITY_EXPLANATION,
                    suggested_correction=SECURITY_CORRECTION,
                ),
                ProhibitedClaim(
                    id="prohibit-secure-completely",
                    text="completely secure",
                    section="\u00a75.4",
                    severity="MEDIUM",
                    confidence=98,
                    title="Prohibited security claim",
                    explanation=SECURITY_EXPLANATION,
                    suggested_correction=SECURITY_CORRECTION,
                ),
                ProhibitedClaim(
                    id="prohibit-secure-fully",
                    text="fully secure",
                    section="\u00a75.4",
                    severity="MEDIUM",
                    confidence=98,
                    title="Prohibited security claim",
                    explanation=SECURITY_EXPLANATION,
                    suggested_correction=SECURITY_CORRECTION,
                ),
                ProhibitedClaim(
                    id="prohibit-zero-latency",
                    text="zero latency",
                    section="\u00a75.4",
                    severity="HIGH",
                    confidence=97,
                    title="Prohibited absolute performance claim",
                    explanation=(
                        "Absolute performance guarantees are prohibited. Describe "
                        "performance with measured, qualified language instead."
                    ),
                    suggested_correction="Low-latency inference.",
                ),
            ),
        ),
        # Product facts — approved figures cited as replacement evidence.
        KnowledgeBundle(
            source=_source(
                "facts",
                "Product Facts",
                "Platform Fact",
                "99.9% platform availability",
                "\u00a72.1",
                "Approved",
                "Oct 18, 2026",
            ),
            product_facts=(
                ProductFact(
                    id="fact-availability",
                    text="99.9% platform availability.",
                    section="\u00a72.1",
                ),
            ),
        ),
    ),
)


def select_knowledge(source_ids: Sequence[str] = ()) -> KnowledgeBase:
    """Resolve a scan's knowledge source selection into a KnowledgeBase.

    - Empty/omitted selection => the complete seeded knowledge base.
    - Non-empty selection => only the selected sources; unknown ids are
      ignored (never fabricated into a source). If nothing valid remains,
      the result is an empty base, so the engine finds no rules and
      invents no evidence.
    """
    ids = tuple(source_ids)
    if not ids:
        return NOVA_KNOWLEDGE_BASE
    wanted = set(ids)
    return KnowledgeBase(
        bundles=tuple(
            bundle for bundle in NOVA_KNOWLEDGE_BASE.bundles if bundle.source.id in wanted
        )
    )
