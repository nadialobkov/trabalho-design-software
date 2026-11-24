from datetime import date, datetime

import pytest

from manutencao.dominio.chamado import Chamado
from manutencao.dominio.departamento import Departamento
from manutencao.dominio.equipamento import Equipamento
from manutencao.dominio.notificacao import Notificacao
from manutencao.dominio.usuario import Usuario


@pytest.fixture
def equipment() -> Equipamento:
    return Equipamento(12, "Microscope", "Biology lab", Departamento(2, "Optics"))


@pytest.fixture
def requester() -> Usuario:
    return Usuario(1, "Ana", "ana@example.com", Usuario.Papel.SOLICITANTE)


@pytest.fixture
def ticket(equipment: Equipamento, requester: Usuario) -> Chamado:
    return Chamado.abrir(
        equipment,
        requester,
        "The microscope will not turn on",
        date(2026, 11, 10),
        "Power cable checked",
        datetime(2026, 11, 13, 10, 30),
    )


def test_open_ticket_uses_equipment_department_and_given_time(
    ticket: Chamado, equipment: Equipamento, requester: Usuario
) -> None:
    assert ticket.estado == Chamado.Estado.ABERTO
    assert ticket.data_abertura == datetime(2026, 11, 13, 10, 30)
    assert ticket.departamento is equipment.departamento
    assert ticket.equipamento is equipment
    assert ticket.solicitante is requester
    assert ticket.descricao_problema == "The microscope will not turn on"
    assert ticket.data_ocorrencia == date(2026, 11, 10)
    assert ticket.informacoes_adicionais == "Power cable checked"
    assert ticket.prioridade is None
    assert ticket.id is None
    assert ticket.tecnicos == []
    assert ticket.diagnostico is None


@pytest.mark.parametrize("description", ["", "   ", "\t\n"])
def test_open_ticket_rejects_blank_description(
    equipment: Equipamento, requester: Usuario, description: str
) -> None:
    with pytest.raises(ValueError):
        Chamado.abrir(
            equipment,
            requester,
            description,
            date(2026, 11, 10),
            "",
            datetime(2026, 11, 13, 10, 30),
        )


def test_failed_notification_stays_pending_and_can_be_sent(ticket: Chamado) -> None:
    notification = Notificacao(ticket, ticket.solicitante.email)

    notification.registrar_falha()

    assert notification.tentativas == 1
    assert notification.status == Notificacao.Status.PENDENTE

    notification.marcar_enviada()

    assert notification.status == Notificacao.Status.ENVIADA
    assert notification.tentativas == 1


def test_notification_stays_pending_after_many_failures(ticket: Chamado) -> None:
    notification = Notificacao(ticket, ticket.solicitante.email)

    for _ in range(Notificacao.TENTATIVAS_POR_RODADA * 3):
        notification.registrar_falha()

    assert notification.status == Notificacao.Status.PENDENTE
    assert notification.tentativas == Notificacao.TENTATIVAS_POR_RODADA * 3


@pytest.mark.parametrize("role", list(Usuario.Papel))
def test_user_is_technician_only_with_technician_role(role: Usuario.Papel) -> None:
    user = Usuario(2, "Bruno", "bruno@example.com", role)

    assert user.e_tecnico() == (role == Usuario.Papel.TECNICO)


def test_coordinator_matches_department_by_id() -> None:
    department = Departamento(1, "Electrical")
    coordinator = Usuario(3, "Carla", "carla@example.com", Usuario.Papel.COORDENADOR, department)

    assert coordinator.e_coordenador_de(Departamento(1, "Same department"))
    assert not coordinator.e_coordenador_de(Departamento(2, "Optics"))

    coordinator.departamento = None

    assert not coordinator.e_coordenador_de(department)


@pytest.mark.parametrize("role", [Usuario.Papel.SOLICITANTE, Usuario.Papel.TECNICO])
def test_other_roles_are_not_coordinators(role: Usuario.Papel) -> None:
    department = Departamento(1, "Electrical")
    user = Usuario(2, "Bruno", "bruno@example.com", role, department)

    assert not user.e_coordenador_de(department)
