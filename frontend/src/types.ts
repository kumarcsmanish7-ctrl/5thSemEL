export interface VideoEvent {
  timestamp?: string | null
  anomaly_score?: number | null
  status?: string | null
  event_type?: string | null
  class_name?: string | null
  confidence?: number | null
  camera_id?: string | null
  severity?: string | null
}

export interface NetworkEvent {
  timestamp?: string | null
  attack_status?: string | null
  traffic_rate?: number | null
  latency?: number | null
  packet_loss_pct?: number | null
  routing_status?: string | null
  active_path?: string | null
  source?: string | null
  severity?: string | null
}

export interface AlertEvent {
  time?: string | null
  timestamp?: string | null
  type?: string | null
  severity?: string | null
  source?: string | null
  source_ip?: string | null
  status?: string | null
}

export interface VideoHistoryPoint extends VideoEvent {}
export interface NetworkHistoryPoint extends NetworkEvent {}

export interface RoutingWeights {
  distance: number
  latency: number
  congestion: number
  security_risk: number
}

export interface IntegrationState {
  video_event: VideoEvent | null
  network_event: NetworkEvent | null
  alerts_history: AlertEvent[]
  routing_weights: RoutingWeights
  video_history: VideoHistoryPoint[]
  network_history: NetworkHistoryPoint[]
}

export interface RagStatus {
  retrieval_backend: string
  knowledge_chunks: number
}

export interface RetrievedChunk {
  chunk: {
    doc_id: string
    title: string
    section: string
    content: string
    source_file: string
  }
  similarity_score: number
}

export interface RagResponse {
  kind: 'retrieval' | 'recommendation'
  query?: string
  incident_type?: string
  threat_category?: string
  severity?: string
  source_node?: string
  retrieved_sources: string[]
  retrieved_chunks?: RetrievedChunk[]
  context_summary?: string
  immediate_actions?: string[]
  sdn_routing_guidance?: string
  post_incident_checklist?: string[]
}

export interface ApiHealth {
  status: string
  role?: string
  time?: number
}
