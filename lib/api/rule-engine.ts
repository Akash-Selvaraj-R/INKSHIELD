import type { Evidence, Finding, Severity } from './types'
import { NOVA_KNOWLEDGE_BASE, type KnowledgeBase, type KnowledgeBundle, type SeededProhibitedClaim } from './knowledge-base'

/**
 * Deterministic rule engine (M1, knowledge-driven since M2).
 *
 * Architecture: Knowledge -> Rules -> Engine -> Findings.
 * `compileRules(knowledge)` turns selected knowledge records into executable
 * rules (the Rules layer); `runRuleEngine` executes them against content.
 * Policy information lives only in the knowledge base — this engine contains
 * no NOVA-specific phrases, limits, or evidence. Every finding cites evidence
 * resolved from the selected knowledge; nothing is ever fabricated.
 */

interface RuleMatch {
  start: number
  end: number
  match: string
  ruleId: string
  category: string
  severity: Severity
  title: string
  explanation: string
  suggestedCorrection: string
  confidence: number
  evidence: Evidence[]
}

/** A rule compiled from knowledge, ready to run against content. */
interface CompiledRule {
  id: string
  pattern: RegExp
  category: string
  severity: Severity
  title: string
  explanation: string
  confidence: number
  evidence: Evidence[]
  correction: (match: RegExpExecArray) => string
  /** Optional guard: only accept matches that satisfy it (e.g. value above the approved bound). */
  accept?: (match: RegExpExecArray) => boolean
}

export interface CompiledRules {
  quantitative: CompiledRule[]
  prohibited: CompiledRule[]
  superlatives: CompiledRule[]
  terminology: CompiledRule[]
}

/** Generic detection pattern for unverified market superlatives (pattern mechanics, not policy). */
const SUPERLATIVE_PATTERNS: Array<{ id: string; pattern: RegExp }> = [
  { id: 'fastest-best', pattern: /\b(?:the\s+)?(?:fastest|best)\s+(?:ai\s+)?(?:engine|platform)\b/i },
  { id: 'number-one', pattern: /[#＃]\s*1\s+(?:ai\s+)?(?:engine|platform)\b/i },
]
const SUPERLATIVE_EXPLANATION =
  'Superlatives imply an unverified market comparison that the approved knowledge base does not substantiate.'

function superlativeCorrection(match: string): string {
  return match
    .replace(/\b(?:the\s+)?(?:fastest|best)\b\s*/i, 'an ')
    .replace(/[#＃]\s*1\s+/i, 'an ')
    .replace(/\b(?:engine|platform)\b/i, 'infrastructure')
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** Parse an approved quantitative bound out of a claim such as “Up to 30% faster inference.”. */
function parseQuantitativeBound(claimText: string): { max: number; metric: string } | null {
  const match = /up\s+to\s+(\d+(?:[.,]\d+)?)\s*%\s*([a-z]+)/i.exec(claimText)
  if (!match) return null
  const max = Number.parseFloat(match[1].replace(',', '.'))
  if (!Number.isFinite(max)) return null
  return { max, metric: match[2].toLowerCase() }
}

/**
 * Evidence for a prohibited claim, resolved strictly from selected knowledge:
 * 1. the record referenced by `evidenceRef` (when that source is selected),
 * 2. else the bundle's policy chunk,
 * 3. else the prohibited claim record itself.
 */
function resolveProhibitedEvidence(knowledge: KnowledgeBase, bundle: KnowledgeBundle, claim: SeededProhibitedClaim): Evidence {
  const ref = claim.evidenceRef
  if (ref) {
    const refBundle = knowledge.bundles.find((b) => b.source.id === ref.sourceId)
    const fact = refBundle?.productFacts.find((f) => f.id === ref.recordId)
    if (refBundle && fact) return { source: refBundle.source.name, section: fact.section, text: fact.text }
  }
  const policy = bundle.chunks[0]
  if (policy) return { source: bundle.source.name, section: policy.section, text: policy.text }
  return { source: bundle.source.name, section: claim.section, text: claim.text }
}

/**
 * Rules layer: compile the selected knowledge into executable rules.
 * Records without citable evidence produce no rule (evidence-first).
 */
export function compileRules(knowledge: KnowledgeBase): CompiledRules {
  const quantitative: CompiledRule[] = []
  const prohibited: CompiledRule[] = []
  const superlatives: CompiledRule[] = []
  const terminology: CompiledRule[] = []

  for (const bundle of knowledge.bundles) {
    const sourceName = bundle.source.name

    // Approved claims => quantitative bounds derived from the claim text itself.
    for (const claim of bundle.approvedClaims) {
      const bound = parseQuantitativeBound(claim.text)
      if (!bound) continue
      quantitative.push({
        id: `quantitative-${claim.id}`,
        pattern: new RegExp(`(\\d+(?:[.,]\\d+)?)\\s*%\\s*${escapeRegExp(bound.metric)}\\b(?:\\s+\\w+)?`, 'gi'),
        category: 'CLAIM',
        severity: 'CRITICAL',
        title: 'Unsupported performance claim',
        explanation: `The submitted performance claim exceeds the maximum approved quantitative claim in the brand knowledge base (up to ${bound.max}% ${bound.metric}).`,
        confidence: 96,
        evidence: [{ source: sourceName, section: claim.section, text: claim.text }],
        correction: () => claim.text,
        // Only claims above the approved bound are violations (the exact approved claim never flags).
        accept: (m) => {
          const value = Number.parseFloat(m[1].replace(',', '.'))
          return Number.isFinite(value) && value > bound.max
        },
      })
    }

    // Prohibited claims => literal phrase matches with resolved evidence.
    for (const claim of bundle.prohibitedClaims) {
      prohibited.push({
        id: `prohibited-${claim.id}`,
        pattern: new RegExp(`\\b${escapeRegExp(claim.text)}\\b`, 'i'),
        category: 'CLAIM',
        severity: claim.severity ?? 'HIGH',
        title: claim.title ?? 'Prohibited claim',
        explanation: claim.explanation ?? `This phrase is listed as prohibited in the brand knowledge base (${claim.section}). Remove it or replace it with approved, substantiated wording.`,
        confidence: claim.confidence ?? 90,
        evidence: [resolveProhibitedEvidence(knowledge, bundle, claim)],
        correction: () => claim.suggestedCorrection ?? 'Replace with an approved, substantiated statement.',
      })
    }

    // Brand rules: sources authorized for superlatives contribute their policy chunk as evidence.
    const brandChunk = bundle.ruleKinds?.includes('superlative') ? bundle.chunks[0] : undefined
    if (brandChunk) {
      const evidence: Evidence[] = [{ source: sourceName, section: brandChunk.section, text: brandChunk.text }]
      for (const { id, pattern } of SUPERLATIVE_PATTERNS) {
        superlatives.push({
          id: `superlative-${id}-${bundle.source.id}`,
          pattern,
          category: 'TERMINOLOGY',
          severity: 'HIGH',
          title: 'Unverified market superlative',
          explanation: SUPERLATIVE_EXPLANATION,
          confidence: 94,
          evidence,
          correction: (m) => superlativeCorrection(m[0]),
        })
      }
    }

    // Terminology: rules with a prohibited phrase; evidence is the bundle's terminology chunk.
    const termChunk = bundle.chunks[0]
    for (const rule of bundle.terminologyRules) {
      if (!rule.prohibited || !termChunk) continue
      terminology.push({
        id: `terminology-${rule.id}`,
        pattern: new RegExp(`\\b${escapeRegExp(rule.prohibited)}\\b(?:\\s+(\\w+))?`, 'i'),
        category: 'TERMINOLOGY',
        severity: rule.severity ?? 'MEDIUM',
        title: 'Unapproved terminology',
        explanation: rule.explanation ?? `“${rule.prohibited}” is not approved terminology in this knowledge base. Use “${rule.approved}” instead.`,
        confidence: rule.confidence ?? 90,
        evidence: [{ source: sourceName, section: termChunk.section, text: termChunk.text }],
        correction: (m) => (m[1] ? `${rule.approved} ${m[1]}` : rule.approved),
      })
    }
  }

  return { quantitative, prohibited, superlatives, terminology }
}

/** Collect every non-empty match of `pattern` (cloned with /g) in `content`, keeping only matches accepted by `accept`. */
function collect(
  content: string,
  pattern: RegExp,
  build: (match: RegExpExecArray) => Omit<RuleMatch, 'start' | 'end' | 'match'>,
  accept?: (match: RegExpExecArray) => boolean,
): RuleMatch[] {
  const globalPattern = new RegExp(pattern.source, pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`)
  const matches: RuleMatch[] = []
  let match: RegExpExecArray | null
  while ((match = globalPattern.exec(content)) !== null) {
    if (match[0].length === 0) {
      globalPattern.lastIndex += 1
      continue
    }
    if (accept && !accept(match)) continue
    matches.push({ start: match.index, end: match.index + match[0].length, match: match[0], ...build(match) })
  }
  return matches
}

function runGroup(content: string, rules: CompiledRule[]): RuleMatch[] {
  return rules.flatMap((rule) =>
    collect(
      content,
      rule.pattern,
      (m) => ({
        ruleId: rule.id,
        category: rule.category,
        severity: rule.severity,
        title: rule.title,
        explanation: rule.explanation,
        suggestedCorrection: rule.correction(m),
        confidence: rule.confidence,
        evidence: rule.evidence.map((e) => ({ ...e })),
      }),
      rule.accept,
    ),
  )
}

function toFinding(match: RuleMatch, index: number): Finding {
  return {
    id: `INK-${String(index + 42).padStart(4, '0')}`,
    category: match.category,
    severity: match.severity,
    status: 'OPEN',
    title: match.title,
    submittedText: match.match,
    explanation: match.explanation,
    suggestedCorrection: match.suggestedCorrection,
    confidence: match.confidence,
    evidence: match.evidence.map((e) => ({ ...e })),
    review: { required: true, decision: null },
  }
}

/**
 * Run every deterministic rule compiled from `knowledge` against `content`.
 *
 * Rule groups are evaluated in priority order (quantitative claims, prohibited
 * absolutes, superlatives, terminology). A later match that overlaps an
 * already-accepted span is suppressed, so a phrase such as “fastest AI engine”
 * yields a single superlative finding instead of a duplicate terminology hit.
 * Findings are returned in reading order with sequential IDs from INK-0042.
 * Defaults to the complete seeded NOVA knowledge base.
 */
export function runRuleEngine(content: string, knowledge: KnowledgeBase = NOVA_KNOWLEDGE_BASE): Finding[] {
  const rules = compileRules(knowledge)
  const candidates: RuleMatch[] = [
    ...runGroup(content, rules.quantitative),
    ...runGroup(content, rules.prohibited),
    ...runGroup(content, rules.superlatives),
    ...runGroup(content, rules.terminology),
  ]

  const accepted: RuleMatch[] = []
  for (const candidate of candidates) {
    const overlaps = accepted.some((a) => candidate.start < a.end && a.start < candidate.end)
    if (overlaps) continue
    accepted.push(candidate)
  }

  accepted.sort((a, b) => a.start - b.start || a.ruleId.localeCompare(b.ruleId))
  return accepted.map((match, index) => toFinding(match, index))
}
