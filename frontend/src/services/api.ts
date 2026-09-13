/** Centralized API client: base URL, timeouts, JSON, error envelope parsing. */
import type { ApiErrorEnvelope } from '../types/api'

// Same-origin '/api' in production builds (works on localhost AND LAN IPs);
// the dev server has no /api proxy, so dev keeps the absolute backend URL.
const BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? 'http://127.0.0.1:8000/api' : '/api')

/** Per-endpoint timeout strategy: short reads, long analysis (never one tiny
 *  timeout for everything - analysis legitimately takes 30-120+ seconds). */
const TIMEOUTS = {
  fast: 15_000,       // health/list/stats/detail/text
  upload: 60_000,     // multipart upload + parse
  analyze: 300_000,   // synchronous ML analysis
} as const

/** Human-friendly messages for backend error codes (never raw JSON). */
const FRIENDLY: Record<string, string> = {
  UNSUPPORTED_FILE_TYPE: 'That file type is not supported. Please upload a PDF, DOCX or TXT document.',
  FILE_TOO_LARGE: 'The file is too large. Please upload a smaller document.',
  EMPTY_FILE: 'The selected file is empty.',
  INVALID_FILENAME: 'The file name is not valid.',
  CORRUPT_DOCUMENT: 'The document appears to be corrupt and could not be read.',
  ENCRYPTED_DOCUMENT: 'The document is password-protected and cannot be read.',
  EMPTY_DOCUMENT: 'The document contains no readable text.',
  OCR_REQUIRED: 'This looks like a scanned or image-only PDF. Text extraction needs a text layer — OCR is not available yet.',
  PARSE_ERROR: 'The document could not be parsed.',
  CONTRACT_NOT_FOUND: 'This contract could not be found. It may have been deleted.',
  RAW_TEXT_UNAVAILABLE: 'The original text was not stored for this contract, so the document view is unavailable.',
  MODEL_UNAVAILABLE: 'The analysis engine is not available right now. Please set up the model and try again.',
  ANALYSIS_FAILURE: 'The analysis failed. Please try again.',
  ANALYSIS_IN_PROGRESS: 'An analysis for this contract is already running.',
  DATABASE_FAILURE: 'A storage error occurred. Please try again.',
  VALIDATION_ERROR: 'The request was not valid.',
  INTERNAL_ERROR: 'Something went wrong on the server. Please try again.',
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly requestId?: string

  constructor(status: number, envelope: Partial<ApiErrorEnvelope> & { message?: string }) {
    const code = envelope.error ?? 'NETWORK_ERROR'
    super(FRIENDLY[code] ?? envelope.message ?? 'An unexpected error occurred.')
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.requestId = envelope.request_id
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  formData?: FormData
  timeoutMs?: number
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, formData, timeoutMs = TIMEOUTS.analyze } = opts
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: formData ? undefined : { 'Content-Type': 'application/json' },
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal: controller.signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(0, { error: 'TIMEOUT', message: 'The request timed out.' })
    }
    throw new ApiError(0, { error: 'BACKEND_OFFLINE', message: 'The ContractIQ engine is offline.' })
  } finally {
    clearTimeout(timer)
  }

  if (!res.ok) {
    let envelope: ApiErrorEnvelope = { error: `HTTP_${res.status}`, message: res.statusText }
    try {
      const data = await res.json()
      if (data && typeof data === 'object') {
        envelope = 'detail' in data && !('error' in data)
          ? { error: `HTTP_${res.status}`, message: String((data as { detail: unknown }).detail) }
          : (data as ApiErrorEnvelope)
      }
    } catch { /* non-JSON error body */ }
    throw new ApiError(res.status, envelope)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  health: () => request<import('../types/api').Health>('/health', { timeoutMs: 8_000 }),
  stats: () => request<import('../types/api').Stats>('/stats', { timeoutMs: TIMEOUTS.fast }),
  upload: (file: File) => {
    const fd = new FormData()
    fd.append('upload', file)
    return request<import('../types/api').Contract>('/contracts/upload',
      { method: 'POST', formData: fd })
  },
  listContracts: (params: {
    page?: number
    page_size?: number
    search?: string
    status?: string
    risk_level?: string
    sort?: string
  }) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') q.set(k, String(v))
    })
    const qs = q.toString()
    return request<import('../types/api').ContractListResponse>(`/contracts${qs ? `?${qs}` : ''}`,
      { timeoutMs: TIMEOUTS.fast })
  },
  getContract: (id: string) => request<import('../types/api').Contract>(`/contracts/${id}`, { timeoutMs: TIMEOUTS.fast }),
  getRawText: (id: string) => request<import('../types/api').RawText>(`/contracts/${id}/text`, { timeoutMs: TIMEOUTS.fast }),
  analyze: (id: string) =>
    request<{ analysis_id: number; contract_id: string; status: string }>(
      `/contracts/${id}/analyze`, { method: 'POST', timeoutMs: TIMEOUTS.analyze },
    ),
  getAnalysis: (id: string) => request<import('../types/api').Analysis>(`/contracts/${id}/analysis`, { timeoutMs: TIMEOUTS.fast }),
  getAnalysisById: (analysisId: number) =>
    request<import('../types/api').Analysis>(`/analyses/${analysisId}`, { timeoutMs: TIMEOUTS.fast }),
  deleteContract: (id: string) => request<{ deleted: boolean; id: string }>(`/contracts/${id}`, { method: 'DELETE', timeoutMs: TIMEOUTS.fast }),
}

export const API_BASE_URL = BASE_URL
