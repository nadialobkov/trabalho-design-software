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
        for coordenador in self._coordenadores_departamento(chamado.departamento.id):
            self._salvar_email(
                chamado,
                coordenador.email,
                f"Chamado #{chamado.id} aberto",
                f"O chamado #{chamado.id} foi aberto para {chamado.equipamento.nome}. "
                "Atribua um técnico responsável.",
            )
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
            if usuario.papel == Usuario.Papel.TECNICO:
                if filtros.tecnico_id is not None and filtros.tecnico_id != usuario.id:
                    return []
                filtros_restritos = replace(
                    filtros_restritos,
                    departamento_id=usuario.departamento.id,
                    tecnico_id=usuario.id,
                )
        return self.repo.listar_chamados(filtros_restritos)

    def atribuir_tecnicos(
        self,
        usuario_id: int,
        chamado_id: int,
        tecnicos_ids: list[int],
    ) -> Chamado:
        coordenador = self._verificar_permissao(usuario_id, "consultar")
        chamado = self.repo.buscar_chamado(chamado_id)
        if chamado is None:
            raise AcessoNegado("Ticket not found.")
        if (
            coordenador.papel != Usuario.Papel.COORDENADOR
            or coordenador.departamento is None
            or coordenador.departamento.id != chamado.departamento.id
        ):
            raise AcessoNegado("Only the responsible coordinator may assign technicians.")
        if chamado.estado != Chamado.Estado.ABERTO:
            raise ValueError("Only open tickets can be assigned.")
        if not tecnicos_ids:
            raise ValueError("At least one technician must be selected.")

        tecnicos = []
        for tecnico_id in tecnicos_ids:
            tecnico = self.repo.buscar_usuario(tecnico_id)
            if (
                tecnico is None
                or tecnico.papel != Usuario.Papel.TECNICO
                or tecnico.departamento is None
                or tecnico.departamento.id != chamado.departamento.id
            ):
                raise AcessoNegado("Technician is not authorized for this department.")
            tecnicos.append(tecnico)

        anteriores = ",".join(str(tecnico.id) for tecnico in chamado.tecnicos)
        novos = ",".join(str(tecnico.id) for tecnico in tecnicos)
        chamado.tecnicos = tecnicos
        chamado.estado = Chamado.Estado.ATRIBUIDO
        agora = datetime.now()
        auditoria = RegistroAuditoria(
            chamado,
            coordenador,
            agora,
            campo="tecnicos",
            valor_anterior=anteriores or None,
            valor_novo=novos,
        )
        self.repo.salvar_chamado(chamado, auditoria)
        for tecnico in tecnicos:
            self._salvar_email(
                chamado,
                tecnico.email,
                f"Novo chamado #{chamado.id} atribuído",
                f"Você recebeu o chamado #{chamado.id} para {chamado.equipamento.nome}.",
            )
        nomes = ", ".join(tecnico.nome for tecnico in tecnicos)
        for coordenador in self._coordenadores_departamento(chamado.departamento.id):
            self._salvar_email(
                chamado,
                coordenador.email,
                f"Chamado #{chamado.id} atribuído",
                f"O chamado #{chamado.id} foi atribuído ao técnico {nomes} com sucesso.",
            )
        return chamado

    def definir_prioridade(
        self,
        usuario_id: int,
        chamado_id: int,
        prioridade: Chamado.Prioridade,
    ) -> Chamado:
        coordenador = self._verificar_permissao(usuario_id, "consultar")
        chamado = self.repo.buscar_chamado(chamado_id)
        if chamado is None:
            raise AcessoNegado("Ticket not found.")
        if (
            coordenador.papel != Usuario.Papel.COORDENADOR
            or coordenador.departamento is None
            or coordenador.departamento.id != chamado.departamento.id
        ):
            raise AcessoNegado("Only the responsible coordinator may change priority.")

        anterior = str(chamado.prioridade) if chamado.prioridade else None
        chamado.prioridade = prioridade
        agora = datetime.now()
        auditoria = RegistroAuditoria(
            chamado,
            coordenador,
            agora,
            campo="prioridade",
            valor_anterior=anterior,
            valor_novo=str(prioridade),
        )
        self.repo.salvar_chamado(chamado, auditoria)
        self._notificar_estado(
            chamado,
            tecnico,
            assunto="Chamado em andamento",
            mensagem_solicitante=f"Seu chamado #{chamado.id} está em andamento.",
            mensagem_tecnico=f"Chamado #{chamado.id} está em andamento agora.",
            mensagem_coordenador=f"O técnico {tecnico.nome} está resolvendo o chamado #{chamado.id}.",
        )
        return chamado

    def iniciar_atendimento(self, usuario_id: int, chamado_id: int) -> Chamado:
        tecnico = self._verificar_permissao(usuario_id, "consultar")
        chamado = self.repo.buscar_chamado(chamado_id)
        if chamado is None:
            raise AcessoNegado("Ticket not found.")
        if not self._tecnico_responsavel(tecnico, chamado):
            raise AcessoNegado("Only an assigned technician may start this ticket.")
        if chamado.estado != Chamado.Estado.ATRIBUIDO:
            raise ValueError("Only assigned tickets can be started.")

        chamado.estado = Chamado.Estado.EM_ATENDIMENTO
        chamado.data_inicio_atendimento = datetime.now()
        agora = chamado.data_inicio_atendimento
        auditoria = RegistroAuditoria(
            chamado,
            tecnico,
            agora,
            campo="estado",
            valor_anterior="ATRIBUIDO",
            valor_novo="EM_ATENDIMENTO",
        )
        self.repo.salvar_chamado(chamado, auditoria)
        self._notificar_estado(
            chamado,
            tecnico,
            assunto="Chamado concluído",
            mensagem_solicitante=(
                f"Seu chamado #{chamado.id} foi concluído. "
                f"Intervenção: {chamado.descricao_intervencao}"
            ),
            mensagem_tecnico=f"Chamado #{chamado.id} concluído com sucesso.",
            mensagem_coordenador=(
                f"O técnico {tecnico.nome} concluiu o chamado #{chamado.id} com sucesso."
            ),
        )
        return chamado

    def concluir_atendimento(
        self,
        usuario_id: int,
        chamado_id: int,
        diagnostico: str,
        descricao_intervencao: str,
    ) -> Chamado:
        tecnico = self._verificar_permissao(usuario_id, "consultar")
        chamado = self.repo.buscar_chamado(chamado_id)
        if chamado is None:
            raise AcessoNegado("Ticket not found.")
        if not self._tecnico_responsavel(tecnico, chamado):
            raise AcessoNegado("Only an assigned technician may conclude this ticket.")
        if chamado.estado != Chamado.Estado.EM_ATENDIMENTO:
            raise ValueError("Only tickets in attendance can be concluded.")
        if not diagnostico.strip():
            raise ValueError("Diagnosis must not be empty.")
        if not descricao_intervencao.strip():
            raise ValueError("Intervention description must not be empty.")

        chamado.diagnostico = diagnostico.strip()
        chamado.descricao_intervencao = descricao_intervencao.strip()
        chamado.estado = Chamado.Estado.CONCLUIDO
        chamado.concluido_por = tecnico
        chamado.data_conclusao = datetime.now()
        auditoria = RegistroAuditoria(
            chamado,
            tecnico,
            chamado.data_conclusao,
            campo="estado",
            valor_anterior="EM_ATENDIMENTO",
            valor_novo="CONCLUIDO",
        )
        self.repo.salvar_chamado(chamado, auditoria)
        return chamado

    def listar_notificacoes(self, usuario_id: int) -> list[dict]:
        usuario = self._verificar_permissao(usuario_id, "consultar")
        chamadas = self.consultar_chamados(usuario_id, FiltrosChamado())
        eventos: list[dict] = []

        for chamado in chamadas:
            for auditoria in self.repo.listar_auditoria(chamado.id):
                mensagem = None
                remetente = "SGME"

                if auditoria.campo == "estado" and auditoria.valor_novo == "ABERTO":
                    if usuario.papel == Usuario.Papel.SOLICITANTE:
                        mensagem = f"Chamado #{chamado.id} registrado com sucesso."
                        remetente = "SGME"
                    elif usuario.papel == Usuario.Papel.COORDENADOR:
                        mensagem = f"Chamado #{chamado.id} aberto. Atribua um técnico."
                        remetente = chamado.solicitante.nome
                elif auditoria.campo == "tecnicos":
                    tecnicos_ids = {
                        int(valor)
                        for valor in (auditoria.valor_novo or "").split(",")
                        if valor
                    }
                    if usuario.papel == Usuario.Papel.TECNICO and usuario.id in tecnicos_ids:
                        mensagem = f"Novo chamado #{chamado.id} atribuído a você."
                        remetente = auditoria.autor.nome
                    elif usuario.papel == Usuario.Papel.COORDENADOR:
                        nomes = [
                            tecnico.nome
                            for tecnico in chamado.tecnicos
                            if tecnico.id in tecnicos_ids
                        ]
                        mensagem = (
                            f"Chamado #{chamado.id} atribuído ao técnico "
                            f"{', '.join(nomes) if nomes else 'responsável'} com sucesso."
                        )
                        remetente = auditoria.autor.nome
                elif (
                    auditoria.campo == "estado"
                    and auditoria.valor_novo == "EM_ATENDIMENTO"
                ):
                    if usuario.papel == Usuario.Papel.SOLICITANTE:
                        mensagem = f"Seu chamado #{chamado.id} está em andamento."
                        remetente = auditoria.autor.nome
                    elif usuario.papel == Usuario.Papel.TECNICO:
                        if any(tecnico.id == usuario.id for tecnico in chamado.tecnicos):
                            mensagem = f"Chamado #{chamado.id} está em andamento agora."
                            remetente = usuario.nome
                    elif usuario.papel == Usuario.Papel.COORDENADOR:
                        mensagem = (
                            f"O técnico {auditoria.autor.nome} está resolvendo "
                            f"o chamado #{chamado.id}."
                        )
                        remetente = auditoria.autor.nome
                elif (
                    auditoria.campo == "estado"
                    and auditoria.valor_novo == "CONCLUIDO"
                ):
                    if usuario.papel == Usuario.Papel.SOLICITANTE:
                        mensagem = (
                            f"Seu chamado #{chamado.id} foi concluído. "
                            f"Intervenção: {chamado.descricao_intervencao or '-'}"
                        )
                        remetente = auditoria.autor.nome
                    elif usuario.papel == Usuario.Papel.TECNICO:
                        if any(tecnico.id == usuario.id for tecnico in chamado.tecnicos):
                            mensagem = f"Chamado #{chamado.id} concluído com sucesso."
                            remetente = usuario.nome
                    elif usuario.papel == Usuario.Papel.COORDENADOR:
                        mensagem = (
                            f"O técnico {auditoria.autor.nome} concluiu o chamado "
                            f"#{chamado.id} com sucesso."
                        )
                        remetente = auditoria.autor.nome

                if mensagem:
                    eventos.append({
                        "id": auditoria.id or 0,
                        "chamado_id": chamado.id,
                        "data": auditoria.data_hora.isoformat(),
                        "remetente": remetente,
                        "mensagem": mensagem,
                    })

        eventos.sort(key=lambda evento: evento["data"], reverse=True)
        return eventos

    def _coordenadores_departamento(self, departamento_id: int) -> list[Usuario]:
        return [
            usuario
            for usuario in self.repo.listar_usuarios()
            if usuario.papel == Usuario.Papel.COORDENADOR
            and usuario.departamento is not None
            and usuario.departamento.id == departamento_id
        ]

    def _salvar_email(
        self,
        chamado: Chamado,
        destinatario: str,
        assunto: str,
        mensagem: str,
    ) -> None:
        self.repo.salvar_notificacao(
            Notificacao(
                chamado=chamado,
                destinatario=destinatario,
                assunto=assunto,
                mensagem=mensagem,
            )
        )

    def _notificar_estado(
        self,
        chamado: Chamado,
        tecnico: Usuario,
        assunto: str,
        mensagem_solicitante: str,
        mensagem_tecnico: str,
        mensagem_coordenador: str,
    ) -> None:
        self._salvar_email(
            chamado, chamado.solicitante.email, assunto, mensagem_solicitante
        )
        self._salvar_email(
            chamado, tecnico.email, assunto, mensagem_tecnico
        )
        for coordenador in self._coordenadores_departamento(chamado.departamento.id):
            self._salvar_email(
                chamado, coordenador.email, assunto, mensagem_coordenador
            )

    @staticmethod
    def _tecnico_responsavel(tecnico: Usuario, chamado: Chamado) -> bool:
        return (
            tecnico.papel == Usuario.Papel.TECNICO
            and tecnico.departamento is not None
            and tecnico.departamento.id == chamado.departamento.id
            and any(responsavel.id == tecnico.id for responsavel in chamado.tecnicos)
        )

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
        notificacao.assunto = f"Chamado #{chamado.id} registrado com sucesso"
        # O e-mail inclui os dados registrados para o solicitante ter uma cópia (RF08).
        notificacao.mensagem = (
            f"Olá, {chamado.solicitante.nome}.\n"
            "\n"
            f"Seu chamado #{chamado.id} foi registrado com sucesso.\n"
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
