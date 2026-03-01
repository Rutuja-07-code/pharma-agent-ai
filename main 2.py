from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parent
APP_DIR = ROOT_DIR / "backend" / "app"
APP_FILE = APP_DIR / "main.py"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

spec = spec_from_file_location("backend_app_main", APP_FILE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load ASGI module from {APP_FILE}")

backend_main = module_from_spec(spec)
spec.loader.exec_module(backend_main)

app = backend_main.app

