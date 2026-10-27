import { describe, expect, it } from 'vitest'
import { calculateComplianceScore, ScanValidationError, scanContent, summarizeFindings } from '../lib/api/scans'
import type { ScanRequest } from '../lib/api/types'

const request = (content: string): ScanRequest => ({ content, contentType: 'landing_page', knowledgeSources: ['claims', 'terms', 'guidelines', 'prohibited', 'facts'] })

describe('scanContent', () => {
  it('TEST 8 — rejects empty content with a validation error', async () => {
    await expect(scanContent(request(''))).rejects.toThrow(ScanValidationError)
    await expect(scanContent(request('   '))).rejects.toThrow('Content is required')
  })

  it('returns a completed Scan with the original content and type preserved', async () => {
    const content = 'NOVA Cloud delivers up to 30% faster inference for enterprise AI workloads.'
    const scan = await scanContent(request(content))

    expect(scan.status).toBe('completed')
    expect(scan.content).toBe(content)
    expect(scan.contentType).toBe('landing_page')
    expect(scan.id).toMatch(/^scan_/)
  })

  it('TEST 1–6 through the full pipeline: summary counts match findings', async () => {
    const scan = await scanContent(request('50% faster inference with 100% uptime and completely secure'))

    expect(scan.findings).toHaveLength(3)
    expect(scan.summary).toEqual({ totalFindings: 3, critical: 1, high: 1, medium: 1, low: 0 })
    expect(scan.complianceScore).toBe(100 - 15 - 10 - 5)
  })

  it('gives a perfect score and empty summary for compliant content', async () => {
    const scan = await scanContent(request('NOVA Cloud is an inference platform for enterprise AI workloads.'))

    expect(scan.findings).toHaveLength(0)
    expect(scan.summary).toEqual({ totalFindings: 0, critical: 0, high: 0, medium: 0, low: 0 })
    expect(scan.complianceScore).toBe(100)
  })

  it('scan IDs are unique across calls', async () => {
    const first = await scanContent(request('100% uptime'))
    const second = await scanContent(request('100% uptime'))

    expect(first.id).not.toBe(second.id)
  })
})

describe('summarizeFindings', () => {
  it('tallies each severity bucket', async () => {
    const scan = await scanContent(request('50% faster inference with 100% uptime and completely secure'))
    const summary = summarizeFindings(scan.findings)

    expect(summary.totalFindings).toBe(scan.findings.length)
    expect(summary.critical + summary.high + summary.medium + summary.low).toBe(summary.totalFindings)
  })
})

describe('calculateComplianceScore', () => {
  it('is deterministic, clamped, and monotonically decreasing with severity weight', () => {
    expect(calculateComplianceScore({ totalFindings: 0, critical: 0, high: 0, medium: 0, low: 0 })).toBe(100)
    expect(calculateComplianceScore({ totalFindings: 1, critical: 1, high: 0, medium: 0, low: 0 })).toBe(85)
    expect(calculateComplianceScore({ totalFindings: 1, critical: 0, high: 1, medium: 0, low: 0 })).toBe(90)
    expect(calculateComplianceScore({ totalFindings: 1, critical: 0, high: 0, medium: 1, low: 0 })).toBe(95)
    expect(calculateComplianceScore({ totalFindings: 1, critical: 0, high: 0, medium: 0, low: 1 })).toBe(98)
    // Never below zero.
    expect(calculateComplianceScore({ totalFindings: 20, critical: 20, high: 0, medium: 0, low: 0 })).toBe(0)
  })
})
