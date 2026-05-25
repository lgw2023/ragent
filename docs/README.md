# Documentation

This directory is the maintained documentation entry point for Ragent. Large
generated outputs, benchmark artifacts, platform reference dumps, and
presentation materials stay next to their source data, but are linked here so
readers do not have to search the repository root.

## Start Here

- [Project quick start](../README.md): repository overview, environment split,
  install commands, and MEP packaging commands.
- [Full user guide](../presentation/README.md): setup details, MinerU model
  download, CLI usage, and Python examples.
- [MEP vocabulary and boundaries](../CONTEXT.md): shared terms for the MEP
  inference component and model package boundary.

## MEP Delivery

- [Component contract](mep/component.md): component/model package boundary,
  request parsing, async response contract, deployment notes, and local
  simulation flow.
- [End-to-end validation plan](mep/e2e_validation_plan.md): current MEP
  validation conclusions, known gaps, and platform checklist.
- [Offline full-chain runbook](mep/offline_full_chain_runbook.md): repeatable
  offline validation procedure for Ascend/vLLM MEP delivery.
- [Qwen3 embedding runtime ADR](adr/0001-component-owned-qwen3-embedding-runtime.md):
  decision record for keeping Qwen3 runtime adaptation in the component package.
- [MEP platform references](mep/platform_rule/README.md): source platform
  examples, Q&A, frozen requirement snapshots, copied upstream rule documents,
  and timeliness notes.

## Deployment And Operations

- [Offline deployment](deployment/offline.md): shipping source, MinerU models,
  offline wheelhouses, and component-owned dependencies to an offline server.
- [Strict offline replay](operations/offline_replay.md): exporting raw merge
  units and replaying them into a deterministic final KG project.
- [Bulk KG build pipeline](operations/bulk_kg_pipeline.md): recommended
  export/replay/canonical-merge structure for large document corpora.
- [Latency benchmark usage](../benchmark/README.md): benchmark service flow,
  scenario semantics, output files, and validation checks.

## Supporting Materials

- [Presentation materials](../presentation/): slides, framework prompts, SFT
  data synthesis notes, and contribution summaries.
- [Benchmark artifacts](../benchmark/): historical retrieval answers, ground
  truth files, latency reports, and review notes.
- [Examples](../example/): generated sample projects and parsed document
  outputs. These are data artifacts rather than maintained docs.

## Maintenance Rules

- Keep root-level docs minimal: `README.md` is the quick start and
  `CONTEXT.md` is the shared vocabulary file.
- Put maintained project docs under `docs/` by topic.
- Keep generated outputs beside their producing workflow, and link to them from
  this index instead of moving them into `docs/`.
- Do not treat dependency package docs under `mep/component_deps/`,
  `mep/model_packages/`, `vendor/`, or generated `example/` outputs as project
  documentation.
