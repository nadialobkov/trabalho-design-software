import { ESTADOS, PRIORIDADES } from "../dados/catalogo.js";

// Colored labels for ticket state (RN03 flow) and priority (RF04).
export function EtiquetaEstado({ estado }) {
  return (
    <span className={`etiqueta estado-${estado.toLowerCase()}`}>
      <span className="ponto" aria-hidden="true" />
      {ESTADOS[estado] ?? estado}
    </span>
  );
}

export function EtiquetaPrioridade({ prioridade }) {
  if (!prioridade) {
    return <span className="etiqueta prioridade-nenhuma">Não definida</span>;
  }
  return (
    <span className={`etiqueta prioridade-${prioridade.toLowerCase()}`}>
      {PRIORIDADES[prioridade] ?? prioridade}
    </span>
  );
}
