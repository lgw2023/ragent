# Ragent

Ragent is a multimodal RAG framework that combines vector retrieval with a
knowledge graph for traceable one-hop and multi-hop QA.

## Environment split

This repo now supports two separate runtime profiles:

- `build`: document parsing, enhanced markdown generation, wide-table import,
  and KG indexing.
- `inference`: one-hop / multi-hop / chat over an existing `project_dir`.

The inference path no longer imports `MinerU`, `pandas`, `openpyxl`, or
`markdown-it-py` at module import time. If you only need to query an existing
graph, you can keep a much lighter environment.

## Install

Using `uv`:

```bash
uv sync --extra build --extra openai
uv sync --extra inference --extra openai
```

Using `pip`:

```bash
pip install -e ".[build,openai]"
pip install -e ".[inference,openai]"
```

## Env files

The repo includes two example env files:

- `.env.build.example`
- `.env.inference.example`

Copy the one that matches the environment you are preparing to `.env`.

## Detailed guide

See [presentation/README.md](presentation/README.md) for the full setup,
MinerU model download instructions, CLI usage, and Python examples.
