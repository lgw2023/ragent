# component/deps

Component-owned runtime dependencies go here when a target MEP image lacks a
small Python package required by the Ragent component itself.

This directory is copied into the component upload package as `deps/`, so
`process.py` can load it before looking at optional model `data/deps/`.

For the Qwen3 vLLM Ascend image, do not place the validated Ascend/vLLM stack
here. The image owns `torch`, `torch_npu`, `vllm`, `vllm_ascend`, and the
Ascend runtime libraries. Keep this directory limited to small application
dependencies such as `nano-vectordb` or `litellm` only after the target image
probe proves they are missing.
