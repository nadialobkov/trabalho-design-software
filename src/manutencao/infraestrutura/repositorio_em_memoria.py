from manutencao.aplicacao.filtros import FiltrosChamado
from manutencao.aplicacao.interface_repositorio import ManutencaoRepositorio
from manutencao.dominio.chamado import Chamado
from manutencao.dominio.departamento import Departamento
from manutencao.dominio.equipamento import Equipamento
from manutencao.dominio.notificacao import Notificacao
from manutencao.dominio.registro_auditoria import RegistroAuditoria
from manutencao.dominio.usuario import Usuario


class RepositorioEmMemoria(ManutencaoRepositorio):
    def __init__(self) -> None:
        self._chamados: dict[int, Chamado] = {}
        self._auditorias: list[RegistroAuditoria] = []
        self._notificacoes: dict[int, Notificacao] = {}
        self._equipamentos: dict[int, Equipamento] = {}
        self._usuarios: dict[int, Usuario] = {}
        self._departamentos: dict[int, Departamento] = {}
        self._proximo_chamado_id = 1
        self._proxima_auditoria_id = 1
        self._proxima_notificacao_id = 1

    def buscar_chamado(self, chamado_id: int) -> Chamado | None:
        return self._chamados.get(chamado_id)

    def listar_chamados(self, filtros: FiltrosChamado) -> list[Chamado]:
        resultado = []
        for chamado_id in sorted(self._chamados):
            chamado = self._chamados[chamado_id]
            if (
                filtros.equipamento_id is not None
                and chamado.equipamento.id != filtros.equipamento_id
            ):
                continue
            if filtros.prioridade is not None and chamado.prioridade != filtros.prioridade:
                continue
            if filtros.tecnico_id is not None and not any(
                tecnico.id == filtros.tecnico_id for tecnico in chamado.tecnicos
            ):
                continue
            if filtros.estado is not None and chamado.estado != filtros.estado:
                continue
            if (
                filtros.aberto_de is not None
                and chamado.data_abertura.date() < filtros.aberto_de
            ):
                continue
            if (
                filtros.aberto_ate is not None
                and chamado.data_abertura.date() > filtros.aberto_ate
            ):
                continue
            if (
                filtros.solicitante_id is not None
                and chamado.solicitante.id != filtros.solicitante_id
            ):
                continue
            if (
                filtros.departamento_id is not None
                and chamado.departamento.id != filtros.departamento_id
            ):
                continue
            resultado.append(chamado)
        return resultado

    def salvar_chamado(
        self,
        chamado: Chamado,
        auditoria: RegistroAuditoria,
        notificacao: Notificacao | None = None,
    ) -> None:
        if chamado.id is None:
            chamado.id = self._proximo_chamado_id
            self._proximo_chamado_id += 1
        self._chamados[chamado.id] = chamado

        if auditoria.id is None:
            auditoria.id = self._proxima_auditoria_id
            self._proxima_auditoria_id += 1
        self._auditorias.append(auditoria)

        if notificacao is not None:
            if notificacao.id is None:
                notificacao.id = self._proxima_notificacao_id
                self._proxima_notificacao_id += 1
            self._notificacoes[notificacao.id] = notificacao

    def buscar_equipamento(self, equipamento_id: int) -> Equipamento | None:
        return self._equipamentos.get(equipamento_id)

    def historico_equipamento(self, equipamento_id: int) -> list[Chamado]:
        return self.listar_chamados(FiltrosChamado(equipamento_id=equipamento_id))

    def buscar_usuario(self, usuario_id: int) -> Usuario | None:
        return self._usuarios.get(usuario_id)

    def buscar_departamento(self, departamento_id: int) -> Departamento | None:
        return self._departamentos.get(departamento_id)

    def listar_auditoria(self, chamado_id: int) -> list[RegistroAuditoria]:
        return [
            registro for registro in self._auditorias
            if registro.chamado.id == chamado_id
        ]

    def listar_pendentes(self) -> list[Notificacao]:
        # Copia os valores porque uma requisição pode adicionar uma notificação durante a leitura pelo agendador.
        return [
            notificacao
            for notificacao in list(self._notificacoes.values())
            if notificacao.status == Notificacao.Status.PENDENTE
        ]

    def atualizar_notificacao(self, notificacao: Notificacao) -> None:
        if notificacao.id is not None:
            self._notificacoes[notificacao.id] = notificacao

    def adicionar_departamento(self, d: Departamento) -> None:
        self._departamentos[d.id] = d

    def adicionar_usuario(self, u: Usuario) -> None:
        self._usuarios[u.id] = u

    def adicionar_equipamento(self, e: Equipamento) -> None:
        self._equipamentos[e.id] = e

    @classmethod
    def com_dados_de_exemplo(cls) -> "RepositorioEmMemoria":
        repo = cls()
        eletrica = Departamento(1, "Elétrica")
        optica = Departamento(2, "Óptica")
        for departamento in (eletrica, optica):
            repo.adicionar_departamento(departamento)

        for usuario in (
            Usuario(1, "Ana", "ana@example.com", Usuario.Papel.SOLICITANTE),
            Usuario(2, "Bruno", "bruno@example.com", Usuario.Papel.TECNICO, eletrica),
            Usuario(3, "Carla", "carla@example.com", Usuario.Papel.COORDENADOR, eletrica),
            Usuario(4, "Davi", "davi@example.com", Usuario.Papel.TECNICO, optica),
            Usuario(5, "Eva", "eva@example.com", Usuario.Papel.SOLICITANTE),
        ):
            repo.adicionar_usuario(usuario)

        for equipamento in (
            Equipamento(10, "Osciloscópio", "Laboratório de Física", eletrica),
            Equipamento(11, "Fonte de bancada", "Laboratório de Física", eletrica),
            Equipamento(12, "Microscópio", "Laboratório de Biologia", optica),
        ):
            repo.adicionar_equipamento(equipamento)
        return repo
