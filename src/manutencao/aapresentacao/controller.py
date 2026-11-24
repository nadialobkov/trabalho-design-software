import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import date

from fastapi import APIRouter, FastAPI, Header, Request
from fastapi.responses import JSONResponse

from manutencao.dominio.chamado import Chamado
from manutencao.aplicacao.erros import AcessoNegado, EquipamentoNaoEncontrado
from manutencao.aplicacao.filtros import FiltrosChamado
from manutencao.aplicacao.servico import ManutencaoService
from manutencao.aapresentacao.agendador import AgendadorNotificacoes
from manutencao.aapresentacao.esquemas import (
    AbrirChamadoRequisicao,
    AtribuirTecnicosRequisicao,
    ChamadoResposta,
    ConcluirAtendimentoRequisicao,
    DefinirPrioridadeRequisicao,
    para_resposta,
)


class ManutencaoController:
    def __init__(self, servico: ManutencaoService) -> None:
        self.servico = servico
        self.router = APIRouter()
        self.router.add_api_route(
            "/chamados", self.post_chamados, methods=["POST"],
            status_code=201, response_model=ChamadoResposta,
        )
        self.router.add_api_route(
            "/chamados", self.get_chamados, methods=["GET"],
            response_model=list[ChamadoResposta],
        )
        self.router.add_api_route(
            "/chamados/{chamado_id}/atribuicao",
            self.patch_atribuicao,
            methods=["PATCH"],
            response_model=ChamadoResposta,
        )
        self.router.add_api_route(
            "/chamados/{chamado_id}/prioridade",
            self.patch_prioridade,
            methods=["PATCH"],
            response_model=ChamadoResposta,
        )
        self.router.add_api_route(
            "/chamados/{chamado_id}/iniciar",
            self.patch_iniciar,
            methods=["PATCH"],
            response_model=ChamadoResposta,
        )
        self.router.add_api_route(
            "/chamados/{chamado_id}/concluir",
            self.patch_concluir,
            methods=["PATCH"],
            response_model=ChamadoResposta,
        )

    def patch_iniciar(
        self,
        chamado_id: int,
        x_usuario_id: int | None = Header(default=None),
    ) -> ChamadoResposta:
        if x_usuario_id is None:
            raise AcessoNegado("User header is required.")
        return para_resposta(
            self.servico.iniciar_atendimento(x_usuario_id, chamado_id)
        )

    def patch_concluir(
        self,
        chamado_id: int,
        corpo: ConcluirAtendimentoRequisicao,
        x_usuario_id: int | None = Header(default=None),
    ) -> ChamadoResposta:
        if x_usuario_id is None:
            raise AcessoNegado("User header is required.")
        return para_resposta(
            self.servico.concluir_atendimento(
                x_usuario_id,
                chamado_id,
                corpo.diagnostico,
                corpo.descricao_intervencao,
            )
        )

    def patch_atribuicao(
        self,
        chamado_id: int,
        corpo: AtribuirTecnicosRequisicao,
        x_usuario_id: int | None = Header(default=None),
    ) -> ChamadoResposta:
        if x_usuario_id is None:
            raise AcessoNegado("User header is required.")
        chamado = self.servico.atribuir_tecnicos(
            x_usuario_id, chamado_id, corpo.tecnicos_ids
        )
        return para_resposta(chamado)

    def patch_prioridade(
        self,
        chamado_id: int,
        corpo: DefinirPrioridadeRequisicao,
        x_usuario_id: int | None = Header(default=None),
    ) -> ChamadoResposta:
        if x_usuario_id is None:
            raise AcessoNegado("User header is required.")
        chamado = self.servico.definir_prioridade(
            x_usuario_id, chamado_id, corpo.prioridade
        )
        return para_resposta(chamado)

    def post_chamados(
        self,
        corpo: AbrirChamadoRequisicao,
        x_usuario_id: int | None = Header(default=None),
    ) -> ChamadoResposta:
        if x_usuario_id is None:
            raise AcessoNegado("User header is required.")
        chamado = self.servico.abrir_chamado(
            usuario_id=x_usuario_id,
            equipamento_id=corpo.equipamento_id,
            descricao_problema=corpo.descricao_problema,
            data_ocorrencia=corpo.data_ocorrencia,
            informacoes_adicionais=corpo.informacoes_adicionais,
        )
        return para_resposta(chamado)

    def get_chamados(
        self,
        x_usuario_id: int | None = Header(default=None),
        equipamento_id: int | None = None,
        prioridade: Chamado.Prioridade | None = None,
        tecnico_id: int | None = None,
        estado: Chamado.Estado | None = None,
        aberto_de: date | None = None,
        aberto_ate: date | None = None,
        solicitante_id: int | None = None,
        departamento_id: int | None = None,
    ) -> list[ChamadoResposta]:
        if x_usuario_id is None:
            raise AcessoNegado("User header is required.")
        filtros = FiltrosChamado(
            equipamento_id=equipamento_id,
            prioridade=prioridade,
            tecnico_id=tecnico_id,
            estado=estado,
            aberto_de=aberto_de,
            aberto_ate=aberto_ate,
            solicitante_id=solicitante_id,
            departamento_id=departamento_id,
        )
        return [
            para_resposta(chamado)
            for chamado in self.servico.consultar_chamados(x_usuario_id, filtros)
        ]


def criar_app(
    servico: ManutencaoService, agendador: AgendadorNotificacoes | None = None
) -> FastAPI:
    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        # Inicia o agendador junto com o servidor e o encerra ao desligar.
        tarefa = asyncio.create_task(agendador.rodar()) if agendador else None
        yield
        if tarefa is not None:
            tarefa.cancel()
            with suppress(asyncio.CancelledError):
                await tarefa

    app = FastAPI(lifespan=ciclo_de_vida)
    app.include_router(ManutencaoController(servico).router)

    def registrar_erro(tipo: type[Exception], codigo: int) -> None:
        async def tratar_erro(request: Request, erro: Exception) -> JSONResponse:
            return JSONResponse(status_code=codigo, content={"erro": str(erro)})

        app.add_exception_handler(tipo, tratar_erro)

    registrar_erro(AcessoNegado, 403)
    registrar_erro(EquipamentoNaoEncontrado, 404)
    # O domínio lança ValueError para dados inválidos, como uma descrição em branco.
    registrar_erro(ValueError, 422)
    return app
