from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.parse

# ──────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────
ADMIN_KEY     = os.environ.get("ADMIN_KEY", "wolfxworm7889")
PRODUCT_SLUGS = ["free", "basic", "full", "complex", "esp", "bypass"]

# Storage file path — Vercel gives /tmp as writable scratch space
# For persistence across deployments use Vercel KV (see README)
DB_PATH = "/tmp/wolfxrevange_db.json"

# ──────────────────────────────────────────────
#  DB HELPERS  (local /tmp JSON — no blobs)
# ──────────────────────────────────────────────
def get_db() -> dict:
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def put_db(data: dict) -> bool:
    try:
        with open(DB_PATH, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

# ──────────────────────────────────────────────
#  AUTH
# ──────────────────────────────────────────────
def auth_ok(params: dict) -> bool:
    return params.get("key") == ADMIN_KEY

# ──────────────────────────────────────────────
#  RESPONSE SHORTCUTS
# ──────────────────────────────────────────────
def ok(data):
    return (200, data)

def err(msg, code=400):
    return (code, {"error": msg})

# ──────────────────────────────────────────────
#  ROUTE HANDLERS
# ──────────────────────────────────────────────

def handle_ping(params, _body):
    if not auth_ok(params):
        return err("Unauthorized", 401)
    return ok({"status": "online", "api": "WolfXRevange API", "version": "1.0"})


def handle_list_keys(params, _body):
    if not auth_ok(params):
        return err("Unauthorized", 401)
    db = get_db()
    result = {}
    for k, v in db.items():
        if k == "__global_configs__":
            continue
        if isinstance(v, dict):
            products = [p.upper() for p in PRODUCT_SLUGS
                        if isinstance(v.get(p), dict) and v[p].get("enabled")]
            result[k] = {"client": v.get("client", ""), "products": products}
        else:
            result[k] = {"client": "Legacy", "products": str(v).split("/")}
    return ok({"keys": result, "total": len(result)})


def handle_get_key(params, _body):
    if not auth_ok(params):
        return err("Unauthorized", 401)
    license_key = params.get("license", "").strip()
    if not license_key:
        return err("Missing 'license' parameter")
    db  = get_db()
    val = db.get(license_key)
    if val is None:
        return err("License key not found", 404)
    if isinstance(val, dict):
        products = [p.upper() for p in PRODUCT_SLUGS
                    if isinstance(val.get(p), dict) and val[p].get("enabled")]
        return ok({"license": license_key, "client": val.get("client", ""), "products": products})
    return ok({"license": license_key, "client": "Legacy", "products": str(val).split("/")})


def handle_check_key(params, _body):
    """Public endpoint — used by the C++ loader. No admin key required."""
    license_key = params.get("license", "").strip()
    product     = params.get("product", "").strip().lower()
    if not license_key:
        return err("Missing 'license' parameter")

    db  = get_db()
    val = db.get(license_key)
    if val is None:
        return ok({"valid": False, "reason": "License not found"})

    if isinstance(val, dict):
        if product:
            p_data  = val.get(product, {})
            enabled = p_data.get("enabled", False) if isinstance(p_data, dict) else False
            if not enabled:
                enabled = product in val.get("products", "").split("/")
            g_cfg = db.get("__global_configs__", {}).get(product, {})
            return ok({"valid": True, "product_access": enabled, "global_config": g_cfg})
        return ok({"valid": True, "client": val.get("client", "")})

    # legacy flat string
    products = str(val).split("/")
    access   = (product in products) if product else True
    return ok({"valid": True, "product_access": access})


def handle_create_key(params, body):
    """
    POST body:
    {
      "license":  "WXR-001",
      "client":   "PlayerName",
      "products": ["esp", "bypass"]
    }
    """
    if not auth_ok(params):
        return err("Unauthorized", 401)

    license_key = body.get("license", "").strip()
    if not license_key:
        return err("Missing 'license' in body")
    if license_key == "__global_configs__":
        return err("Reserved key name")
    if license_key.upper().startswith("KEYAUTH-"):
        license_key = "WolfXRevange-" + license_key[8:]

    client  = body.get("client", "").strip()
    enabled = [p.lower() for p in body.get("products", []) if p.lower() in PRODUCT_SLUGS]

    key_data = {"client": client}
    for prod in PRODUCT_SLUGS:
        key_data[prod] = {"enabled": prod in enabled}
    key_data["products"] = "/".join(enabled) if enabled else ""

    db = get_db()
    existed = license_key in db
    db[license_key] = key_data
    if put_db(db):
        action = "updated" if existed else "created"
        return ok({"message": f"License '{license_key}' {action} successfully",
                   "license": license_key, "products": enabled})
    return err("Failed to save to database", 500)


def handle_update_key(params, body):
    """Same as create — full upsert."""
    return handle_create_key(params, body)


def handle_delete_key(params, body):
    """POST body: { "license": "WXR-001" }"""
    if not auth_ok(params):
        return err("Unauthorized", 401)

    license_key = body.get("license", "").strip()
    if license_key.upper().startswith("KEYAUTH-"):
        license_key = "WolfXRevange-" + license_key[8:]
    if not license_key:
        return err("Missing 'license' in body")
    if license_key == "__global_configs__":
        return err("Reserved key name")

    db = get_db()
    if license_key not in db:
        return err("License key not found", 404)
    del db[license_key]
    if put_db(db):
        return ok({"message": f"License '{license_key}' deleted successfully"})
    return err("Failed to save to database", 500)


def handle_get_configs(params, _body):
    if not auth_ok(params):
        return err("Unauthorized", 401)
    db = get_db()
    return ok({"global_configs": db.get("__global_configs__", {})})


def handle_set_configs(params, body):
    """
    POST body:
    {
      "configs": {
        "esp":  { "mode": 1, "dll": "https://..." },
        "full": { "mode": 3, "cimgui": "...", "Client": "...", "AotBst": "..." }
      }
    }
    """
    if not auth_ok(params):
        return err("Unauthorized", 401)

    configs = body.get("configs", {})
    if not isinstance(configs, dict):
        return err("'configs' must be an object")

    for prod in configs:
        if prod not in PRODUCT_SLUGS:
            return err(f"Unknown product slug: '{prod}'")

    db = get_db()
    existing = db.get("__global_configs__", {})
    existing.update(configs)
    db["__global_configs__"] = existing
    if put_db(db):
        return ok({"message": "Global configs updated", "updated": list(configs.keys())})
    return err("Failed to save to database", 500)


def handle_wipe_db(params, body):
    """POST body: { "confirm": "WIPE_EVERYTHING" }"""
    if not auth_ok(params):
        return err("Unauthorized", 401)
    if body.get("confirm") != "WIPE_EVERYTHING":
        return err('Send { "confirm": "WIPE_EVERYTHING" } to confirm this destructive action')
    if put_db({}):
        return ok({"message": "Database wiped completely"})
    return err("Failed to wipe database", 500)


def handle_export_db(params, _body):
    """Download the full raw DB as JSON."""
    if not auth_ok(params):
        return err("Unauthorized", 401)
    return ok(get_db())


def handle_import_db(params, body):
    """
    POST body: raw DB dict to overwrite current database.
    { "data": { ...full db... } }
    """
    if not auth_ok(params):
        return err("Unauthorized", 401)
    data = body.get("data")
    if not isinstance(data, dict):
        return err("'data' must be a JSON object")
    if put_db(data):
        return ok({"message": "Database imported successfully", "keys": len(data)})
    return err("Failed to import database", 500)


# ──────────────────────────────────────────────
#  ROUTER
# ──────────────────────────────────────────────
ROUTES = {
    # GET actions
    "ping":        handle_ping,
    "list_keys":   handle_list_keys,
    "get_key":     handle_get_key,
    "check_key":   handle_check_key,
    "get_configs": handle_get_configs,
    "export_db":   handle_export_db,
    # POST actions
    "create_key":  handle_create_key,
    "update_key":  handle_update_key,
    "delete_key":  handle_delete_key,
    "set_configs": handle_set_configs,
    "wipe_db":     handle_wipe_db,
    "import_db":   handle_import_db,
}

# ──────────────────────────────────────────────
#  VERCEL ENTRY POINT
# ──────────────────────────────────────────────
class handler(BaseHTTPRequestHandler):

    def _send(self, status: int, data: dict):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _params(self) -> dict:
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        if n == 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode())
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        params = self._params()
        action = params.get("action", "")
        fn = ROUTES.get(action)
        if fn is None:
            status, data = err(
                f"Unknown action '{action}'. Available: {list(ROUTES.keys())}", 404)
        else:
            status, data = fn(params, {})
        self._send(status, data)

    def do_POST(self):
        params = self._params()
        action = params.get("action", "")
        body   = self._body()
        fn = ROUTES.get(action)
        if fn is None:
            status, data = err(
                f"Unknown action '{action}'. Available: {list(ROUTES.keys())}", 404)
        else:
            status, data = fn(params, body)
        self._send(status, data)

    def log_message(self, *args):
        pass
