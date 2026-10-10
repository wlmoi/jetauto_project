import math
import time
from collections import OrderedDict

from platform_app.contracts import Command, Velocity, utcnow


ZERO = Velocity(vx=0, vy=0, wz=0)


def motor_rps(velocity, diameter=0.097, wheelbase=0.216, track_width=0.195):
    vp = velocity.wz * (wheelbase + track_width) / 2
    vx, vy = velocity.vx, velocity.vy
    return [v / (math.pi * diameter) for v in (vx - vy - vp, vx + vy - vp, -vx - vy - vp, -vx + vy - vp)]


class SafetyController:
    def __init__(self, robot_id, clock=time.monotonic):
        self.robot_id = robot_id
        self.clock = clock
        self.velocity = ZERO
        self.deadline = 0.0
        self.stopped = True
        self.seen = OrderedDict()
        self.last_issued = None

    def accept(self, command: Command, retained=False, now=None):
        now = now or utcnow()
        if retained:
            return "rejected", "retained_command"
        if command.robot_id != self.robot_id:
            return "rejected", "robot_mismatch"
        if command.id in self.seen:
            return "rejected", "duplicate_command"
        ttl = (command.expires_at - now).total_seconds()
        lifespan = (command.expires_at - command.issued_at).total_seconds()
        if ttl <= 0:
            return "expired", "command_expired"
        if not 0 < lifespan <= 0.5 or command.issued_at > now or ttl > 0.5:
            return "rejected", "invalid_command_window"
        if self.last_issued is not None and command.issued_at <= self.last_issued:
            return "rejected", "out_of_order"
        self.last_issued = command.issued_at
        self.seen[command.id] = True
        if len(self.seen) > 4096:
            self.seen.popitem(last=False)
        self.velocity = command.velocity
        self.deadline = self.clock() + min(ttl, 0.5)
        self.stopped = False
        return "accepted_gateway", None

    def tick(self, connected=True):
        if not connected or self.clock() >= self.deadline:
            self.velocity = ZERO
            self.stopped = True
        return self.velocity

    def stop(self):
        self.velocity = ZERO
        self.stopped = True
        self.deadline = 0
