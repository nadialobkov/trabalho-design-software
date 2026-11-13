import socket
from datetime import date, datetime
from email.message import EmailMessage

import pytest

from manutencao.dominio.chamado import Chamado
from manutencao.dominio.notificacao import Notificacao
from manutencao.infraestrutura import notificador_smtp
from manutencao.infraestrutura.notificador_smtp import SmtpNotificador
from manutencao.infraestrutura.repositorio_em_memoria import RepositorioEmMemoria


@pytest.fixture
def notification() -> Notificacao:
    repo = RepositorioEmMemoria.com_dados_de_exemplo()
    ticket = Chamado.abrir(
        repo.buscar_equipamento(12), repo.buscar_usuario(1), "Will not turn on",
        date(2026, 11, 10), "", datetime(2026, 11, 13, 10, 30),
    )
    return Notificacao(ticket, "ana@example.com", "Chamado #1 registrado", "Seu chamado #1 ...")


class FakeSMTP:
    """Stands in for smtplib.SMTP and records what it was asked to do."""

    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.address = (host, port)
        self.calls: list[str] = []
        self.sent: list[EmailMessage] = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *args: object) -> None:
        self.calls.append("quit")

    def starttls(self) -> None:
        self.calls.append("starttls")

    def login(self, user: str, password: str) -> None:
        self.calls.append(f"login {user}")

    def send_message(self, message: EmailMessage) -> None:
        self.sent.append(message)


@pytest.mark.parametrize("user", [None, "me@example.com"])
def test_sends_email_with_notification_fields(
    monkeypatch: pytest.MonkeyPatch, notification: Notificacao, user: str | None,
) -> None:
    FakeSMTP.instances = []
    monkeypatch.setattr(notificador_smtp.smtplib, "SMTP", FakeSMTP)
    notifier = SmtpNotificador("localhost", 1025, "manutencao@example.com", user, "secret")

    notifier.enviar(notification)

    [server] = FakeSMTP.instances
    assert server.address == ("localhost", 1025)
    [message] = server.sent
    assert message["From"] == "manutencao@example.com"
    assert message["To"] == "ana@example.com"
    assert message["Subject"] == "Chamado #1 registrado"
    assert message.get_content().strip() == "Seu chamado #1 ..."
    # Login (with TLS) only when a user is configured, as Mailpit needs none.
    expected = ["starttls", f"login {user}", "quit"] if user else ["quit"]
    assert server.calls == expected


def test_server_down_raises_oserror(notification: Notificacao) -> None:
    # Get a free port and close it, so nothing is listening there.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    notifier = SmtpNotificador("127.0.0.1", port, "manutencao@example.com")

    with pytest.raises(OSError):
        notifier.enviar(notification)
