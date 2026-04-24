# data/deps

Place MEP image-specific runtime dependencies here when the target vLLM image does not already include them.

Supported local bootstrap paths:

- `pythonpath/`
- `site-packages/`
- `python/`
- `wheelhouse/*.whl` for pure-Python wheels

Compiled packages should be unpacked or installed into a compatible `site-packages/` tree for the target image.
