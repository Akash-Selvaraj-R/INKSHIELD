import type { Finding, Scan, ScanRequest, ScanSummary, Severity } from './types'
import { selectKnowledgeBase } from './knowledge-base'
import { runRuleEngine } from './rule-engine'

/**
 * Thrown when a ScanRequest fails validation (Phase 2 contract).
 */
export class ScanValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ScanValidationError'
  }
}

const SEVERITY_WEIGHT: Record<Severity, number> = { CRITICAL: 15, HIGH: 10, MEDIUM: 5, LOW: 2 }

let scanSequence = 0
function nextScanId(): string {
  scanSequence += 1
  return `scan_${Date.now().toString(36)}_${scanSequence.toString(36).padStart(4, '0')}`
}

/**
 * Tally findings by severity into the ScanSummary shape used by the frontend.
 */
export function summarizeFindings(findings: Finding[]): ScanSummary {
  const summary: ScanSummary = { totalFindings: findings.length, critical: 0, high: 0, medium: 0, low: 0 }
  for (const finding of findings) {
    if (finding.severity === 'CRITICAL') summary.critical += 1
    else if (finding.severity === 'HIGH') summary.high += 1
    else if (finding.severity === 'MEDIUM') summary.medium += 1
    else summary.low += 1
  }
  return summary
}

/**
 * Deterministic compliance score: start at 100, subtract a fixed weight per
 * finding by severity, clamped to [0, 100]. Zero findings => 100.
 */
export function calculateComplianceScore(summary: ScanSummary): number {
  const penalty =
    summary.critical * SEVERITY_WEIGHT.CRITICAL +
    summary.high * SEVERITY_WEIGHT.HIGH +
    summary.medium * SEVERITY_WEIGHT.MEDIUM +
    summary.low * SEVERITY_WEIGHT.LOW
  return Math.max(0, Math.min(100, 100 - penalty))
}

/**
 * Real scan pipeline (Phase 2 / M2): validate -> select knowledge sources ->
 * run the deterministic rule engine -> summarize -> score -> completed Scan.
 * `request.knowledgeSources` selects which knowledge sources apply (empty =
 * complete demo knowledge base; unknown ids are ignored, never fabricated).
 * Mock data remains available in mock-data.ts as demo fallback.
 */
export async function scanContent(request: ScanRequest): Promise<Scan> {
  if (!request.content || request.content.trim().length === 0) {
    throw new ScanValidationError('Content is required and cannot be empty.')
  }

  const knowledge = selectKnowledgeBase(request.knowledgeSources)
  const findings = runRuleEngine(request.content, knowledge)
  const summary = summarizeFindings(findings)

  return {
    id: nextScanId(),
    status: 'completed',
    complianceScore: calculateComplianceScore(summary),
    summary,
    findings,
    content: request.content,
    contentType: request.contentType,
  }
}
