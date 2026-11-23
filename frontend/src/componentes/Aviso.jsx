// Message box for errors and success. role="alert" makes screen readers announce it.
export default function Aviso({ tipo = "erro", titulo, children }) {
  return (
    <div className={`aviso aviso-${tipo}`} role={tipo === "erro" ? "alert" : "status"}>
      {titulo && <strong>{titulo}</strong>}
      <div>{children}</div>
    </div>
  );
}
