// HTTP client for ManutencaoController. Screens never call fetch directly.
// Every request sends the X-Usuario-Id header, because the prototype has no login (ASR02).

const BASE = "/api";

export class ErroApi extends Error {
  constructor(mensagem, status) {
    super(mensagem);
    this.status = status;
  }
}

// Backend messages are in English. The screens show Portuguese text chosen by status code.
const MENSAGENS = {
  403: "Acesso negado: usuário não encontrado ou sem permissão (ASR02).",
  404: "Equipamento não encontrado. Confira o código do equipamento (RN01).",
  422: "Dados inválidos. Confira os campos do formulário.",
};

async function requisitar(caminho, usuarioId, opcoes = {}) {
  let resposta;
  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      ...opcoes,
      headers: {
        "Content-Type": "application/json",
        "X-Usuario-Id": String(usuarioId),
        ...opcoes.headers,
      },
    });
  } catch {
    throw new ErroApi("Não foi possível falar com o servidor. Ele está rodando?", 0);
  }

  if (!resposta.ok) {
    const mensagem =
      MENSAGENS[resposta.status] ?? `Erro inesperado do servidor (HTTP ${resposta.status}).`;
    throw new ErroApi(mensagem, resposta.status);
  }
  return resposta.json();
}

// UC01 / RF01: POST /chamados
export function abrirChamado(usuarioId, dados) {
  return requisitar("/chamados", usuarioId, {
    method: "POST",
    body: JSON.stringify(dados),
  });
}

// UC02 / RF02, RF03: GET /chamados with optional filters. Empty filters are not sent.
export function consultarChamados(usuarioId, filtros = {}) {
  const parametros = new URLSearchParams();
  for (const [chave, valor] of Object.entries(filtros)) {
    if (valor !== "" && valor !== null && valor !== undefined) {
      parametros.set(chave, valor);
    }
  }
  const consulta = parametros.toString();
  return requisitar(`/chamados${consulta ? `?${consulta}` : ""}`, usuarioId);
}
