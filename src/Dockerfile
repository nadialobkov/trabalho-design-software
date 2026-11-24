# Imagem do backend monolítico com Python 3.12 e versões fixadas das dependências.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Instala as bibliotecas primeiro para reutilizar esta camada quando só o código mudar.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY manutencao ./src/manutencao
RUN uv sync --locked --no-dev

EXPOSE 7555
CMD ["uv", "run", "--no-sync", "fastapi", "run", "src/manutencao/main.py", "--host", "0.0.0.0", "--port", "7555"]
