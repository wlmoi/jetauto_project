import asyncio
import hmac
import json
import logging
import queue
import secrets
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import Settings, settings
from .contracts import Command, Login, Telemetry, Velocity, utcnow
from .database import Store
from .mqtt_link import make_client

log = logging.getLogger("backend")


class Runtime:
    def __init__(self, config):
        self.config = config
        self.store = Store(config.database_url)
        self.inbox = queue.Queue(maxsize=2000)
        self.bus = deque(maxlen=70)
        self.latest = None
        self.last_seen = 0.0
        self.connected = False
        self.gateway_online = False
        self.received = 0
        self.invalid = 0
        self.dropped = 0
        self.started = time.monotonic()
        self.sessions = {}
        self.attempts = {}
        self.lease = None
        self.last_command = 0.0
        self.last_sequence = None
        self.client = make_client("jetauto-backend", config)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self.connected = reason_code == 0
        if self.connected:
            base = f"jetauto/{self.config.robot_id}"
            for suffix in ("telemetry", "status", "acks", "events"):
                client.subscribe(f"{base}/{suffix}", qos=1)

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False
        self.gateway_online = False
        self.lease = None

    def on_message(self, client, userdata, message):
        if len(message.payload) > 16384:
            self.invalid += 1
            return
        try:
            self.inbox.put_nowait((message.topic, bytes(message.payload), message.qos, message.retain))
        except queue.Full:
            self.dropped += 1

    def event(self, topic, payload, qos=0, retained=False, direction="RX"):
        self.bus.appendleft({"at": utcnow().isoformat(), "topic": topic, "payload": payload, "qos": qos, "retained": retained, "direction": direction})

    def ingest(self, topic, raw, qos, retained):
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("MQTT payload must be object")
        suffix = topic.rsplit("/", 1)[-1]
        if suffix == "telemetry":
            sample = Telemetry.model_validate(payload)
            if sample.robot_id != self.config.robot_id or retained:
                raise ValueError("Invalid telemetry source")
            age = (utcnow() - sample.captured_at).total_seconds()
            if age < -2 or age > 5:
                raise ValueError("Stale telemetry timestamp")
            identity = (sample.boot_id, sample.sequence)
            if self.last_sequence and identity[0] == self.last_sequence[0] and identity[1] <= self.last_sequence[1]:
                return
            self.last_sequence = identity
            payload = sample.model_dump(mode="json")
            self.store.sample(payload)
            self.latest = payload
            self.last_seen = time.monotonic()
            self.received += 1
        elif suffix == "status":
            self.gateway_online = payload.get("online") is True
            if not self.gateway_online:
                self.lease = None
        elif suffix == "acks":
            allowed = {"simulated_applied", "sent_uart", "accepted_gateway", "rejected", "expired"}
            if payload.get("status") not in allowed or not isinstance(payload.get("id"), str):
                raise ValueError("Invalid acknowledgement")
            self.store.ack(payload["id"], payload["status"], str(payload.get("detail") or "")[:256])
        elif suffix == "events":
            self.store.audit("gateway", str(payload.get("event", "unknown"))[:64], json.dumps(payload))
        self.event(topic, payload, qos, retained)

    async def consume(self):
        last_prune = 0.0
        while True:
            for _ in range(50):
                try:
                    item = self.inbox.get_nowait()
                except queue.Empty:
                    break
                try:
                    self.ingest(*item)
                except Exception as exc:
                    self.invalid += 1
                    log.warning("MQTT processing failed: %s", type(exc).__name__)
            if time.monotonic() - last_prune > 3600:
                self.store.prune()
                last_prune = time.monotonic()
            await asyncio.sleep(0.02)

    def snapshot(self):
        age = time.monotonic() - self.last_seen if self.latest else None
        lease = self.lease if self.lease and self.lease[1] > time.monotonic() else None
        return {"robot": self.latest, "mqtt": {"connected": self.connected, "host": self.config.mqtt_host, "port": self.config.mqtt_port, "tls": self.config.mqtt_tls, "received": self.received, "invalid": self.invalid, "dropped": self.dropped}, "gateway_online": self.gateway_online and self.connected and age is not None and age < 2, "age_ms": round(age * 1000) if age is not None else None, "deployment": self.config.deployment, "database": "PostgreSQL" if self.config.database_url.startswith("postgresql") else "SQLite", "lease_active": lease is not None, "bus": list(self.bus)[:25]}


def create_app(config: Settings = settings, connect_mqtt=True):
    @asynccontextmanager
    async def lifespan(app):
        if len(config.session_secret) < 32 or len(config.operator_password) < 12 or len(config.viewer_password) < 12:
            raise RuntimeError("Provide SESSION_SECRET (32+ chars), OPERATOR_PASSWORD and VIEWER_PASSWORD (12+ chars). Run scripts/start-local.ps1 to generate local configuration.")
        state = Runtime(config)
        app.state.runtime = state
        if connect_mqtt:
            state.client.connect_async(config.mqtt_host, config.mqtt_port, keepalive=5)
            state.client.loop_start()
        consumer = asyncio.create_task(state.consume())
        try:
            yield
        finally:
            consumer.cancel()
            try:
                await consumer
            except asyncio.CancelledError:
                pass
            if connect_mqtt:
                state.client.disconnect()
                state.client.loop_stop()
            state.store.close()

    app = FastAPI(title="JetAuto Cloud Control", version="1.0.0", lifespan=lifespan)
    app.add_middleware(SessionMiddleware, secret_key=config.session_secret or "unconfigured", session_cookie="jetauto_session", same_site="strict", https_only=config.secure_cookie, max_age=28800)

    def rt():
        return app.state.runtime

    def same_origin(connection):
        origin = connection.headers.get("origin")
        if origin and urlparse(origin).netloc != connection.headers.get("host"):
            raise HTTPException(403, "Origin tidak diizinkan")

    def user(connection, operator=False):
        sid = connection.session.get("sid")
        session = rt().sessions.get(sid)
        if not session or session[1] < time.monotonic():
            raise HTTPException(401, "Silakan login")
        if operator and session[0] != "operator":
            raise HTTPException(403, "Akses kendali hanya untuk operator")
        return {"username": session[0], "role": session[0], "sid": sid}

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health():
        return {"service": "jetauto-backend", "status": "ok", "mqtt_connected": rt().connected}

    @app.post("/api/login")
    def login(body: Login, request: Request):
        same_origin(request)
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        attempts = rt().attempts.get(key, [])
        attempts = [t for t in attempts if now - t < 60]
        if len(attempts) >= 10:
            raise HTTPException(429, "Terlalu banyak percobaan login")
        attempts.append(now)
        rt().attempts[key] = attempts
        expected = config.operator_password if body.username == "operator" else config.viewer_password
        if not hmac.compare_digest(body.password.encode(), expected.encode()):
            raise HTTPException(401, "Username atau password salah")
        previous = request.session.get("sid")
        rt().sessions.pop(previous, None)
        sid = secrets.token_urlsafe(32)
        rt().sessions[sid] = (body.username, now + 28800)
        request.session.clear()
        request.session["sid"] = sid
        rt().store.audit(body.username, "login")
        return {"username": body.username, "role": body.username}

    @app.get("/api/me")
    def me(request: Request):
        identity = user(request)
        return {"username": identity["username"], "role": identity["role"]}

    @app.post("/api/logout")
    def logout(request: Request):
        same_origin(request)
        identity = user(request)
        if rt().lease and rt().lease[0] == identity["sid"]:
            rt().lease = None
        rt().sessions.pop(identity["sid"], None)
        request.session.clear()
        return {"ok": True}

    @app.get("/api/status")
    def status(request: Request):
        user(request)
        return rt().snapshot()

    @app.get("/api/history")
    def history(request: Request, limit: int = Query(default=120, ge=1, le=600)):
        user(request)
        return rt().store.history(config.robot_id, limit)

    @app.get("/api/commands")
    def commands(request: Request):
        user(request)
        return rt().store.commands()

    @app.get("/api/audit")
    def audits(request: Request):
        user(request)
        return rt().store.audits()

    @app.post("/api/control/acquire")
    def acquire(request: Request):
        same_origin(request)
        identity = user(request, operator=True)
        if not rt().snapshot()["gateway_online"]:
            raise HTTPException(503, "Gateway belum online")
        now = time.monotonic()
        if rt().lease and rt().lease[1] > now and rt().lease[0] != identity["sid"]:
            raise HTTPException(409, "Robot sedang dikendalikan sesi lain")
        rt().lease = (identity["sid"], now + 15)
        rt().store.audit(identity["username"], "control_acquired")
        return {"lease_seconds": 15}

    def publish_velocity(velocity, request):
        same_origin(request)
        identity = user(request, operator=True)
        now = time.monotonic()
        if not rt().lease or rt().lease[0] != identity["sid"] or rt().lease[1] < now:
            raise HTTPException(409, "Ambil kendali terlebih dahulu")
        if not rt().snapshot()["gateway_online"]:
            raise HTTPException(503, "Gateway offline atau telemetri kedaluwarsa")
        moving = velocity.vx != 0 or velocity.vy != 0 or velocity.wz != 0
        if moving and now - rt().last_command < 0.07:
            raise HTTPException(429, "Laju perintah terlalu tinggi")
        rt().lease = (identity["sid"], now + 15)
        rt().last_command = now
        issued = utcnow()
        command = Command(id=secrets.token_hex(16), robot_id=config.robot_id, operator_id=identity["username"], issued_at=issued, expires_at=issued + timedelta(milliseconds=500), velocity=velocity)
        payload = command.model_dump(mode="json")
        rt().store.command(payload)
        topic = f"jetauto/{config.robot_id}/commands"
        info = rt().client.publish(topic, json.dumps(payload), qos=1, retain=False)
        if info.rc != 0:
            rt().store.ack(command.id, "publish_failed", "MQTT disconnected")
            raise HTTPException(503, "Pengiriman MQTT gagal")
        rt().event(topic, payload, qos=1, direction="TX")
        return {"id": command.id, "status": "accepted_backend", "expires_at": payload["expires_at"]}

    @app.post("/api/control/velocity")
    def velocity(body: Velocity, request: Request):
        return publish_velocity(body, request)

    @app.post("/api/control/release")
    def release(request: Request):
        same_origin(request)
        identity = user(request, operator=True)
        if rt().lease and rt().lease[0] == identity["sid"]:
            if rt().snapshot()["gateway_online"]:
                publish_velocity(Velocity(vx=0, vy=0, wz=0), request)
            rt().lease = None
            rt().store.audit(identity["username"], "control_released")
        return {"ok": True}

    @app.websocket("/api/live")
    async def live(websocket: WebSocket):
        try:
            same_origin(websocket)
            user(websocket)
        except HTTPException:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        try:
            while True:
                user(websocket)
                await websocket.send_json(rt().snapshot())
                await asyncio.sleep(0.1)
        except (WebSocketDisconnect, HTTPException, RuntimeError):
            try:
                await websocket.close()
            except RuntimeError:
                pass

    dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(dist / "index.html")
    else:
        @app.get("/")
        def index():
            return {"message": "Build frontend with npm run build in frontend", "docs": "/docs"}

    return app


app = create_app()
