import smtplib
from email.message import EmailMessage

from manutencao.aplicacao.interface_notificador import Notificador
from manutencao.dominio.notificacao import Notificacao


class SmtpNotificador(Notificador):
    """Sends notifications by e-mail through an SMTP server (RF08).

    Locally this is Mailpit (no login, port 1025). A real provider such as
    Gmail also needs `usuario` and `senha`; then the connection uses TLS.
    """

    def __init__(
        self,
        host: str,
        porta: int,
        remetente: str,
        usuario: str | None = None,
        senha: str | None = None,
    ) -> None:
        self.host = host
        self.porta = porta
        self.remetente = remetente
        self.usuario = usuario
        self.senha = senha

    def enviar(self, notificacao: Notificacao) -> None:
        mensagem = EmailMessage()
        mensagem["From"] = self.remetente
        mensagem["To"] = notificacao.destinatario
        mensagem["Subject"] = notificacao.assunto
        mensagem.set_content(notificacao.mensagem)

        # Any failure (server down, refused login, timeout) is an OSError,
        # which the service turns into a retry later (ASR03).
        with smtplib.SMTP(self.host, self.porta, timeout=10) as servidor:
            if self.usuario:
                servidor.starttls()
                servidor.login(self.usuario, self.senha or "")
            servidor.send_message(mensagem)
