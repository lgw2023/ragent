# data/deps

Place MEP image-specific runtime dependencies here when the target image does
not already include them. This directory is part of the model package's
read-only `data/` payload, so it is available when the MEP server has no
network access.

The current target image is:

```text
swr.cn-southwest-2.myhuaweicloud.com/mep-dev-ga/mep-vllm-ascend:11.3.10.300.2
```

Its effective Python platform tag is:

```text
linux-arm64-py3.9
```

Supported local bootstrap paths:

- `pythonpath/`
- `site-packages/`
- `python/`
- `keyword_wheelhouse/<platform-tag>/*.whl`
- `wheelhouse/<platform-tag>/*.whl`
- `wheelhouse/*.whl` for legacy flat pure-Python wheels

At startup, `process.py` first calls `mep_dependency_bootstrap.py` before
importing `ragent`. The bootstrap does two things:

1. It runs an offline pip install when a matching
   `requirements-<platform-tag>.txt` file exists:

   ```bash
   python3 -m pip install --no-index \
     --find-links data/deps/wheelhouse/linux-arm64-py3.9 \
     -c data/deps/constraints-linux-arm64-py3.9.txt \
     -r data/deps/requirements-linux-arm64-py3.9.txt
   ```

   Already installed packages with matching versions are skipped by pip. This
   path handles native wheels such as `tiktoken`, `jiter`, and `fastuuid`.

2. It adds pure-Python dependency paths to `sys.path` as a fallback. Native
   wheels with `.so`, `.pyd`, `.dll`, or `.dylib` payloads are not zipimported.

`image-baseline-constraints-linux-arm64-py3.9.txt` pins the package versions
observed in the target image, especially `torch`, `torch_npu`, `transformers`,
`tokenizers`, `numpy`, and `huggingface-hub`. This prevents the resolver from
silently replacing the tested Ascend/transformers stack.

`constraints-linux-arm64-py3.9.txt` is the final resolved constraints file. It
keeps the image baseline pins and adds the latest compatible versions for the
missing application dependencies.

Regenerate the wheelhouse and constraints with:

```bash
python tools/export_mep_transformers_embedding_wheelhouse.py --clean
```

The exporter writes `manifest.json` and `downloaded-wheels.txt` beside the
wheel files. Pass `--index-url` or `--extra-index-url` when using an internal
PyPI mirror.

`keyword_wheelhouse/<platform-tag>/` remains reserved for no-LLM keyword
fallback dependencies such as GLiNER, Stanza, and ONNX Runtime. Keep it separate
from the embedding/application wheelhouse so keyword extraction packages do not
change the validated BGE-M3 embedding runtime.
