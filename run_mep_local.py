from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_process_module():
    process_path = Path(__file__).resolve().parent / "process.py"
    spec = importlib.util.spec_from_file_location("ragent_mep_process", process_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load process module from {process_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_bundle_paths_for_local_run(module, model_root: str | None):
    resolver = getattr(module, "resolve_component_bundle_paths", None)
    process_file = getattr(module, "__file__", None)
    if not callable(resolver) or process_file is None:
        return None
    kwargs = {"model_root": model_root} if model_root is not None else {}
    return resolver(process_file, **kwargs)


def _resolve_requested_gen_json_path(request_payload: dict) -> Path | None:
    data = request_payload.get("data")
    if not isinstance(data, dict):
        return None
    generate_path = data.get("generatePath")
    if not generate_path:
        file_info = data.get("fileInfo")
        if isinstance(file_info, list) and file_info and isinstance(file_info[0], dict):
            generate_path = file_info[0].get("generatePath")
    if not isinstance(generate_path, str) or not generate_path.strip():
        return None
    return Path(generate_path).expanduser().resolve() / "gen.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Local MEP load/calc simulator.")
    parser.add_argument("--request", required=True, help="Path to req_Data JSON file")
    parser.add_argument(
        "--model-root",
        help="Optional model_root passed to CustomerModel. Accepts runtime_root or model_dir.",
    )
    args = parser.parse_args()

    request_path = Path(args.request).expanduser().resolve()
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))

    module = _load_process_module()
    bundle_paths = _resolve_bundle_paths_for_local_run(module, args.model_root)
    if bundle_paths is not None:
        print(
            "resolved bundle paths: "
            f"model_dir={bundle_paths.model_dir} ({bundle_paths.model_source}), "
            f"data_dir={bundle_paths.data_dir} ({bundle_paths.data_source}), "
            f"meta_dir={bundle_paths.meta_dir} ({bundle_paths.meta_source})",
            file=sys.stderr,
        )
    model_kwargs = {"model_root": args.model_root} if args.model_root is not None else {}
    model = module.CustomerModel(**model_kwargs)
    model.load()
    result = model.calc(request_payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    gen_json_path = _resolve_requested_gen_json_path(request_payload)
    if gen_json_path is not None:
        print(f"gen.json: {gen_json_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
