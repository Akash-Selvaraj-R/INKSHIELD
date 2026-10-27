import type { KnowledgeSource } from './types'
import { mockKnowledgeSources } from './mock-data'

export async function listKnowledgeSources(): Promise<KnowledgeSource[]> {
  return Promise.resolve(mockKnowledgeSources)
}
