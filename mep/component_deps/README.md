# component/deps

Component-owned runtime dependencies go here when a target MEP image lacks
packages or local model assets required by the Ragent component itself.

This directory is copied into the component upload package as `deps/`, so
`process.py` can load it before looking at optional model `data/deps/`.

Current contents:

- `site-packages/linux-arm64-py3.10/`
- `site-packages/linux-arm64-py3.11/`
- `requirements-linux-arm64-py3.10.txt`
- `requirements-linux-arm64-py3.11.txt`
- `wheelhouse/linux-arm64-py3.10/`
- `wheelhouse/linux-arm64-py3.11/`
- `keyword-requirements-linux-arm64-py3.10.txt`
- `keyword-requirements-linux-arm64-py3.11.txt`
- `keyword_wheelhouse/linux-arm64-py3.10/`
- `keyword_wheelhouse/linux-arm64-py3.11/`
- `models/keyword_extraction/knowledgator-gliner-x-small/`

These platform directories carry the pure-Python `litellm` and `openai`
packages required by the component. They are shared by Qwen3 and legacy BGE
model packages because they belong to the component runtime, not to a specific
embedding model.

The wheelhouse currently carries small component runtime requirements that the
target images do not provide, including `fastuuid` for LiteLLM and `tenacity`
for `ragent.llm.openai`. Native wheels such as `fastuuid` must be installed by
`process.py` inside the Linux ARM64 container instead of being imported from the
unpacked `site-packages` tree.

The no-LLM keyword fallback is also component-owned. Its GLiNER Python wheels
live under `keyword_wheelhouse/`, and the local `knowledgator-gliner-x-small`
snapshot lives under `models/keyword_extraction/`. Do not duplicate these assets
under individual embedding model packages. The `keyword-requirements-*` files
are installed with pip `--no-deps` so the component uses the packaged GLiNER
direct dependencies without asking pip to resolve the image-owned torch and
transformers stack.

For the Qwen3 vLLM Ascend image, do not place the validated Ascend/vLLM stack
here. The image owns `torch`, `torch_npu`, `vllm`, `vllm_ascend`, and the
Ascend runtime libraries. Keep this directory limited to component application
dependencies and component-owned fallback assets after the target image probe
proves they are missing.
