from dataclasses import dataclass
from datetime import datetime

from manutencao.dominio.chamado import Chamado
from manutencao.dominio.usuario import Usuario


@dataclass
class RegistroAuditoria:
    chamado: Chamado
    autor: Usuario
    data_hora: datetime
    campo: str
    valor_anterior: str | None
    valor_novo: str | None
    observacao: str = ""
    id: int | None = None
