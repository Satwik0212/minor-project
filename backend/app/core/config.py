from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://swm_ics:change_me@localhost:5432/swm_ics"
    log_level: str = "INFO"
    firebase_project_id: str = ""
    cors_allowed_origins: str = "http://localhost:5500"
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 8883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_ca_cert_path: str = ""
    mqtt_client_id: str = "swm-ics-worker-local"
    osrm_base_url: str = "https://router.project-osrm.org"
    otp_demo_mode: bool = False
settings = Settings()
