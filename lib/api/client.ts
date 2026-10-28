import type { ContentType, Evidence, Finding, Scan, ScanRequest, ScanSummary } from './types'

/**
 * Typed HTTP client for the INKSHIELD FastAPI backend (M4).
 *
 * - Base URL comes from NEXT_PUBLIC_API_URL (local default only in dev;
 *   production deployments MUST configure it, e.g. on Vercel).
 * - Components call `createScan` and never hardcode URLs themselves.
 * - The request body uses the frontend's camelCase naming
 *   ({ content, contentType, knowledgeSources }); the FastAPI schema
 *   accepts both spellings for knowledge sources.
 * - The snake_case FastAPI response is parsed and mapped into the
 *   existing frontend `Scan` / `Finding` types.
 */

/** Raw backend response shapes, mirroring backend/app/schemas/scan.py. */
interface ApiEvidence {
  source: string
  section: string
  text: string
}

interface ApiFinding {
  id: string
  category: string
  severity: Finding['severity']
  status: 'OPEN'
  title: string
  submitted_text: string
  explanation: string
  suggested_correction: string
  confidence: number
  evidence: ApiEvidence[]
}

interface ApiScanSummary {
  total_findings: number
  critical: number
  high: number
  medium: number
  low: number
}

interface ApiScanResponse {
  id: string
  status: 'completed'
  compliance_score: number
  summary: ApiScanSummary
  findings: ApiFinding[]
  content: string
}

/** Thrown for unreachable backends and non-2xx API responses. */
export class ScanApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ScanApiError'
    this.status = status
  }
}

/** Safe local-development default; production must set NEXT_PUBLIC_API_URL. */
const DEFAULT_LOCAL_API_URL = 'http://127.0.0.1:8000'

function resolveApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim()
  if (configured) return configured.replace(/\/+$/, '')
  if (process.env.NODE_ENV === 'production') {
    throw new ScanApiError(
      'NEXT_PUBLIC_API_URL is not configured. Set it to the deployed FastAPI origin (e.g. https://your-api.example.com) in your environment.',
    )
  }
  return DEFAULT_LOCAL_API_URL
}

/** Extract a human-readable message from a FastAPI error body (e.g. HTTP 422). */
async function readApiError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    const detail = (body as { detail?: unknown })?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => (item as { msg?: unknown })?.msg)
        .filter((msg): msg is string => typeof msg === 'string')
        .join(' ')
      if (messages) return `Validation failed: ${messages}`
    }
  } catch {
    // Non-JSON error body; fall through to the generic message.
  }
  return `The INKSHIELD API rejected the request (HTTP ${response.status}).`
}

function mapEvidence(evidence: ApiEvidence): Evidence {
  return { source: evidence.source, section: evidence.section, text: evidence.text }
}

function mapFinding(finding: ApiFinding): Finding {
  return {
    id: finding.id,
    category: finding.category,
    severity: finding.severity,
    status: finding.status,
    title: finding.title,
    submittedText: finding.submitted_text,
    explanation: finding.explanation,
    suggestedCorrection: finding.suggested_correction,
    confidence: finding.confidence,
    evidence: finding.evidence.map(mapEvidence),
    review: { required: true, decision: null },
  }
}

function mapSummary(summary: ApiScanSummary): ScanSummary {
  return {
    totalFindings: summary.total_findings,
    critical: summary.critical,
    high: summary.high,
    medium: summary.medium,
    low: summary.low,
  }
}

function mapScan(response: ApiScanResponse, contentType: ContentType): Scan {
  return {
    id: response.id,
    status: response.status,
    complianceScore: response.compliance_score,
    summary: mapSummary(response.summary),
    findings: response.findings.map(mapFinding),
    content: response.content,
    contentType,
  }
}

/**
 * Run a scan on the FastAPI backend (POST /api/v1/scans).
 * Throws `ScanApiError` when the backend is unreachable or responds non-2xx.
 */
export async function createScan(
  request: ScanRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<Scan> {
  const baseUrl = resolveApiBaseUrl()

  let response: Response
  try {
    response = await fetchImpl(`${baseUrl}/api/v1/scans`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: request.content,
        contentType: request.contentType,
        knowledgeSources: request.knowledgeSources,
      }),
    })
  } catch {
    throw new ScanApiError(
      `Could not reach the INKSHIELD API at ${baseUrl}. Start the backend (uvicorn app.main:app) or check NEXT_PUBLIC_API_URL.`,
    )
  }

  if (!response.ok) {
    throw new ScanApiError(await readApiError(response), response.status)
  }

  const payload = (await response.json()) as ApiScanResponse
  return mapScan(payload, request.contentType)
}
