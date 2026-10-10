import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./runtime/jetauto.db")
    mqtt_host: str = os.getenv("MQTT_HOST", "127.0.0.1")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username: str = os.getenv("MQTT_USERNAME", "")
    mqtt_password: str = os.getenv("MQTT_PASSWORD", "")
    mqtt_ca: str = os.getenv("MQTT_CA", "")
    mqtt_tls: bool = os.getenv("MQTT_TLS", "false").lower() == "true"
    robot_id: str = os.getenv("ROBOT_ID", "jetauto-01")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    operator_password: str = os.getenv("OPERATOR_PASSWORD", "")
    viewer_password: str = os.getenv("VIEWER_PASSWORD", "")
    secure_cookie: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    deployment: str = os.getenv("DEPLOYMENT_NAME", "LOCAL / ON-PREMISE")
    gateway_mode: str = os.getenv("GATEWAY_MODE", "simulator")


settings = Settings()
