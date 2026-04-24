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

The repository root contains the MEP component source, but it is not treated as
the final platform runtime layout. Use [tools/build_mep_layout.py](tools/build_mep_layout.py)
to assemble a local MEP-like runtime under `.mep_build/`:

```bash
python tools/build_mep_layout.py --model-package bge-m3
```

The assembled runtime has sibling `component/`, `model/`, `data/`, and `meta/`
directories, matching the MEP platform view. The current `scope` in
[package.json](package.json) is `semtp`; replace it before uploading if the
target WiseDevOps namespace is different.

For a materialized local handoff artifact, copy the model package directories
and archive the assembled runtime:

```bash
python tools/build_mep_layout.py --model-package bge-m3 --materialize --archive-format zip
```

If `--archive-output` is provided, point it outside the assembled runtime root
and use a file path, not an existing directory; the builder rejects paths under
the runtime root so the archive cannot include itself. In `--materialize` mode,
source symlinks inside `model/`, `data/`, or `meta/` are dereferenced so the
assembled runtime is self-contained.

The component only queries an existing KG snapshot. The model package standard
is `modelDir/model/` for Hugging Face model directories only, plus
`modelDir/data/` for component-readable read-only data such as embedding config,
KG snapshots, dependency payloads, and samples. `action=create` writes
`{generatePath}/gen.json` and returns `recommendResult`; direct local requests
without `action` still return the result payload in `recommendResult.content`.

See [MEP_COMPONENT.md](MEP_COMPONENT.md) for the full component/model package
boundary, request parsing rules, async response contract, deployment notes, and
local simulation flow.
