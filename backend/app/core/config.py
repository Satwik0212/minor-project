from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")
    database_url: str = "postgresql+psycopg://swm_ics:change_me@localhost:5432/swm_ics"
    log_level: str = "INFO"
    firebase_project_id: str = ""
    cors_allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5500,"
        "http://127.0.0.1:5500,http://localhost:3000,http://127.0.0.1:3000"
    )
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 8883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_ca_cert_path: str = ""
    mqtt_client_id: str = "swm-ics-worker-local"
    mqtt_telemetry_topic_template: str = "smartwaste/device/{device_id}/telemetry"
    mqtt_status_topic_template: str = "smartwaste/device/{device_id}/status"
    mqtt_config_topic_template: str = "smartwaste/device/{device_id}/config"
    mqtt_ack_topic_template: str = "smartwaste/device/{device_id}/ack"
    mqtt_keepalive_seconds: int = 60
    mqtt_telemetry_qos: int = 1
    device_offline_after_seconds: int = 180
    default_sampling_interval_seconds: int = 60
    osrm_base_url: str = "https://router.project-osrm.org"
    otp_demo_mode: bool = False
settings = Settings()
