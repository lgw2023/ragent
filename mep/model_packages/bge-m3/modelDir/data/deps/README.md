# data/deps

Place MEP image-specific runtime dependencies here when the target vLLM image
does not already include them. This directory is part of the model package's
read-only `data/` payload, so it is available even when the MEP server has no
network access.

Supported local bootstrap paths:

- `pythonpath/`
- `site-packages/`
- `python/`
- `keyword_wheelhouse/<platform-tag>/*.whl`
- `wheelhouse/<platform-tag>/*.whl`
- `wheelhouse/<platform-tag>/*.tar.gz`
- `wheelhouse/*.whl` for legacy flat pure-Python wheels

`<platform-tag>` uses `linux-arm64-py3.10` style tags. The current MEP Ascend
910B target image is `linux-arm64-py3.10`.

At startup the component checks platform-specific directories first, then the
legacy flat directories. Only pure-Python wheels are directly zipimported from
`wheelhouse/`; native wheels with `.so`, `.pyd`, `.dll`, or `.dylib` payloads and
source archives such as `.tar.gz` are left for an offline `pip install` repair step or a pre-expanded
`site-packages/<platform-tag>/` tree. A pure-Python wheel is skipped only when
the same distribution and exact version are already installed in the target
image. Set `RAGENT_MEP_FORCE_WHEELHOUSE=1` to force pure-Python wheels into the
bootstrap path.

`keyword_wheelhouse/<platform-tag>/` is reserved for no-LLM keyword fallback
dependencies such as GLiNER, Stanza, and ONNX Runtime. Keeping this separate
prevents keyword extraction packages from changing the validated Ascend vLLM
repair wheelhouse. The full-chain validation installs this wheelhouse with
`--no-index --no-deps` before running retrieval-only requests.

Use `wheelhouse/<platform-tag>/` for universal pure-Python wheels and for native
wheel/source archive artifacts that are installed by a configured offline repair
step. Other compiled packages should be unpacked or installed into a compatible
`site-packages/<platform-tag>/` tree for the target image.

The bge-m3 embedding config uses this wheelhouse to repair the validated vLLM
stack before launch. It reinstalls all wheel files from the matching
platform-specific wheelhouse with `--no-deps`, so dependencies are restored as
the exact exported wheels instead of being re-resolved. `cbor2==5.9.0`,
`triton-ascend==3.2.0`, `vllm==0.13.0`, and `vllm-ascend==0.13.0` are still
validated as required repair artifacts.

For the validated Ascend 910B vLLM embedding image, export exact `cp310`
`aarch64` wheels with:

```bash
python tools/export_mep_vllm_ascend_wheelhouse.py
```

Export the GLiNER keyword fallback model snapshot and keyword wheelhouse with:

```bash
python tools/export_mep_keyword_fallback_assets.py
```

The exporter writes `manifest.json`, `downloaded-wheels.txt`,
`source-archives.txt`, `downloaded-artifacts.txt`, `failed-requirements.txt`, and
`local-file-requirements.txt` beside the artifacts.
`@ file://...whl` entries under `/tmp/ragent-mep-test` are resolved from the
configured package indexes by default; this covers `triton-ascend==3.2.0` from
the validated startup repair step. Other image-internal `file://` entries are
recorded as image-provided by default and are not downloaded. Use
`--local-wheel-dir <dir>` when those wheels were downloaded separately, or
`--resolve-local-file-wheels` to explicitly resolve all local wheel entries from
configured package indexes.
