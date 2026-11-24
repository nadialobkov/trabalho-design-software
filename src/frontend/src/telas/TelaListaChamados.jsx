import { useCallback, useEffect, useState } from "react";
import { consultarChamados } from "../api/manutencaoApi.js";
import {
  DEPARTAMENTOS,
  EQUIPAMENTOS,
  ESTADOS,
  PRIORIDADES,
  USUARIOS,
  nomeDepartamento,
  nomeUsuario,
} from "../dados/catalogo.js";
import { EtiquetaEstado, EtiquetaPrioridade } from "../componentes/Etiquetas.jsx";
import Aviso from "../componentes/Aviso.jsx";
import ModalChamado from "../componentes/ModalChamado.jsx";

// Keys match the query parameters of GET /chamados (RF03).
const FILTROS_VAZIOS = {
  equipamento_id: "",
  estado: "",
  prioridade: "",
  tecnico_id: "",
  solicitante_id: "",
  departamento_id: "",
  aberto_de: "",
  aberto_ate: "",
};

const formatarData = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR");
const formatarDataHora = (iso) =>
  new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

// Tells the user which tickets the backend lets them see (rule in ManutencaoService).
function textoVisibilidade(usuario) {
  if (usuario.papel === "SOLICITANTE") {
    return "Como solicitante, você vê apenas os chamados que abriu.";
  }
  return `Você vê os chamados do departamento de ${nomeDepartamento(usuario.departamentoId)}.`;
}

// UC02 — List and filter tickets (RF02, RF03).
export default function TelaListaChamados({ usuario }) {
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS);
  const [chamados, setChamados] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [mostrarFiltros, setMostrarFiltros] = useState(false);
  const [chamadoSelecionado, setChamadoSelecionado] = useState(null);

  const carregar = useCallback(
    async (filtrosUsados) => {
      setCarregando(true);
      setErro(null);
      try {
        setChamados(await consultarChamados(usuario.id, filtrosUsados));
      } catch (falha) {
        setErro(falha.message);
        setChamados([]);
      } finally {
        setCarregando(false);
      }
    },
    [usuario.id],
  );

  // Reload when the selected user changes. Filters reset because each user sees other tickets.
  useEffect(() => {
    setFiltros(FILTROS_VAZIOS);
    carregar(FILTROS_VAZIOS);
  }, [carregar]);

  const mudar = (campo) => (e) => setFiltros({ ...filtros, [campo]: e.target.value });
  const filtrosAtivos = Object.values(filtros).filter(Boolean).length;

  function aplicar(e) {
    e.preventDefault();
    carregar(filtros);
  }

  function limpar() {
    setFiltros(FILTROS_VAZIOS);
    carregar(FILTROS_VAZIOS);
  }

  const contagem = Object.keys(ESTADOS).map((estado) => ({
    estado,
    total: chamados.filter((c) => c.estado === estado).length,
  }));

  return (
    <main className="area-interna">
    <section className="painel painel-lista">
      <header className="cartao-cabecalho cabecalho-lista">
        <div>
          <h2>Chamados</h2>
          <p className="texto-suave">{textoVisibilidade(usuario)}</p>
        </div>
        <div className="acoes-topo">
          <button
            type="button"
            className="botao-painel"
            aria-expanded={mostrarFiltros}
            onClick={() => setMostrarFiltros(!mostrarFiltros)}
          >
            Filtros{filtrosAtivos > 0 && <span className="contador">{filtrosAtivos}</span>}
          </button>
          <button
            type="button"
            className="botao-painel"
            onClick={() => carregar(filtros)}
            disabled={carregando}
          >
            Atualizar
          </button>
        </div>
      </header>

      {mostrarFiltros && (
        <form className="filtros" onSubmit={aplicar}>
          <div className="campo">
            <label htmlFor="f-equip">Equipamento</label>
            <select id="f-equip" value={filtros.equipamento_id} onChange={mudar("equipamento_id")}>
              <option value="">Todos</option>
              {EQUIPAMENTOS.map((eq) => (
                <option key={eq.id} value={eq.id}>
                  {eq.nome}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="f-estado">Estado</label>
            <select id="f-estado" value={filtros.estado} onChange={mudar("estado")}>
              <option value="">Todos</option>
              {Object.entries(ESTADOS).map(([valor, texto]) => (
                <option key={valor} value={valor}>
                  {texto}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="f-prio">Prioridade</label>
            <select id="f-prio" value={filtros.prioridade} onChange={mudar("prioridade")}>
              <option value="">Todas</option>
              {Object.entries(PRIORIDADES).map(([valor, texto]) => (
                <option key={valor} value={valor}>
                  {texto}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="f-tec">Técnico</label>
            <select id="f-tec" value={filtros.tecnico_id} onChange={mudar("tecnico_id")}>
              <option value="">Todos</option>
              {USUARIOS.filter((u) => u.papel === "TECNICO").map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nome}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="f-sol">Solicitante</label>
            <select id="f-sol" value={filtros.solicitante_id} onChange={mudar("solicitante_id")}>
              <option value="">Todos</option>
              {USUARIOS.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nome}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="f-dep">Departamento</label>
            <select id="f-dep" value={filtros.departamento_id} onChange={mudar("departamento_id")}>
              <option value="">Todos</option>
              {DEPARTAMENTOS.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="f-de">Aberto de</label>
            <input id="f-de" type="date" value={filtros.aberto_de} onChange={mudar("aberto_de")} />
          </div>
          <div className="campo">
            <label htmlFor="f-ate">Aberto até</label>
            <input
              id="f-ate"
              type="date"
              min={filtros.aberto_de || undefined}
              value={filtros.aberto_ate}
              onChange={mudar("aberto_ate")}
            />
          </div>
          <div className="acoes filtros-acoes">
            <button type="button" className="botao botao-texto" onClick={limpar}>
              Limpar
            </button>
            <button type="submit" className="botao">
              Aplicar filtros
            </button>
          </div>
        </form>
      )}

      <ul className="resumo" aria-label="Chamados por estado">
        {contagem.map(({ estado, total }) => (
          <li key={estado} className={`resumo-item estado-${estado.toLowerCase()}`}>
            <span className="resumo-numero">{total}</span>
            <span>{ESTADOS[estado]}</span>
          </li>
        ))}
      </ul>

      {erro && <Aviso titulo="Não foi possível carregar os chamados">{erro}</Aviso>}

      {carregando ? (
        <p className="vazio">Carregando…</p>
      ) : chamados.length === 0 && !erro ? (
        <p className="vazio">
          Nenhum chamado encontrado{filtrosAtivos > 0 ? " com esses filtros" : ""}.
        </p>
      ) : (
        chamados.length > 0 && (
          <div className="tabela-rolagem">
            <table className="tabela">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Equipamento</th>
                  <th>Problema</th>
                  <th>Estado</th>
                  <th>Prioridade</th>
                  <th>Departamento</th>
                  <th>Técnicos</th>
                  <th>Solicitante</th>
                  <th>Datas</th>
                  <th>Mais ações</th>
                </tr>
              </thead>
              <tbody>
                {chamados.map((c) => (
                  <tr key={c.id}>
                    <td data-rotulo="#" className="col-id">
                      {c.id}
                    </td>
                    <td data-rotulo="Equipamento">{c.equipamento_nome}</td>
                    <td data-rotulo="Problema" className="col-problema">
                      {c.descricao_problema}
                    </td>
                    <td data-rotulo="Estado">
                      <EtiquetaEstado estado={c.estado} />
                    </td>
                    <td data-rotulo="Prioridade">
                      <EtiquetaPrioridade prioridade={c.prioridade} />
                    </td>
                    <td data-rotulo="Departamento">{nomeDepartamento(c.departamento_id)}</td>
                    <td data-rotulo="Técnicos">
                      {c.tecnicos_ids.length > 0 ? (
                        c.tecnicos_ids.map(nomeUsuario).join(", ")
                      ) : (
                        <span className="texto-suave">—</span>
                      )}
                    </td>
                    <td data-rotulo="Solicitante">{nomeUsuario(c.solicitante_id)}</td>
                    <td data-rotulo="Datas" className="col-datas">
                      <span>Ocorreu em {formatarData(c.data_ocorrencia)}</span>
                      <span className="texto-suave">Aberto em {formatarDataHora(c.data_abertura)}</span>
                    </td>
                    <td data-rotulo="Ações" className="col-acoes">
                      <button
                        type="button"
                        className="botao-ver"
                        onClick={() => setChamadoSelecionado(c)}
                      >
                        Ver chamado
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </section>
    {chamadoSelecionado && (
      <ModalChamado
        chamado={chamadoSelecionado}
        usuario={usuario}
        onFechar={() => setChamadoSelecionado(null)}
        onAtualizado={(atualizado) => {
          setChamadoSelecionado(atualizado);
          setChamados((atuais) =>
            atuais.map((item) => item.id === atualizado.id ? atualizado : item),
          );
        }}
      />
    )}
    </main>
  );
}
