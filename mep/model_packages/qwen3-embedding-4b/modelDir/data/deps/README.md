# Qwen3 model data dependencies

This Qwen3 model package intentionally does not vendor the legacy BGE-M3
offline dependency wheelhouse.

The target Ascend vLLM image owns the heavy runtime stack (`torch`,
`torch_npu`, `vllm`, `vllm_ascend`, transformers runtime, and Ascend
libraries). Ragent component dependencies should be carried by the component
package under `component/deps` when an image probe shows they are missing.
In this repository those shared component dependencies are sourced from
`mep/component_deps/` and copied into the assembled MEP runtime as
`component/deps/`.

The GLiNER no-LLM keyword fallback is also component-owned. Its Python wheels
and local `knowledgator-gliner-x-small` snapshot live under
`mep/component_deps/`, not under this Qwen3 model package.
