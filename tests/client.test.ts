import { describe, expect, it } from 'vitest'
import { createScan, listAuditEvents, reviewFinding, ScanApiError } from '../lib/api/client'
import type { ScanRequest } from '../lib/api/types'

const request = (content: string): ScanRequest => ({ content, contentType: 'landing_page', knowledgeSources: ['claims'] })

/** A raw FastAPI (snake_case) scan response, as returned by POST /api/v1/scans. */
const apiScan = {
  id: 'scan_abc123def456',
  status: 'completed',
  compliance_score: 85,
  summary: { total_findings: 1, critical: 0, high: 1, medium: 0, low: 0 },
  findings: [
    {
      id: 'INK-0042',
      category: 'CLAIM',
      severity: 'HIGH',
      status: 'OPEN',
      title: 'Prohibited absolute availability claim',
      submitted_text: '100% uptime',
      explanation: 'Absolute availability claims are prohibited.',
      suggested_correction: '99.9% platform availability.',
      confidence: 99,
      evidence: [{ source: 'Product Facts', section: '\u00a72.1', text: '99.9% platform availability.' }],
      review: { required: true, decision: null },
      corrected_text: null,
    },
  ],
  content: '100% uptime',
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('createScan', () => {
  it('sends the camelCase payload and maps the FastAPI response into frontend types', async () => {
    const calls: { url?: string; init?: RequestInit } = {}
    const fetchImpl = (async (url: string, init?: RequestInit) => {
      calls.url = url
      calls.init = init
      return jsonResponse(apiScan)
    }) as unknown as typeof fetch

    const scan = await createScan(request('100% uptime'), fetchImpl)

    expect(calls.url).toBe('http://127.0.0.1:8000/api/v1/scans')
    expect(calls.init?.method).toBe('POST')
    expect(JSON.parse(String(calls.init?.body))).toEqual({
      content: '100% uptime',
      contentType: 'landing_page',
      knowledgeSources: ['claims'],
    })
    expect(scan).toEqual({
      id: 'scan_abc123def456',
      status: 'completed',
      complianceScore: 85,
      summary: { totalFindings: 1, critical: 0, high: 1, medium: 0, low: 0 },
      findings: [
        {
          id: 'INK-0042',
          category: 'CLAIM',
          severity: 'HIGH',
          status: 'OPEN',
          title: 'Prohibited absolute availability claim',
          submittedText: '100% uptime',
          explanation: 'Absolute availability claims are prohibited.',
          suggestedCorrection: '99.9% platform availability.',
          confidence: 99,
          evidence: [{ source: 'Product Facts', section: '\u00a72.1', text: '99.9% platform availability.' }],
          review: { required: true, decision: null },
          correctedText: null,
        },
      ],
      content: '100% uptime',
      contentType: 'landing_page',
    })
  })

  it('throws ScanApiError with the FastAPI detail for non-2xx responses', async () => {
    const fetchImpl = (async () =>
      jsonResponse({ detail: [{ msg: 'Value error, content must not be empty or whitespace-only' }] }, 422)) as unknown as typeof fetch

    const error = await createScan(request(''), fetchImpl).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ScanApiError)
    expect((error as ScanApiError).status).toBe(422)
    expect((error as ScanApiError).message).toContain('content must not be empty')
  })

  it('throws a useful ScanApiError when the backend is unreachable', async () => {
    const fetchImpl = (async () => {
      throw new TypeError('fetch failed')
    }) as unknown as typeof fetch

    const error = await createScan(request('100% uptime'), fetchImpl).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ScanApiError)
    expect((error as ScanApiError).message).toContain('Could not reach the INKSHIELD API')
  })
})

/** A raw FastAPI (snake_case) finding returned by the review endpoint. */
const apiReviewedFinding = {
  id: 'INK-0043',
  category: 'CLAIM',
  severity: 'CRITICAL',
  status: 'EDITED',
  title: 'Unsupported performance claim',
  submitted_text: '50% faster inference',
  explanation: 'The claim exceeds the approved quantitative claim.',
  suggested_correction: 'Up to 30% faster inference.',
  confidence: 96,
  evidence: [{ source: 'Product Claims', section: '\u00a74.2', text: 'Up to 30% faster inference.' }],
  review: { required: true, decision: 'EDITED' },
  corrected_text: 'Up to 30% faster inference.',
}

describe('reviewFinding', () => {
  it('sends the camelCase PATCH request and maps the successful EDITED response', async () => {
    const calls: { url?: string; init?: RequestInit } = {}
    const fetchImpl = (async (url: string, init?: RequestInit) => {
      calls.url = url
      calls.init = init
      return jsonResponse(apiReviewedFinding)
    }) as unknown as typeof fetch

    const updated = await reviewFinding(
      'scan_abc123def456',
      'INK-0043',
      { decision: 'EDITED', correctedText: 'Up to 30% faster inference.' },
      fetchImpl,
    )

    expect(calls.url).toBe('http://127.0.0.1:8000/api/v1/scans/scan_abc123def456/findings/INK-0043/review')
    expect(calls.init?.method).toBe('PATCH')
    expect(JSON.parse(String(calls.init?.body))).toEqual({
      decision: 'EDITED',
      correctedText: 'Up to 30% faster inference.',
    })
    expect(updated).toEqual({
      id: 'INK-0043',
      category: 'CLAIM',
      severity: 'CRITICAL',
      status: 'EDITED',
      title: 'Unsupported performance claim',
      submittedText: '50% faster inference',
      explanation: 'The claim exceeds the approved quantitative claim.',
      suggestedCorrection: 'Up to 30% faster inference.',
      confidence: 96,
      evidence: [{ source: 'Product Claims', section: '\u00a74.2', text: 'Up to 30% faster inference.' }],
      review: { required: true, decision: 'EDITED' },
      correctedText: 'Up to 30% faster inference.',
    })
  })

  it('maps a successful APPROVED response and omits correctedText from the request', async () => {
    const calls: { body?: string } = {}
    const fetchImpl = (async (_url: string, init?: RequestInit) => {
      calls.body = String(init?.body)
      return jsonResponse({
        ...apiReviewedFinding,
        status: 'APPROVED',
        corrected_text: null,
        review: { required: true, decision: 'APPROVED' },
      })
    }) as unknown as typeof fetch

    const updated = await reviewFinding('scan_abc123def456', 'INK-0043', { decision: 'APPROVED' }, fetchImpl)

    expect(JSON.parse(String(calls.body))).toEqual({ decision: 'APPROVED' })
    expect(updated.status).toBe('APPROVED')
    expect(updated.review).toEqual({ required: true, decision: 'APPROVED' })
    expect(updated.correctedText).toBeNull()
    expect(updated.suggestedCorrection).toBe('Up to 30% faster inference.')
  })

  it('throws ScanApiError with the status and FastAPI detail on non-2xx responses', async () => {
    const fetchImpl = (async () =>
      jsonResponse({ detail: "Finding 'INK-9999' was not found in scan 'scan_abc123def456'" }, 404)) as unknown as typeof fetch

    const error = await reviewFinding('scan_abc123def456', 'INK-9999', { decision: 'REJECTED' }, fetchImpl).catch(
      (e: unknown) => e,
    )

    expect(error).toBeInstanceOf(ScanApiError)
    expect((error as ScanApiError).status).toBe(404)
    expect((error as ScanApiError).message).toContain("Finding 'INK-9999' was not found")
  })

  it('throws a useful ScanApiError when the backend is unreachable', async () => {
    const fetchImpl = (async () => {
      throw new TypeError('fetch failed')
    }) as unknown as typeof fetch

    const error = await reviewFinding('scan_abc123def456', 'INK-0043', { decision: 'ESCALATED' }, fetchImpl).catch(
      (e: unknown) => e,
    )

    expect(error).toBeInstanceOf(ScanApiError)
    expect((error as ScanApiError).message).toContain('Could not reach the INKSHIELD API')
  })
})

/** Raw FastAPI (snake_case) audit events, as returned by GET /api/v1/audit-events. */
const apiAuditEvents = [
  {
    id: 'audit_1a2b3c4d5e6f',
    timestamp: '2026-10-28T13:05:11+00:00',
    actor: 'INKSHIELD Scanner',
    actor_type: 'SYSTEM',
    action: 'Scan completed',
    object_type: 'SCAN',
    object_id: 'scan_abc123def456',
    previous_state: 'RUNNING',
    new_state: 'NEEDS REVIEW',
  },
  {
    id: 'audit_9f8e7d6c5b4a',
    timestamp: '2026-10-28T13:05:40+00:00',
    actor: 'Reviewer',
    actor_type: 'HUMAN',
    action: 'Correction edited',
    object_type: 'FINDING',
    object_id: 'INK-0043',
    previous_state: 'PENDING',
    new_state: 'EDITED',
  },
]

describe('listAuditEvents', () => {
  it('requests the audit endpoint and maps the snake_case response into AuditEvent', async () => {
    const calls: { url?: string; init?: RequestInit } = {}
    const fetchImpl = (async (url: string, init?: RequestInit) => {
      calls.url = url
      calls.init = init
      return jsonResponse(apiAuditEvents)
    }) as unknown as typeof fetch

    const events = await listAuditEvents(fetchImpl)

    expect(calls.url).toBe('http://127.0.0.1:8000/api/v1/audit-events')
    expect(calls.init?.method ?? 'GET').toBe('GET')
    expect(events).toEqual([
      {
        id: 'audit_1a2b3c4d5e6f',
        timestamp: '2026-10-28T13:05:11+00:00',
        actor: 'INKSHIELD Scanner',
        actorType: 'SYSTEM',
        action: 'Scan completed',
        objectType: 'SCAN',
        objectId: 'scan_abc123def456',
        previousState: 'RUNNING',
        newState: 'NEEDS REVIEW',
      },
      {
        id: 'audit_9f8e7d6c5b4a',
        timestamp: '2026-10-28T13:05:40+00:00',
        actor: 'Reviewer',
        actorType: 'HUMAN',
        action: 'Correction edited',
        objectType: 'FINDING',
        objectId: 'INK-0043',
        previousState: 'PENDING',
        newState: 'EDITED',
      },
    ])
  })

  it('returns an empty list when no events have been recorded', async () => {
    const fetchImpl = (async () => jsonResponse([])) as unknown as typeof fetch

    await expect(listAuditEvents(fetchImpl)).resolves.toEqual([])
  })

  it('throws ScanApiError with the status for non-2xx responses', async () => {
    const fetchImpl = (async () => jsonResponse({ detail: 'Audit log unavailable' }, 503)) as unknown as typeof fetch

    const error = await listAuditEvents(fetchImpl).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ScanApiError)
    expect((error as ScanApiError).status).toBe(503)
    expect((error as ScanApiError).message).toContain('Audit log unavailable')
  })

  it('throws a useful ScanApiError when the backend is unreachable', async () => {
    const fetchImpl = (async () => {
      throw new TypeError('fetch failed')
    }) as unknown as typeof fetch

    const error = await listAuditEvents(fetchImpl).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ScanApiError)
    expect((error as ScanApiError).message).toContain('Could not reach the INKSHIELD API')
  })
})
