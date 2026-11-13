from dataclasses import dataclass

from manutencao.dominio.departamento import Departamento


@dataclass
class Equipamento:
    id: int
    nome: str
    laboratorio: str
    departamento: Departamento
