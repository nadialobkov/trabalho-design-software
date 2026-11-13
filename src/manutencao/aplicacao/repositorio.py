from abc import ABC, abstractmethod

from manutencao.aplicacao.filtros import FiltrosChamado
from manutencao.dominio.chamado import Chamado
from manutencao.dominio.departamento import Departamento
from manutencao.dominio.equipamento import Equipamento
from manutencao.dominio.notificacao import Notificacao
from manutencao.dominio.registro_auditoria import RegistroAuditoria
from manutencao.dominio.usuario import Usuario


class ManutencaoRepositorio(ABC):
    @abstractmethod
    def buscar_chamado(self, chamado_id: int) -> Chamado | None:
        ...

    @abstractmethod
    def listar_chamados(self, filtros: FiltrosChamado) -> list[Chamado]:
        ...

    @abstractmethod
    def salvar_chamado(
        self,
        chamado: Chamado,
        auditoria: RegistroAuditoria,
        notificacao: Notificacao | None = None,
    ) -> None:
        ...

    @abstractmethod
    def buscar_equipamento(self, equipamento_id: int) -> Equipamento | None:
        ...

    @abstractmethod
    def historico_equipamento(self, equipamento_id: int) -> list[Chamado]:
        ...

    @abstractmethod
    def buscar_usuario(self, usuario_id: int) -> Usuario | None:
        ...

    @abstractmethod
    def buscar_departamento(self, departamento_id: int) -> Departamento | None:
        ...

    @abstractmethod
    def listar_auditoria(self, chamado_id: int) -> list[RegistroAuditoria]:
        ...

    @abstractmethod
    def listar_pendentes(self) -> list[Notificacao]:
        ...

    @abstractmethod
    def atualizar_notificacao(self, notificacao: Notificacao) -> None:
        ...
