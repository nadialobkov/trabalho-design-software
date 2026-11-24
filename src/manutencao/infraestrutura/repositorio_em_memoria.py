from datetime import date, datetime

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

    def listar_usuarios(self) -> list[Usuario]:
        return [self._usuarios[id] for id in sorted(self._usuarios)]

    def salvar_notificacao(self, notificacao: Notificacao) -> None:
        if notificacao.id is None:
            notificacao.id = self._proxima_notificacao_id
            self._proxima_notificacao_id += 1
        self._notificacoes[notificacao.id] = notificacao

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
        informatica = Departamento(3, "Informática")
        mecanica = Departamento(4, "Mecânica")
        for departamento in (eletrica, optica, informatica, mecanica):
            repo.adicionar_departamento(departamento)

        for usuario in (
            Usuario(1, "Ana", "ana@example.com", Usuario.Papel.SOLICITANTE),
            Usuario(2, "Bruno", "bruno@example.com", Usuario.Papel.TECNICO, eletrica),
            Usuario(3, "Carla", "carla@example.com", Usuario.Papel.COORDENADOR, eletrica),
            Usuario(4, "Davi", "davi@example.com", Usuario.Papel.TECNICO, optica),
            Usuario(5, "Eva", "eva@example.com", Usuario.Papel.SOLICITANTE),
            Usuario(6, "Fábio", "fabio@example.com", Usuario.Papel.TECNICO, eletrica),
            Usuario(7, "Helena", "helena@example.com", Usuario.Papel.COORDENADOR, optica),
            Usuario(8, "Igor", "igor@example.com", Usuario.Papel.TECNICO, informatica),
            Usuario(9, "Juliana", "juliana@example.com", Usuario.Papel.COORDENADOR, informatica),
            Usuario(10, "Lucas", "lucas@example.com", Usuario.Papel.TECNICO, mecanica),
            Usuario(11, "Marina", "marina@example.com", Usuario.Papel.COORDENADOR, mecanica),
            Usuario(12, "Paulo", "paulo@example.com", Usuario.Papel.SOLICITANTE),
        ):
            repo.adicionar_usuario(usuario)

        for equipamento in (
            Equipamento(10, "Osciloscópio", "Laboratório de Física", eletrica),
            Equipamento(11, "Fonte de bancada", "Laboratório de Física", eletrica),
            Equipamento(12, "Microscópio", "Laboratório de Biologia", optica),
            Equipamento(13, "Projetor", "Sala Multimídia", informatica),
            Equipamento(14, "Computador Lenovo", "Laboratório de Redes", informatica),
            Equipamento(15, "Servidor Dell", "Centro de Dados", informatica),
            Equipamento(16, "Centrífuga", "Laboratório de Química", mecanica),
            Equipamento(17, "Balança analítica", "Laboratório de Química", mecanica),
            Equipamento(18, "Espectrofotômetro", "Laboratório de Química", optica),
            Equipamento(19, "Impressora 3D", "Laboratório Maker", mecanica),
            Equipamento(20, "Bancada elétrica", "Laboratório de Eletrônica", eletrica),
            Equipamento(21, "Gerador de sinais", "Laboratório de Telecomunicações", eletrica),
        ):
            repo.adicionar_equipamento(equipamento)

        exemplos = (
            (10, 1, "Osciloscópio apresenta ruído na tela", date(2026, 11, 20),
             Chamado.Prioridade.ALTA, Chamado.Estado.ATRIBUIDO, (2,)),
            (13, 5, "Projetor não liga durante a aula", date(2026, 11, 21),
             Chamado.Prioridade.MEDIA, Chamado.Estado.ABERTO,()),
            (12, 1, "A lente não fica estabilizada", date(2026, 11, 18),
             Chamado.Prioridade.URGENTE, Chamado.Estado.EM_ATENDIMENTO, (4,)),
            (14, 12, "Computador reinicia sozinho", date(2026, 11, 17),
             Chamado.Prioridade.BAIXA, Chamado.Estado.CONCLUIDO, (8,)),
            (16, 5, "Centrífuga vibra excessivamente", date(2026, 11, 16),
             Chamado.Prioridade.ALTA, Chamado.Estado.ABERTO,()),
            (20, 12, "Bancada apresenta queda de tensão", date(2026, 11, 15),
             Chamado.Prioridade.URGENTE, Chamado.Estado.ATRIBUIDO, (6,)),
        )
        for numero, (equipamento_id, solicitante_id, descricao, ocorrencia,
                     prioridade, estado, tecnicos_ids) in enumerate(exemplos, start=1):
            equipamento = repo.buscar_equipamento(equipamento_id)
            solicitante = repo.buscar_usuario(solicitante_id)
            chamado = Chamado.abrir(
                equipamento,
                solicitante,
                descricao,
                ocorrencia,
                "Chamado fictício para demonstração.",
                datetime(2026, 11, 22, 9, numero * 10),
            )
            chamado.prioridade = prioridade
            chamado.estado = estado
            chamado.tecnicos = [
                repo.buscar_usuario(tecnico_id) for tecnico_id in tecnicos_ids
            ]
            auditoria = RegistroAuditoria(
                chamado,
                solicitante,
                chamado.data_abertura,
                "estado",
                None,
                str(chamado.estado),
            )
            repo.salvar_chamado(chamado, auditoria)
        return repo
