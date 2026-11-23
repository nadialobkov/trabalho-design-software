// Copy of the sample data in banco/dados_exemplo.sql.
// The API has no endpoints for users, equipment, or departments yet,
// so the screens use this list to fill dropdowns and to show names instead of IDs.
// The backend still checks everything: an ID that is not here is rejected there.

export const DEPARTAMENTOS = [
  { id: 1, nome: "Elétrica" },
  { id: 2, nome: "Óptica" },
];

export const USUARIOS = [
  { id: 1, nome: "Ana", papel: "SOLICITANTE", departamentoId: null },
  { id: 2, nome: "Bruno", papel: "TECNICO", departamentoId: 1 },
  { id: 3, nome: "Carla", papel: "COORDENADOR", departamentoId: 1 },
  { id: 4, nome: "Davi", papel: "TECNICO", departamentoId: 2 },
  { id: 5, nome: "Eva", papel: "SOLICITANTE", departamentoId: null },
];

export const EQUIPAMENTOS = [
  { id: 10, nome: "Osciloscópio", laboratorio: "Laboratório de Física", departamentoId: 1 },
  { id: 11, nome: "Fonte de bancada", laboratorio: "Laboratório de Física", departamentoId: 1 },
  { id: 12, nome: "Microscópio", laboratorio: "Laboratório de Biologia", departamentoId: 2 },
];

export const PAPEIS = {
  SOLICITANTE: "Solicitante",
  TECNICO: "Técnico",
  COORDENADOR: "Coordenador(a)",
};

// Values match Chamado.Estado and Chamado.Prioridade in the domain.
export const ESTADOS = {
  ABERTO: "Aberto",
  ATRIBUIDO: "Atribuído",
  EM_ATENDIMENTO: "Em atendimento",
  CONCLUIDO: "Concluído",
};

export const PRIORIDADES = {
  BAIXA: "Baixa",
  MEDIA: "Média",
  ALTA: "Alta",
  CRITICA: "Crítica",
};

export const nomeUsuario = (id) => USUARIOS.find((u) => u.id === id)?.nome ?? `Usuário ${id}`;
export const nomeDepartamento = (id) =>
  DEPARTAMENTOS.find((d) => d.id === id)?.nome ?? `Departamento ${id}`;
export const buscarEquipamento = (id) => EQUIPAMENTOS.find((e) => e.id === id);
