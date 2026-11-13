from dataclasses import dataclass
from enum import StrEnum

from manutencao.dominio.departamento import Departamento


@dataclass
class Usuario:
    class Papel(StrEnum):
        SOLICITANTE = "SOLICITANTE"
        TECNICO = "TECNICO"
        COORDENADOR = "COORDENADOR"

    id: int
    nome: str
    email: str
    papel: Papel
    departamento: Departamento | None = None

    def e_tecnico(self) -> bool:
        return self.papel == self.Papel.TECNICO

    def e_coordenador_de(self, departamento: Departamento) -> bool:
        return (
            self.papel == self.Papel.COORDENADOR
            and self.departamento is not None
            and self.departamento.id == departamento.id
        )
