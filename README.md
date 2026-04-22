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

## MEP Component

The repository root now also serves as the MEP component package root. The
top-level [process.py](process.py), [config.json](config.json), and
[package.json](package.json) are laid out for MEP packaging.

Before uploading to WiseDevOps/MEP, replace the placeholder `scope` value in
[package.json](package.json) with the real organization/namespace required by
your DevOps workspace. The current `replace-me` value is only a template.

See [MEP_COMPONENT.md](MEP_COMPONENT.md) for the MEP-specific request format,
runtime behavior, and local simulation flow.
