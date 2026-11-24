import { useCallback, useEffect, useState } from "react";
import { consultarChamados } from "../api/manutencaoApi.js";
import { nomeUsuario } from "../dados/catalogo.js";
import Aviso from "../componentes/Aviso.jsx";

function formatarData(iso) {
  return new Date(iso).toLocaleDateString("pt-BR");
}

function formatarHora(iso) {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export default function TelaNotificacoes({ usuario, onAbrirChamado }) {
  const [chamados, setChamados] = useState([]);
  const [erro, setErro] = useState(null);

  const carregar = useCallback(async () => {
    setErro(null);
    try {
      setChamados(await consultarChamados(usuario.id));
    } catch (falha) {
      setErro(falha.message);
    }
  }, [usuario.id]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const notificacoes = [...chamados]
    .sort((a, b) => new Date(b.data_abertura) - new Date(a.data_abertura))
    .map((chamado) => ({
      chamado,
      data: chamado.data_abertura,
      remetente: "SGME",
      mensagem: `Chamado #${chamado.id} registrado para ${chamado.equipamento_nome}.`,
    }));

  return (
    <main className="area-interna">
      <section className="painel painel-notificacoes">
        <header className="cartao-cabecalho">
          <h2>Notificações</h2>
          <p className="texto-suave">Veja as notificações do seu departamento</p>
        </header>

        {erro && <Aviso titulo="Não foi possível carregar as notificações">{erro}</Aviso>}

        <button type="button" className="contador-nao-lidas">
          {notificacoes.length} NÃO LIDAS
        </button>

        <div className="tabela-rolagem tabela-notificacoes">
          <table className="tabela">
            <thead>
              <tr>
                <th>Data</th>
                <th>Horário</th>
                <th>Remetente</th>
                <th>Mensagem</th>
                <th>Mais ações</th>
              </tr>
            </thead>
            <tbody>
              {notificacoes.map(({ chamado, data, remetente, mensagem }) => (
                <tr key={chamado.id}>
                  <td data-rotulo="Data">{formatarData(data)}</td>
                  <td data-rotulo="Horário">{formatarHora(data)}</td>
                  <td data-rotulo="Remetente">{remetente}</td>
                  <td data-rotulo="Mensagem">{mensagem} <small>Solicitante: {nomeUsuario(chamado.solicitante_id)}</small></td>
                  <td data-rotulo="Ações">
                    <button type="button" className="botao-ver" onClick={onAbrirChamado}>
                      Ver chamado
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
