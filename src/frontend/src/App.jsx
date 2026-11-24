import { useState } from "react";
import { Bell } from "lucide-react";
import { USUARIOS } from "./dados/catalogo.js";
import SeletorUsuario from "./componentes/SeletorUsuario.jsx";
import TelaAbrirChamado from "./telas/TelaAbrirChamado.jsx";
import TelaListaChamados from "./telas/TelaListaChamados.jsx";
import TelaInicial from "./telas/TelaInicial.jsx";
import TelaNotificacoes from "./telas/TelaNotificacoes.jsx";
import TelaPrototipo from "./telas/TelaPrototipo.jsx";

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
  { id: "inicio", titulo: "Início" },
  { id: "abrir", titulo: "Abrir chamado" },
  { id: "equipamentos", titulo: "Equipamentos" },
  { id: "chamados", titulo: "Consultar chamados" },
];

export default function App() {
  const [usuarioId, setUsuarioId] = useState(usuarioSalvo);
  const [tela, setTela] = useState("inicio");
  const usuario = USUARIOS.find((u) => u.id === usuarioId);

  function mudarUsuario(id) {
    setUsuarioId(id);
    setTela("inicio");
    try {
      localStorage.setItem(CHAVE_USUARIO, String(id));
    } catch {
      // Not saving is fine: the choice still works until the page reloads.
    }
  }

  return (
    <div className="app">
      <header className="cabecalho-sgme">
        <div className="cabecalho-superior">
          <button className="marca-sgme" type="button" onClick={() => setTela("inicio")}>
            <strong>SGME</strong>
            <span>Sistema de Gerenciamento e<br />Manutenção de Equipamentos</span>
          </button>
          <div className="area-usuario">
            <span className="acesso-como">acessando como</span>
            <SeletorUsuario usuarioId={usuarioId} onMudar={mudarUsuario} />
            <button
              className="botao-sino"
              type="button"
              aria-label="Abrir notificações"
              onClick={() => setTela("notificacoes")}
            >
              <Bell size={27} strokeWidth={2.2} aria-hidden="true" />
              <i aria-hidden="true" />
            </button>
          </div>
        </div>
        <nav className="navegacao-sgme" aria-label="Navegação principal">
          {TELAS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={tela === item.id ? "ativo" : ""}
              onClick={() => setTela(item.id)}
            >
              {item.titulo}
            </button>
          ))}
        </nav>
      </header>

      {tela === "inicio" && (
        <TelaInicial onAbrir={() => setTela("abrir")} />
      )}
      {tela === "abrir" && (
        <TelaAbrirChamado usuario={usuario} onVerLista={() => setTela("chamados")} />
      )}
      {tela === "chamados" && (
        <TelaListaChamados usuario={usuario} />
      )}
      {tela === "notificacoes" && (
        <TelaNotificacoes usuario={usuario} onAbrirChamado={() => setTela("chamados")} />
      )}
      {tela === "equipamentos" && (
        <TelaPrototipo titulo="Equipamentos" />
      )}
    </div>
  );
}
