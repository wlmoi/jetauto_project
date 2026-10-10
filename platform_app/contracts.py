from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utcnow():
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Velocity(StrictModel):
    vx: float = Field(ge=-0.2, le=0.2)
    vy: float = Field(ge=-0.2, le=0.2)
    wz: float = Field(ge=-0.5, le=0.5)


class Command(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    robot_id: str
    operator_id: str
    issued_at: datetime
    expires_at: datetime
    velocity: Velocity

    @field_validator("issued_at", "expires_at")
    @classmethod
    def aware_timestamp(cls, value):
        if value.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
        return value


class Telemetry(StrictModel):
    robot_id: str
    boot_id: str
    sequence: int = Field(ge=0)
    captured_at: datetime
    mode: Literal["simulator", "serial"]
    battery_v: float | None = Field(default=None, ge=0, le=100)
    x_m: float
    y_m: float
    yaw_rad: float
    vx_mps: float
    vy_mps: float
    wz_radps: float
    imu_accel_mps2: list[float] = Field(min_length=3, max_length=3)
    imu_gyro_radps: list[float] = Field(min_length=3, max_length=3)
    motor_rps: list[float] = Field(min_length=4, max_length=4)
    watchdog_stopped: bool
    fault: str | None = None
    quality: Literal["simulated", "measured", "partial"]

    @field_validator("captured_at")
    @classmethod
    def aware_timestamp(cls, value):
        if value.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
        return value


class Login(StrictModel):
    username: Literal["operator", "viewer"]
    password: str = Field(min_length=1, max_length=256)
