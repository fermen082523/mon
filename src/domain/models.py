from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EstadoOrden(str, Enum):
    PENDIENTE_SOLICITUD = "PENDIENTE_SOLICITUD"
    SOLICITADA = "SOLICITADA"
    FINALIZADA = "FINALIZADA"
    ANULADA = "ANULADA"
    ERROR = "ERROR"


@dataclass
class Orden:
    id: int
    placa: str
    numero_orden: Optional[str]
    estado: EstadoOrden
    intentos: int
