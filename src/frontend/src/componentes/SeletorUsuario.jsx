import { PAPEIS, USUARIOS, nomeDepartamento } from "../dados/catalogo.js";

// The prototype has no login. This picker chooses which user the requests are sent as
// (header X-Usuario-Id). The backend decides what that user may do and see (ASR02).
export default function SeletorUsuario({ usuarioId, onMudar }) {
  return (
    <label className="seletor-usuario">
      <span>Acessando como</span>
      <select value={usuarioId} onChange={(e) => onMudar(Number(e.target.value))}>
        {USUARIOS.map((u) => (
          <option key={u.id} value={u.id}>
            {u.nome} · {PAPEIS[u.papel]}
            {u.departamentoId ? ` (${nomeDepartamento(u.departamentoId)})` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
