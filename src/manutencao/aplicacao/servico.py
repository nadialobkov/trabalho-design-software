from dataclasses import replace
from datetime import date, datetime

from manutencao.aplicacao.erros import AcessoNegado, EquipamentoNaoEncontrado
from manutencao.aplicacao.filtros import FiltrosChamado
from manutencao.aplicacao.notificador import Notificador
from manutencao.aplicacao.repositorio import ManutencaoRepositorio
from manutencao.dominio.chamado import Chamado
from manutencao.dominio.notificacao import Notificacao
from manutencao.dominio.registro_auditoria import RegistroAuditoria
from manutencao.dominio.usuario import Usuario


class ManutencaoService:
    def __init__(self, repo: ManutencaoRepositorio, notificador: Notificador) -> None:
        self.repo = repo
        self.notificador = notificador

    def abrir_chamado(
        self,
        usuario_id: int,
        equipamento_id: int,
        descricao_problema: str,
        data_ocorrencia: date,
        informacoes_adicionais: str = "",
    ) -> Chamado:
        usuario = self._verificar_permissao(usuario_id, "abrir")
        equipamento = self.repo.buscar_equipamento(equipamento_id)
        if equipamento is None:
            raise EquipamentoNaoEncontrado("Equipment not found.")

        agora = datetime.now()
        chamado = Chamado.abrir(
            equipamento, usuario, descricao_problema, data_ocorrencia,
            informacoes_adicionais, agora,
        )
        auditoria = RegistroAuditoria(
            chamado, usuario, agora,
            campo="estado", valor_anterior=None, valor_novo="ABERTO",
        )
        # The e-mail is not sent here. It is saved as PENDENTE together with the
        # ticket, and AgendadorNotificacoes sends it later (RF08, ASR03).
        notificacao = Notificacao(chamado, destinatario=usuario.email)
        self.repo.salvar_chamado(chamado, auditoria, notificacao)

        # The ticket id only exists after saving, so the text is filled now.
        notificacao.assunto = f"Chamado #{chamado.id} registrado"
        notificacao.mensagem = (
            f"Seu chamado #{chamado.id} para o equipamento {equipamento.nome} "
            "foi registrado."
        )
        self.repo.atualizar_notificacao(notificacao)
        return chamado

    def consultar_chamados(
        self, usuario_id: int, filtros: FiltrosChamado
    ) -> list[Chamado]:
        usuario = self._verificar_permissao(usuario_id, "consultar")
        if usuario.papel == Usuario.Papel.SOLICITANTE:
            if filtros.solicitante_id is not None and filtros.solicitante_id != usuario.id:
                return []
            filtros_restritos = replace(filtros, solicitante_id=usuario.id)
        else:
            if usuario.departamento is None:
                return []
            if (
                filtros.departamento_id is not None
                and filtros.departamento_id != usuario.departamento.id
            ):
                return []
            filtros_restritos = replace(filtros, departamento_id=usuario.departamento.id)
        return self.repo.listar_chamados(filtros_restritos)

    def reenviar_notificacoes(self) -> None:
        """UC09: try to send every pending notification once.

        Called by AgendadorNotificacoes, not by a user, so there is no
        permission check.
        """
        for notificacao in self.repo.listar_pendentes():
            if not notificacao.assunto:
                # Ticket saved but text not filled yet; take it next round.
                continue
            try:
                self.notificador.enviar(notificacao)
            except OSError:
                # E-mail server down: keep it pending and try next round (ASR03).
                notificacao.registrar_falha()
            else:
                notificacao.marcar_enviada()
            self.repo.atualizar_notificacao(notificacao)

    def _verificar_permissao(self, usuario_id: int, acao: str) -> Usuario:
        usuario = self.repo.buscar_usuario(usuario_id)
        if usuario is None:
            raise AcessoNegado("User not found.")
        if acao not in ("abrir", "consultar"):
            raise AcessoNegado("Action not allowed.")
        return usuario
