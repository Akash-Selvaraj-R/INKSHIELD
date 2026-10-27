import type { ApprovedClaim, KnowledgeChunk, KnowledgeSource, ProductFact, ProhibitedClaim, Severity, TerminologyRule } from './types'
import { mockKnowledgeSources } from './mock-data'

/**
 * INKSHIELD knowledge model (M2).
 *
 * Architecture: Knowledge Sources -> Knowledge Rules -> Rule Engine -> Findings.
 * This module is the first layer: the seeded NOVA demo knowledge, expressed with
 * the existing types from types.ts (no parallel/duplicate interfaces). Seed-only
 * reporting metadata extends those interfaces via `Seeded*` subtypes below.
 *
 * Policy information lives here exactly once:
 * - approved quantitative limits come from ApprovedClaim texts,
 * - prohibited phrases come from ProhibitedClaim records,
 * - approved/prohibited terminology comes from TerminologyRule records,
 * - brand (superlative) rules are authorized by a bundle's `ruleKinds`.
 *
 * The rule engine compiles these records; it never hardcodes NOVA policy.
 * Everything is in-memory for now (no backend until M3+).
 */

/** Rule families a knowledge source can authorize (e.g. superlative checks need brand-guideline evidence). */
export type RuleKind = 'superlative'

/** Seed-level reporting metadata for a TerminologyRule (base type stays untouched). */
export interface SeededTerminologyRule extends TerminologyRule {
  severity?: Severity
  confidence?: number
  explanation?: string
}

/** Seed-level reporting metadata for a ProhibitedClaim (base type stays untouched). */
export interface SeededProhibitedClaim extends ProhibitedClaim {
  severity?: Severity
  confidence?: number
  title?: string
  explanation?: string
  suggestedCorrection?: string
  /** Cite evidence from another knowledge record (e.g. the approved fact that replaces the claim) when that source is selected. */
  evidenceRef?: { sourceId: string; recordId: string }
}

/** All knowledge owned by one selectable KnowledgeSource. */
export interface KnowledgeBundle {
  source: KnowledgeSource
  /** Rule families this source authorizes. */
  ruleKinds?: RuleKind[]
  chunks: KnowledgeChunk[]
  approvedClaims: ApprovedClaim[]
  terminologyRules: SeededTerminologyRule[]
  productFacts: ProductFact[]
  prohibitedClaims: SeededProhibitedClaim[]
}

/** The knowledge view consumed by the rule engine. */
export interface KnowledgeBase {
  bundles: KnowledgeBundle[]
}

/** Build a bundle from a registered demo source id; fails fast if the seed drifts from mock-data. */
function bundle(sourceId: string, init: Partial<Omit<KnowledgeBundle, 'source'>> = {}): KnowledgeBundle {
  const source = mockKnowledgeSources.find((s) => s.id === sourceId)
  if (!source) throw new Error(`INKSHIELD knowledge seed references unknown source "${sourceId}"`)
  return {
    source: { ...source },
    chunks: [],
    approvedClaims: [],
    terminologyRules: [],
    productFacts: [],
    prohibitedClaims: [],
    ...init,
  }
}

const SECURITY_EXPLANATION = 'Absolute security guarantees cannot be substantiated and are prohibited by policy.'
const SECURITY_CORRECTION = 'Built for enterprise AI workloads.'

/** The complete seeded NOVA demo knowledge base. */
export const NOVA_KNOWLEDGE_BASE: KnowledgeBase = {
  bundles: [
    // Approved claims — the source of approved quantitative limits.
    bundle('claims', {
      approvedClaims: [{ id: 'claim-faster-inference', text: 'Up to 30% faster inference.', section: '§4.2' }],
    }),
    // Terminology — approved and prohibited terms.
    bundle('terms', {
      chunks: [{ id: 'chunk-terms-approved', sourceId: 'terms', text: 'NOVA Cloud · AI infrastructure · inference platform', section: '§3.1' }],
      terminologyRules: [
        { id: 'term-nova-ai', approved: 'NOVA Cloud', prohibited: 'NOVA AI', section: '§3.1', severity: 'MEDIUM', confidence: 97, explanation: 'This product name is not in the approved terminology set for customer-facing content.' },
        { id: 'term-ai-infrastructure', approved: 'AI infrastructure', prohibited: 'AI engine', section: '§3.1', severity: 'MEDIUM', confidence: 95, explanation: '“AI engine” is not approved terminology. Use “AI infrastructure” or “inference platform” instead.' },
        { id: 'term-inference-platform', approved: 'inference platform', section: '§3.1' },
      ],
    }),
    // Brand guidelines — authorize superlative checks with citable evidence.
    bundle('guidelines', {
      ruleKinds: ['superlative'],
      chunks: [{ id: 'chunk-brand-voice', sourceId: 'guidelines', text: 'Precise · Technical · Confident. NOVA is an AI infrastructure company. Avoid unsupported market superlatives such as “fastest AI engine”, “best AI platform”, “#1 AI platform”.', section: '§1.3' }],
    }),
    // Prohibited claims — the prohibited phrase list plus policy evidence.
    bundle('prohibited', {
      chunks: [{ id: 'chunk-prohibited-absolute', sourceId: 'prohibited', text: 'Absolute claims (e.g. “100% uptime”, “100% secure”, “zero latency”) are prohibited; cite approved measured facts instead.', section: '§5.4' }],
      prohibitedClaims: [
        { id: 'prohibit-uptime', text: '100% uptime', section: '§5.4', severity: 'HIGH', confidence: 99, title: 'Prohibited absolute availability claim', explanation: 'Absolute availability claims are prohibited. Use the approved platform availability figure instead.', suggestedCorrection: '99.9% platform availability.', evidenceRef: { sourceId: 'facts', recordId: 'fact-availability' } },
        { id: 'prohibit-secure-percent', text: '100% secure', section: '§5.4', severity: 'HIGH', confidence: 98, title: 'Prohibited absolute security claim', explanation: SECURITY_EXPLANATION, suggestedCorrection: SECURITY_CORRECTION },
        { id: 'prohibit-secure-completely', text: 'completely secure', section: '§5.4', severity: 'MEDIUM', confidence: 98, title: 'Prohibited security claim', explanation: SECURITY_EXPLANATION, suggestedCorrection: SECURITY_CORRECTION },
        { id: 'prohibit-secure-fully', text: 'fully secure', section: '§5.4', severity: 'MEDIUM', confidence: 98, title: 'Prohibited security claim', explanation: SECURITY_EXPLANATION, suggestedCorrection: SECURITY_CORRECTION },
        { id: 'prohibit-zero-latency', text: 'zero latency', section: '§5.4', severity: 'HIGH', confidence: 97, title: 'Prohibited absolute performance claim', explanation: 'Absolute performance guarantees are prohibited. Describe performance with measured, qualified language instead.', suggestedCorrection: 'Low-latency inference.' },
      ],
    }),
    // Product facts — approved figures cited as replacement evidence.
    bundle('facts', {
      productFacts: [{ id: 'fact-availability', text: '99.9% platform availability.', section: '§2.1' }],
    }),
  ],
}

function cloneBundle(b: KnowledgeBundle): KnowledgeBundle {
  return {
    source: { ...b.source },
    ruleKinds: b.ruleKinds ? [...b.ruleKinds] : undefined,
    chunks: b.chunks.map((c) => ({ ...c })),
    approvedClaims: b.approvedClaims.map((c) => ({ ...c })),
    terminologyRules: b.terminologyRules.map((r) => ({ ...r })),
    productFacts: b.productFacts.map((f) => ({ ...f })),
    prohibitedClaims: b.prohibitedClaims.map((c) => ({ ...c })),
  }
}

function cloneBase(kb: KnowledgeBase): KnowledgeBase {
  return { bundles: kb.bundles.map(cloneBundle) }
}

/**
 * Resolve a scan's `knowledgeSources` selection into a KnowledgeBase.
 * - Empty/omitted selection => the complete approved demo knowledge base.
 * - Non-empty selection => only the selected sources; unknown ids are ignored
 *   (never fabricated into a source). If nothing valid remains, the result is
 *   an empty base, so the engine finds no rules and invents no evidence.
 */
export function selectKnowledgeBase(sourceIds: readonly string[] = []): KnowledgeBase {
  if (sourceIds.length === 0) return cloneBase(NOVA_KNOWLEDGE_BASE)
  const wanted = new Set(sourceIds)
  return { bundles: NOVA_KNOWLEDGE_BASE.bundles.filter((b) => wanted.has(b.source.id)).map(cloneBundle) }
}
