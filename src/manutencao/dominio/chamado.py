from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from manutencao.dominio.departamento import Departamento
from manutencao.dominio.equipamento import Equipamento
from manutencao.dominio.usuario import Usuario


@dataclass
class Chamado:
    class Estado(StrEnum):
        ABERTO = "ABERTO"
        ATRIBUIDO = "ATRIBUIDO"
        EM_ATENDIMENTO = "EM_ATENDIMENTO"
        CONCLUIDO = "CONCLUIDO"

    class Prioridade(StrEnum):
        BAIXA = "BAIXA"
        MEDIA = "MEDIA"
        ALTA = "ALTA"
        URGENTE = "URGENTE"
        CRITICA = "CRITICA"

    equipamento: Equipamento
    solicitante: Usuario
    departamento: Departamento
    descricao_problema: str
    data_ocorrencia: date
    data_abertura: datetime
    informacoes_adicionais: str = ""
    estado: Estado = Estado.ABERTO
    prioridade: Prioridade | None = None
    tecnicos: list[Usuario] = field(default_factory=list)
    data_inicio_atendimento: datetime | None = None
    diagnostico: str | None = None  # Causa identificada pelo técnico (RF06, RF07).
    descricao_intervencao: str | None = None
    concluido_por: Usuario | None = None
    data_conclusao: datetime | None = None
    id: int | None = None

    @classmethod
    def abrir(
        cls,
        equipamento: Equipamento,
        solicitante: Usuario,
        descricao_problema: str,
        data_ocorrencia: date,
        informacoes_adicionais: str,
        agora: datetime,
    ) -> "Chamado":
        if not descricao_problema.strip():
            raise ValueError("Problem description must not be empty.")

        return cls(
            equipamento=equipamento,
            solicitante=solicitante,
            departamento=equipamento.departamento,
            descricao_problema=descricao_problema,
            data_ocorrencia=data_ocorrencia,
            data_abertura=agora,
            informacoes_adicionais=informacoes_adicionais,
        )
