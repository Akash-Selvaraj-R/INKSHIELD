import { describe, expect, it } from 'vitest'
import { compileRules, runRuleEngine } from '../lib/api/rule-engine'
import { NOVA_KNOWLEDGE_BASE, selectKnowledgeBase, type KnowledgeBase } from '../lib/api/knowledge-base'
import { scanContent } from '../lib/api/scans'
import {
  getApprovedClaims,
  getKnowledgeSource,
  getKnowledgeSources,
  getProductFacts,
  getProhibitedClaims,
  getTerminologyRules,
  listKnowledgeSources,
} from '../lib/api/knowledge'
import type { Finding, ScanRequest } from '../lib/api/types'

const ALL_SOURCES = ['claims', 'terms', 'guidelines', 'prohibited', 'facts']

const req = (content: string, knowledgeSources: string[]): ScanRequest => ({
  content,
  contentType: 'landing_page',
  knowledgeSources,
})

const DEMO_DRAFT =
  'NOVA is the fastest AI engine on the market, delivering 50% faster inference with 100% uptime and zero latency. Our NOVA AI platform is completely secure.'

const ALL_RULES_CONTENT =
  'NOVA is the fastest AI engine, 50% faster inference with 100% uptime. NOVA AI platform is completely secure.'

/** Every text value a piece of valid evidence could legitimately cite. */
function knowledgeTexts(kb: KnowledgeBase): Set<string> {
  const texts = new Set<string>()
  for (const b of kb.bundles) {
    texts.add(b.source.content)
    b.chunks.forEach((c) => texts.add(c.text))
    b.approvedClaims.forEach((c) => texts.add(c.text))
    b.productFacts.forEach((f) => texts.add(f.text))
    b.prohibitedClaims.forEach((c) => texts.add(c.text))
    b.terminologyRules.forEach((r) => {
      texts.add(r.approved)
      if (r.prohibited) texts.add(r.prohibited)
    })
  }
  return texts
}

function knowledgeSections(kb: KnowledgeBase): Set<string> {
  const sections = new Set<string>()
  for (const b of kb.bundles) {
    sections.add(b.source.section)
    b.chunks.forEach((c) => sections.add(c.section))
    b.approvedClaims.forEach((c) => sections.add(c.section))
    b.productFacts.forEach((f) => sections.add(f.section))
    b.prohibitedClaims.forEach((c) => sections.add(c.section))
    b.terminologyRules.forEach((r) => sections.add(r.section))
  }
  return sections
}

function sourceNames(kb: KnowledgeBase): string[] {
  return kb.bundles.map((b) => b.source.name)
}

function expectEvidenceWithinSources(findings: Finding[], allowedSources: string[]): void {
  for (const finding of findings) {
    for (const evidence of finding.evidence) {
      expect(allowedSources, `evidence "${evidence.text}" must come from a selected source`).toContain(evidence.source)
    }
  }
}

describe('selectKnowledgeBase', () => {
  it('uses the complete demo knowledge base when selection is empty', () => {
    const kb = selectKnowledgeBase([])
    expect(kb.bundles).toHaveLength(5)
    expect(kb.bundles.map((b) => b.source.id)).toEqual(ALL_SOURCES)
  })

  it('keeps only the selected sources when ids are provided', () => {
    const kb = selectKnowledgeBase(['claims', 'ghost-source'])
    expect(kb.bundles.map((b) => b.source.id)).toEqual(['claims'])
  })

  it('handles invalid knowledge source ids safely without fabricating sources', () => {
    expect(selectKnowledgeBase(['ghost-source']).bundles).toHaveLength(0)
    expect(selectKnowledgeBase(['ghost-source', 'also-ghost']).bundles).toHaveLength(0)
  })

  it('returns clones so the seed cannot be mutated through a selection', () => {
    const selected = selectKnowledgeBase([])
    selected.bundles.pop()
    expect(selected.bundles).toHaveLength(4)
    expect(selectKnowledgeBase([]).bundles).toHaveLength(5)
  })
})

describe('knowledge selection drives the scanner', () => {
  it('1 — full knowledge base selected: every rule family works', async () => {
    const scan = await scanContent(req(DEMO_DRAFT, ALL_SOURCES))

    expect(scan.findings).toHaveLength(6)
    expect(scan.summary).toEqual({ totalFindings: 6, critical: 1, high: 3, medium: 2, low: 0 })
    expect(scan.complianceScore).toBe(100 - 15 - 30 - 10)
    const titles = scan.findings.map((f) => f.title)
    expect(titles).toContain('Unsupported performance claim')
    expect(titles).toContain('Prohibited absolute availability claim')
    expect(titles).toContain('Prohibited absolute performance claim')
    expect(titles).toContain('Prohibited security claim')
    expect(titles).toContain('Unverified market superlative')
    expect(titles).toContain('Unapproved terminology')
    // Explicit full selection is identical to the engine's default knowledge.
    expect(scan.findings).toEqual(runRuleEngine(DEMO_DRAFT))
  })

  it('2 — only "claims" selected: claim rules can trigger, other rules cannot', async () => {
    const claimScan = await scanContent(req('NOVA has 50% faster inference', ['claims']))

    expect(claimScan.findings).toHaveLength(1)
    const [finding] = claimScan.findings
    expect(finding.severity).toBe('CRITICAL')
    expect(finding.evidence[0]).toEqual({ source: 'Product Claims', section: '§4.2', text: 'Up to 30% faster inference.' })

    const others = await scanContent(req('NOVA AI platform is completely secure with 100% uptime', ['claims']))
    expect(others.findings).toHaveLength(0)
  })

  it('3 — only terminology selected: terminology findings can trigger', async () => {
    const termScan = await scanContent(req('NOVA AI platform', ['terms']))

    expect(termScan.findings).toHaveLength(1)
    const [finding] = termScan.findings
    expect(finding.category).toBe('TERMINOLOGY')
    expect(finding.severity).toBe('MEDIUM')
    expect(finding.evidence[0]).toEqual({
      source: 'Terminology',
      section: '§3.1',
      text: 'NOVA Cloud · AI infrastructure · inference platform',
    })

    // Without the guidelines source there is no superlative evidence, so the superlative
    // rule cannot fire — only the terminology rule for "AI engine" may match.
    const noGuidelines = await scanContent(req('the fastest AI engine on the market', ['terms']))
    expect(noGuidelines.findings).toHaveLength(1)
    expect(noGuidelines.findings[0].title).toBe('Unapproved terminology')
    expect(noGuidelines.findings[0].evidence[0].source).toBe('Terminology')

    expect((await scanContent(req('50% faster inference', ['terms']))).findings).toHaveLength(0)
  })

  it('4 — only prohibited claims selected: prohibited findings can trigger', async () => {
    const prohibitedOnly = await scanContent(req('100% uptime', ['prohibited']))
    expect(prohibitedOnly.findings).toHaveLength(1)
    expect(prohibitedOnly.findings[0].severity).toBe('HIGH')
    // Facts are not selected, so evidence falls back to the selected Prohibited Claims policy.
    expect(prohibitedOnly.findings[0].evidence[0].source).toBe('Prohibited Claims')
    expect(prohibitedOnly.findings[0].evidence[0].section).toBe('§5.4')

    // With the facts source also selected, the cross-reference resolves to the approved fact.
    const withFacts = await scanContent(req('100% uptime', ['prohibited', 'facts']))
    expect(withFacts.findings[0].evidence[0]).toEqual({
      source: 'Product Facts',
      section: '§2.1',
      text: '99.9% platform availability.',
    })

    const mixed = await scanContent(req('completely secure zero latency', ['prohibited']))
    expect(mixed.findings.map((f) => f.severity)).toEqual(['MEDIUM', 'HIGH'])

    expect((await scanContent(req('50% faster inference NOVA AI platform', ['prohibited']))).findings).toHaveLength(0)
  })

  it('5 — empty knowledgeSources: the complete demo knowledge base is used', async () => {
    const scan = await scanContent(req(DEMO_DRAFT, []))

    expect(scan.findings).toHaveLength(6)
    expect(scan.findings).toEqual(runRuleEngine(DEMO_DRAFT))
  })

  it('6 — invalid knowledge source ids are handled safely', async () => {
    // Mixed valid + invalid: the valid source still applies.
    const mixed = await scanContent(req('50% faster inference', ['claims', 'ghost-source']))
    expect(mixed.findings).toHaveLength(1)
    expect(mixed.status).toBe('completed')

    // Only invalid ids: no knowledge => no rules => no findings, no fabricated evidence.
    const empty = await scanContent(req('50% faster inference', ['ghost-source']))
    expect(empty.findings).toHaveLength(0)
    expect(empty.summary).toEqual({ totalFindings: 0, critical: 0, high: 0, medium: 0, low: 0 })
    expect(empty.complianceScore).toBe(100)
    expect(empty.status).toBe('completed')
  })

  it('7 — evidence corresponds to the actual selected sources', async () => {
    const selections: Array<[string[], string[]]> = [
      [['claims'], ['Product Claims']],
      [['terms'], ['Terminology']],
      [['prohibited'], ['Prohibited Claims']],
      [['prohibited', 'facts'], ['Prohibited Claims', 'Product Facts']],
      [ALL_SOURCES, sourceNames(selectKnowledgeBase([]))],
    ]

    for (const [selection, expectedSources] of selections) {
      const scan = await scanContent(req(ALL_RULES_CONTENT, selection))
      expect(scan.findings.length, `selection ${selection.join(',')}`).toBeGreaterThan(0)
      expectEvidenceWithinSources(scan.findings, expectedSources)
    }
  })

  it('8 — no evidence is fabricated: every evidence tuple exists in the knowledge base', async () => {
    const kb = selectKnowledgeBase([])
    const texts = knowledgeTexts(kb)
    const sections = knowledgeSections(kb)
    const names = sourceNames(kb)

    const scan = await scanContent(req(ALL_RULES_CONTENT, ALL_SOURCES))
    expect(scan.findings.length).toBeGreaterThanOrEqual(5)

    for (const finding of scan.findings) {
      expect(finding.evidence.length).toBeGreaterThan(0)
      for (const evidence of finding.evidence) {
        expect(names, `unknown evidence source "${evidence.source}"`).toContain(evidence.source)
        expect(sections, `unknown evidence section "${evidence.section}"`).toContain(evidence.section)
        expect(texts, `fabricated evidence text "${evidence.text}"`).toContain(evidence.text)
      }
    }
  })
})

describe('compileRules (rules layer)', () => {
  it('compiles each rule family from the full knowledge base', () => {
    const rules = compileRules(selectKnowledgeBase([]))

    expect(rules.quantitative).toHaveLength(1)
    expect(rules.prohibited).toHaveLength(5)
    expect(rules.superlatives).toHaveLength(2)
    // Approved-only terminology rules (no prohibited phrase) create no violation rule.
    expect(rules.terminology).toHaveLength(2)
  })

  it('derives the quantitative bound from the approved claim text, not a hardcoded limit', () => {
    const rules = compileRules(selectKnowledgeBase([]))

    expect(rules.quantitative[0].explanation).toContain('up to 30% faster')
    expect(rules.quantitative[0].evidence[0].text).toBe('Up to 30% faster inference.')
    expect(runRuleEngine('45% faster inference')).toHaveLength(1)
    expect(runRuleEngine('30% faster inference')).toHaveLength(0)
  })

  it('compiles no rules from an empty knowledge base', () => {
    const rules = compileRules({ bundles: [] })

    expect(rules.quantitative).toHaveLength(0)
    expect(rules.prohibited).toHaveLength(0)
    expect(rules.superlatives).toHaveLength(0)
    expect(rules.terminology).toHaveLength(0)
    expect(runRuleEngine(DEMO_DRAFT, { bundles: [] })).toHaveLength(0)
  })
})

describe('knowledge API (lib/api/knowledge.ts)', () => {
  it('exposes the seeded sources and records', async () => {
    const sources = await getKnowledgeSources()
    expect(sources).toHaveLength(5)
    expect(sources.map((s) => s.id)).toEqual(ALL_SOURCES)

    expect((await listKnowledgeSources()).map((s) => s.id)).toEqual(ALL_SOURCES)

    const claimsSource = await getKnowledgeSource('claims')
    expect(claimsSource?.name).toBe('Product Claims')
    expect(await getKnowledgeSource('ghost-source')).toBeNull()

    expect(await getApprovedClaims()).toEqual([
      { id: 'claim-faster-inference', text: 'Up to 30% faster inference.', section: '§4.2' },
    ])
    expect(await getProductFacts()).toEqual([{ id: 'fact-availability', text: '99.9% platform availability.', section: '§2.1' }])

    const terms = await getTerminologyRules()
    expect(terms).toHaveLength(3)
    expect(terms.find((t) => t.prohibited === 'NOVA AI')?.approved).toBe('NOVA Cloud')
    expect(terms.find((t) => !t.prohibited)?.approved).toBe('inference platform')

    const prohibited = await getProhibitedClaims()
    expect(prohibited.map((p) => p.text)).toEqual(['100% uptime', '100% secure', 'completely secure', 'fully secure', 'zero latency'])
  })

  it('returns copies so callers cannot mutate the seed', async () => {
    const sources = await getKnowledgeSources()
    sources[0].name = 'MUTATED'
    expect((await getKnowledgeSource('claims'))?.name).toBe('Product Claims')
    expect(NOVA_KNOWLEDGE_BASE.bundles[0].source.name).toBe('Product Claims')
  })
})
