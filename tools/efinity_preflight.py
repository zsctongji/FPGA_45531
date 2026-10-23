"""Check the same Interface Designer import used by the official CLI.

No tool files or Windows security settings are changed.
"""
import importlib
import os
from pathlib import Path
import sys
import traceback

if os.environ.get("EFX_SKIP_PT", "0") != "0":
    print("FAIL: EFX_SKIP_PT would skip Interface Designer.", flush=True)
    sys.exit(1)

sys.path.insert(0, str(Path(os.environ["EFINITY_HOME"]) / "scripts"))
try:
    importlib.import_module("efx_run_pt_unified")
except Exception:
    print("FAIL: Interface Designer component cannot load.", flush=True)
    traceback.print_exc()
    sys.exit(1)
print("INTERFACE_DESIGNER_IMPORT_OK", flush=True)
