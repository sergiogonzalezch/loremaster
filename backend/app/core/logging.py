import logging
import re

PII_PATTERNS = {
    "password": re.compile(r"(password|passwd|pwd)[=:]?\s*\S+", re.IGNORECASE),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "token": re.compile(
        r"(token|jwt|authorization)[=:]?\s*Bearer\s+\S+", re.IGNORECASE
    ),
    "secret": re.compile(
        r"(secret|api_key|apikey|client_secret)[=:]?\s*\S+", re.IGNORECASE
    ),
}


class PIIFilter(logging.Filter):
    """Filtro de logging que scrub PII básico de mensajes.

    Reemplaza patrones sensibles con [REDACTED] para evitar que datos personales
    aparezcan en los logs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.msg:
            msg_str = str(record.msg)

            if record.args:
                try:
                    msg_str = msg_str % record.args
                except (ValueError, TypeError):
                    pass

            for pii_type, pattern in PII_PATTERNS.items():
                msg_str = pattern.sub(f"[{pii_type.upper()}:REDACTED]", msg_str)

            record.msg = msg_str
            record.args = ()

        return True


def configure_logging(level: str = "INFO") -> None:
    """Configura el logging de la aplicación con filtrado PII.

    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    handler = logging.StreamHandler()
    handler.addFilter(PIIFilter())

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())
    root_logger.addHandler(handler)
