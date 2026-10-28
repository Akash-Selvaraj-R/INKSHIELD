import { describe, expect, it } from 'vitest'
import { createScan, ScanApiError } from '../lib/api/client'
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
