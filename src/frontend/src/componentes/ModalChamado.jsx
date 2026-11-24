import { nomeDepartamento, nomeUsuario, USUARIOS } from "../dados/catalogo.js";
import { EtiquetaEstado } from "./Etiquetas.jsx";
import {
  atribuirTecnicos,
  concluirAtendimento,
  definirPrioridade,
  iniciarAtendimento,
} from "../api/manutencaoApi.js";
import { useState } from "react";

function formatarData(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR");
}

export default function ModalChamado({ chamado, usuario, onFechar, onAtualizado }) {
  const [tecnicoId, setTecnicoId] = useState(
    chamado.tecnicos_ids.length === 1 ? String(chamado.tecnicos_ids[0]) : "",
  );
  const [prioridade, setPrioridade] = useState(chamado.prioridade ?? "");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [diagnostico, setDiagnostico] = useState("");
  const [intervencao, setIntervencao] = useState("");
  const tecnicoResponsavel =
    usuario.papel === "TECNICO" &&
    chamado.tecnicos_ids.includes(usuario.id);
  const podeAtribuir =
    chamado.estado === "ABERTO" && usuario.papel === "COORDENADOR";
  const tecnicos = USUARIOS.filter(
    (item) => item.papel === "TECNICO" && item.departamentoId === chamado.departamento_id,
  );

  let textoBotao = "OK";
  if (podeAtribuir && !tecnicoResponsavel) {
    textoBotao = "Salvar";
  } else if (tecnicoResponsavel && chamado.estado === "ATRIBUIDO") {
    textoBotao = "Marcar como em andamento";
  } else if (tecnicoResponsavel && chamado.estado === "EM_ATENDIMENTO") {
    textoBotao = "Marcar como concluído";
  }

  async function salvar() {
    setErro("");
    if (
      tecnicoResponsavel &&
      chamado.estado === "EM_ATENDIMENTO" &&
      (!diagnostico.trim() || !intervencao.trim())
    ) {
      setErro("Informe o diagnóstico e a intervenção realizada.");
      return;
    }
    setSalvando(true);
    try {
      let atualizado = chamado;
      if (usuario.papel === "COORDENADOR") {
        if (tecnicoId) {
          atualizado = await atribuirTecnicos(usuario.id, chamado.id, [Number(tecnicoId)]);
        }
        if (prioridade) {
          atualizado = await definirPrioridade(usuario.id, chamado.id, prioridade);
        }
      } else if (usuario.papel === "TECNICO") {
        if (chamado.estado === "ATRIBUIDO") {
          atualizado = await iniciarAtendimento(usuario.id, chamado.id);
        } else if (chamado.estado === "EM_ATENDIMENTO") {
          atualizado = await concluirAtendimento(
            usuario.id,
            chamado.id,
            diagnostico,
            intervencao,
          );
        }
      }
      onAtualizado?.(atualizado);
      onFechar();
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="modal-fundo" role="presentation" onMouseDown={onFechar}>
      <section
        className="modal-chamado"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-modal"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button className="botao-fechar" type="button" aria-label="Fechar" onClick={onFechar}>
          ×
        </button>
        <h2 id="titulo-modal">Chamado #{String(chamado.id).padStart(5, "0")}</h2>
        <dl className="detalhes-chamado">
          <div><dt>Nº chamado:</dt><dd>#{chamado.id}</dd></div>
          <div><dt>Data:</dt><dd>{formatarData(chamado.data_ocorrencia)}</dd></div>
          <div><dt>Departamento:</dt><dd>{nomeDepartamento(chamado.departamento_id)}</dd></div>
          <div><dt>ID equipamento:</dt><dd>{chamado.equipamento_id}</dd></div>
          <div><dt>Nome equipamento:</dt><dd>{chamado.equipamento_nome}</dd></div>
          <div><dt>Solicitante:</dt><dd>{nomeUsuario(chamado.solicitante_id)}</dd></div>
          <div><dt>Status:</dt><dd><EtiquetaEstado estado={chamado.estado} /></dd></div>
          <div><dt>Descrição:</dt><dd>{chamado.descricao_problema}</dd></div>
        </dl>

        {podeAtribuir ? (
          <>
            <div className="campo campo-modal">
              <label htmlFor="tecnico">Atribuir técnico</label>
              <select id="tecnico" value={tecnicoId} onChange={(event) => setTecnicoId(event.target.value)}>
                <option value="" disabled>Selecione um técnico</option>
                {tecnicos.map((tecnico) => (
                  <option key={tecnico.id} value={tecnico.id}>{tecnico.nome}</option>
                ))}
              </select>
            </div>
            <div className="campo campo-modal">
              <label htmlFor="prioridade">Prioridade</label>
              <select id="prioridade" value={prioridade} onChange={(event) => setPrioridade(event.target.value)}>
                <option value="">Não definida</option>
                <option value="BAIXA">Baixa</option>
                <option value="MEDIA">Média</option>
                <option value="ALTA">Alta</option>
                <option value="URGENTE">Urgente</option>
              </select>
            </div>
          </>
        ) : chamado.tecnicos_ids.length > 0 ? (
          <p><strong>Técnico responsável:</strong> {chamado.tecnicos_ids.map(nomeUsuario).join(", ")}</p>
        ) : null}

        {tecnicoResponsavel && chamado.estado === "EM_ATENDIMENTO" && (
          <>
            <div className="campo campo-modal campo-modal-amplo">
              <label htmlFor="diagnostico">Diagnóstico *</label>
              <textarea
                id="diagnostico"
                rows="3"
                required
                value={diagnostico}
                onChange={(event) => setDiagnostico(event.target.value)}
                placeholder="Informe a causa encontrada"
              />
            </div>
            <div className="campo campo-modal campo-modal-amplo">
              <label htmlFor="intervencao">Intervenção realizada *</label>
              <textarea
                id="intervencao"
                rows="3"
                required
                value={intervencao}
                onChange={(event) => setIntervencao(event.target.value)}
                placeholder="Descreva como o problema foi resolvido"
              />
            </div>
          </>
        )}

        {tecnicoResponsavel && chamado.estado === "ATRIBUIDO" && (
          <p className="texto-suave">Você pode iniciar o atendimento deste chamado.</p>
        )}

        {erro && <p className="aviso aviso-erro">{erro}</p>}
        <button type="button" className="botao-pilula botao-salvar" onClick={salvar} disabled={salvando}>
          {salvando ? "Salvando…" : textoBotao}
        </button>
      </section>
    </div>
  );
}
