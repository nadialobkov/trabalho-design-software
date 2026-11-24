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
    data_inicio_atendimento: datetime | None = None
    diagnostico: str | None = None
    descricao_intervencao: str | None = None
    data_conclusao: datetime | None = None


class AtribuirTecnicosRequisicao(BaseModel):
    tecnicos_ids: list[int] = Field(min_length=1)


class DefinirPrioridadeRequisicao(BaseModel):
    prioridade: Chamado.Prioridade


class ConcluirAtendimentoRequisicao(BaseModel):
    diagnostico: str = Field(min_length=1)
    descricao_intervencao: str = Field(min_length=1)


class NotificacaoResposta(BaseModel):
    id: int
    chamado_id: int
    data: datetime
    remetente: str
    mensagem: str


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
        data_inicio_atendimento=chamado.data_inicio_atendimento,
        diagnostico=chamado.diagnostico,
        descricao_intervencao=chamado.descricao_intervencao,
        data_conclusao=chamado.data_conclusao,
    )
