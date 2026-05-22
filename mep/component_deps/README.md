# component/deps

Component-owned runtime dependencies go here when a target MEP image lacks a
small Python package required by the Ragent component itself.

This directory is copied into the component upload package as `deps/`, so
`process.py` can load it before looking at optional model `data/deps/`.

Current contents:

- `site-packages/linux-arm64-py3.10/`
- `site-packages/linux-arm64-py3.11/`
- `requirements-linux-arm64-py3.10.txt`
- `requirements-linux-arm64-py3.11.txt`
- `wheelhouse/linux-arm64-py3.10/`
- `wheelhouse/linux-arm64-py3.11/`

These platform directories carry the pure-Python `litellm` and `openai`
packages required by the component. They are shared by Qwen3 and legacy BGE
model packages because they belong to the component runtime, not to a specific
embedding model.

The wheelhouse currently carries `fastuuid`, a native LiteLLM dependency that
must be installed by `process.py` inside the Linux ARM64 container instead of
being imported from the unpacked `site-packages` tree.

For the Qwen3 vLLM Ascend image, do not place the validated Ascend/vLLM stack
here. The image owns `torch`, `torch_npu`, `vllm`, `vllm_ascend`, and the
Ascend runtime libraries. Keep this directory limited to small application
dependencies such as `nano-vectordb` or `litellm` only after the target image
probe proves they are missing.
