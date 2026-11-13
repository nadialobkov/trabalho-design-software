import time

from fastapi.testclient import TestClient

from manutencao.aapresentacao.agendador import AgendadorNotificacoes
from manutencao.aapresentacao.controller import criar_app
from manutencao.aplicacao.servico import ManutencaoService
from manutencao.infraestrutura.notificador_fake import NotificadorFake
from manutencao.infraestrutura.repositorio_em_memoria import RepositorioEmMemoria


BODY = {
    "equipamento_id": 12,
    "descricao_problema": "O microscópio não liga",
    "data_ocorrencia": "2026-11-10",
}


def test_scheduler_sends_pending_email_in_background() -> None:
    notifier = NotificadorFake()
    service = ManutencaoService(RepositorioEmMemoria.com_dados_de_exemplo(), notifier)
    scheduler = AgendadorNotificacoes(service, intervalo_segundos=0.01)

    with TestClient(criar_app(service, scheduler)) as client:
        response = client.post("/chamados", headers={"X-Usuario-Id": "1"}, json=BODY)
        assert response.status_code == 201
        deadline = time.monotonic() + 2
        while not notifier.enviadas and time.monotonic() < deadline:
            time.sleep(0.01)

    assert len(notifier.enviadas) == 1
    assert notifier.enviadas[0].chamado.id == response.json()["id"]


class FlakyService:
    """Fails on the first round, then counts the rounds."""

    def __init__(self) -> None:
        self.rounds = 0

    def reenviar_notificacoes(self) -> None:
        self.rounds += 1
        if self.rounds == 1:
            raise RuntimeError("unexpected")


def test_scheduler_keeps_running_after_a_failed_round() -> None:
    service = FlakyService()
    scheduler = AgendadorNotificacoes(service, intervalo_segundos=0.01)

    with TestClient(criar_app(service, scheduler)):
        deadline = time.monotonic() + 2
        while service.rounds < 2 and time.monotonic() < deadline:
            time.sleep(0.01)

    assert service.rounds >= 2
