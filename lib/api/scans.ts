import type { Scan, ScanRequest } from './types'
import { mockScanResponse } from './mock-data'

export async function scanContent(request: ScanRequest): Promise<Scan> {
  void request
  return Promise.resolve(mockScanResponse)
}
