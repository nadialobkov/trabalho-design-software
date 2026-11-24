import { useState } from "react";
import { abrirChamado } from "../api/manutencaoApi.js";
import { EQUIPAMENTOS, buscarEquipamento, nomeDepartamento } from "../dados/catalogo.js";
import Aviso from "../componentes/Aviso.jsx";

const OUTRO = "outro";

// Today's date as YYYY-MM-DD in local time (toISOString would use UTC).
function hoje() {
  const d = new Date();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

const FORMULARIO_VAZIO = {
  equipamento: "",
  codigoOutro: "",
  descricao: "",
  dataOcorrencia: hoje(),
  informacoes: "",
};

// UC01 — Register a maintenance ticket (RF01). Error flow: equipment not found (RN01).
export default function TelaAbrirChamado({ usuario, onVerLista }) {
  const [form, setForm] = useState(FORMULARIO_VAZIO);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);
  const [criado, setCriado] = useState(null);

  const mudar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  const equipamentoId =
    form.equipamento === OUTRO ? Number(form.codigoOutro) : Number(form.equipamento);
  const equipamento = buscarEquipamento(equipamentoId);

  async function enviar(e) {
    e.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      const chamado = await abrirChamado(usuario.id, {
        equipamento_id: equipamentoId,
        descricao_problema: form.descricao.trim(),
        data_ocorrencia: form.dataOcorrencia,
        informacoes_adicionais: form.informacoes.trim(),
      });
      setCriado(chamado);
      setForm({ ...FORMULARIO_VAZIO, dataOcorrencia: hoje() });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setEnviando(false);
    }
  }

  if (criado) {
    return (
      <main className="area-interna">
        <section className="painel cartao-sucesso">
          <div className="sucesso-icone" aria-hidden="true">✓</div>
          <h2>Chamado #{criado.id} registrado</h2>
          <p>
            <strong>{criado.equipamento_nome}</strong> — {criado.descricao_problema}
          </p>
          <p className="texto-suave">
            O chamado está <strong>Aberto</strong> e foi enviado ao departamento de{" "}
            {nomeDepartamento(criado.departamento_id)}. Um e-mail de confirmação será
            enviado em alguns segundos (RF08).
          </p>
          <div className="acoes">
            <button type="button" className="botao botao-secundario" onClick={() => setCriado(null)}>
              Abrir outro chamado
            </button>
            <button type="button" className="botao" onClick={onVerLista}>
              Ver chamados
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="area-interna">
      <section className="painel">
        <header className="cartao-cabecalho">
          <h2>Abrir chamado</h2>
          <p className="texto-suave">
            Informe o equipamento com problema. O chamado vai para o departamento responsável
            por ele.
          </p>
        </header>

        {erro && <Aviso titulo="Não foi possível abrir o chamado">{erro}</Aviso>}

        <form onSubmit={enviar} className="formulario">
        <div className="campo">
          <label htmlFor="equipamento">Equipamento *</label>
          <select id="equipamento" required value={form.equipamento} onChange={mudar("equipamento")}>
            <option value="" disabled>
              Selecione o equipamento
            </option>
            {EQUIPAMENTOS.map((eq) => (
              <option key={eq.id} value={eq.id}>
                {eq.id} · {eq.nome} — {eq.laboratorio}
              </option>
            ))}
            <option value={OUTRO}>Informar outro código…</option>
          </select>
        </div>

        {form.equipamento === OUTRO && (
          <div className="campo">
            <label htmlFor="codigo">Código do equipamento *</label>
            <input
              id="codigo"
              type="number"
              min="1"
              required
              placeholder="Ex.: 12"
              value={form.codigoOutro}
              onChange={mudar("codigoOutro")}
            />
            <small className="texto-suave">
              O código fica na etiqueta de patrimônio do equipamento.
            </small>
          </div>
        )}

        {equipamento && (
          <p className="dica">
            Departamento responsável: <strong>{nomeDepartamento(equipamento.departamentoId)}</strong>
          </p>
        )}

        <div className="campo">
          <label htmlFor="descricao">Descrição do problema *</label>
          <textarea
            id="descricao"
            rows="4"
            required
            maxLength={1000}
            placeholder="O que aconteceu? Ex.: o microscópio não liga."
            value={form.descricao}
            onChange={mudar("descricao")}
          />
        </div>

        <div className="campo campo-curto">
          <label htmlFor="data">Data da ocorrência *</label>
          <input
            id="data"
            type="date"
            required
            max={hoje()}
            value={form.dataOcorrencia}
            onChange={mudar("dataOcorrencia")}
          />
        </div>

        <div className="campo">
          <label htmlFor="info">Informações adicionais</label>
          <textarea
            id="info"
            rows="3"
            maxLength={1000}
            placeholder="Opcional. Ex.: aparece uma luz vermelha piscando."
            value={form.informacoes}
            onChange={mudar("informacoes")}
          />
        </div>

          <div className="acoes">
            <span className="texto-suave">
              Solicitante: <strong>{usuario.nome}</strong>
            </span>
            <button type="submit" className="botao-pilula" disabled={enviando}>
              {enviando ? "Enviando…" : "Abrir chamado"} <span aria-hidden="true">＋</span>
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
