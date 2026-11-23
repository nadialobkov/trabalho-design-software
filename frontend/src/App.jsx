import { useState } from "react";
import { USUARIOS } from "./dados/catalogo.js";
import SeletorUsuario from "./componentes/SeletorUsuario.jsx";
import TelaAbrirChamado from "./telas/TelaAbrirChamado.jsx";
import TelaListaChamados from "./telas/TelaListaChamados.jsx";

const CHAVE_USUARIO = "manutencao.usuarioId";

// Remembers the chosen demo user between page reloads. Storage can fail (private window),
// so any error just falls back to the first user.
function usuarioSalvo() {
  try {
    const id = Number(localStorage.getItem(CHAVE_USUARIO));
    return USUARIOS.some((u) => u.id === id) ? id : USUARIOS[0].id;
  } catch {
    return USUARIOS[0].id;
  }
}

const TELAS = [
  { id: "abrir", titulo: "Abrir chamado" },
  { id: "lista", titulo: "Chamados" },
];

export default function App() {
  const [usuarioId, setUsuarioId] = useState(usuarioSalvo);
  const [tela, setTela] = useState("abrir");
  const usuario = USUARIOS.find((u) => u.id === usuarioId);

  function mudarUsuario(id) {
    setUsuarioId(id);
    try {
      localStorage.setItem(CHAVE_USUARIO, String(id));
    } catch {
      // Not saving is fine: the choice still works until the page reloads.
    }
  }

  return (
    <div className="app">
      <header className="topo">
        <div className="topo-conteudo">
          <div className="marca">
            <img src="/icone.svg" alt="" width="32" height="32" />
            <div>
              <h1>Manutenção de Laboratório</h1>
              <span>Chamados de equipamentos · UFPR</span>
            </div>
          </div>
          <SeletorUsuario usuarioId={usuarioId} onMudar={mudarUsuario} />
        </div>
        <nav className="abas" aria-label="Telas">
          {TELAS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`aba ${tela === t.id ? "aba-ativa" : ""}`}
              aria-current={tela === t.id ? "page" : undefined}
              onClick={() => setTela(t.id)}
            >
              {t.titulo}
            </button>
          ))}
        </nav>
      </header>

      <main className="conteudo">
        {tela === "abrir" ? (
          <TelaAbrirChamado usuario={usuario} onVerLista={() => setTela("lista")} />
        ) : (
          <TelaListaChamados usuario={usuario} />
        )}
      </main>
    </div>
  );
}
