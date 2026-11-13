from dataclasses import dataclass
from datetime import date

from manutencao.dominio.chamado import Chamado


@dataclass
class FiltrosChamado:
    equipamento_id: int | None = None
    prioridade: Chamado.Prioridade | None = None
    tecnico_id: int | None = None
    estado: Chamado.Estado | None = None
    aberto_de: date | None = None
    aberto_ate: date | None = None
    solicitante_id: int | None = None
    departamento_id: int | None = None
