import type { ApprovedClaim, KnowledgeSource, ProductFact, ProhibitedClaim, TerminologyRule } from './types'
import { NOVA_KNOWLEDGE_BASE } from './knowledge-base'

/**
 * Typed in-memory knowledge API (local only — no backend until M3+).
 * Serves the seeded NOVA knowledge base; returns copies so callers cannot
 * mutate the seed. Future milestones swap these implementations for
 * NEXT_PUBLIC_API_URL fetches without touching consumers.
 */

export async function getKnowledgeSources(): Promise<KnowledgeSource[]> {
  return NOVA_KNOWLEDGE_BASE.bundles.map((b) => ({ ...b.source }))
}

export async function getKnowledgeSource(id: string): Promise<KnowledgeSource | null> {
  const source = NOVA_KNOWLEDGE_BASE.bundles.find((b) => b.source.id === id)?.source
  return source ? { ...source } : null
}

export async function getApprovedClaims(): Promise<ApprovedClaim[]> {
  return NOVA_KNOWLEDGE_BASE.bundles.flatMap((b) => b.approvedClaims.map((c) => ({ ...c })))
}

export async function getTerminologyRules(): Promise<TerminologyRule[]> {
  return NOVA_KNOWLEDGE_BASE.bundles.flatMap((b) => b.terminologyRules.map((r) => ({ ...r })))
}

export async function getProductFacts(): Promise<ProductFact[]> {
  return NOVA_KNOWLEDGE_BASE.bundles.flatMap((b) => b.productFacts.map((f) => ({ ...f })))
}

export async function getProhibitedClaims(): Promise<ProhibitedClaim[]> {
  return NOVA_KNOWLEDGE_BASE.bundles.flatMap((b) => b.prohibitedClaims.map((c) => ({ ...c })))
}

/** @deprecated Prefer getKnowledgeSources(); kept for backward compatibility. */
export async function listKnowledgeSources(): Promise<KnowledgeSource[]> {
  return getKnowledgeSources()
}
