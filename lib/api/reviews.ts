import type { Finding, ReviewDecision } from './types'

export async function updateReview(finding: Finding, decision: ReviewDecision): Promise<Finding> {
  return Promise.resolve({ ...finding, status: decision === 'PENDING' ? 'OPEN' : decision, review: { ...finding.review, decision } })
}
