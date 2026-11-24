from dataclasses import replace
from datetime import date

import pytest

from manutencao.dominio.chamado import Chamado
from manutencao.dominio.notificacao import Notificacao
from manutencao.aplicacao.erros import AcessoNegado, EquipamentoNaoEncontrado
from manutencao.aplicacao.filtros import FiltrosChamado
from manutencao.aplicacao.servico import ManutencaoService
from manutencao.infraestrutura.notificador_fake import NotificadorFake
from manutencao.infraestrutura.repositorio_em_memoria import RepositorioEmMemoria


@pytest.fixture
def repo() -> RepositorioEmMemoria:
    return RepositorioEmMemoria.com_dados_de_exemplo(com_chamados=False)


@pytest.fixture
def notifier() -> NotificadorFake:
    return NotificadorFake()


@pytest.fixture
def service(repo: RepositorioEmMemoria, notifier: NotificadorFake) -> ManutencaoService:
    return ManutencaoService(repo, notifier)


def confirmation(repo: RepositorioEmMemoria) -> Notificacao:
    """Returns Ana's confirmation e-mail. Opening also queues one per coordinator."""
    [notification] = [
        n for n in repo.listar_pendentes() if n.destinatario == "ana@example.com"
    ]
    return notification


def test_open_ticket_saves_audit_and_pending_confirmation(
    service: ManutencaoService, repo: RepositorioEmMemoria, notifier: NotificadorFake
) -> None:
    ticket = service.abrir_chamado(
        1, 12, "Will not turn on", date(2026, 11, 10), "Power cable checked"
    )

    assert ticket.id == 1
    assert ticket.estado == Chamado.Estado.ABERTO
    assert ticket.departamento.id == 2
    assert ticket.informacoes_adicionais == "Power cable checked"
    assert repo.listar_chamados(FiltrosChamado()) == [ticket]
    audits = repo.listar_auditoria(ticket.id)
    assert len(audits) == 1
    audit = audits[0]
    assert audit.chamado is ticket
    assert audit.autor.id == 1
    assert audit.data_hora == ticket.data_abertura
    assert (audit.campo, audit.valor_anterior, audit.valor_novo) == ("estado", None, "ABERTO")
    # A abertura coloca o e-mail na fila para envio posterior.
    assert notifier.enviadas == []
    pending = repo.listar_pendentes()
    # Ana gets the confirmation; Helena, the Optics coordinator, gets a notice.
    assert [n.destinatario for n in pending] == ["ana@example.com", "helena@example.com"]
    notification = pending[0]
    assert notification.chamado is ticket
    assert notification.id == 1
    assert notification.destinatario == "ana@example.com"
    assert notification.status == Notificacao.Status.PENDENTE
    assert notification.tentativas == 0
    assert notification.assunto == f"Chamado #{ticket.id} registrado com sucesso"
    assert notification.mensagem == (
        "Olá, Ana.\n"
        "\n"
        f"Seu chamado #{ticket.id} foi registrado com sucesso.\n"
        "\n"
        "Equipamento: Microscópio (Laboratório de Biologia)\n"
        "Problema: Will not turn on\n"
        "Data da ocorrência: 10/11/2026\n"
        "Informações adicionais: Power cable checked\n"
        f"Aberto em: {ticket.data_abertura:%d/%m/%Y %H:%M}\n"
        "Estado: Aberto\n"
    )


def test_resend_sends_pending_notifications(
    service: ManutencaoService, repo: RepositorioEmMemoria, notifier: NotificadorFake
) -> None:
    service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10))
    pending = repo.listar_pendentes()

    service.reenviar_notificacoes()

    assert notifier.enviadas == pending
    assert all(n.status == Notificacao.Status.ENVIADA for n in pending)
    assert repo.listar_pendentes() == []

    service.reenviar_notificacoes()

    assert notifier.enviadas == pending


def test_missing_equipment_saves_nothing(
    service: ManutencaoService, repo: RepositorioEmMemoria, notifier: NotificadorFake
) -> None:
    with pytest.raises(EquipamentoNaoEncontrado):
        service.abrir_chamado(1, 999, "Will not turn on", date(2026, 11, 10))

    assert repo.listar_chamados(FiltrosChamado()) == []
    assert repo.listar_auditoria(1) == []
    assert repo.listar_pendentes() == []
    assert notifier.enviadas == []


@pytest.mark.parametrize("action", ["abrir", "consultar"])
def test_unknown_user_is_rejected(
    service: ManutencaoService, repo: RepositorioEmMemoria,
    notifier: NotificadorFake, action: str,
) -> None:
    with pytest.raises(AcessoNegado, match="User not found"):
        if action == "abrir":
            service.abrir_chamado(999, 12, "Will not turn on", date(2026, 11, 10))
        else:
            service.consultar_chamados(999, FiltrosChamado())

    assert repo.listar_chamados(FiltrosChamado()) == []
    assert notifier.enviadas == []


def test_send_failure_keeps_notification_pending_until_service_returns(
    repo: RepositorioEmMemoria,
) -> None:
    notifier = NotificadorFake(falhar=True)
    service = ManutencaoService(repo, notifier)
    ticket = service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10))
    notification = confirmation(repo)

    # Several rounds with the e-mail service down: each round tries 5 times.
    for _ in range(3):
        service.reenviar_notificacoes()

    assert repo.buscar_chamado(ticket.id) is ticket
    assert notification.status == Notificacao.Status.PENDENTE
    assert notification.tentativas == Notificacao.TENTATIVAS_POR_RODADA * 3
    assert notifier.enviadas == []

    # The service comes back: the next round sends it.
    notifier.falhar = False
    service.reenviar_notificacoes()

    assert notification.status == Notificacao.Status.ENVIADA
    assert notification in notifier.enviadas


def test_resend_rebuilds_notification_without_text(
    service: ManutencaoService, repo: RepositorioEmMemoria, notifier: NotificadorFake
) -> None:
    # Simula a interrupção da aplicação entre a gravação do chamado e a do texto.
    ticket = service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10))
    notification = confirmation(repo)
    texto_original = notification.mensagem
    notification.assunto = ""
    notification.mensagem = ""

    service.reenviar_notificacoes()

    assert notification in notifier.enviadas
    assert notification.assunto == f"Chamado #{ticket.id} registrado com sucesso"
    assert notification.mensagem == texto_original
    assert notification.status == Notificacao.Status.ENVIADA


def test_requester_sees_own_tickets_without_changing_filters(
    service: ManutencaoService,
) -> None:
    own_ticket = service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10))
    service.abrir_chamado(5, 12, "Blurry image", date(2026, 11, 10))
    filters = FiltrosChamado(estado=Chamado.Estado.ABERTO)
    original = replace(filters)

    assert service.consultar_chamados(1, filters) == [own_ticket]
    assert filters == original
    assert service.consultar_chamados(1, FiltrosChamado(solicitante_id=5)) == []


@pytest.mark.parametrize("user_id", [3, 7])
def test_coordinators_only_see_their_department_without_changing_filters(
    service: ManutencaoService, user_id: int,
) -> None:
    electrical_ticket = service.abrir_chamado(1, 10, "No signal", date(2026, 11, 10))
    optics_ticket = service.abrir_chamado(5, 12, "Blurry image", date(2026, 11, 10))
    expected = optics_ticket if user_id == 7 else electrical_ticket
    filters = FiltrosChamado()

    assert service.consultar_chamados(user_id, filters) == [expected]
    assert filters == FiltrosChamado()
    other_department = 1 if user_id == 7 else 2
    assert service.consultar_chamados(
        user_id, FiltrosChamado(departamento_id=other_department)
    ) == []


def test_coordinator_combines_state_and_equipment_filters(
    service: ManutencaoService,
) -> None:
    matching = service.abrir_chamado(1, 10, "No signal", date(2026, 11, 10))
    completed = service.abrir_chamado(5, 11, "No power", date(2026, 11, 10))
    completed.estado = Chamado.Estado.CONCLUIDO
    service.abrir_chamado(1, 12, "Blurry image", date(2026, 11, 10))

    assert service.consultar_chamados(
        3, FiltrosChamado(estado=Chamado.Estado.ABERTO, equipamento_id=10)
    ) == [matching]
    assert service.consultar_chamados(
        3, FiltrosChamado(estado=Chamado.Estado.ABERTO, equipamento_id=11)
    ) == []


@pytest.mark.parametrize("user_id", [2, 3])
def test_staff_without_department_see_no_tickets(
    service: ManutencaoService, repo: RepositorioEmMemoria, user_id: int,
) -> None:
    service.abrir_chamado(1, 10, "No signal", date(2026, 11, 10))
    user = repo.buscar_usuario(user_id)
    assert user is not None
    user.departamento = None

    assert service.consultar_chamados(user_id, FiltrosChamado()) == []


def test_unknown_action_is_denied(service: ManutencaoService) -> None:
    with pytest.raises(AcessoNegado):
        service._verificar_permissao(1, "unknown")


def test_assigned_technician_starts_and_concludes_ticket(
    service: ManutencaoService,
) -> None:
    ticket = service.abrir_chamado(1, 10, "No signal", date(2026, 11, 10))
    service.atribuir_tecnicos(3, ticket.id, [2])

    started = service.iniciar_atendimento(2, ticket.id)
    assert started.estado == Chamado.Estado.EM_ATENDIMENTO
    assert started.data_inicio_atendimento is not None

    concluded = service.concluir_atendimento(
        2,
        ticket.id,
        "Conector solto",
        "Conector reinstalado e equipamento testado",
    )
    assert concluded.estado == Chamado.Estado.CONCLUIDO
    assert concluded.concluido_por.id == 2
    assert concluded.diagnostico == "Conector solto"
    assert concluded.descricao_intervencao == "Conector reinstalado e equipamento testado"
    assert concluded.data_conclusao is not None


def test_unassigned_technician_cannot_change_status(
    service: ManutencaoService,
) -> None:
    ticket = service.abrir_chamado(1, 10, "No signal", date(2026, 11, 10))
    service.atribuir_tecnicos(3, ticket.id, [2])

    with pytest.raises(AcessoNegado):
        service.iniciar_atendimento(6, ticket.id)


def test_conclusion_requires_diagnosis_and_intervention(
    service: ManutencaoService,
) -> None:
    ticket = service.abrir_chamado(1, 10, "No signal", date(2026, 11, 10))
    service.atribuir_tecnicos(3, ticket.id, [2])
    service.iniciar_atendimento(2, ticket.id)

    with pytest.raises(ValueError, match="Diagnosis"):
        service.concluir_atendimento(2, ticket.id, "  ", "Replaced cable")
    with pytest.raises(ValueError, match="Intervention"):
        service.concluir_atendimento(2, ticket.id, "Damaged cable", " ")
