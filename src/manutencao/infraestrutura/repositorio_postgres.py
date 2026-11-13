from typing import Any

import psycopg
from psycopg.rows import dict_row

from manutencao.aplicacao.filtros import FiltrosChamado
from manutencao.aplicacao.interface_repositorio import ManutencaoRepositorio
from manutencao.dominio.chamado import Chamado
from manutencao.dominio.departamento import Departamento
from manutencao.dominio.equipamento import Equipamento
from manutencao.dominio.notificacao import Notificacao
from manutencao.dominio.registro_auditoria import RegistroAuditoria
from manutencao.dominio.usuario import Usuario


Cursor = psycopg.Cursor[dict[str, Any]]


class PostgresManutencaoRepositorio(ManutencaoRepositorio):
    """Stores everything in PostgreSQL. Tables are in banco/schema.sql.

    Each method opens its own connection, so it is safe to use from the
    request threads and from the scheduler thread at the same time.
    """

    # How long a notification stays reserved for the instance sending it.
    # Much longer than one send (SMTP timeout is 10 s).
    RESERVA = "5 minutes"

    def __init__(self, url: str) -> None:
        self.url = url

    def _conectar(self) -> psycopg.Connection[dict[str, Any]]:
        # "with" on the connection commits on success and rolls back on error.
        return psycopg.connect(self.url, row_factory=dict_row)

    # --- tickets ---------------------------------------------------------

    def buscar_chamado(self, chamado_id: int) -> Chamado | None:
        with self._conectar() as conn, conn.cursor() as cur:
            return self._carregar_chamado(cur, chamado_id)

    def listar_chamados(self, filtros: FiltrosChamado) -> list[Chamado]:
        condicoes: list[str] = []
        valores: list[Any] = []
        for coluna, valor in (
            ("equipamento_id", filtros.equipamento_id),
            ("prioridade", filtros.prioridade),
            ("estado", filtros.estado),
            ("solicitante_id", filtros.solicitante_id),
            ("departamento_id", filtros.departamento_id),
        ):
            if valor is not None:
                condicoes.append(f"{coluna} = %s")
                valores.append(str(valor) if coluna in ("prioridade", "estado") else valor)
        if filtros.tecnico_id is not None:
            condicoes.append(
                "EXISTS (SELECT 1 FROM chamado_tecnico ct"
                " WHERE ct.chamado_id = chamado.id AND ct.tecnico_id = %s)"
            )
            valores.append(filtros.tecnico_id)
        if filtros.aberto_de is not None:
            condicoes.append("data_abertura::date >= %s")
            valores.append(filtros.aberto_de)
        if filtros.aberto_ate is not None:
            condicoes.append("data_abertura::date <= %s")
            valores.append(filtros.aberto_ate)

        sql = "SELECT * FROM chamado"
        if condicoes:
            sql += " WHERE " + " AND ".join(condicoes)
        sql += " ORDER BY id"

        with self._conectar() as conn, conn.cursor() as cur:
            cur.execute(sql, valores)
            linhas = cur.fetchall()
            return [self._montar_chamado(cur, linha) for linha in linhas]

    def salvar_chamado(
        self,
        chamado: Chamado,
        auditoria: RegistroAuditoria,
        notificacao: Notificacao | None = None,
    ) -> None:
        # One transaction: ticket, audit and notification are saved together
        # or not at all (ASR01, ASR03).
        with self._conectar() as conn, conn.cursor() as cur:
            valores = {
                "equipamento_id": chamado.equipamento.id,
                "solicitante_id": chamado.solicitante.id,
                "departamento_id": chamado.departamento.id,
                "descricao_problema": chamado.descricao_problema,
                "informacoes_adicionais": chamado.informacoes_adicionais,
                "data_ocorrencia": chamado.data_ocorrencia,
                "data_abertura": chamado.data_abertura,
                "estado": str(chamado.estado),
                "prioridade": str(chamado.prioridade) if chamado.prioridade else None,
                "data_inicio_atendimento": chamado.data_inicio_atendimento,
                "diagnostico": chamado.diagnostico,
                "descricao_intervencao": chamado.descricao_intervencao,
                "concluido_por_id": chamado.concluido_por.id if chamado.concluido_por else None,
                "data_conclusao": chamado.data_conclusao,
            }
            colunas = list(valores)
            if chamado.id is None:
                cur.execute(
                    f"INSERT INTO chamado ({', '.join(colunas)})"
                    f" VALUES ({', '.join(f'%({c})s' for c in colunas)}) RETURNING id",
                    valores,
                )
                chamado.id = cur.fetchone()["id"]
            else:
                cur.execute(
                    f"UPDATE chamado SET {', '.join(f'{c} = %({c})s' for c in colunas)}"
                    " WHERE id = %(id)s",
                    {**valores, "id": chamado.id},
                )

            # Rewrite the technician list so it matches chamado.tecnicos.
            cur.execute("DELETE FROM chamado_tecnico WHERE chamado_id = %s", (chamado.id,))
            for tecnico in chamado.tecnicos:
                cur.execute(
                    "INSERT INTO chamado_tecnico (chamado_id, tecnico_id) VALUES (%s, %s)",
                    (chamado.id, tecnico.id),
                )

            cur.execute(
                "INSERT INTO registro_auditoria"
                " (chamado_id, autor_id, data_hora, campo, valor_anterior, valor_novo, observacao)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (
                    chamado.id, auditoria.autor.id, auditoria.data_hora, auditoria.campo,
                    auditoria.valor_anterior, auditoria.valor_novo, auditoria.observacao,
                ),
            )
            auditoria.id = cur.fetchone()["id"]

            if notificacao is not None:
                if notificacao.id is None:
                    # Without text yet, it starts reserved, so the scheduler does
                    # not take it before atualizar_notificacao() writes the text.
                    cur.execute(
                        "INSERT INTO notificacao (chamado_id, destinatario, assunto,"
                        " mensagem, status, tentativas, reservada_ate)"
                        " VALUES (%s, %s, %s, %s, %s, %s,"
                        f" CASE WHEN %s = '' THEN now() + interval '{self.RESERVA}' END)"
                        " RETURNING id",
                        (
                            chamado.id, notificacao.destinatario, notificacao.assunto,
                            notificacao.mensagem, str(notificacao.status),
                            notificacao.tentativas, notificacao.assunto,
                        ),
                    )
                    notificacao.id = cur.fetchone()["id"]
                else:
                    self._atualizar_notificacao(cur, notificacao)

    def historico_equipamento(self, equipamento_id: int) -> list[Chamado]:
        return self.listar_chamados(FiltrosChamado(equipamento_id=equipamento_id))

    # --- reference data --------------------------------------------------

    def buscar_equipamento(self, equipamento_id: int) -> Equipamento | None:
        with self._conectar() as conn, conn.cursor() as cur:
            return self._carregar_equipamento(cur, equipamento_id)

    def buscar_usuario(self, usuario_id: int) -> Usuario | None:
        with self._conectar() as conn, conn.cursor() as cur:
            return self._carregar_usuario(cur, usuario_id)

    def buscar_departamento(self, departamento_id: int) -> Departamento | None:
        with self._conectar() as conn, conn.cursor() as cur:
            return self._carregar_departamento(cur, departamento_id)

    # --- audit and notifications ----------------------------------------

    def listar_auditoria(self, chamado_id: int) -> list[RegistroAuditoria]:
        with self._conectar() as conn, conn.cursor() as cur:
            chamado = self._carregar_chamado(cur, chamado_id)
            if chamado is None:
                return []
            cur.execute(
                "SELECT * FROM registro_auditoria WHERE chamado_id = %s ORDER BY id",
                (chamado_id,),
            )
            return [
                RegistroAuditoria(
                    chamado=chamado,
                    autor=self._carregar_usuario(cur, linha["autor_id"]),
                    data_hora=linha["data_hora"],
                    campo=linha["campo"],
                    valor_anterior=linha["valor_anterior"],
                    valor_novo=linha["valor_novo"],
                    observacao=linha["observacao"],
                    id=linha["id"],
                )
                for linha in cur.fetchall()
            ]

    def listar_pendentes(self) -> list[Notificacao]:
        # Reserves the rows it returns, so two app instances on the same database
        # never send the same e-mail. SKIP LOCKED: rows another instance is
        # reserving right now are left out instead of waited for.
        # atualizar_notificacao() frees the row again.
        with self._conectar() as conn, conn.cursor() as cur:
            cur.execute(
                f"UPDATE notificacao SET reservada_ate = now() + interval '{self.RESERVA}'"
                " WHERE id IN ("
                "   SELECT id FROM notificacao WHERE status = 'PENDENTE'"
                "   AND (reservada_ate IS NULL OR reservada_ate < now())"
                "   ORDER BY id FOR UPDATE SKIP LOCKED"
                ") RETURNING *"
            )
            linhas = sorted(cur.fetchall(), key=lambda linha: linha["id"])
            return [
                Notificacao(
                    chamado=self._carregar_chamado(cur, linha["chamado_id"]),
                    destinatario=linha["destinatario"],
                    assunto=linha["assunto"],
                    mensagem=linha["mensagem"],
                    status=Notificacao.Status(linha["status"]),
                    tentativas=linha["tentativas"],
                    id=linha["id"],
                )
                for linha in linhas
            ]

    def atualizar_notificacao(self, notificacao: Notificacao) -> None:
        if notificacao.id is None:
            return
        with self._conectar() as conn, conn.cursor() as cur:
            self._atualizar_notificacao(cur, notificacao)

    # --- helpers: turn rows into domain objects --------------------------

    @staticmethod
    def _atualizar_notificacao(cur: Cursor, notificacao: Notificacao) -> None:
        cur.execute(
            "UPDATE notificacao SET assunto = %s, mensagem = %s, status = %s, tentativas = %s,"
            " reservada_ate = NULL"  # done with it: free it for the next round
            " WHERE id = %s",
            (
                notificacao.assunto, notificacao.mensagem, str(notificacao.status),
                notificacao.tentativas, notificacao.id,
            ),
        )

    def _carregar_departamento(self, cur: Cursor, departamento_id: int | None) -> Departamento | None:
        if departamento_id is None:
            return None
        cur.execute("SELECT * FROM departamento WHERE id = %s", (departamento_id,))
        linha = cur.fetchone()
        return Departamento(linha["id"], linha["nome"]) if linha else None

    def _carregar_usuario(self, cur: Cursor, usuario_id: int | None) -> Usuario | None:
        if usuario_id is None:
            return None
        cur.execute("SELECT * FROM usuario WHERE id = %s", (usuario_id,))
        linha = cur.fetchone()
        if linha is None:
            return None
        return Usuario(
            linha["id"], linha["nome"], linha["email"], Usuario.Papel(linha["papel"]),
            self._carregar_departamento(cur, linha["departamento_id"]),
        )

    def _carregar_equipamento(self, cur: Cursor, equipamento_id: int) -> Equipamento | None:
        cur.execute("SELECT * FROM equipamento WHERE id = %s", (equipamento_id,))
        linha = cur.fetchone()
        if linha is None:
            return None
        return Equipamento(
            linha["id"], linha["nome"], linha["laboratorio"],
            self._carregar_departamento(cur, linha["departamento_id"]),
        )

    def _carregar_chamado(self, cur: Cursor, chamado_id: int) -> Chamado | None:
        cur.execute("SELECT * FROM chamado WHERE id = %s", (chamado_id,))
        linha = cur.fetchone()
        return self._montar_chamado(cur, linha) if linha else None

    def _montar_chamado(self, cur: Cursor, linha: dict[str, Any]) -> Chamado:
        cur.execute(
            "SELECT tecnico_id FROM chamado_tecnico WHERE chamado_id = %s ORDER BY tecnico_id",
            (linha["id"],),
        )
        tecnico_ids = [t["tecnico_id"] for t in cur.fetchall()]
        return Chamado(
            equipamento=self._carregar_equipamento(cur, linha["equipamento_id"]),
            solicitante=self._carregar_usuario(cur, linha["solicitante_id"]),
            departamento=self._carregar_departamento(cur, linha["departamento_id"]),
            descricao_problema=linha["descricao_problema"],
            data_ocorrencia=linha["data_ocorrencia"],
            data_abertura=linha["data_abertura"],
            informacoes_adicionais=linha["informacoes_adicionais"],
            estado=Chamado.Estado(linha["estado"]),
            prioridade=Chamado.Prioridade(linha["prioridade"]) if linha["prioridade"] else None,
            tecnicos=[self._carregar_usuario(cur, t) for t in tecnico_ids],
            data_inicio_atendimento=linha["data_inicio_atendimento"],
            diagnostico=linha["diagnostico"],
            descricao_intervencao=linha["descricao_intervencao"],
            concluido_por=self._carregar_usuario(cur, linha["concluido_por_id"]),
            data_conclusao=linha["data_conclusao"],
            id=linha["id"],
        )
