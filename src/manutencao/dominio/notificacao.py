from dataclasses import dataclass
from typing import ClassVar
from enum import StrEnum

from manutencao.dominio.chamado import Chamado


@dataclass
class Notificacao:
    class Status(StrEnum):
        PENDENTE = "PENDENTE"
        ENVIADA = "ENVIADA"
        FALHOU = "FALHOU"

    # Limite de falhas de envio antes de encerrar as tentativas (ASR03).
    MAX_TENTATIVAS: ClassVar[int] = 5

    chamado: Chamado
    destinatario: str
    assunto: str = ""
    mensagem: str = ""
    status: Status = Status.PENDENTE
    tentativas: int = 0
    id: int | None = None

    def marcar_enviada(self) -> None:
        self.status = self.Status.ENVIADA

    def registrar_falha(self) -> None:
        self.tentativas += 1
        if self.tentativas >= self.MAX_TENTATIVAS:
            self.status = self.Status.FALHOU
        else:
            self.status = self.Status.PENDENTE
