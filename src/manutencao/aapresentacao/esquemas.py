from datetime import date, datetime

from pydantic import BaseModel, Field

from manutencao.dominio.chamado import Chamado


class AbrirChamadoRequisicao(BaseModel):
    equipamento_id: int
    descricao_problema: str = Field(min_length=1)
    data_ocorrencia: date
    informacoes_adicionais: str = ""


class ChamadoResposta(BaseModel):
    id: int
    equipamento_id: int
    equipamento_nome: str
    solicitante_id: int
    departamento_id: int
    prioridade: Chamado.Prioridade | None
    estado: Chamado.Estado
    tecnicos_ids: list[int]
    descricao_problema: str
    data_ocorrencia: date
    data_abertura: datetime


def para_resposta(chamado: Chamado) -> ChamadoResposta:
    return ChamadoResposta(
        id=chamado.id,
        equipamento_id=chamado.equipamento.id,
        equipamento_nome=chamado.equipamento.nome,
        solicitante_id=chamado.solicitante.id,
        departamento_id=chamado.departamento.id,
        prioridade=chamado.prioridade,
        estado=chamado.estado,
        tecnicos_ids=[tecnico.id for tecnico in chamado.tecnicos],
        descricao_problema=chamado.descricao_problema,
        data_ocorrencia=chamado.data_ocorrencia,
        data_abertura=chamado.data_abertura,
    )
