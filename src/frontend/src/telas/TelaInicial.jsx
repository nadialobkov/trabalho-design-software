export default function TelaInicial({ onAbrir }) {
  return (
    <main className="tela-inicial">
      <section className="hero-laboratorio">
        <div className="hero-cartao">
          <p>LABORATÓRIOS</p>
          <h1>merecem os<br />melhores<br />equipamentos</h1>
          <button type="button" className="botao-pilula" onClick={onAbrir}>
            Ver mais <span aria-hidden="true">⚗</span>
          </button>
        </div>
      </section>

      <section className="secao-problemas">
        <h2>PROBLEMAS?</h2>
        <button type="button" className="botao-pilula botao-pilula-grande" onClick={onAbrir}>
          Abrir chamado <span aria-hidden="true">＋</span>
        </button>
      </section>
    </main>
  );
}
