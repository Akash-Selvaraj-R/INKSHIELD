import type { AuditEvent, Finding, KnowledgeSource, Scan } from './types'

export const demoContent = 'NOVA is the fastest AI engine on the market, delivering 50% faster inference with 100% uptime and zero latency. Our NOVA AI platform is completely secure.'

const f = (id: string, severity: Finding['severity'], category: string, title: string, submittedText: string, text: string, source: string, section: string, explanation: string, suggestedCorrection: string, confidence: number): Finding => ({ id, severity, category, title, submittedText, explanation, suggestedCorrection, confidence, status: 'OPEN', evidence: [{ source, section, text }], review: { required: true, decision: null } })

export const demoFindings: Finding[] = [
  f('INK-0042', 'CRITICAL', 'CLAIM', 'Unsupported performance claim', '50% faster inference', 'Up to 30% faster inference.', 'Product Claims', '§4.2', 'The submitted performance claim exceeds the maximum approved quantitative claim in the brand knowledge base.', 'Up to 30% faster inference.', 96),
  f('INK-0043', 'HIGH', 'CLAIM', 'Prohibited absolute availability claim', '100% uptime', '99.9% platform availability.', 'Product Facts', '§2.1', 'Absolute availability claims are prohibited. Use the approved platform availability figure instead.', '99.9% platform availability.', 99),
  f('INK-0044', 'HIGH', 'TERMINOLOGY', 'Unapproved superlative', 'the fastest AI engine', 'NOVA is an AI infrastructure company.', 'Brand Guidelines', '§1.3', 'Superlatives imply an unverified market comparison and are not consistent with NOVA’s precise, evidence-led voice.', 'NOVA inference platform', 94),
  f('INK-0045', 'MEDIUM', 'TERMINOLOGY', 'Unapproved terminology', 'NOVA AI platform', 'NOVA Cloud · inference platform', 'Terminology', '§3.1', 'This product name is not in the approved terminology set for customer-facing content.', 'NOVA Cloud platform', 97),
  f('INK-0046', 'MEDIUM', 'CLAIM', 'Prohibited security claim', 'completely secure', 'Built for enterprise AI workloads.', 'Prohibited Claims', '§5.4', 'Absolute security guarantees cannot be substantiated and are prohibited by policy.', 'Built for enterprise AI workloads.', 98),
]
export const mockScanResponse: Scan = { id: 'scan_001', status: 'completed', complianceScore: 72, summary: { totalFindings: 5, critical: 1, high: 2, medium: 2, low: 0 }, findings: demoFindings, content: demoContent, contentType: 'landing_page' }
export const mockKnowledgeSources: KnowledgeSource[] = [
 { id: 'claims', name: 'Product Claims', type: 'Approved Claim', content: '“Up to 30% faster inference.”', section: '§4.2', status: 'Approved', updatedAt: 'Oct 24, 2026' },
 { id: 'terms', name: 'Terminology', type: 'Approved Term', content: 'NOVA Cloud', section: '§3.1', status: 'Approved', updatedAt: 'Oct 22, 2026' },
 { id: 'guidelines', name: 'Brand Guidelines', type: 'Voice Rule', content: 'Precise · Technical · Confident', section: '§1.1', status: 'Approved', updatedAt: 'Oct 20, 2026' },
 { id: 'prohibited', name: 'Prohibited Claims', type: 'Policy', content: '“100% uptime”', section: '§5.4', status: 'Active', updatedAt: 'Oct 19, 2026' },
 { id: 'facts', name: 'Product Facts', type: 'Platform Fact', content: '99.9% platform availability', section: '§2.1', status: 'Approved', updatedAt: 'Oct 18, 2026' },
]
export const mockAuditEvents: AuditEvent[] = [
 { id: 'audit_001', timestamp: '10:42:18', actor: 'AI ANALYST', actorType: 'AI', action: 'Finding created', objectType: 'FINDING', objectId: 'INK-0042', previousState: '—', newState: 'PENDING' },
 { id: 'audit_002', timestamp: '10:43:07', actor: 'A. Selvaraj', actorType: 'HUMAN', action: 'Correction approved', objectType: 'FINDING', objectId: 'INK-0042', previousState: 'PENDING', newState: 'APPROVED' },
 { id: 'audit_003', timestamp: '10:44:31', actor: 'Priya M.', actorType: 'HUMAN', action: 'Finding escalated', objectType: 'FINDING', objectId: 'INK-0048', previousState: 'PENDING', newState: 'ESCALATED' },
 { id: 'audit_004', timestamp: '09:18:02', actor: 'AI ANALYST', actorType: 'AI', action: 'Scan completed', objectType: 'SCAN', objectId: 'scan_001', previousState: 'RUNNING', newState: 'NEEDS REVIEW' },
]
