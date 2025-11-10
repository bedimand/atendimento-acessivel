# Backend (FastAPI + uv)

## Pré-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Instalação

```bash
uv sync
```

## Execução do servidor

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

As variáveis esperadas estão descritas em `.env.example`.
