# Offline Deployment

This project can run `singlefile.py parse` without downloading MinerU models at
runtime. The current local setup uses:

- `MINERU_MODEL_SOURCE=local` in `.env`
- `~/mineru.json` with `models-dir.pipeline` and `models-dir.vlm`
- `~/.cache/modelscope`, which is a symlink to `/Users/liguowei/ssd1/.cache/modelscope`

For a server that cannot download models or Python packages, ship three things:

1. Source code.
2. Project-local MinerU models under `vendor/mineru-models/`.
3. Offline Python wheels under `vendor/wheelhouse/<platform>/`.

## Prepare On This Machine

Copy the currently configured MinerU model directories into the project:

```bash
cd /Volumes/SSD1/ragent
python3 tools/offline_runtime.py copy-models
```

This reads `~/mineru.json` and copies only the model directories required by
MinerU:

- `vendor/mineru-models/pipeline`
- `vendor/mineru-models/vlm`

The full ModelScope cache is about 16G on this machine. Copying only these two
configured directories avoids transferring lock/temp folders and unrelated
cache entries. The copy script also excludes ModelScope's self-referential
absolute symlinks inside each model root.

## Build Python Wheels

Build wheels on an online machine that matches the target server's OS, CPU
architecture, Python version, and CUDA/CPU requirements. Do not build these on
macOS for a Linux server.

```bash
cd /path/to/ragent
PYTHON_BIN=python3.13 tools/build_wheelhouse.sh
```

This writes wheels to a platform-specific directory such as:

```text
vendor/wheelhouse/linux-amd64-py3.12/
vendor/wheelhouse/linux-arm64-py3.12/
```

If PyTorch/CUDA wheels are needed, make sure the build host can download the
same wheel variants that the server will use.

The script writes wheels only. It prefers published binary wheels, and when a
package only publishes a source distribution it builds that wheel on the online
build host so the offline server still installs with `--no-index`.

To build both Linux amd64 and arm64 wheelhouses from Docker with Ubuntu images:

```bash
cd /path/to/ragent
tools/build_docker_wheelhouses.sh
```

The Docker helper first creates reusable local builder images:

```text
ragent-wheelhouse-builder:ubuntu24.04-py3.12-amd64
ragent-wheelhouse-builder:ubuntu24.04-py3.12-arm64
```

Those images contain Ubuntu's Python, pip, venv, and build tools, so future
wheelhouse rebuilds do not reinstall apt packages. Set
`BUILD_BUILDER_IMAGE=always` to refresh them, or `BUILD_BUILDER_IMAGE=never` to
require them to already exist.

The default `ubuntu:latest` image currently resolves to Ubuntu 24.04 and
provides Python 3.12, so the resulting wheelhouses are tagged `py3.12`. If the
target server will run Python 3.13, build with a Python 3.13 base image and make
sure the target uses the same Python minor version.

## Transfer

Transfer the project directory after the models and wheelhouse exist. A typical
archive command is:

```bash
tar --exclude='.git' --exclude='.venv' -czf ragent-offline.tar.gz ragent
```

Keep the real `.env` out of Git, but include it in the transferred folder if
the target server should reuse the same model endpoint configuration. Otherwise
copy `.env.offline.example` to `.env` on the target and fill in the endpoint
URLs and keys.

## Bootstrap On The Target Server

On the offline server:

```bash
cd /path/to/ragent
cp .env.offline.example .env  # skip this if you transferred a real .env
vi .env                       # fill endpoint URLs and keys
PYTHON_BIN=python3.12 tools/bootstrap_offline_runtime.sh
```

The bootstrap script:

- generates `.runtime/mineru.json` with absolute model paths for this server
- updates `.env` with `MINERU_TOOLS_CONFIG_JSON=.runtime/mineru.json`
- creates `.venv`
- selects `vendor/wheelhouse/<current-linux-arch-and-python>/`
- installs dependencies from that wheelhouse with `--no-index`
- validates that the MinerU model directories exist

## Run

```bash
.venv/bin/python singlefile.py parse /path/to/input.pdf /path/to/mineru_out /path/to/project_dir
```

If you only need Markdown extraction:

```bash
.venv/bin/python singlefile.py parse /path/to/input.pdf /path/to/mineru_out md
```

## Notes

- `MINERU_TOOLS_CONFIG_JSON` may be a project-relative path such as
  `.runtime/mineru.json`; `integrations.py` resolves it to an absolute path
  before MinerU is imported.
- `.env` remains the place for model endpoint configuration.
- `.runtime/`, `vendor/mineru-models/`, and `vendor/wheelhouse/` are runtime
  artifacts and should not be committed.
