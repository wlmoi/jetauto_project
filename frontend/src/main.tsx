import React, { useCallback, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Activity, ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Battery, Check, ChevronRight, Cloud, Cpu, Database, Gauge, LayoutDashboard, LogOut, Radio, RotateCcw, RotateCw, ShieldCheck, Square, Terminal, Wifi, X } from 'lucide-react'
import { api } from './api'
import type { Audit, BusEvent, CommandRecord, Identity, Robot, Snapshot, Velocity } from './types'
import './style.css'

const ZERO: Velocity = { vx: 0, vy: 0, wz: 0 }
const fmt = (value: number | null | undefined, digits = 2) => value == null ? '—' : value.toFixed(digits)
const time = (value: string) => new Date(value).toLocaleTimeString('id-ID', { hour12: false })

function Login({ onLogin }: { onLogin: (identity: Identity) => void }) {
  const [username, setUsername] = useState('operator')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  return <div className="login-page">
    <div className="login-brand"><div className="brand-icon"><Cpu size={25} /></div> JETAUTO <span>MISSION CONTROL</span></div>
    <div className="login-card">
      <span className="eyebrow">ROBOTICS / SOFTWARE / CLOUD</span>
      <h1>Satu ruang kendali.<br /><em>Seluruh alur terlihat.</em></h1>
      <p>Pantau robot, telusuri pesan MQTT, dan kendalikan gerak dengan pengamanan lokal.</p>
      <form onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try { onLogin(await api<Identity>('/login', { username, password })) } catch (err) { setError((err as Error).message) } finally { setBusy(false) } }}>
        <label>Peran pengguna<select value={username} onChange={e => setUsername(e.target.value)}><option value="operator">Operator</option><option value="viewer">Viewer</option></select></label>
        <label>Password<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required /></label>
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? 'Menghubungkan...' : 'Masuk ke dashboard'}<ArrowRight size={17} /></button>
      </form>
      <div className="login-note"><ShieldCheck size={16} /> Kredensial lokal tersimpan di runtime/credentials.txt</div>
    </div>
    <div className="login-foot">JETAUTO RESEARCH PLATFORM <span>01 / ENGINEERING DEMO</span></div>
  </div>
}

function Sparkline({ values, color = '#75dcb7' }: { values: number[], color?: string }) {
  if (values.length < 2) return <div className="spark-empty" />
  const min = Math.min(...values), max = Math.max(...values)
  const span = Math.max(max - min, .05)
  const path = values.map((v, i) => `${i === 0 ? 'M' : 'L'} ${(i / (values.length - 1)) * 260} ${45 - ((v - min) / span) * 32}`).join(' ')
  return <svg className="spark" viewBox="0 0 260 55" preserveAspectRatio="none"><path d={`${path} L 260 55 L 0 55 Z`} fill={color} opacity=".07" /><path d={path} stroke={color} strokeWidth="1.6" fill="none" /></svg>
}

function Metric({ label, value, unit, children, icon }: { label: string, value: string, unit?: string, children: React.ReactNode, icon: React.ReactNode }) {
  return <div className="metric card"><div className="metric-label">{label}{icon}</div><div className="metric-value">{value}<span>{unit}</span></div>{children}</div>
}

function MapPanel({ robot, trail }: { robot: Robot | null, trail: Robot[] }) {
  const scale = 48, centerX = 260, centerY = 150
  const coords = (r: Robot) => `${centerX + r.y_m * scale},${centerY - r.x_m * scale}`
  return <div className="card map-panel"><div className="panel-heading"><div><span className="eyebrow">LOCAL FRAME</span><h2>Posisi robot</h2></div><span className="chip">ODOMETRY ESTIMATE</span></div>
    <svg className="map-svg" viewBox="0 0 520 300" role="img" aria-label="Estimasi posisi robot dan lintasan">
      <defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M 24 0 L 0 0 0 24" fill="none" stroke="#233039" strokeWidth=".65" /></pattern><radialGradient id="glow"><stop stopColor="#75dcb7" stopOpacity=".1" /><stop offset="1" stopColor="#75dcb7" stopOpacity="0" /></radialGradient></defs>
      <rect width="520" height="300" fill="url(#grid)" /><ellipse cx={centerX} cy={centerY} rx="155" ry="130" fill="url(#glow)" />
      <line x1="260" y1="20" x2="260" y2="280" stroke="#35454e" strokeDasharray="4 5" /><line x1="20" y1="150" x2="500" y2="150" stroke="#35454e" strokeDasharray="4 5" />
      <text x="267" y="30" fill="#647782" fontSize="10">+X</text><text x="483" y="143" fill="#647782" fontSize="10">+Y</text>
      {trail.length > 1 && <polyline points={trail.map(coords).join(' ')} fill="none" stroke="#75dcb7" strokeWidth="2" opacity=".55" />}
      <g transform={`translate(${robot ? centerX + robot.y_m * scale : centerX},${robot ? centerY - robot.x_m * scale : centerY}) rotate(${(robot?.yaw_rad ?? 0) * 180 / Math.PI})`}>
        <circle r="33" fill="#75dcb7" opacity=".06" /><rect x="-14" y="-20" width="28" height="40" rx="7" fill="#172f2d" stroke="#75dcb7" strokeWidth="1.5" />
        <rect x="-19" y="-14" width="5" height="9" rx="2" fill="#75dcb7" /><rect x="14" y="-14" width="5" height="9" rx="2" fill="#75dcb7" /><rect x="-19" y="5" width="5" height="9" rx="2" fill="#75dcb7" /><rect x="14" y="5" width="5" height="9" rx="2" fill="#75dcb7" /><path d="M -5 -4 L 0 -10 L 5 -4" stroke="#75dcb7" strokeWidth="2" fill="none" />
      </g>
      <text x="20" y="280" fill="#647782" fontSize="10">1 GRID = 0.5 m</text>
    </svg>
    <div className="coordinates"><span>X <b>{fmt(robot?.x_m, 3)} m</b></span><span>Y <b>{fmt(robot?.y_m, 3)} m</b></span><span>YAW <b>{fmt(robot ? robot.yaw_rad * 180 / Math.PI : null, 1)}°</b></span></div>
    <p className="caption">Posisi diintegrasikan dari kecepatan perintah. Belum dikoreksi dengan sensor posisi.</p>
  </div>
}

function Controls({ identity, online, onError }: { identity: Identity, online: boolean, onError: (error: string) => void }) {
  const [leased, setLeased] = useState(false)
  const [active, setActive] = useState('')
  const [speed, setSpeed] = useState(.12)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)
  const desired = useRef<Velocity>(ZERO)
  const pending = useRef<Promise<void>>(Promise.resolve())
  const busy = useRef(false)
  const leaseDeadline = useRef(0)

  const send = useCallback((v: Velocity) => {
    if (busy.current) return
    busy.current = true
    pending.current = api('/control/velocity', v).then(() => { leaseDeadline.current = Date.now() + 15000 }).catch(err => {
      if (timer.current) clearInterval(timer.current)
      timer.current = null
      desired.current = ZERO
      setLeased(false)
      setActive('')
      onError((err as Error).message)
    }).finally(() => { busy.current = false })
  }, [onError])

  const stop = useCallback(() => {
    if (timer.current) clearInterval(timer.current)
    timer.current = null
    desired.current = ZERO
    setActive('')
    if (leaseDeadline.current > Date.now()) {
      pending.current = pending.current.then(async () => { await api('/control/velocity', ZERO).catch(() => {}) })
    }
  }, [])

  const start = (name: string, v: Velocity) => {
    if (!leased || !online || leaseDeadline.current < Date.now()) return
    if (timer.current) clearInterval(timer.current)
    desired.current = v
    setActive(name)
    send(v)
    timer.current = setInterval(() => send(desired.current), 120)
  }

  useEffect(() => {
    const stopHidden = () => { if (document.hidden) stop() }
    window.addEventListener('pointerup', stop)
    window.addEventListener('pointercancel', stop)
    window.addEventListener('blur', stop)
    document.addEventListener('visibilitychange', stopHidden)
    const expiry = setInterval(() => { if (leaseDeadline.current && leaseDeadline.current < Date.now()) { stop(); setLeased(false) } }, 500)
    return () => { if (timer.current) clearInterval(timer.current); clearInterval(expiry); window.removeEventListener('pointerup', stop); window.removeEventListener('pointercancel', stop); window.removeEventListener('blur', stop); document.removeEventListener('visibilitychange', stopHidden) }
  }, [stop])

  useEffect(() => { if (!online) { stop(); setLeased(false) } }, [online, stop])
  const disabled = !leased || !online
  const hold = (name: string, icon: React.ReactNode, v: Velocity, cls = '') => <button aria-label={name} title={name} className={`direction ${cls} ${active === name ? 'pressed' : ''}`} disabled={disabled} onPointerDown={e => { e.preventDefault(); e.currentTarget.setPointerCapture(e.pointerId); start(name, v) }} onLostPointerCapture={stop} onKeyDown={e => { if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) { e.preventDefault(); start(name, v) } }} onKeyUp={stop} onBlur={stop}>{icon}</button>
  return <div className="card control-panel"><div className="panel-heading"><div><span className="eyebrow">OPERATOR CONSOLE</span><h2>Kendali gerak</h2></div><ShieldCheck size={20} className="mint" /></div>
    <div className="control-status"><span className={`dot ${leased ? 'online' : ''}`} />{leased ? 'Sesi kendali aktif' : identity.role === 'viewer' ? 'Mode pemantauan' : 'Kendali belum diambil'}<span>TTL 500 ms</span></div>
    <div className="dpad">
      {hold('Putar kiri', <RotateCcw size={19} />, { vx: 0, vy: 0, wz: .3 }, 'rotate')}
      {hold('Maju', <ArrowUp size={23} />, { vx: speed, vy: 0, wz: 0 })}
      {hold('Putar kanan', <RotateCw size={19} />, { vx: 0, vy: 0, wz: -.3 }, 'rotate')}
      {hold('Kiri', <ArrowLeft size={23} />, { vx: 0, vy: -speed, wz: 0 })}
      <button className="stop-control" title="Berhenti" aria-label="Berhenti" disabled={disabled} onClick={stop}><Square size={17} fill="currentColor" /></button>
      {hold('Kanan', <ArrowRight size={23} />, { vx: 0, vy: speed, wz: 0 })}
      <span />{hold('Mundur', <ArrowDown size={23} />, { vx: -speed, vy: 0, wz: 0 })}<span />
    </div>
    <div className="speed-setting"><label htmlFor="speed">Kecepatan linear <b>{speed.toFixed(2)} m/s</b></label><input id="speed" type="range" min=".04" max=".2" step=".01" value={speed} disabled={active !== ''} onChange={e => setSpeed(Number(e.target.value))} /></div>
    {identity.role === 'operator' && <button className={leased ? 'secondary wide' : 'primary wide'} disabled={!online} onClick={async () => { try { if (leased) { stop(); await pending.current; await api('/control/release', {}); setLeased(false); leaseDeadline.current = 0 } else { await api('/control/acquire', {}); leaseDeadline.current = Date.now() + 15000; setLeased(true) } } catch (err) { onError((err as Error).message) } }}>{leased ? 'Lepaskan kendali' : 'Ambil kendali'}<ChevronRight size={15} /></button>}
    <p className="caption">Tahan tombol untuk bergerak. Lepaskan untuk berhenti. Gateway menghentikan gerak saat perintah kedaluwarsa.</p>
  </div>
}

function BusPanel({ events }: { events: BusEvent[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')
  const rows = events.filter(e => filter === 'all' || e.topic.endsWith(filter))
  return <div className="card bus-panel"><div className="panel-heading"><div><span className="eyebrow">MESSAGE TRANSPORT</span><h2>MQTT live stream</h2></div><select aria-label="Filter topic" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">Semua topic</option><option value="telemetry">Telemetri</option><option value="commands">Perintah</option><option value="acks">Acknowledgement</option><option value="events">Event</option></select></div>
    <div className="bus-header"><span>WAKTU</span><span>ARAH</span><span>TOPIC / PAYLOAD</span><span>QoS</span></div>
    <div className="bus-rows">{rows.length === 0 && <div className="empty">Menunggu pesan MQTT pada filter ini</div>}{rows.slice(0, 12).map((e, i) => { const key = `${e.at}-${i}`; return <React.Fragment key={key}><button className="bus-row" onClick={() => setExpanded(expanded === key ? null : key)}><span>{time(e.at)}</span><span className={`message-dir ${e.direction === 'TX' ? 'tx' : ''}`}>{e.direction}</span><span className="topic">{e.topic}<small>{e.topic.endsWith('telemetry') ? `seq ${e.payload.sequence} / ${e.payload.mode}` : String(e.payload.status ?? e.payload.event ?? e.payload.id ?? 'status update')}{e.retained ? ' / retained' : ''}</small></span><span className="qos">{e.qos}</span></button>{expanded === key && <pre className="payload">{JSON.stringify(e.payload, null, 2)}</pre>}</React.Fragment> })}</div>
    <div className="panel-footer"><Radio size={13} />Pesan berasal dari broker MQTT<span>Klik baris untuk melihat payload</span></div>
  </div>
}

function App() {
  const [identity, setIdentity] = useState<Identity | null>(null)
  const [checking, setChecking] = useState(true)
  const [state, setState] = useState<Snapshot | null>(null)
  const [history, setHistory] = useState<Robot[]>([])
  const [trail, setTrail] = useState<Robot[]>([])
  const [commands, setCommands] = useState<CommandRecord[]>([])
  const [audit, setAudit] = useState<Audit[]>([])
  const [tab, setTab] = useState<'overview' | 'commands' | 'audit'>('overview')
  const [error, setError] = useState('')
  const [live, setLive] = useState(false)
  const errorHandler = useCallback((message: string) => setError(message), [])
  useEffect(() => { api<Identity>('/me').then(setIdentity).catch(() => {}).finally(() => setChecking(false)) }, [])
  useEffect(() => {
    if (!identity) return
    let ws: WebSocket | null = null, retry: ReturnType<typeof setTimeout> | null = null, disposed = false
    const connect = () => {
      if (disposed) return
      ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/live`)
      ws.onopen = () => setLive(true)
      ws.onmessage = e => { const snapshot = JSON.parse(e.data) as Snapshot; setState(snapshot); if (snapshot.robot) { const robot = snapshot.robot; setHistory(prev => prev.at(-1)?.sequence === robot.sequence && prev.at(-1)?.boot_id === robot.boot_id ? prev : [...prev.slice(-119), robot]); setTrail(prev => prev.at(-1)?.sequence === robot.sequence && prev.at(-1)?.boot_id === robot.boot_id ? prev : [...prev.slice(-299), robot]) } }
      ws.onclose = e => { setLive(false); if (!disposed) { if (e.code === 1008) setIdentity(null); else retry = setTimeout(connect, 1500) } }
    }
    connect()
    api<Robot[]>('/history').then(setHistory).catch(() => {})
    const poll = async () => { try { const [c, a] = await Promise.all([api<CommandRecord[]>('/commands'), api<Audit[]>('/audit')]); if (!disposed) { setCommands(c); setAudit(a) } } catch { /* WebSocket manages visible connectivity */ } }
    void poll()
    const interval = setInterval(poll, 1800)
    return () => { disposed = true; ws?.close(); if (retry) clearTimeout(retry); clearInterval(interval) }
  }, [identity])
  if (checking) return <div className="loading">Menghubungkan Mission Control...</div>
  if (!identity) return <Login onLogin={setIdentity} />
  const robot = state?.robot ?? null
  const online = Boolean(state?.gateway_online && live)
  const running = online && robot && !robot.watchdog_stopped && (robot.vx_mps !== 0 || robot.vy_mps !== 0 || robot.wz_radps !== 0)
  return <div className="shell">
    <aside className="sidebar"><a className="brand" href="/"><div className="brand-icon"><Cpu size={22} /></div><div>JETAUTO<small>MISSION CONTROL</small></div></a><span className="nav-label">WORKSPACE</span><button className={tab === 'overview' ? 'nav active' : 'nav'} onClick={() => setTab('overview')}><LayoutDashboard size={18} /> Overview</button><button className={tab === 'commands' ? 'nav active' : 'nav'} onClick={() => setTab('commands')}><Terminal size={18} /> Riwayat perintah <span>{commands.length}</span></button><button className={tab === 'audit' ? 'nav active' : 'nav'} onClick={() => setTab('audit')}><ShieldCheck size={18} /> Audit aktivitas</button>
      <div className="sidebar-bottom"><div className="stack-label">PLATFORM STACK</div><div><Radio size={14} /> MQTT 3.1.1</div><div><Database size={14} /> {state?.database ?? 'Database'}</div><div><Cloud size={14} /> {state?.deployment ?? 'Menghubungkan'}</div><div className="sidebar-version">RESEARCH BUILD <span>v1.0.0</span></div></div>
    </aside>
    <div className="workspace"><header><div className="breadcrumb">Workspace <ChevronRight size={13} /><b>JetAuto Research</b></div><div className="header-right"><span className={`connection ${live ? 'mint' : ''}`}><span className={`dot ${live ? 'online' : ''}`} />{live ? 'Live connection' : 'Reconnecting'}</span><div className="user"><span className="avatar">{identity.role === 'operator' ? 'OP' : 'VW'}</span><div>{identity.username}<small>{identity.role}</small></div></div><button className="icon-button" title="Logout" aria-label="Logout" onClick={async () => { await api('/logout', {}); setIdentity(null); setState(null); setTrail([]); setHistory([]) }}><LogOut size={17} /></button></div></header>
      <main><div className="page-title"><div><span className="eyebrow">ROBOT OPERATIONS / JETAUTO-01</span><h1>{tab === 'overview' ? 'Mission overview' : tab === 'commands' ? 'Riwayat perintah' : 'Audit aktivitas'}</h1><p>{tab === 'overview' ? 'Telemetri, koneksi, dan gerak robot dalam satu tampilan.' : 'Telusuri aktivitas platform berdasarkan bukti yang tersimpan.'}</p></div><div className="mode-badge"><span className="dot online" />{robot?.mode === 'serial' ? 'HARDWARE MODE' : 'SIMULATOR MODE'}<small>{state?.deployment ?? 'LOCAL'}</small></div></div>
      {error && <div className="error notice">{error}<button className="icon-button" aria-label="Tutup pesan" onClick={() => setError('')}><X size={16} /></button></div>}
      {tab === 'overview' ? <>
      <div className="metrics"><Metric label="ROBOT STATUS" value={online ? running ? 'Moving' : 'Standby' : 'Offline'} icon={<Cpu size={18} />}><div className="metric-note"><span className={`dot ${online ? 'online' : ''}`} />{online ? `Gateway aktif / ${robot?.quality}` : 'Menunggu telemetri'}</div><div className="metric-bottom"><ShieldCheck size={13} />{robot?.watchdog_stopped ? 'Watchdog menghentikan gerak' : 'Watchdog siap'}</div></Metric>
      <Metric label="BATTERY VOLTAGE" value={fmt(robot?.battery_v)} unit="V" icon={<Battery size={18} />}><Sparkline values={history.flatMap(r => r.battery_v == null ? [] : [r.battery_v])} /><div className="metric-bottom">{robot?.mode === 'serial' ? 'Pembacaan controller' : 'Data simulasi'}</div></Metric>
      <Metric label="LINEAR VELOCITY" value={fmt(robot ? Math.hypot(robot.vx_mps, robot.vy_mps) : null, 3)} unit="m/s" icon={<Gauge size={18} />}><Sparkline values={history.map(r => Math.hypot(r.vx_mps, r.vy_mps))} color="#9bbff7" /><div className="metric-bottom">Batas sumbu 0.20 m/s</div></Metric>
      <Metric label="TELEMETRY AGE" value={state?.age_ms == null ? '—' : String(state.age_ms)} unit="ms" icon={<Activity size={18} />}><div className="metric-note"><span className={`dot ${online ? 'online' : ''}`} />{online ? 'Data terkini' : 'Data belum tersedia atau kedaluwarsa'}</div><div className="metric-bottom">10 Hz / #{robot?.sequence ?? '—'}</div></Metric></div>
      <div className="architecture card"><div className="arch-node"><Cpu size={18} /><div>JetAuto<small>{robot?.mode === 'serial' ? 'UART controller' : 'Simulator gateway'}</small></div><span className={`dot ${online ? 'online' : ''}`} /></div><div className={`arch-line ${online ? 'flow' : ''}`} /><div className="arch-node"><Radio size={18} /><div>MQTT broker<small>{state?.mqtt.host}:{state?.mqtt.port}</small></div><span className={`dot ${state?.mqtt.connected ? 'online' : ''}`} /></div><div className={`arch-line ${online ? 'flow' : ''}`} /><div className="arch-node"><Cloud size={18} /><div>Backend<small>{state?.deployment ?? '—'}</small></div><span className={`dot ${live ? 'online' : ''}`} /></div><div className={`arch-line ${live ? 'flow' : ''}`} /><div className="arch-node"><Database size={18} /><div>{state?.database ?? 'Storage'}<small>{state?.mqtt.received ?? 0} sampel diterima</small></div></div>
      <div className="middle-grid"><MapPanel robot={robot} trail={trail} /><Controls identity={identity} online={online} onError={errorHandler} /><div className="card sensors-panel"><div className="panel-heading"><div><span className="eyebrow">INERTIAL MEASUREMENT</span><h2>Sensor & motor</h2></div><Activity size={19} className="muted" /></div><div className="sensor-title">ACCELEROMETER <span>m/s²</span></div>{['X', 'Y', 'Z'].map((axis, i) => <div className="sensor-row" key={axis}><span>{axis}</span><div className="sensor-bar"><i style={{ width: `${Math.min(100, Math.abs(robot?.imu_accel_mps2[i] ?? 0) * 9)}%` }} /></div><b>{fmt(robot?.imu_accel_mps2[i], 3)}</b></div>)}<div className="sensor-title">GYROSCOPE <span>rad/s</span></div><div className="gyro-values">{['X', 'Y', 'Z'].map((a, i) => <div key={a}><small>{a}</small><b>{fmt(robot?.imu_gyro_radps[i], 3)}</b></div>)}</div><div className="sensor-title">MOTOR SPEED <span>rps</span></div><div className="motor-grid">{[0, 1, 2, 3].map(i => <div key={i}><span>M{i + 1}</span><b>{fmt(robot?.motor_rps[i], 3)}</b></div>)}</div><div className="sensor-quality"><Check size={13} />{robot?.quality ?? 'Menunggu sensor'}<span>{robot?.fault ?? 'No fault reported'}</span></div></div></div>
      <BusPanel events={state?.bus ?? []} />
      </> : <div className="card records"><div className="panel-heading"><h2>{tab === 'commands' ? 'Status pengiriman dan respons gateway' : 'Aktivitas pengguna dan gateway'}</h2><span className="chip">DATABASE HISTORY</span></div>{tab === 'commands' ? <table><thead><tr><th>Waktu</th><th>Command ID</th><th>Velocity</th><th>Status</th></tr></thead><tbody>{commands.map(c => <tr key={c.id}><td>{time(c.created_at)}</td><td className="mono">{c.id.slice(0, 12)}</td><td className="mono">{c.payload.velocity.vx} / {c.payload.velocity.vy} / {c.payload.velocity.wz}</td><td><span className="status-label">{c.status}</span>{c.detail && <small>{c.detail}</small>}</td></tr>)}</tbody></table> : <table><thead><tr><th>Waktu</th><th>Actor</th><th>Event</th><th>Detail</th></tr></thead><tbody>{audit.map(a => <tr key={a.id}><td>{time(a.at)}</td><td>{a.actor}</td><td className="mono">{a.event}</td><td>{a.detail}</td></tr>)}</tbody></table>}{(tab === 'commands' ? commands : audit).length === 0 && <div className="empty">Belum ada riwayat. Aktivitas akan muncul setelah dilakukan.</div>}</div>}
      <footer><span><Wifi size={13} /> {state?.mqtt.connected ? 'MQTT connected' : 'MQTT disconnected'} / {state?.mqtt.tls ? 'TLS enabled' : 'Local transport'}</span><span>Invalid {state?.mqtt.invalid ?? 0} / Dropped {state?.mqtt.dropped ?? 0}</span><span>JETAUTO RESEARCH © 2026</span></footer></main>
    </div>
  </div>
}

createRoot(document.getElementById('root')!).render(<App />)
