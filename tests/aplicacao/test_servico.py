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
    return RepositorioEmMemoria.com_dados_de_exemplo()


@pytest.fixture
def notifier() -> NotificadorFake:
    return NotificadorFake()


@pytest.fixture
def service(repo: RepositorioEmMemoria, notifier: NotificadorFake) -> ManutencaoService:
    return ManutencaoService(repo, notifier)


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
    # Opening only queues the e-mail; nothing is sent yet.
    assert notifier.enviadas == []
    [notification] = repo.listar_pendentes()
    assert notification.chamado is ticket
    assert notification.id == 1
    assert notification.destinatario == "ana@example.com"
    assert notification.status == Notificacao.Status.PENDENTE
    assert notification.tentativas == 0
    assert notification.assunto == f"Chamado #{ticket.id} registrado"
    assert notification.mensagem == (
        "Olá, Ana.\n"
        "\n"
        f"Seu chamado #{ticket.id} foi registrado.\n"
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
    [notification] = repo.listar_pendentes()

    service.reenviar_notificacoes()

    assert notifier.enviadas == [notification]
    assert notification.status == Notificacao.Status.ENVIADA
    assert repo.listar_pendentes() == []

    service.reenviar_notificacoes()

    assert notifier.enviadas == [notification]


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


def test_send_failure_keeps_notification_pending_until_retry_limit(
    repo: RepositorioEmMemoria,
) -> None:
    notifier = NotificadorFake(falhar=True)
    service = ManutencaoService(repo, notifier)
    ticket = service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10))
    [notification] = repo.listar_pendentes()

    service.reenviar_notificacoes()

    assert repo.buscar_chamado(ticket.id) is ticket
    assert notification.status == Notificacao.Status.PENDENTE
    assert notification.tentativas == 1

    for _ in range(Notificacao.MAX_TENTATIVAS - 1):
        service.reenviar_notificacoes()

    assert notification.status == Notificacao.Status.FALHOU
    assert notification.tentativas == Notificacao.MAX_TENTATIVAS
    assert repo.listar_pendentes() == []
    assert notifier.enviadas == []


def test_resend_rebuilds_notification_without_text(
    service: ManutencaoService, repo: RepositorioEmMemoria, notifier: NotificadorFake
) -> None:
    # Simulates the app stopping between saving the ticket and writing the text.
    ticket = service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10))
    [notification] = repo.listar_pendentes()
    texto_original = notification.mensagem
    notification.assunto = ""
    notification.mensagem = ""

    service.reenviar_notificacoes()

    assert notifier.enviadas == [notification]
    assert notification.assunto == f"Chamado #{ticket.id} registrado"
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


@pytest.mark.parametrize("user_id", [2, 3, 4])
def test_staff_only_see_their_department_without_changing_filters(
    service: ManutencaoService, user_id: int,
) -> None:
    electrical_ticket = service.abrir_chamado(1, 10, "No signal", date(2026, 11, 10))
    optics_ticket = service.abrir_chamado(5, 12, "Blurry image", date(2026, 11, 10))
    expected = optics_ticket if user_id == 4 else electrical_ticket
    filters = FiltrosChamado()

    assert service.consultar_chamados(user_id, filters) == [expected]
    assert filters == FiltrosChamado()
    other_department = 1 if user_id == 4 else 2
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
