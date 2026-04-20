from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppSettings:
    soap_endpoint: str = os.getenv("SOAP_ENDPOINT", "")
    soap_action_solicitar: str = os.getenv(
        "SOAP_ACTION_SOLICITAR",
        "http://www.ant.gob.ec/solicitarOrdenGAD",
    )
    soap_action_finalizar: str = os.getenv(
        "SOAP_ACTION_FINALIZAR",
        "http://www.ant.gob.ec/finalizarOrden",
    )
    soap_action_anular: str = os.getenv(
        "SOAP_ACTION_ANULAR",
        "http://www.ant.gob.ec/anularOrden",
    )
    # Credenciales enviadas como headers HTTP (USERNAME/PASSWORD)
    soap_username: str = os.getenv("SOAP_USERNAME", "GADSANVIC")
    soap_password_solicitar: str = os.getenv("SOAP_PASSWORD_SOLICITAR", "")
    soap_password_finalizar: str = os.getenv("SOAP_PASSWORD_FINALIZAR", "")
    soap_password_anular: str = os.getenv("SOAP_PASSWORD_ANULAR", "")
    soap_timeout_seconds: int = int(os.getenv("SOAP_TIMEOUT_SECONDS", "30"))
    wait_min_minutes: float = float(os.getenv("WAIT_MIN_MINUTES", "2.5"))
    wait_max_minutes: float = float(os.getenv("WAIT_MAX_MINUTES", "5.0"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_backoff_seconds: int = int(os.getenv("RETRY_BACKOFF_SECONDS", "5"))
    database_path: str = os.getenv("DATABASE_PATH", "auto_rtv.db")
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")
    supabase_orders_table: str = os.getenv("SUPABASE_ORDERS_TABLE", "rtv_ordenes")
    supabase_audit_table: str = os.getenv("SUPABASE_AUDIT_TABLE", "rtv_auditoria")
    supabase_sync_every_seconds: int = int(os.getenv("SUPABASE_SYNC_EVERY_SECONDS", "60"))


def get_settings() -> AppSettings:
    return AppSettings()
