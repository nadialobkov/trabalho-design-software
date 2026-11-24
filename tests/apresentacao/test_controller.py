from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from manutencao.aplicacao.erros import AcessoNegado
from manutencao.aplicacao.servico import ManutencaoService
from manutencao.aapresentacao.controller import criar_app
from manutencao.infraestrutura.notificador_fake import NotificadorFake
from manutencao.infraestrutura.repositorio_em_memoria import RepositorioEmMemoria


BODY = {
    "equipamento_id": 12,
    "descricao_problema": "O microscópio não liga",
    "data_ocorrencia": "2026-11-10",
}


@pytest.fixture
def service() -> ManutencaoService:
    return ManutencaoService(
        RepositorioEmMemoria.com_dados_de_exemplo(com_chamados=False), NotificadorFake()
    )


@pytest.fixture
def client(service: ManutencaoService) -> Iterator[TestClient]:
    with TestClient(criar_app(service)) as client:
        yield client


def test_create_ticket_returns_201(client: TestClient) -> None:
    response = client.post("/chamados", headers={"X-Usuario-Id": "1"}, json=BODY)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["equipamento_id"] == 12
    assert body["estado"] == "ABERTO"
    assert datetime.fromisoformat(body["data_abertura"])


def test_missing_equipment_returns_404(client: TestClient) -> None:
    response = client.post(
        "/chamados", headers={"X-Usuario-Id": "1"},
        json={**BODY, "equipamento_id": 999},
    )

    assert response.status_code == 404
    assert response.json() == {"erro": "Equipment not found."}


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_missing_user_header_returns_403(client: TestClient, method: str) -> None:
    response = client.request(
        method, "/chamados", **({"json": BODY} if method == "POST" else {})
    )

    assert response.status_code == 403
    assert response.json() == {"erro": "User header is required."}


def test_requester_lists_only_own_open_tickets(client: TestClient) -> None:
    created = client.post("/chamados", headers={"X-Usuario-Id": "1"}, json=BODY)
    assert created.status_code == 201
    other = client.post("/chamados", headers={"X-Usuario-Id": "5"}, json=BODY)
    assert other.status_code == 201

    response = client.get("/chamados?estado=ABERTO", headers={"X-Usuario-Id": "1"})

    assert response.status_code == 200
    assert response.json() == [{
        "id": created.json()["id"],
        "equipamento_id": 12,
        "equipamento_nome": "Microscópio",
        "solicitante_id": 1,
        "departamento_id": 2,
        "prioridade": None,
        "estado": "ABERTO",
        "tecnicos_ids": [],
        "descricao_problema": BODY["descricao_problema"],
        "data_ocorrencia": BODY["data_ocorrencia"],
        "data_abertura": created.json()["data_abertura"],
        "data_inicio_atendimento": None,
        "diagnostico": None,
        "descricao_intervencao": None,
        "data_conclusao": None,
    }]


def test_coordinator_lists_only_department_tickets(client: TestClient) -> None:
    for equipment_id in (10, 11, 12):
        response = client.post(
            "/chamados", headers={"X-Usuario-Id": "1"},
            json={**BODY, "equipamento_id": equipment_id},
        )
        assert response.status_code == 201

    response = client.get("/chamados", headers={"X-Usuario-Id": "3"})

    assert response.status_code == 200
    assert [ticket["equipamento_id"] for ticket in response.json()] == [10, 11]
    assert all(ticket["departamento_id"] == 1 for ticket in response.json())


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_unknown_user_returns_403(client: TestClient, method: str) -> None:
    response = client.request(
        method, "/chamados", headers={"X-Usuario-Id": "999"},
        **({"json": BODY} if method == "POST" else {}),
    )

    assert response.status_code == 403
    assert response.json() == {"erro": "User not found."}


def test_blank_description_returns_domain_error(client: TestClient) -> None:
    response = client.post(
        "/chamados", headers={"X-Usuario-Id": "1"},
        json={**BODY, "descricao_problema": "   "},
    )

    assert response.status_code == 422
    assert response.json() == {"erro": "Problem description must not be empty."}


@pytest.mark.parametrize("body", [
    {}, {**BODY, "equipamento_id": "invalid"}, {**BODY, "data_ocorrencia": "invalid"},
])
def test_invalid_request_returns_422(client: TestClient, body: dict) -> None:
    response = client.post("/chamados", headers={"X-Usuario-Id": "1"}, json=body)

    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.parametrize(("query", "expected_status"), [
    ("estado=ABERTO", 200),
    ("estado=INVALID", 422),
    ("prioridade=ALTA", 200),
    ("prioridade=INVALID", 422),
])
def test_nested_enum_query_validation(
    client: TestClient, query: str, expected_status: int,
) -> None:
    response = client.get(f"/chamados?{query}", headers={"X-Usuario-Id": "1"})

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json() == []


def test_access_denied_returns_403(
    client: TestClient, service: ManutencaoService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_access(*args, **kwargs):
        raise AcessoNegado("Action not allowed.")

    monkeypatch.setattr(service, "consultar_chamados", deny_access)

    response = client.get("/chamados", headers={"X-Usuario-Id": "1"})

    assert response.status_code == 403
    assert response.json() == {"erro": "Action not allowed."}


def test_coordinator_assigns_technician_and_priority(client: TestClient) -> None:
    created = client.post(
        "/chamados",
        headers={"X-Usuario-Id": "1"},
        json={**BODY, "equipamento_id": 10},
    )

    assigned = client.patch(
        f"/chamados/{created.json()['id']}/atribuicao",
        headers={"X-Usuario-Id": "3"},
        json={"tecnicos_ids": [2]},
    )
    prioritized = client.patch(
        f"/chamados/{created.json()['id']}/prioridade",
        headers={"X-Usuario-Id": "3"},
        json={"prioridade": "URGENTE"},
    )

    assert assigned.status_code == 200
    assert assigned.json()["estado"] == "ATRIBUIDO"
    assert assigned.json()["tecnicos_ids"] == [2]
    assert prioritized.status_code == 200
    assert prioritized.json()["prioridade"] == "URGENTE"


def test_technician_only_lists_assigned_tickets(client: TestClient) -> None:
    first = client.post(
        "/chamados",
        headers={"X-Usuario-Id": "1"},
        json={**BODY, "equipamento_id": 10},
    )
    second = client.post(
        "/chamados",
        headers={"X-Usuario-Id": "1"},
        json={**BODY, "equipamento_id": 11},
    )
    client.patch(
        f"/chamados/{first.json()['id']}/atribuicao",
        headers={"X-Usuario-Id": "3"},
        json={"tecnicos_ids": [2]},
    )

    response = client.get(
        "/chamados",
        headers={"X-Usuario-Id": "2"},
    )

    assert response.status_code == 200
    assert [ticket["id"] for ticket in response.json()] == [first.json()["id"]]
    assert second.json()["id"] not in [ticket["id"] for ticket in response.json()]
