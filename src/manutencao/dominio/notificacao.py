from dataclasses import dataclass
from typing import ClassVar
from enum import StrEnum

from manutencao.dominio.chamado import Chamado


@dataclass
class Notificacao:
    class Status(StrEnum):
        PENDENTE = "PENDENTE"
        ENVIADA = "ENVIADA"

    # Envios seguidos em cada rodada do agendador. Se todos falharem, a
    # notificação continua PENDENTE e a próxima rodada tenta de novo (ASR03).
    TENTATIVAS_POR_RODADA: ClassVar[int] = 5

    chamado: Chamado
    destinatario: str
    assunto: str = ""
    mensagem: str = ""
    status: Status = Status.PENDENTE
    # Total de falhas desde a criação, somando todas as rodadas.
    tentativas: int = 0
    id: int | None = None

    def marcar_enviada(self) -> None:
        self.status = self.Status.ENVIADA

    def registrar_falha(self) -> None:
        # Uma falha nunca encerra o envio: a notificação espera o serviço voltar.
        self.tentativas += 1
        self.status = self.Status.PENDENTE
