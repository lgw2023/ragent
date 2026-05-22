# Component-Owned Qwen3 Embedding Runtime in MEP

MEP model packages are still built as `modelDir/model`, `modelDir/data`, and
`modelDir/meta`, but the Qwen3-Embedding-4B embedding runtime depends on
image-specific process behavior that should not be encoded in the model files.
We will keep the Qwen3 model directory standard Hugging Face, let the MEP
Component own vLLM startup and Ascend runtime adaptation inside the same MEP
container, and treat transformers as a fallback only.

**Status**: accepted

**Considered Options**

- Put vLLM, Ascend, and embedding dimension settings in the model package, for
  example through `embedding.properties`.
- Put runtime adaptation in the component package and let the model package
  supply standard Hugging Face files plus read-only KG assets.

**Consequences**

The component package owns the local OpenAI-compatible vLLM embedding service,
Ascend environment defaults, Qwen3 embedding runtime defaults, and any small
Ragent Python dependencies that the target image lacks. Heavy validated image
packages such as `torch`, `torch_npu`, `vllm`, and `vllm_ascend` stay in the
image rather than in the model package wheelhouse. Qwen3-backed KG snapshots
should use the full Qwen3-Embedding-4B vector size of 2560 dimensions unless a
future KG is explicitly built at a smaller dimension, and the Qwen3 model
package should not depend on `embedding.properties` or the legacy BGE-M3
`data/deps` tree.
