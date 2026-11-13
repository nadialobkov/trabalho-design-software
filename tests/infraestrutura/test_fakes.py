from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest

from manutencao.dominio.usuario import Usuario
from manutencao.aplicacao.filtros import FiltrosChamado
from manutencao.dominio.chamado import Chamado
from manutencao.dominio.notificacao import Notificacao
from manutencao.dominio.registro_auditoria import RegistroAuditoria
from manutencao.infraestrutura.notificador_fake import NotificadorFake
from manutencao.infraestrutura.repositorio_em_memoria import RepositorioEmMemoria


@pytest.fixture
def repo() -> RepositorioEmMemoria:
    return RepositorioEmMemoria.com_dados_de_exemplo()


@pytest.fixture
def ticket(repo: RepositorioEmMemoria) -> Chamado:
    equipment = repo.buscar_equipamento(10)
    requester = repo.buscar_usuario(1)
    assert equipment is not None
    assert requester is not None
    return Chamado.abrir(
        equipment, requester, "Will not turn on", date(2026, 11, 10), "",
        datetime(2026, 11, 13, 10, 30),
    )


def save_ticket(
    repo: RepositorioEmMemoria, ticket: Chamado, notification: Notificacao | None = None
) -> RegistroAuditoria:
    audit = RegistroAuditoria(
        ticket, ticket.solicitante, ticket.data_abertura, "estado", None, "ABERTO"
    )
    repo.salvar_chamado(ticket, audit, notification)
    return audit


def test_sample_data_and_missing_records(repo: RepositorioEmMemoria) -> None:
    coordinator = repo.buscar_usuario(3)
    assert coordinator is not None
    assert coordinator.nome == "Carla"
    assert coordinator.papel == Usuario.Papel.COORDENADOR
    assert coordinator.departamento is repo.buscar_departamento(1)
    assert repo.listar_chamados(FiltrosChamado()) == []
    assert repo.listar_pendentes() == []
    assert repo.buscar_usuario(999) is None
    assert repo.buscar_equipamento(999) is None
    assert repo.buscar_departamento(999) is None
    assert repo.buscar_chamado(999) is None


def test_save_bundle_preserves_audit_and_updates_notification(
    repo: RepositorioEmMemoria, ticket: Chamado
) -> None:
    notification = Notificacao(ticket, ticket.solicitante.email)
    first_audit = save_ticket(repo, ticket, notification)
    assert (ticket.id, first_audit.id, notification.id) == (1, 1, 1)
    assert repo.buscar_chamado(1) is ticket
    assert repo.historico_equipamento(10) == [ticket]
    assert repo.historico_equipamento(12) == []
    assert repo.listar_auditoria(1) == [first_audit]
    assert repo.listar_auditoria(999) == []
    assert repo.listar_pendentes() == [notification]

    updated_notification = replace(notification)
    updated_notification.marcar_enviada()
    repo.atualizar_notificacao(updated_notification)
    assert repo.listar_pendentes() == []

    second_audit = save_ticket(repo, ticket)
    assert ticket.id == 1
    assert second_audit.id == 2
    assert repo.listar_auditoria(1) == [first_audit, second_audit]
    second_ticket = replace(ticket, id=None)
    second_notification = Notificacao(second_ticket, ticket.solicitante.email)
    third_audit = save_ticket(repo, second_ticket, second_notification)
    assert (second_ticket.id, third_audit.id, second_notification.id) == (2, 3, 2)


def test_filters_combine_include_date_limits_and_sort_by_id(
    repo: RepositorioEmMemoria, ticket: Chamado
) -> None:
    first_technician = repo.buscar_usuario(2)
    second_technician = repo.buscar_usuario(4)
    assert first_technician is not None
    assert second_technician is not None
    ticket.prioridade = Chamado.Prioridade.ALTA
    ticket.tecnicos = [first_technician, second_technician]
    ticket.id = 7
    save_ticket(repo, ticket)
    earlier_ticket = replace(ticket, id=3)
    save_ticket(repo, earlier_ticket)
    opening_date = ticket.data_abertura.date()
    filters = FiltrosChamado(
        equipamento_id=10, prioridade=Chamado.Prioridade.ALTA, tecnico_id=4,
        estado=Chamado.Estado.ABERTO, aberto_de=opening_date, aberto_ate=opening_date,
        solicitante_id=1, departamento_id=1,
    )
    assert repo.listar_chamados(filters) == [earlier_ticket, ticket]
    for mismatch in (
        {"equipamento_id": 12}, {"prioridade": Chamado.Prioridade.BAIXA}, {"tecnico_id": 999},
        {"estado": Chamado.Estado.CONCLUIDO},
        {"aberto_de": opening_date + timedelta(days=1)},
        {"aberto_ate": opening_date - timedelta(days=1)},
        {"solicitante_id": 5}, {"departamento_id": 2},
    ):
        assert repo.listar_chamados(replace(filters, **mismatch)) == [], mismatch


@pytest.mark.parametrize("fail", [False, True])
def test_fake_notifier_sends_or_raises(ticket: Chamado, fail: bool) -> None:
    notifier = NotificadorFake(falhar=fail)
    notification = Notificacao(ticket, ticket.solicitante.email)
    if fail:
        with pytest.raises(OSError, match="falha simulada"):
            notifier.enviar(notification)
        assert notifier.enviadas == []
    else:
        notifier.enviar(notification)
        assert notifier.enviadas == [notification]
