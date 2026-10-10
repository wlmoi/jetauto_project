import json
import logging
import math
import os
import queue
import signal
import time
import uuid

from platform_app.config import settings
from platform_app.contracts import Command, utcnow
from platform_app.mqtt_link import make_client
from .control import SafetyController, motor_rps

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gateway")


class Gateway:
    def __init__(self, config=settings):
        self.config = config
        self.base = f"jetauto/{config.robot_id}"
        self.control = SafetyController(config.robot_id)
        self.inbox = queue.Queue(maxsize=20)
        self.client = make_client(f"gateway-{config.robot_id}", config)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.will_set(f"{self.base}/status", json.dumps({"online": False, "mode": config.gateway_mode}), qos=1, retain=True)
        self.connected = False
        self.running = True
        self.link_fault = None
        self.board = None
        self.boot_id = str(uuid.uuid4())
        self.sequence = 0
        self.x = self.y = self.yaw = 0.0
        self.last = time.monotonic()
        self.last_telemetry = 0.0
        self.was_stopped = True
        self.battery = 12.4
        self.imu = [0, 0, 9.80665, 0, 0, 0]

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self.connected = reason_code == 0
        self.control.stop()
        if self.connected:
            client.subscribe(f"{self.base}/commands", qos=1)
            client.publish(f"{self.base}/status", json.dumps({"online": True, "mode": self.config.gateway_mode, "boot_id": self.boot_id}), qos=1, retain=True)
            log.info("MQTT connected to %s:%s", self.config.mqtt_host, self.config.mqtt_port)

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False
        # Main loop applies zero within the next 20 ms.
        log.warning("MQTT disconnected, stopping locally")

    def on_message(self, client, userdata, message):
        if len(message.payload) > 4096:
            return
        try:
            self.inbox.put_nowait((message.payload, message.retain))
        except queue.Full:
            log.warning("Command queue full, command discarded")

    def ack(self, command_id, status, detail=None):
        self.client.publish(f"{self.base}/acks", json.dumps({"id": command_id, "status": status, "detail": detail, "at": utcnow().isoformat()}), qos=1)

    def process_commands(self):
        while not self.inbox.empty():
            payload, retained = self.inbox.get_nowait()
            try:
                command = Command.model_validate_json(payload)
                status, detail = self.control.accept(command, retained=retained)
                if self.link_fault:
                    self.control.stop()
                    status, detail = "rejected", "serial_fault"
                if status == "accepted_gateway":
                    self.apply(self.control.velocity)
                    status = "simulated_applied" if self.board is None else "sent_uart"
                self.ack(command.id, status, detail)
            except Exception as exc:
                self.control.stop()
                log.warning("Rejected command: %s", type(exc).__name__)

    def apply(self, velocity):
        if self.board:
            try:
                self.board.set_motor_speed([[i + 1, speed] for i, speed in enumerate(motor_rps(velocity))])
            except Exception as exc:
                self.link_fault = f"serial_{type(exc).__name__}"
                self.control.stop()
                log.exception("Serial write failed")
                raise

    def read_sensors(self):
        if not self.board:
            self.battery = max(11.4, self.battery - 0.000002)
            self.imu = [0.02 * math.sin(self.sequence / 8), 0.01 * math.cos(self.sequence / 7), 9.80665, 0, 0, self.control.velocity.wz]
            return "simulated"
        imu = self.board.get_imu()
        battery = self.board.get_battery()
        if imu:
            # Supplied ROS node converts acceleration in g and gyro degrees/s.
            self.imu = [v * 9.80665 for v in imu[:3]] + [math.radians(v) for v in imu[3:]]
        self.battery = battery / 1000 if battery is not None else None
        return "measured" if imu and battery is not None else "partial"

    def telemetry(self):
        quality = self.read_sensors()
        v = self.control.velocity
        payload = dict(robot_id=self.config.robot_id, boot_id=self.boot_id, sequence=self.sequence, captured_at=utcnow().isoformat(), mode=self.config.gateway_mode, battery_v=self.battery, x_m=self.x, y_m=self.y, yaw_rad=self.yaw, vx_mps=v.vx, vy_mps=v.vy, wz_radps=v.wz, imu_accel_mps2=self.imu[:3], imu_gyro_radps=self.imu[3:], motor_rps=motor_rps(v), watchdog_stopped=self.control.stopped, fault=self.link_fault, quality=quality)
        self.client.publish(f"{self.base}/telemetry", json.dumps(payload), qos=0, retain=False)
        self.sequence += 1

    def run(self):
        if self.config.gateway_mode == "serial":
            if os.getenv("ALLOW_HARDWARE") != "true":
                raise RuntimeError("Set ALLOW_HARDWARE=true after preparing physical stop and safe test area")
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jetauto_driver/jetauto_driver/ros_robot_controller/src"))
            from ros_robot_controller.ros_robot_controller_sdk import Board
            self.board = Board(device=os.getenv("SERIAL_DEVICE", "/dev/rrc"))
            self.board.enable_reception()
            self.apply(self.control.velocity)
        self.client.connect_async(self.config.mqtt_host, self.config.mqtt_port, keepalive=5)
        self.client.loop_start()
        try:
            while self.running:
                self.process_commands()
                v = self.control.tick(connected=self.connected and not self.link_fault)
                if self.control.stopped and not self.was_stopped:
                    try:
                        self.apply(v)
                    except Exception:
                        pass
                    self.client.publish(f"{self.base}/events", json.dumps({"event": "watchdog_stop", "at": utcnow().isoformat()}), qos=1)
                self.was_stopped = self.control.stopped
                now = time.monotonic()
                dt, self.last = min(now - self.last, 0.1), now
                self.x += (v.vx * math.cos(self.yaw) - v.vy * math.sin(self.yaw)) * dt
                self.y += (v.vx * math.sin(self.yaw) + v.vy * math.cos(self.yaw)) * dt
                self.yaw += v.wz * dt
                if self.connected and now - self.last_telemetry >= 0.1:
                    self.telemetry()
                    self.last_telemetry = now
                time.sleep(0.02)
        finally:
            self.control.stop()
            try:
                self.apply(self.control.velocity)
            finally:
                self.client.publish(f"{self.base}/status", json.dumps({"online": False, "mode": self.config.gateway_mode}), qos=1, retain=True).wait_for_publish(timeout=1)
                self.client.disconnect()
                self.client.loop_stop()


if __name__ == "__main__":
    gateway = Gateway()
    signal.signal(signal.SIGINT, lambda *_: setattr(gateway, "running", False))
    signal.signal(signal.SIGTERM, lambda *_: setattr(gateway, "running", False))
    gateway.run()
