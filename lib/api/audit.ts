import type { AuditEvent } from './types'
import { mockAuditEvents } from './mock-data'

export async function listAuditEvents(): Promise<AuditEvent[]> {
  return Promise.resolve(mockAuditEvents)
}
