import type {
  ApiHealth,
  IntegrationState,
  RagResponse,
  RagStatus,
  RoutingWeights,
} from './types'

export const DEFAULT_API_URL = ''

function apiUrl(baseUrl: string, path: string) {
  return `${baseUrl.replace(/\/+$/, '')}${path}`
}

async function requestJson<T>(
  baseUrl: string,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(apiUrl(baseUrl, path), {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(body?.detail || `Request failed (${response.status})`)
  }

  return response.json() as Promise<T>
}

export const fetchHealth = (baseUrl: string) =>
  requestJson<ApiHealth>(baseUrl, '/api/health')

export const fetchState = (baseUrl: string) =>
  requestJson<IntegrationState>(baseUrl, '/api/state')

export const fetchRagStatus = (baseUrl: string) =>
  requestJson<RagStatus>(baseUrl, '/api/rag/status')

export const saveRoutingWeights = (baseUrl: string, weights: RoutingWeights) =>
  requestJson<{ status: string; routing_weights: RoutingWeights }>(
    baseUrl,
    '/api/network/routing-weights',
    { method: 'PUT', body: JSON.stringify(weights) },
  )

export const queryRag = (
  baseUrl: string,
  query: string,
  alertData?: Record<string, unknown>,
) =>
  requestJson<RagResponse>(baseUrl, '/api/rag/query', {
    method: 'POST',
    body: JSON.stringify({ query, alert_data: alertData }),
  })
