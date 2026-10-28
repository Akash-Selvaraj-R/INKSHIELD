export type ContentType = 'landing_page' | 'social_post' | 'email' | 'advertisement'
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
export type FindingStatus = 'OPEN' | 'APPROVED' | 'REJECTED' | 'EDITED' | 'ESCALATED'
export type ReviewDecision = 'APPROVED' | 'REJECTED' | 'EDITED' | 'ESCALATED' | 'PENDING'
export type ActorType = 'HUMAN' | 'AI' | 'SYSTEM'

export interface Evidence { source: string; section: string; text: string }
export interface Review { required: boolean; decision: ReviewDecision | null }
export interface Finding { id: string; category: string; severity: Severity; status: FindingStatus; title: string; submittedText: string; explanation: string; suggestedCorrection: string; confidence: number; evidence: Evidence[]; review: Review; correctedText?: string | null }
export interface ScanSummary { totalFindings: number; critical: number; high: number; medium: number; low: number }
export interface Scan { id: string; status: 'running' | 'completed' | 'failed'; complianceScore: number; summary: ScanSummary; findings: Finding[]; content: string; contentType: ContentType }
export interface ScanRequest { content: string; contentType: ContentType; knowledgeSources: string[] }
export interface KnowledgeSource { id: string; name: string; type: string; content: string; section: string; status: 'Approved' | 'Active'; updatedAt: string }
export interface KnowledgeChunk { id: string; sourceId: string; text: string; section: string }
export interface ApprovedClaim { id: string; text: string; section: string }
export interface TerminologyRule { id: string; approved: string; prohibited?: string; section: string }
export interface ProductFact { id: string; text: string; section: string }
export interface ProhibitedClaim { id: string; text: string; section: string }
export interface AuditEvent { id: string; timestamp: string; actor: string; actorType: ActorType; action: string; objectType: 'FINDING' | 'SCAN' | 'KNOWLEDGE_SOURCE'; objectId: string; previousState: string; newState: string }
