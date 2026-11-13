"""Checks PostgresManutencaoRepositorio against a real database.

Skipped unless TEST_DATABASE_URL points to a database that may be wiped,
for example: TEST_DATABASE_URL=postgresql:///manutencao_teste
"""
import os
from datetime import date, datetime
from pathlib import Path

import psycopg
import pytest

from manutencao.aplicacao.filtros import FiltrosChamado
from manutencao.aplicacao.servico import ManutencaoService
from manutencao.dominio.chamado import Chamado
from manutencao.dominio.notificacao import Notificacao
from manutencao.dominio.registro_auditoria import RegistroAuditoria
from manutencao.infraestrutura.notificador_fake import NotificadorFake
from manutencao.infraestrutura.repositorio_postgres import PostgresManutencaoRepositorio


URL = os.environ.get("TEST_DATABASE_URL")
BANCO = Path(__file__).resolve().parents[2] / "banco"

pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL is not set")


@pytest.fixture
def repo() -> PostgresManutencaoRepositorio:
    # Fresh tables and sample data for every test.
    with psycopg.connect(URL) as conn:
        conn.execute((BANCO / "schema.sql").read_text(encoding="utf-8"))
        conn.execute((BANCO / "dados_exemplo.sql").read_text(encoding="utf-8"))
    return PostgresManutencaoRepositorio(URL)


@pytest.fixture
def notifier() -> NotificadorFake:
    return NotificadorFake()


@pytest.fixture
def service(repo: PostgresManutencaoRepositorio, notifier: NotificadorFake) -> ManutencaoService:
    return ManutencaoService(repo, notifier)


def test_sample_data_is_loaded(repo: PostgresManutencaoRepositorio) -> None:
    carla = repo.buscar_usuario(3)
    assert carla is not None
    assert carla.papel == carla.Papel.COORDENADOR
    assert carla.departamento.nome == "Elétrica"
    assert repo.buscar_equipamento(12).departamento.id == 2
    assert repo.buscar_usuario(999) is None
    assert repo.buscar_equipamento(999) is None


def test_open_ticket_saves_ticket_audit_and_pending_notification(
    service: ManutencaoService, repo: PostgresManutencaoRepositorio,
) -> None:
    ticket = service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10), "Cable checked")

    saved = repo.buscar_chamado(ticket.id)
    assert saved.estado == Chamado.Estado.ABERTO
    assert saved.equipamento.nome == "Microscópio"
    assert saved.departamento.id == 2
    assert saved.informacoes_adicionais == "Cable checked"
    assert saved.diagnostico is None
    [audit] = repo.listar_auditoria(ticket.id)
    assert (audit.campo, audit.valor_novo, audit.autor.id) == ("estado", "ABERTO", 1)
    [notification] = repo.listar_pendentes()
    assert notification.chamado.id == ticket.id
    assert notification.assunto == f"Chamado #{ticket.id} registrado"


def test_resend_marks_notification_as_sent(
    service: ManutencaoService, repo: PostgresManutencaoRepositorio, notifier: NotificadorFake,
) -> None:
    service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10))

    service.reenviar_notificacoes()

    assert len(notifier.enviadas) == 1
    assert repo.listar_pendentes() == []


def test_filters_and_visibility_rules(
    service: ManutencaoService, repo: PostgresManutencaoRepositorio,
) -> None:
    ana_ticket = service.abrir_chamado(1, 10, "No signal", date(2026, 11, 10))
    service.abrir_chamado(5, 12, "Blurry image", date(2026, 11, 10))
    technician = repo.buscar_usuario(2)
    ana_ticket.tecnicos = [technician]
    ana_ticket.prioridade = Chamado.Prioridade.ALTA
    audit = RegistroAuditoria(ana_ticket, technician, datetime.now(), "prioridade", None, "ALTA")
    repo.salvar_chamado(ana_ticket, audit)

    assert [c.id for c in service.consultar_chamados(1, FiltrosChamado())] == [ana_ticket.id]
    assert [c.equipamento.id for c in service.consultar_chamados(3, FiltrosChamado())] == [10]
    found = repo.listar_chamados(FiltrosChamado(
        tecnico_id=2, prioridade=Chamado.Prioridade.ALTA, estado=Chamado.Estado.ABERTO,
        aberto_de=ana_ticket.data_abertura.date(), aberto_ate=ana_ticket.data_abertura.date(),
    ))
    assert [c.id for c in found] == [ana_ticket.id]
    assert found[0].tecnicos[0].nome == "Bruno"
    assert repo.listar_chamados(FiltrosChamado(tecnico_id=4)) == []


def test_failed_save_keeps_nothing(repo: PostgresManutencaoRepositorio) -> None:
    equipment, requester = repo.buscar_equipamento(10), repo.buscar_usuario(1)
    ticket = Chamado.abrir(equipment, requester, "No signal", date(2026, 11, 10), "", datetime.now())
    audit = RegistroAuditoria(ticket, requester, datetime.now(), "estado", None, "ABERTO")
    broken = Notificacao(ticket, "ana@example.com", status="NOT_A_STATUS")

    with pytest.raises(psycopg.errors.CheckViolation):
        repo.salvar_chamado(ticket, audit, broken)

    assert repo.listar_chamados(FiltrosChamado()) == []


def test_audit_rows_cannot_be_changed(
    service: ManutencaoService, repo: PostgresManutencaoRepositorio,
) -> None:
    service.abrir_chamado(1, 10, "No signal", date(2026, 11, 10))

    with psycopg.connect(URL) as conn, pytest.raises(psycopg.errors.RaiseException):
        conn.execute("UPDATE registro_auditoria SET valor_novo = 'X'")


def test_two_instances_never_get_the_same_pending_notification(
    service: ManutencaoService, repo: PostgresManutencaoRepositorio,
) -> None:
    service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10))
    other_instance = PostgresManutencaoRepositorio(URL)

    [notification] = repo.listar_pendentes()
    assert other_instance.listar_pendentes() == []

    # A failed send keeps it pending and frees it for the next round.
    notification.registrar_falha()
    repo.atualizar_notificacao(notification)
    assert [n.id for n in other_instance.listar_pendentes()] == [notification.id]


def test_notification_without_text_waits_for_its_text(
    service: ManutencaoService, repo: PostgresManutencaoRepositorio,
) -> None:
    # Between the two steps of abrir_chamado() the scheduler must not take it.
    ticket = service.abrir_chamado(1, 12, "Will not turn on", date(2026, 11, 10))
    notification = Notificacao(ticket, destinatario="ana@example.com")
    repo.salvar_chamado(ticket, RegistroAuditoria(
        ticket, ticket.solicitante, datetime(2026, 11, 13), campo="estado",
        valor_anterior=None, valor_novo="ABERTO",
    ), notification)
    assert notification.id not in [n.id for n in repo.listar_pendentes()]

    # If the app stopped there, the row is free again once the reservation ends.
    with psycopg.connect(URL) as conn:
        conn.execute(
            "UPDATE notificacao SET reservada_ate = now() - interval '1 second' WHERE id = %s",
            (notification.id,),
        )
    [stuck] = repo.listar_pendentes()
    assert (stuck.id, stuck.assunto) == (notification.id, "")
