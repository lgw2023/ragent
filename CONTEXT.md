# Ragent MEP Context

This context defines the vocabulary for the Ragent MEP inference component and
its model package deployment boundary.

## Language

**MEP Component**:
A deployable inference component that answers KG QA requests inside the MEP
platform lifecycle. It owns request handling and runtime initialization.
_Avoid_: script, service package

**Model Package**:
The deployable package that supplies one standard Hugging Face model directory
and read-only data assets for an **MEP Component**. It does not own image-specific
runtime adaptation.
_Avoid_: model root, bundle root

**Embedding Runtime**:
The local runtime the **MEP Component** uses to turn text into vectors before KG
retrieval. For Qwen3-Embedding-4B, the primary **Embedding Runtime** is a
**vLLM Embedding Service**; a **Transformers Fallback** is only a backup path.
_Avoid_: embedding model when referring to the runtime mode

**Runtime Adaptation**:
Component-owned compatibility behavior for the target MEP image, such as local
service startup, Ascend environment setup, and process-level runtime defaults.
_Avoid_: model package config

**vLLM Embedding Service**:
An OpenAI-compatible embedding server started by the **MEP Component** inside
the same MEP container. It is the primary **Embedding Runtime** for
Qwen3-Embedding-4B.
_Avoid_: external embedding API, remote service

**Transformers Fallback**:
An in-process embedding runtime used only when the **vLLM Embedding Service**
cannot be used or is explicitly disabled.
_Avoid_: default transformers runtime

**KG Snapshot**:
A read-only knowledge graph and vector index consumed by the **MEP Component**
at inference time.
_Avoid_: online graph build, project data

## Example Dialogue

Dev: Should Qwen3 use transformers by default?

Domain Expert: No. The MEP Component starts the vLLM Embedding Service inside
the container; transformers is the fallback only.

Dev: Is that an external service?

Domain Expert: No. It is local to the MEP container, but exposed through an
OpenAI-compatible HTTP endpoint.

Dev: Should the Qwen3 model package encode the vLLM command?

Domain Expert: No. The model directory stays standard Hugging Face; the MEP
Component owns Runtime Adaptation for the target image.
