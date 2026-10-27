import { describe, expect, it } from 'vitest'
import { runRuleEngine } from '../lib/api/rule-engine'
import type { Finding } from '../lib/api/types'

const FINDING_ID_PATTERN = /^INK-\d{4}$/

function expectWellFormedFinding(finding: Finding): void {
  expect(finding.id).toMatch(FINDING_ID_PATTERN)
  expect(finding.category).toBeTruthy()
  expect(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']).toContain(finding.severity)
  expect(finding.status).toBe('OPEN')
  expect(finding.title).toBeTruthy()
  expect(finding.submittedText).toBeTruthy()
  expect(finding.explanation).toBeTruthy()
  expect(finding.suggestedCorrection).toBeTruthy()
  expect(finding.confidence).toBeGreaterThan(0)
  expect(finding.confidence).toBeLessThanOrEqual(100)
  expect(finding.evidence.length).toBeGreaterThan(0)
  for (const evidence of finding.evidence) {
    expect(evidence.source).toBeTruthy()
    expect(evidence.section).toBeTruthy()
    expect(evidence.text).toBeTruthy()
  }
  expect(finding.review.required).toBe(true)
  expect(finding.review.decision).toBe(null)
}

describe('runRuleEngine', () => {
  it('TEST 1 — flags "50% faster inference" as an unsupported quantitative claim', () => {
    const findings = runRuleEngine('50% faster inference')

    expect(findings).toHaveLength(1)
    const [finding] = findings
    expectWellFormedFinding(finding)
    expect(finding.category).toBe('CLAIM')
    expect(finding.severity).toBe('CRITICAL')
    expect(finding.submittedText).toBe('50% faster inference')
    expect(finding.evidence[0].source).toBe('Product Claims')
    expect(finding.evidence[0].section).toBe('§4.2')
    expect(finding.evidence[0].text).toBe('Up to 30% faster inference.')
    expect(finding.suggestedCorrection).toBe('Up to 30% faster inference.')
    expect(finding.confidence).toBe(96)
  })

  it('TEST 2 — does not flag the exact approved claim "Up to 30% faster inference."', () => {
    const findings = runRuleEngine('Up to 30% faster inference.')

    const quantitativeFindings = findings.filter((f) => f.title === 'Unsupported performance claim')
    expect(quantitativeFindings).toHaveLength(0)
    expect(findings).toHaveLength(0)
  })

  it('flags other percentages above the approved 30% bound but not below it', () => {
    expect(runRuleEngine('60% faster inference').some((f) => f.severity === 'CRITICAL')).toBe(true)
    expect(runRuleEngine('45% faster inference').some((f) => f.severity === 'CRITICAL')).toBe(true)
    expect(runRuleEngine('20% faster inference')).toHaveLength(0)
  })

  it('TEST 3 — flags "100% uptime" as a prohibited absolute claim', () => {
    const findings = runRuleEngine('100% uptime')

    expect(findings).toHaveLength(1)
    const [finding] = findings
    expectWellFormedFinding(finding)
    expect(finding.category).toBe('CLAIM')
    expect(finding.severity).toBe('HIGH')
    expect(finding.submittedText).toBe('100% uptime')
    expect(finding.evidence[0].source).toBe('Product Facts')
    expect(finding.evidence[0].section).toBe('§2.1')
    expect(finding.evidence[0].text).toBe('99.9% platform availability.')
    expect(finding.suggestedCorrection).toBe('99.9% platform availability.')
  })

  it('TEST 4 — flags "completely secure" as a prohibited security claim', () => {
    const findings = runRuleEngine('completely secure')

    expect(findings).toHaveLength(1)
    const [finding] = findings
    expectWellFormedFinding(finding)
    expect(finding.category).toBe('CLAIM')
    expect(finding.severity).toBe('MEDIUM')
    expect(finding.submittedText).toBe('completely secure')
    expect(finding.evidence[0].source).toBe('Prohibited Claims')
    expect(finding.evidence[0].section).toBe('§5.4')
    expect(finding.suggestedCorrection).toBe('Built for enterprise AI workloads.')
  })

  it('TEST 5 — flags "the fastest AI engine on the market" as an unverified superlative', () => {
    const findings = runRuleEngine('the fastest AI engine on the market')

    expect(findings).toHaveLength(1)
    const [finding] = findings
    expectWellFormedFinding(finding)
    expect(finding.category).toBe('TERMINOLOGY')
    expect(finding.severity).toBe('HIGH')
    expect(finding.submittedText).toContain('fastest')
    expect(finding.evidence[0].source).toBe('Brand Guidelines')
    expect(finding.evidence[0].section).toBe('§1.3')
  })

  it('flags other unverified superlatives from the rule set', () => {
    for (const text of ['the fastest AI platform', 'the best AI platform', '#1 AI platform']) {
      const findings = runRuleEngine(text)
      expect(findings, text).toHaveLength(1)
      expect(findings[0].severity, text).toBe('HIGH')
      expect(findings[0].title, text).toBe('Unverified market superlative')
    }
  })

  it('TEST 6 — flags "NOVA AI platform" as unapproved terminology', () => {
    const findings = runRuleEngine('NOVA AI platform')

    expect(findings).toHaveLength(1)
    const [finding] = findings
    expectWellFormedFinding(finding)
    expect(finding.category).toBe('TERMINOLOGY')
    expect(finding.severity).toBe('MEDIUM')
    expect(finding.submittedText).toBe('NOVA AI platform')
    expect(finding.evidence[0].source).toBe('Terminology')
    expect(finding.evidence[0].section).toBe('§3.1')
    expect(finding.suggestedCorrection).toBe('NOVA Cloud platform')
    expect(finding.confidence).toBe(97)
  })

  it('TEST 7 — returns zero findings for compliant content', () => {
    const findings = runRuleEngine(
      'NOVA Cloud delivers up to 30% faster inference for enterprise AI workloads on our inference platform.',
    )

    expect(findings).toHaveLength(0)
  })

  it('returns zero findings for content with no rule violations', () => {
    expect(runRuleEngine('Welcome to NOVA Cloud.')).toHaveLength(0)
    expect(runRuleEngine('Our inference platform is built for enterprise AI workloads.')).toHaveLength(0)
  })

  it('returns sequential, unique finding IDs starting at INK-0042', () => {
    const findings = runRuleEngine('50% faster inference with 100% uptime and completely secure')

    expect(findings.map((f) => f.id)).toEqual(['INK-0042', 'INK-0043', 'INK-0044'])
  })

  it('suppresses overlapping matches so one phrase yields one finding', () => {
    // "AI engine" inside the superlative must not also raise a terminology finding.
    const findings = runRuleEngine('the fastest AI engine on the market')

    expect(findings).toHaveLength(1)
    expect(findings[0].title).toBe('Unverified market superlative')
  })

  it('processes the full demo draft into well-formed findings in reading order', () => {
    const demo =
      'NOVA is the fastest AI engine on the market, delivering 50% faster inference with 100% uptime and zero latency. Our NOVA AI platform is completely secure.'
    const findings = runRuleEngine(demo)

    expect(findings.length).toBeGreaterThanOrEqual(5)
    for (const finding of findings) expectWellFormedFinding(finding)
    // IDs are unique and sequential from INK-0042 in reading order.
    expect(findings.map((f) => f.id)).toEqual(findings.map((_, i) => `INK-${String(42 + i).padStart(4, '0')}`))
    const positions = findings.map((f) => demo.indexOf(f.submittedText))
    expect(positions).toEqual([...positions].sort((a, b) => a - b))
  })
})
