"""Launch the shared sync engine, writing output to the installed user's log."""
import contextlib
from datetime import datetime
from pathlib import Path
import runpy
import traceback

root = Path(__file__).resolve().parent
with (root / "sync.log").open("a", encoding="utf-8", buffering=1) as log:
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        print(f"=== {datetime.now().isoformat()} sync start ===")
        try:
            runpy.run_path(str(root / "sync.py"), run_name="__main__")
        except Exception:
            traceback.print_exc()
            raise SystemExit(1)
        finally:
            print(f"=== {datetime.now().isoformat()} sync end ===")
