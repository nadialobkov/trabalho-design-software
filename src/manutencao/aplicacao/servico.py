import logging
from dataclasses import replace
from datetime import date, datetime

from manutencao.aplicacao.erros import AcessoNegado, EquipamentoNaoEncontrado
from manutencao.aplicacao.filtros import FiltrosChamado
from manutencao.aplicacao.interface_notificador import Notificador
from manutencao.aplicacao.interface_repositorio import ManutencaoRepositorio
from manutencao.dominio.chamado import Chamado
from manutencao.dominio.notificacao import Notificacao
from manutencao.dominio.registro_auditoria import RegistroAuditoria
from manutencao.dominio.usuario import Usuario


logger = logging.getLogger(__name__)


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
        # A notificação é salva como PENDENTE junto com o chamado.
        # O agendador dispara o envio depois (RF08, ASR03).
        notificacao = Notificacao(chamado, destinatario=usuario.email)
        self.repo.salvar_chamado(chamado, auditoria, notificacao)
        logger.info(
            "Chamado %s registrado para o equipamento %s. Notificação %s na fila.",
            chamado.id, equipamento.id, notificacao.id,
        )

        # Preenche o texto após a gravação, quando o chamado já tem ID.
        self._preencher_confirmacao(notificacao)
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
        """Tenta enviar cada notificação pendente uma vez por rodada (UC09).

        O agendador chama este método em segundo plano, sem verificar permissões.
        """
        for notificacao in self.repo.listar_pendentes():
            if not notificacao.assunto:
                # Se a aplicação parou antes de gravar o texto da notificação,
                # reconstrói a mensagem com os dados do chamado para poder enviá-la (ASR03).
                self._preencher_confirmacao(notificacao)
            tipo_falha = None
            try:
                self.notificador.enviar(notificacao)
            except OSError as erro:
                tipo_falha = type(erro).__name__
                notificacao.registrar_falha()
            else:
                notificacao.marcar_enviada()
            self.repo.atualizar_notificacao(notificacao)

            if tipo_falha is None:
                logger.info(
                    "Notificação %s do chamado %s marcada como enviada.",
                    notificacao.id, notificacao.chamado.id,
                )
            else:
                nivel = (
                    logging.ERROR
                    if notificacao.status == Notificacao.Status.FALHOU
                    else logging.WARNING
                )
                logger.log(
                    nivel,
                    "Falha no envio da notificação %s do chamado %s. Tentativa %d de %d. "
                    "Estado %s. Tipo de erro %s.",
                    notificacao.id, notificacao.chamado.id, notificacao.tentativas,
                    Notificacao.MAX_TENTATIVAS, notificacao.status, tipo_falha,
                )

    @staticmethod
    def _preencher_confirmacao(notificacao: Notificacao) -> None:
        """Monta o e-mail de confirmação a partir do chamado salvo (RF08).

        abrir_chamado() e reenviar_notificacoes() usam este método para gerar
        o mesmo texto, inclusive quando é preciso reconstruí-lo.
        """
        chamado = notificacao.chamado
        equipamento = chamado.equipamento
        notificacao.assunto = f"Chamado #{chamado.id} registrado"
        # O e-mail inclui os dados registrados para o solicitante ter uma cópia (RF08).
        notificacao.mensagem = (
            f"Olá, {chamado.solicitante.nome}.\n"
            "\n"
            f"Seu chamado #{chamado.id} foi registrado.\n"
            "\n"
            f"Equipamento: {equipamento.nome} ({equipamento.laboratorio})\n"
            f"Problema: {chamado.descricao_problema}\n"
            f"Data da ocorrência: {chamado.data_ocorrencia:%d/%m/%Y}\n"
            f"Informações adicionais: {chamado.informacoes_adicionais or '-'}\n"
            f"Aberto em: {chamado.data_abertura:%d/%m/%Y %H:%M}\n"
            "Estado: Aberto\n"
        )

    def _verificar_permissao(self, usuario_id: int, acao: str) -> Usuario:
        usuario = self.repo.buscar_usuario(usuario_id)
        if usuario is None:
            raise AcessoNegado("User not found.")
        if acao not in ("abrir", "consultar"):
            raise AcessoNegado("Action not allowed.")
        return usuario
