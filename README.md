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

For MEP platform upload, build the component package and model package upload
directories instead:

```bash
python tools/build_mep_upload_packages.py --model-package bge-m3
```

This writes `.mep_upload/bge-m3/component_package/` and
`.mep_upload/bge-m3/model_package/modelDir/`. The component package contains the
MEP entry files and `ragent/`, and excludes local-only files such as
`run_mep_local.py` by default. Add `--include-local-runner` only when a debug
runner must be bundled. The model package upload directory always has
`modelDir/` as its first real entry, so the model zip uploaded to MEP should
also have `modelDir/` at the archive root.

To generate upload-ready archives with the same roots:

```bash
python tools/build_mep_upload_packages.py --model-package bge-m3 --archive-format zip
```

By default these archives are written under `.mep_upload/<model-package>/`.
Use `--archive-output-dir <dir>` with `--archive-format` to place them
elsewhere; the builder rejects archive paths inside `component_package/` or
`model_package/` so the archives cannot include themselves. The same source
path protections apply to a custom archive directory.

Before upload, run the preflight checker for the target Ascend Python platform:

```bash
python tools/preflight_mep_upload_packages.py \
  --upload-root .mep_upload/bge-m3 \
  --platform-tag linux-arm64-py3.9
```

Both MEP builders reject output paths that would overwrite the repository root,
component source files/directories, or the source model package. The model
package must include a non-empty `modelDir/meta/type.mf`.

The component only queries an existing KG snapshot. In the MEP model package,
`modelDir/model/` is the Hugging Face model directory itself, with files such as
`config.json`, `tokenizer.json`, and model weights directly inside it.
`modelDir/data/` holds component-readable read-only data such as embedding
config, KG snapshots, dependency payloads, and samples. `action=create` writes
`{generatePath}/gen.json` and returns `recommendResult`; direct local requests
without `action` still return the result payload in `recommendResult.content`.

See [MEP_COMPONENT.md](MEP_COMPONENT.md) for the full component/model package
boundary, request parsing rules, async response contract, deployment notes, and
local simulation flow.
