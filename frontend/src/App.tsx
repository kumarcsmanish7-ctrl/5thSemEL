import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BookOpen,
  Camera,
  Check,
  ChevronRight,
  CircleHelp,
  CircleDot,
  Clock3,
  FileVideo2,
  Gauge,
  GitBranch,
  History,
  LayoutDashboard,
  LoaderCircle,
  Network,
  Search,
  Send,
  Shield,
  ShieldAlert,
  Sparkles,
  Video,
  Wifi,
  WifiOff,
  X,
  Zap,
} from 'lucide-react'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type RefObject,
  type ReactNode,
} from 'react'
import {
  DEFAULT_API_URL,
  fetchHealth,
  fetchRagStatus,
  fetchState,
  queryRag,
  saveRoutingWeights,
} from './api'
import type {
  AlertEvent,
  IntegrationState,
  NetworkHistoryPoint,
  RagResponse,
  RagStatus,
  RoutingWeights,
} from './types'
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'

type TabKey = 'overview' | 'video' | 'network' | 'copilot'
type ConnectionStatus = 'checking' | 'connected' | 'disconnected'
type ToastState = { kind: 'success' | 'error' | 'info'; message: string } | null

interface ChatTurn {
  role: 'user' | 'assistant'
  text: string
  response?: RagResponse
}

const INITIAL_WEIGHTS: RoutingWeights = {
  distance: 0.15,
  latency: 0.25,
  congestion: 0.3,
  security_risk: 0.3,
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#ff5e68',
  HIGH: '#ff9d5c',
  MEDIUM: '#f2c66d',
  LOW: '#48d8c8',
}

const NAV_ITEMS: { id: TabKey; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'video', label: 'Video monitoring', icon: Video },
  { id: 'network', label: 'Network routing', icon: Network },
  { id: 'copilot', label: 'Security copilot', icon: Sparkles },
]

const EMPTY_ALERTS: AlertEvent[] = []
const EMPTY_VIDEO_HISTORY: IntegrationState['video_history'] = []
const EMPTY_NETWORK_HISTORY: IntegrationState['network_history'] = []

function display(value: unknown, suffix = '') {
  if (value === null || value === undefined || value === '') return '—'
  return `${value}${suffix}`
}

function formatTime(value?: string | null, includeDate = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, includeDate
    ? { dateStyle: 'medium', timeStyle: 'short' }
    : { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(date)
}

function severityName(value?: string | null) {
  const severity = (value || 'UNSPECIFIED').toUpperCase()
  return SEVERITY_COLORS[severity] ? severity : 'UNSPECIFIED'
}

function alertTimestamp(alert: AlertEvent) {
  return alert.time || alert.timestamp || ''
}

function buildIncidentContext(alert: AlertEvent): Record<string, unknown> {
  return {
    alert_type: alert.type || 'Security alert',
    severity: alert.severity || 'Unspecified',
    source: alert.source || 'Unspecified',
    details: JSON.stringify(alert),
  }
}

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [apiBaseUrl, setApiBaseUrl] = useState(
    () => localStorage.getItem('soc.apiUrl') || DEFAULT_API_URL,
  )
  const [apiUrlDraft, setApiUrlDraft] = useState(apiBaseUrl)
  const [connection, setConnection] = useState<ConnectionStatus>('checking')
  const [connectionError, setConnectionError] = useState('')
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const [data, setData] = useState<IntegrationState | null>(null)
  const [weightsDraft, setWeightsDraft] = useState<RoutingWeights>(INITIAL_WEIGHTS)
  const weightsDirty = useRef(false)
  const [weightSaving, setWeightSaving] = useState(false)
  const [toast, setToast] = useState<ToastState>(null)
  const [alertSearch, setAlertSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [cameraError, setCameraError] = useState('')
  const cameraRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [ragStatus, setRagStatus] = useState<RagStatus | null>(null)
  const [ragError, setRagError] = useState('')
  const [ragLoading, setRagLoading] = useState(false)
  const [recommendation, setRecommendation] = useState<RagResponse | null>(null)
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([])
  const [query, setQuery] = useState('')
  const [queryLoading, setQueryLoading] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [health, latestState] = await Promise.all([
        fetchHealth(apiBaseUrl),
        fetchState(apiBaseUrl),
      ])
      if (health.status !== 'online') {
        throw new Error('The integration API is not reporting an online status.')
      }
      setData({
        ...latestState,
        video_history: latestState.video_history || [],
        network_history: latestState.network_history || [],
      })
      if (!weightsDirty.current && latestState.routing_weights) {
        setWeightsDraft(latestState.routing_weights)
      }
      setConnection('connected')
      setConnectionError('')
      setLastRefresh(new Date())
    } catch (error) {
      setConnection('disconnected')
      setConnectionError(error instanceof Error ? error.message : 'Unable to reach the integration API.')
    }
  }, [apiBaseUrl])

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => void refresh(), 5000)
    return () => window.clearInterval(timer)
  }, [refresh])

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(null), 4200)
    return () => window.clearTimeout(timer)
  }, [toast])

  useEffect(() => {
    if (cameraRef.current && streamRef.current) {
      cameraRef.current.srcObject = streamRef.current
    }
  }, [cameraActive])

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
  }, [])

  useEffect(() => {
    if (activeTab !== 'copilot' || connection !== 'connected' || ragStatus) return
    let active = true
    fetchRagStatus(apiBaseUrl)
      .then((status) => {
        if (active) {
          setRagStatus(status)
          setRagError('')
        }
      })
      .catch((error: unknown) => {
        if (active) setRagError(error instanceof Error ? error.message : 'Could not load the knowledge base.')
      })
    return () => {
      active = false
    }
  }, [activeTab, apiBaseUrl, connection, ragStatus])

  const videoHistory = data?.video_history || EMPTY_VIDEO_HISTORY
  const networkHistory = data?.network_history || EMPTY_NETWORK_HISTORY
  const alerts = data?.alerts_history || EMPTY_ALERTS
  const videoEvent = data?.video_event || null
  const networkEvent = data?.network_event || null
  const latestAlert = alerts[0] || null
  const weightTotal = Number(Object.values(weightsDraft).reduce((sum, value) => sum + value, 0).toFixed(2))
  const canApplyWeights = Math.abs(weightTotal - 1) < 0.001 && connection === 'connected'

  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {
      CRITICAL: 0,
      HIGH: 0,
      MEDIUM: 0,
      LOW: 0,
    }
    alerts.forEach((alert) => {
      const severity = (alert.severity || '').toUpperCase()
      if (severity in counts) counts[severity] += 1
    })
    return counts
  }, [alerts])

  const trendData = useMemo(() => {
    const groups = new Map<string, { time: string; video: number; network: number }>()
    alerts.forEach((alert) => {
      const parsed = new Date(alertTimestamp(alert))
      if (Number.isNaN(parsed.getTime())) return
      parsed.setMinutes(0, 0, 0)
      const key = parsed.toISOString()
      const entry = groups.get(key) || {
        time: parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        video: 0,
        network: 0,
      }
      if ((alert.type || '').toLowerCase().includes('video')) entry.video += 1
      else entry.network += 1
      groups.set(key, entry)
    })
    return [...groups.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([, value]) => value)
  }, [alerts])

  const severityData = useMemo(
    () => Object.entries(severityCounts)
      .filter(([, value]) => value > 0)
      .map(([name, value]) => ({ name, value, color: SEVERITY_COLORS[name] })),
    [severityCounts],
  )

  const filteredAlerts = useMemo(() => alerts.filter((alert) => {
    const severity = (alert.severity || 'UNSPECIFIED').toUpperCase()
    const queryText = [
      alert.type,
      alert.source,
      alert.status,
      alert.time,
      alert.timestamp,
    ].join(' ').toLowerCase()
    return (severityFilter === 'ALL' || severity === severityFilter)
      && queryText.includes(alertSearch.trim().toLowerCase())
  }), [alerts, alertSearch, severityFilter])

  const videoChartData = useMemo(() => videoHistory.map((point) => ({
    ...point,
    time: formatTime(point.timestamp),
  })), [videoHistory])

  const networkChartData = useMemo(() => networkHistory.map((point) => ({
    ...point,
    time: formatTime(point.timestamp),
  })), [networkHistory])

  const videoObjectUrl = useMemo(
    () => videoFile ? URL.createObjectURL(videoFile) : null,
    [videoFile],
  )

  useEffect(() => {
    return () => {
      if (videoObjectUrl) URL.revokeObjectURL(videoObjectUrl)
    }
  }, [videoObjectUrl])

  const updateApiUrl = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const value = apiUrlDraft.trim().replace(/\/+$/, '')
    localStorage.setItem('soc.apiUrl', value)
    setApiBaseUrl(value)
    setRagStatus(null)
    setToast({ kind: 'info', message: 'Checking the integration API…' })
  }

  const updateWeight = (key: keyof RoutingWeights, value: number) => {
    weightsDirty.current = true
    setWeightsDraft((current) => ({ ...current, [key]: value }))
  }

  const applyWeights = async () => {
    if (Math.abs(weightTotal - 1) >= 0.001) {
      setToast({ kind: 'error', message: 'The four routing weights must add up to 1.00.' })
      return
    }
    setWeightSaving(true)
    try {
      const result = await saveRoutingWeights(apiBaseUrl, weightsDraft)
      weightsDirty.current = false
      setWeightsDraft(result.routing_weights)
      setData((current) => current
        ? { ...current, routing_weights: result.routing_weights }
        : current)
      setToast({ kind: 'success', message: 'Routing weights saved to the integration API.' })
    } catch (error) {
      setToast({
        kind: 'error',
        message: error instanceof Error ? error.message : 'Could not save routing weights.',
      })
    } finally {
      setWeightSaving(false)
    }
  }

  const startCamera = async () => {
    setCameraError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false,
      })
      streamRef.current = stream
      setCameraActive(true)
      if (cameraRef.current) cameraRef.current.srcObject = stream
    } catch (error) {
      setCameraError(error instanceof Error ? error.message : 'Camera access was denied.')
    }
  }

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setCameraActive(false)
  }

  const alertContext = latestAlert ? buildIncidentContext(latestAlert) : undefined

  const getRecommendation = async () => {
    if (!latestAlert) return
    setRagLoading(true)
    setRagError('')
    try {
      const result = await queryRag(
        apiBaseUrl,
        'Recommend mitigation steps for this security alert.',
        alertContext,
      )
      setRecommendation(result)
    } catch (error) {
      setRagError(error instanceof Error ? error.message : 'Could not generate guidance.')
    } finally {
      setRagLoading(false)
    }
  }

  const submitQuery = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const question = query.trim()
    if (!question || queryLoading) return
    setChatTurns((current) => [...current, { role: 'user', text: question }])
    setQuery('')
    setQueryLoading(true)
    try {
      const result = await queryRag(apiBaseUrl, question, alertContext)
      const answer = result.kind === 'recommendation'
        ? result.immediate_actions?.join('\n') || 'No recommendation steps were returned.'
        : result.retrieved_chunks?.map((item) => item.chunk.content).join('\n\n')
          || 'No matching guidance was found in the knowledge base.'
      setChatTurns((current) => [...current, {
        role: 'assistant',
        text: answer,
        response: result,
      }])
    } catch (error) {
      setChatTurns((current) => [...current, {
        role: 'assistant',
        text: error instanceof Error ? error.message : 'The knowledge service is unavailable.',
      }])
    } finally {
      setQueryLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Shield size={22} strokeWidth={2.2} /></div>
          <div>
            <strong>SOC Control</strong>
            <span>CONTROL PANEL</span>
          </div>
        </div>

        <div className="sidebar-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Dashboard sections">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              className={`nav-item ${activeTab === id ? 'selected' : ''}`}
              key={id}
              onClick={() => setActiveTab(id)}
              type="button"
            >
              <Icon size={18} />
              <span>{label}</span>
              {activeTab === id && <ChevronRight className="nav-chevron" size={15} />}
            </button>
          ))}
        </nav>

        <div className="sidebar-section">
          <div className="sidebar-label">CONNECTION</div>
          <form className="api-form" onSubmit={updateApiUrl}>
            <label htmlFor="api-url">Integration API URL</label>
            <div className="api-input-wrap">
              <input
                id="api-url"
                value={apiUrlDraft}
                onChange={(event) => setApiUrlDraft(event.target.value)}
                placeholder="Use local proxy, or enter a full API URL"
                spellCheck={false}
                aria-label="Integration API URL"
              />
              <button type="submit" className="icon-button" aria-label="Save API URL">
                <Check size={15} />
              </button>
            </div>
          </form>
          <div className={`connection-card ${connection}`}>
            {connection === 'connected'
              ? <Wifi size={16} />
              : connection === 'checking'
                ? <LoaderCircle className="spin" size={16} />
                : <WifiOff size={16} />}
            <div>
              <strong>
                {connection === 'connected'
                  ? 'API connected'
                  : connection === 'checking'
                    ? 'Connecting…'
                    : 'API disconnected'}
              </strong>
              <span>
                {connection === 'connected'
                  ? `Updated ${lastRefresh ? formatTime(lastRefresh.toISOString()) : 'now'}`
                  : connectionError || 'Waiting for connection'}
              </span>
            </div>
          </div>
          {connection === 'disconnected' && (
            <div className="connection-help">
              Start the service with:
              <code>uvicorn src.integration_api:app --host 127.0.0.1 --port 8000</code>
            </div>
          )}
        </div>

        <div className="sidebar-section weights-section">
          <div className="sidebar-section-heading">
            <div className="sidebar-label">ROUTING CONTROLS</div>
            <GitBranch size={16} />
          </div>
          <div className="formula">Cost = w₁D + w₂L + w₃C + w₄R</div>
          <p className="side-hint">Weights must total 1.00</p>
          <WeightSlider
            label="Distance"
            value={weightsDraft.distance}
            onChange={(value) => updateWeight('distance', value)}
          />
          <WeightSlider
            label="Latency"
            value={weightsDraft.latency}
            onChange={(value) => updateWeight('latency', value)}
          />
          <WeightSlider
            label="Congestion"
            value={weightsDraft.congestion}
            onChange={(value) => updateWeight('congestion', value)}
          />
          <WeightSlider
            label="Security risk"
            value={weightsDraft.security_risk}
            onChange={(value) => updateWeight('security_risk', value)}
          />
          <div className={`weight-total ${canApplyWeights ? 'valid' : 'invalid'}`}>
            <span>Total</span>
            <strong>{weightTotal.toFixed(2)}</strong>
          </div>
          <button
            className="button button-primary button-full"
            disabled={!canApplyWeights || weightSaving}
            onClick={() => void applyWeights()}
            type="button"
          >
            {weightSaving
              ? <><LoaderCircle className="spin" size={15} /> Saving…</>
              : <><Check size={15} /> Apply weights</>}
          </button>
          <p className="side-hint">
            Saved settings are available to the routing service through the API.
          </p>
        </div>

        <div className="sidebar-footer">
          <div className="footer-status-dot" />
          Live integration mode
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="breadcrumb"><span>Security center</span><ChevronRight size={14} /><strong>Monitoring</strong></div>
          <div className="topbar-right">
            <span className="refresh-indicator"><span className="pulse-dot" /> Refreshes every 5 sec</span>
            <div className={`status-pill ${connection}`}>
              <span className="status-dot" />
              {connection === 'connected' ? 'Live' : connection === 'checking' ? 'Connecting' : 'Offline'}
            </div>
          </div>
        </header>

        {toast && (
          <div className={`toast ${toast.kind}`} role="status">
            {toast.kind === 'success' ? <Check size={17} /> : toast.kind === 'error' ? <AlertTriangle size={17} /> : <Activity size={17} />}
            <span>{toast.message}</span>
            <button className="icon-button" onClick={() => setToast(null)} aria-label="Dismiss notification" type="button"><X size={15} /></button>
          </div>
        )}

        <div className="page-content">
          <section className="page-heading">
            <div>
              <h1 className="hero-title">
                <Shield className="hero-shield" size={40} strokeWidth={2} />
                <span>{activeTab === 'overview'
                  ? 'Cyber-Resilient CCTV Monitoring & Response System'
                  : activeTab === 'video'
                    ? 'Video Anomaly Monitoring & Response'
                    : activeTab === 'network'
                      ? 'Adaptive Network Resilience & Routing'
                      : 'Security Copilot & Response Guidance'}</span>
              </h1>
              <p>
                {activeTab === 'overview'
                  ? 'Video anomaly alerts, network monitoring, and security response guidance.'
                  : activeTab === 'video'
                    ? 'Video alert metadata and local preview controls.'
                    : activeTab === 'network'
                      ? 'Network telemetry and the currently reported forwarding path.'
                      : 'Search security procedures and get alert-grounded response guidance.'}
              </p>
            </div>
            <div className="heading-time">
              <Clock3 size={15} />
              <span>{lastRefresh ? `Updated ${formatTime(lastRefresh.toISOString())}` : 'Awaiting telemetry'}</span>
            </div>
          </section>

          <nav className="reference-tabs" aria-label="Dashboard views">
            {NAV_ITEMS.map(({ id, icon: Icon }) => (
              <button
                type="button"
                key={id}
                className={activeTab === id ? 'active' : ''}
                onClick={() => setActiveTab(id)}
              >
                <Icon size={15} />
                <span>{id === 'overview'
                  ? 'SOC Overview & Active Alerts'
                  : id === 'video'
                    ? 'Video Anomaly Feed'
                    : id === 'network'
                      ? 'Adaptive Network Routing'
                      : 'Security Copilot'}</span>
              </button>
            ))}
          </nav>

          {activeTab === 'overview' && (
            <Overview
              apiConnected={connection === 'connected'}
              alerts={alerts}
              filteredAlerts={filteredAlerts}
              severityCounts={severityCounts}
              trendData={trendData}
              severityData={severityData}
              alertSearch={alertSearch}
              severityFilter={severityFilter}
              onAlertSearch={setAlertSearch}
              onSeverityFilter={setSeverityFilter}
              videoEvent={videoEvent}
              networkEvent={networkEvent}
            />
          )}

          {activeTab === 'video' && (
            <VideoMonitoring
              event={videoEvent}
              history={videoChartData}
              file={videoFile}
              fileUrl={videoObjectUrl}
              onFile={setVideoFile}
              videoRef={cameraRef}
              cameraActive={cameraActive}
              cameraError={cameraError}
              onStartCamera={() => void startCamera()}
              onStopCamera={stopCamera}
            />
          )}

          {activeTab === 'network' && (
            <NetworkMonitoring
              event={networkEvent}
              history={networkChartData}
              weights={weightsDraft}
            />
          )}

          {activeTab === 'copilot' && (
            <Copilot
              apiBaseUrl={apiBaseUrl}
              apiConnected={connection === 'connected'}
              alerts={alerts}
              ragStatus={ragStatus}
              ragError={ragError}
              ragLoading={ragLoading}
              recommendation={recommendation}
              chatTurns={chatTurns}
              query={query}
              queryLoading={queryLoading}
              onQueryChange={setQuery}
              onSubmitQuery={(event) => void submitQuery(event)}
              onGetRecommendation={() => void getRecommendation()}
            />
          )}
        </div>
      </main>
    </div>
  )
}

export default App

function WeightSlider({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (value: number) => void
}) {
  return (
    <label className="weight-slider">
      <span>{label}<strong>{value.toFixed(2)}</strong></span>
      <input
        type="range"
        min="0"
        max="1"
        step="0.05"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  )
}

function Panel({
  title,
  subtitle,
  action,
  children,
  className = '',
}: {
  title: string
  subtitle?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function Overview({
  apiConnected,
  alerts,
  filteredAlerts,
  severityCounts,
  trendData,
  severityData,
  alertSearch,
  severityFilter,
  onAlertSearch,
  onSeverityFilter,
  videoEvent,
  networkEvent,
}: {
  apiConnected: boolean
  alerts: AlertEvent[]
  filteredAlerts: AlertEvent[]
  severityCounts: Record<string, number>
  trendData: { time: string; video: number; network: number }[]
  severityData: { name: string; value: number; color?: string }[]
  alertSearch: string
  severityFilter: string
  onAlertSearch: (value: string) => void
  onSeverityFilter: (value: string) => void
  videoEvent: IntegrationState['video_event']
  networkEvent: IntegrationState['network_event']
}) {
  const cards = [
    { label: 'Critical alerts', value: severityCounts.CRITICAL, color: 'critical', icon: ShieldAlert },
    { label: 'High alerts', value: severityCounts.HIGH, color: 'high', icon: AlertTriangle },
    { label: 'Medium alerts', value: severityCounts.MEDIUM, color: 'medium', icon: Activity },
    { label: 'Low alerts', value: severityCounts.LOW, color: 'low', icon: Check },
  ]

  return (
    <>
      <div className="metric-grid">
        {cards.map(({ label, value, color, icon: Icon }) => (
          <article className={`metric-card ${color}`} key={label}>
            <div className="metric-top">
              <span>{label}</span>
              <span className="metric-icon"><Icon size={17} /></span>
            </div>
            <strong>{apiConnected ? value : '—'}</strong>
            <span className="metric-foot">{apiConnected ? 'From integration API' : 'API unavailable'}</span>
          </article>
        ))}
      </div>

      <div className="overview-grid">
        <Panel
          title="Security alert feed"
          subtitle={`${alerts.length} of 100 recent events`}
          className="alert-panel"
          action={<span className="live-tag"><span className="pulse-dot" /> LIVE FEED</span>}
        >
          <div className="table-tools">
            <div className="search-field">
              <Search size={16} />
              <input
                aria-label="Search alerts"
                placeholder="Search incident, source, status…"
                value={alertSearch}
                onChange={(event) => onAlertSearch(event.target.value)}
              />
            </div>
            <select
              aria-label="Filter by severity"
              value={severityFilter}
              onChange={(event) => onSeverityFilter(event.target.value)}
            >
              <option value="ALL">All severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
              <option value="UNSPECIFIED">Unspecified</option>
            </select>
          </div>
          <div className="alert-list">
            {filteredAlerts.slice(0, 8).map((alert, index) => (
              <div className="alert-row" key={`${alertTimestamp(alert)}-${alert.type}-${index}`}>
                <SeverityBadge severity={alert.severity} />
                <div className="alert-main">
                  <strong>{alert.type || 'Security alert'}</strong>
                  <span>{alert.source || 'Source not provided'} · {formatTime(alertTimestamp(alert), true)}</span>
                </div>
                <span className="alert-status">{alert.status || 'Received'}</span>
              </div>
            ))}
            {!filteredAlerts.length && (
              <EmptyState
                icon={alerts.length ? Search : Shield}
                title={alerts.length ? 'No alerts match your filters' : 'No alerts received yet'}
                message={alerts.length
                  ? 'Try another severity or search term.'
                  : apiConnected
                    ? 'Incoming events will appear here as soon as the connected systems report them.'
                    : 'Connect the integration API to view alert activity.'}
              />
            )}
          </div>
        </Panel>

        <div className="chart-stack">
          <Panel title="Alert activity" subtitle="Hourly count from received alert timestamps">
            {trendData.length ? (
              <div className="chart chart-activity">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData} margin={{ top: 12, right: 12, left: -18, bottom: 0 }}>
                    <CartesianGrid stroke="#202c3d" vertical={false} />
                    <XAxis dataKey="time" tick={{ fill: '#8190a4', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fill: '#8190a4', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Line type="monotone" dataKey="network" name="Network" stroke="#55a6ff" strokeWidth={2.5} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="video" name="Video" stroke="#48d8c8" strokeWidth={2.5} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : <EmptyState compact icon={Activity} title="Waiting for alert history" message="Activity appears as timestamped alerts arrive." />}
          </Panel>
          <Panel title="Severity distribution" subtitle="Recent alerts by reported severity">
            {severityData.length ? (
              <div className="severity-chart-wrap">
                <div className="chart chart-donut">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={severityData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={68} paddingAngle={4} stroke="none">
                        {severityData.map((item) => <Cell key={item.name} fill={item.color} />)}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="severity-legend">
                  {severityData.map((item) => (
                    <div className="legend-row" key={item.name}>
                      <span className="legend-dot" style={{ backgroundColor: item.color }} />
                      <span>{item.name}</span><strong>{item.value}</strong>
                    </div>
                  ))}
                </div>
              </div>
            ) : <EmptyState compact icon={Gauge} title="No severity data" message="Severity breakdown appears when alerts are received." />}
          </Panel>
        </div>
      </div>

      <Panel title="Integrated telemetry" subtitle="Latest values reported by the connected data sources">
        <div className="telemetry-grid">
          <TelemetryCard
            icon={Video}
            label="Video anomaly score"
            value={display(videoEvent?.anomaly_score)}
            detail={videoEvent ? `${videoEvent.camera_id || 'Camera'} · ${videoEvent.status || 'Status unknown'}` : 'Waiting for video events'}
          />
          <TelemetryCard
            icon={Activity}
            label="Network traffic"
            value={display(networkEvent?.traffic_rate, ' pps')}
            detail={networkEvent?.attack_status || 'Waiting for network events'}
          />
          <TelemetryCard
            icon={Zap}
            label="Network latency"
            value={display(networkEvent?.latency, ' ms')}
            detail={`Packet loss ${display(networkEvent?.packet_loss_pct, '%')}`}
          />
          <TelemetryCard
            icon={GitBranch}
            label="Routing state"
            value={display(networkEvent?.routing_status)}
            detail={networkEvent?.active_path || 'Waiting for reported route'}
            compact
          />
        </div>
      </Panel>

      <div className="triage-grid">
        <Panel title="Top alert types" subtitle="Most common in recent history">
          {Object.entries(alerts.reduce<Record<string, number>>((acc, alert) => {
            const name = alert.type || 'Security alert'
            acc[name] = (acc[name] || 0) + 1
            return acc
          }, {})).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([name, count]) => (
            <div className="rank-row" key={name}><span>{name}</span><strong>{count}</strong></div>
          ))}
          {!alerts.length && <p className="quiet-note">Alert categories will appear here as events arrive.</p>}
        </Panel>
        <Panel title="Recent incidents" subtitle="Latest received events">
          {alerts.slice(0, 4).map((alert, index) => (
            <div className="incident-row" key={`${alert.type}-${index}`}>
              <SeverityBadge severity={alert.severity} />
              <div><strong>{alert.type || 'Security alert'}</strong><span>{alert.status || 'Received'}</span></div>
            </div>
          ))}
          {!alerts.length && <p className="quiet-note">No incident events received.</p>}
        </Panel>
        <Panel title="Audit timeline" subtitle="Source and outcome from alert events">
          <div className="audit-list">
            {alerts.slice(0, 5).map((alert, index) => (
              <div className="audit-row" key={`${alertTimestamp(alert)}-${index}`}>
                <span className="audit-time">{formatTime(alertTimestamp(alert))}</span>
                <span className="audit-event">{alert.type || 'Security alert'}</span>
                <span className="audit-source">{alert.source || '—'}</span>
              </div>
            ))}
            {!alerts.length && <p className="quiet-note">Audit entries appear when alerts are received.</p>}
          </div>
        </Panel>
      </div>

      <div className="data-footnote"><History size={14} /> Showing data received from the integration API; no simulated events are displayed.</div>
    </>
  )
}

function TelemetryCard({
  icon: Icon,
  label,
  value,
  detail,
  compact = false,
}: {
  icon: typeof Activity
  label: string
  value: string
  detail: string
  compact?: boolean
}) {
  return (
    <div className="telemetry-card">
      <div className="telemetry-label"><span><Icon size={16} /></span>{label}</div>
      <strong className={compact ? 'compact-value' : ''}>{value}</strong>
      <p>{detail}</p>
    </div>
  )
}

function SeverityBadge({ severity }: { severity?: string | null }) {
  const value = severityName(severity)
  return <span className={`severity-badge ${value.toLowerCase()}`}>{value}</span>
}

function EmptyState({
  icon: Icon,
  title,
  message,
  compact = false,
}: {
  icon: typeof Shield
  title: string
  message: string
  compact?: boolean
}) {
  return (
    <div className={`empty-state ${compact ? 'compact' : ''}`}>
      <div className="empty-icon"><Icon size={20} /></div>
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
  )
}

const tooltipStyle = {
  backgroundColor: '#111a29',
  border: '1px solid #29364a',
  borderRadius: 10,
  color: '#edf4ff',
}

function VideoMonitoring({
  event,
  history,
  file,
  fileUrl,
  onFile,
  videoRef,
  cameraActive,
  cameraError,
  onStartCamera,
  onStopCamera,
}: {
  event: IntegrationState['video_event']
  history: (IntegrationState['video_history'][number] & { time: string })[]
  file: File | null
  fileUrl: string | null
  onFile: (file: File | null) => void
  videoRef: RefObject<HTMLVideoElement | null>
  cameraActive: boolean
  cameraError: string
  onStartCamera: () => void
  onStopCamera: () => void
}) {
  const eventSeverity = severityName(event?.severity)
  const statusText = event?.status || 'Waiting for video event'

  return (
    <>
      <div className="video-metrics">
        <div className="video-status-card">
          <div className="metric-symbol"><Video size={18} /></div>
          <div><span>Camera status</span><strong>{event ? statusText.replaceAll('_', ' ') : 'Awaiting event'}</strong></div>
          {event && <SeverityBadge severity={event.severity} />}
        </div>
        <div className="video-status-card">
          <div className="metric-symbol teal"><Gauge size={18} /></div>
          <div><span>Latest anomaly score</span><strong>{display(event?.anomaly_score)}</strong></div>
          <span className="status-text">{display(event?.timestamp ? formatTime(event.timestamp, true) : null)}</span>
        </div>
        <div className="video-status-card">
          <div className="metric-symbol blue"><Camera size={18} /></div>
          <div><span>Camera source</span><strong>{display(event?.camera_id)}</strong></div>
          <span className="status-text">{event ? `Confidence ${display(event.confidence)}` : 'No source reported'}</span>
        </div>
      </div>

      <div className="video-input-grid">
        <Panel title="Video file preview" subtitle="Select a clip to preview in this browser">
          <label className="upload-zone">
            <input
              type="file"
              accept="video/mp4,video/quicktime,video/webm"
              onChange={(inputEvent) => onFile(inputEvent.target.files?.[0] || null)}
            />
            <div className="upload-icon"><FileVideo2 size={22} /></div>
            <strong>{file ? file.name : 'Choose a video file'}</strong>
            <span>{file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB · Preview only` : 'MP4, MOV, or WebM'}</span>
            <span className="upload-button">Browse files</span>
          </label>
          {fileUrl && (
            <div className="video-preview">
              <video src={fileUrl} controls playsInline />
            </div>
          )}
          <p className="preview-notice"><CircleHelpIcon /> This preview does not send the video to an analyzer.</p>
        </Panel>

        <Panel
          title="Live camera preview"
          subtitle="Browser camera access is required"
          action={<span className={`camera-state ${cameraActive ? 'on' : ''}`}><span />{cameraActive ? 'Camera on' : 'Camera off'}</span>}
        >
          <div className={`camera-stage ${cameraActive ? 'active' : ''}`}>
            {cameraActive
              ? <video ref={videoRef} autoPlay muted playsInline />
              : <div className="camera-empty"><div><Camera size={29} /></div><strong>Camera preview is off</strong><span>Start the camera and allow browser access.</span></div>}
            <span className="camera-overlay-tag"><span /> LOCAL PREVIEW</span>
          </div>
          {cameraError && <div className="inline-error"><AlertTriangle size={15} />{cameraError}</div>}
          <button className={`button ${cameraActive ? 'button-danger' : 'button-primary'}`} type="button" onClick={cameraActive ? onStopCamera : onStartCamera}>
            {cameraActive ? <><X size={15} /> Stop camera</> : <><Camera size={15} /> Start camera</>}
          </button>
          <p className="preview-notice"><CircleHelpIcon /> Camera frames are not sent to the video detection service.</p>
        </Panel>
      </div>

      <Panel title="Inference score history" subtitle="Scores reported by the video integration; no synthetic points are shown">
        {history.length ? (
          <div className="chart chart-large">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history} margin={{ top: 15, right: 18, left: -10, bottom: 4 }}>
                <CartesianGrid stroke="#202c3d" vertical={false} />
                <XAxis dataKey="time" tick={{ fill: '#8190a4', fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={30} />
                <YAxis domain={[0, 1]} tick={{ fill: '#8190a4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <ReferenceLine y={0.6} stroke="#f2c66d" strokeDasharray="5 5" label={{ value: 'Alert threshold', fill: '#f2c66d', fontSize: 11 }} />
                <Line type="monotone" dataKey="anomaly_score" name="Anomaly score" stroke="#48d8c8" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState icon={Activity} title="No inference history yet" message="This chart will populate when video scores are posted to the integration API." />
        )}
        {event && (
          <div className="video-event-footer">
            <span>Latest event: <strong>{statusText.replaceAll('_', ' ')}</strong></span>
            <span>Severity: <SeverityBadge severity={eventSeverity} /></span>
            <span>Class: <strong>{event.event_type || event.class_name || '—'}</strong></span>
          </div>
        )}
      </Panel>
    </>
  )
}

function CircleHelpIcon() {
  return <CircleHelp size={14} />
}

function NetworkMonitoring({
  event,
  history,
  weights,
}: {
  event: IntegrationState['network_event']
  history: (IntegrationState['network_history'][number] & { time: string })[]
  weights: RoutingWeights
}) {
  const path = event?.active_path?.split(/\s*(?:->|→)\s*/).filter(Boolean) || []
  const networkSeverity = severityName(event?.severity)
  const statusIsAttack = Boolean(event?.attack_status && /attack|ddos|flood/i.test(event.attack_status))

  return (
    <>
      {statusIsAttack && (
        <div className="incident-banner">
          <div className="incident-banner-icon"><AlertTriangle size={20} /></div>
          <div><strong>{event?.attack_status?.replaceAll('_', ' ')}</strong><span>Reported by network telemetry · {display(event?.source, '')}</span></div>
          <SeverityBadge severity={event?.severity || 'CRITICAL'} />
        </div>
      )}
      <div className="network-kpis">
        <TelemetryCard icon={Activity} label="Traffic rate" value={display(event?.traffic_rate, ' pps')} detail={event?.attack_status || 'Waiting for telemetry'} />
        <TelemetryCard icon={Clock3} label="Latency" value={display(event?.latency, ' ms')} detail={`Last update ${display(event?.timestamp ? formatTime(event.timestamp) : null)}`} />
        <TelemetryCard icon={ArrowDownRight} label="Packet loss" value={display(event?.packet_loss_pct, '%')} detail="Reported by network source" />
        <TelemetryCard icon={GitBranch} label="Routing state" value={display(event?.routing_status)} detail={event?.severity ? `Severity ${networkSeverity}` : 'Reported by network source'} compact />
      </div>

      <div className="network-grid">
        <Panel title="Forwarding path" subtitle="Route reported by the connected network system" className="path-panel">
          {path.length ? (
            <div className="route-flow">
              {path.map((node, index) => (
                <div className="route-segment" key={`${node}-${index}`}>
                  <div className={`route-node ${node.toUpperCase().startsWith('SW') ? 'switch' : ''}`}>
                    {node.toUpperCase().startsWith('SW') ? <Network size={16} /> : <CircleDot size={16} />}
                    <span>{node}</span>
                  </div>
                  {index < path.length - 1 && <div className="route-connector"><ChevronRight size={17} /></div>}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon={GitBranch} title="No route reported" message="The active forwarding path will appear when network telemetry arrives." />
          )}
          <div className="route-meta">
            <span><span className={`route-health ${statusIsAttack ? 'warn' : ''}`} />{event?.routing_status || 'Awaiting route state'}</span>
            <span>Updated {display(event?.timestamp ? formatTime(event.timestamp, true) : null)}</span>
          </div>
        </Panel>
        <Panel title="Dijkstra cost model" subtitle="Operator-selected parameters">
          <div className="formula-card">Cost(e) = w₁D + w₂L + w₃C + w₄R</div>
          <div className="weight-legend">
            {([
              ['Distance', weights.distance, '#55a6ff'],
              ['Latency', weights.latency, '#48d8c8'],
              ['Congestion', weights.congestion, '#f2c66d'],
              ['Security risk', weights.security_risk, '#ff817d'],
            ] as const).map(([label, value, color]) => (
              <div className="weight-legend-row" key={label}>
                <span><i style={{ backgroundColor: color }} />{label}</span>
                <strong>{value.toFixed(2)}</strong>
                <div className="weight-bar"><span style={{ width: `${value * 100}%`, backgroundColor: color }} /></div>
              </div>
            ))}
          </div>
          <p className="quiet-note">Settings are stored by the API. The routing system must consume them to change a route.</p>
        </Panel>
      </div>

      <div className="network-grid charts-row">
        <Panel title="Traffic history" subtitle="Actual reported packets per second">
          {history.some((point) => point.traffic_rate !== null && point.traffic_rate !== undefined)
            ? <TelemetryLine data={history} dataKey="traffic_rate" color="#55a6ff" unit="pps" />
            : <EmptyState compact icon={Activity} title="No traffic history" message="History appears when telemetry is received." />}
        </Panel>
        <Panel title="Latency history" subtitle="Actual reported network latency">
          {history.some((point) => point.latency !== null && point.latency !== undefined)
            ? <TelemetryLine data={history} dataKey="latency" color="#48d8c8" unit="ms" />
            : <EmptyState compact icon={Clock3} title="No latency history" message="History appears when telemetry is received." />}
        </Panel>
      </div>
    </>
  )
}

function TelemetryLine({
  data,
  dataKey,
  color,
  unit,
}: {
  data: (NetworkHistoryPoint & { time: string })[]
  dataKey: string
  color: string
  unit: string
}) {
  return (
    <div className="chart chart-medium">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 14, left: -17, bottom: 0 }}>
          <CartesianGrid stroke="#202c3d" vertical={false} />
          <XAxis dataKey="time" tick={{ fill: '#8190a4', fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={25} />
          <YAxis tick={{ fill: '#8190a4', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${value} ${unit}`, dataKey.replace('_', ' ')]} />
          <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function Copilot({
  apiBaseUrl,
  apiConnected,
  alerts,
  ragStatus,
  ragError,
  ragLoading,
  recommendation,
  chatTurns,
  query,
  queryLoading,
  onQueryChange,
  onSubmitQuery,
  onGetRecommendation,
}: {
  apiBaseUrl: string
  apiConnected: boolean
  alerts: AlertEvent[]
  ragStatus: RagStatus | null
  ragError: string
  ragLoading: boolean
  recommendation: RagResponse | null
  chatTurns: ChatTurn[]
  query: string
  queryLoading: boolean
  onQueryChange: (value: string) => void
  onSubmitQuery: (event: FormEvent<HTMLFormElement>) => void
  onGetRecommendation: () => void
}) {
  const latestAlert = alerts[0]
  const messageEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatTurns, queryLoading])

  return (
    <>
      <div className="rag-summary">
        <div className="rag-summary-icon"><BookOpen size={20} /></div>
        <div><strong>Security knowledge base</strong><span>{ragStatus
          ? `${ragStatus.retrieval_backend} · ${ragStatus.knowledge_chunks} indexed knowledge chunks`
          : ragLoading ? 'Loading knowledge base…' : apiConnected ? 'Checking knowledge base…' : 'Knowledge base status loads when connected.'}</span></div>
        <span className="rag-availability">{ragStatus ? 'READY' : ragError ? 'UNAVAILABLE' : 'RAG'}</span>
      </div>
      {ragError && <div className="inline-error"><AlertTriangle size={15} />{ragError}</div>}

      <div className="copilot-grid">
        <div className="copilot-left">
          <Panel title="Incident response guidance" subtitle="Recommendations are based on the latest received alert">
            {latestAlert ? (
              <>
                <div className="incident-context">
                  <div className="incident-context-top"><SeverityBadge severity={latestAlert.severity} /><span>{formatTime(alertTimestamp(latestAlert), true)}</span></div>
                  <strong>{latestAlert.type || 'Security alert'}</strong>
                  <span>Source: {latestAlert.source || 'Not provided'}</span>
                </div>
                <button className="button button-primary" disabled={ragLoading || !apiConnected} onClick={onGetRecommendation} type="button">
                  {ragLoading ? <><LoaderCircle className="spin" size={16} /> Retrieving guidance…</> : <><Sparkles size={16} /> Get response guidance</>}
                </button>
                {recommendation && (
                  <div className="recommendation-content">
                    <h3>Immediate actions</h3>
                    {recommendation.immediate_actions?.map((action, index) => (
                      <div className="action-row" key={`${action}-${index}`}><span>{index + 1}</span><p>{action}</p></div>
                    ))}
                    {recommendation.sdn_routing_guidance && (
                      <div className="routing-guidance"><GitBranch size={16} /><div><strong>Routing guidance</strong><p>{recommendation.sdn_routing_guidance}</p></div></div>
                    )}
                    <h3>Retrieved sources</h3>
                    <div className="source-chips">
                      {recommendation.retrieved_sources?.map((source) => <span key={source}><BookOpen size={13} />{source}</span>)}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <EmptyState icon={Shield} title="No incident to triage" message="Once an alert arrives, this panel can retrieve relevant actions from the security procedures." />
            )}
          </Panel>
          <div className="rag-disclaimer"><CircleHelp size={15} /> Guidance is retrieved from the configured security procedures. Review actions before applying them.</div>
        </div>

        <Panel title="Security copilot" subtitle="Ask a question about the procedures or the latest alert" className="chat-panel">
          <div className="chat-messages">
            {!chatTurns.length && (
              <div className="chat-welcome">
                <div className="copilot-orb"><Sparkles size={20} /></div>
                <strong>How can I help with security guidance?</strong>
                <span>Questions are answered using your indexed security procedures.</span>
                <div className="suggestion-list">
                  {[
                    'What should I do for a DDoS alert?',
                    'How can camera tampering be handled?',
                    'How do I preserve recording during rerouting?',
                  ].map((suggestion) => (
                    <button key={suggestion} onClick={() => onQueryChange(suggestion)} type="button">{suggestion}<ArrowUpRight size={13} /></button>
                  ))}
                </div>
              </div>
            )}
            {chatTurns.map((turn, index) => (
              <div className={`chat-turn ${turn.role}`} key={`${turn.role}-${index}`}>
                <div className="chat-avatar">{turn.role === 'assistant' ? <Sparkles size={15} /> : 'OP'}</div>
                <div className="chat-bubble">
                  <span className="chat-role">{turn.role === 'assistant' ? 'Security copilot' : 'You'}</span>
                  <p>{turn.text}</p>
                  {turn.response?.retrieved_sources?.length ? (
                    <div className="chat-sources">Sources: {turn.response.retrieved_sources.join(', ')}</div>
                  ) : null}
                </div>
              </div>
            ))}
            {queryLoading && <div className="chat-loading"><LoaderCircle className="spin" size={16} /> Searching security procedures…</div>}
            <div ref={messageEndRef} />
          </div>
          <form className="chat-form" onSubmit={onSubmitQuery}>
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Ask about an alert or security procedure…"
              aria-label="Ask the security copilot"
            />
            <button type="submit" disabled={!query.trim() || queryLoading || !apiConnected} aria-label="Send question">
              <Send size={17} />
            </button>
          </form>
          <div className="chat-footnote"><Zap size={13} /> Retrieval grounded · No external AI service</div>
        </Panel>
      </div>
      {!apiConnected && <p className="quiet-note">RAG endpoints are unavailable at {apiBaseUrl || 'the same origin (Vite API proxy)'} until the integration service connects.</p>}
    </>
  )
}

