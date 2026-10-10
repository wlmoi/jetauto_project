export type Velocity = { vx: number, vy: number, wz: number }
export type Robot = {
  robot_id: string
  boot_id: string
  sequence: number
  captured_at: string
  mode: 'simulator' | 'serial'
  battery_v: number | null
  x_m: number
  y_m: number
  yaw_rad: number
  vx_mps: number
  vy_mps: number
  wz_radps: number
  imu_accel_mps2: number[]
  imu_gyro_radps: number[]
  motor_rps: number[]
  watchdog_stopped: boolean
  quality: string
  fault: string | null
}
export type BusEvent = { at: string, topic: string, payload: Record<string, unknown>, qos: number, retained: boolean, direction: string }
export type Snapshot = {
  robot: Robot | null
  mqtt: { connected: boolean, host: string, port: number, tls: boolean, received: number, invalid: number, dropped: number }
  gateway_online: boolean
  age_ms: number | null
  deployment: string
  database: string
  lease_active: boolean
  bus: BusEvent[]
}
export type Identity = { username: string, role: 'operator' | 'viewer' }
export type CommandRecord = { id: string, created_at: string, status: string, detail: string | null, payload: { velocity: Velocity } }
export type Audit = { id: number, at: string, actor: string, event: string, detail: string }
