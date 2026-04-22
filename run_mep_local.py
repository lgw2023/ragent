from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def _load_process_module():
    process_path = Path(__file__).resolve().parent / "process.py"
    spec = importlib.util.spec_from_file_location("ragent_mep_process", process_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load process module from {process_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description="Local MEP load/calc simulator.")
    parser.add_argument("--request", required=True, help="Path to req_Data JSON file")
    args = parser.parse_args()

    request_path = Path(args.request).expanduser().resolve()
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))

    module = _load_process_module()
    model = module.CustomerModel()
    model.load()
    result = model.calc(request_payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
