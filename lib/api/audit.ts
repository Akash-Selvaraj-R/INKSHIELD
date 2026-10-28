/**
 * Audit trail access (M6). The previously mock-backed stub now delegates
 * to the shared API client, which fetches real events from
 * GET /api/v1/audit-events and maps them into the existing AuditEvent
 * type — no duplicate request/mapping code lives here.
 */
export { listAuditEvents } from './client'
