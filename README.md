# WolfXRevange API

Zero external dependencies. No blobs. Pure Python — deploy to Vercel in one command.

---

## Deploy

```bash
npm i -g vercel
cd wolfxrevange-api
vercel --prod
```

Your API goes live at:
```
https://your-project.vercel.app/api
```

---

## Environment Variables

Set these in **Vercel Dashboard → Project → Settings → Environment Variables**:

| Variable   | Example Value    | Description               |
|------------|------------------|---------------------------|
| `ADMIN_KEY`| `wolfxworm7889`  | Master key for all actions |

> No BLOB_URL needed anymore — storage is handled internally.

---

## Storage Note

Vercel uses `/tmp` for writable storage (wiped on cold starts / redeployments).  
For **permanent persistence**, add Vercel KV (free tier):

1. Dashboard → Storage → Create KV Store
2. Connect it to your project
3. Replace `get_db()` / `put_db()` in `api/index.py` to use `os.environ["KV_REST_API_URL"]`

Or just use `export_db` to back up and `import_db` to restore after redeploy.

---

## All Endpoints

Base URL: `https://your-project.vercel.app/api`  
All admin actions need `?key=YOUR_ADMIN_KEY`

---

### PING
```
GET /api?action=ping&key=wolfxworm7889
```
```json
{ "status": "online", "api": "WolfXRevange API", "version": "1.0" }
```

---

### LIST ALL KEYS
```
GET /api?action=list_keys&key=wolfxworm7889
```
```json
{
  "keys": {
    "WXR-001": { "client": "PlayerX", "products": ["ESP", "BYPASS"] }
  },
  "total": 1
}
```

---

### GET ONE KEY
```
GET /api?action=get_key&key=wolfxworm7889&license=WXR-001
```

---

### CHECK KEY  *(Public — no admin key)*
Used by your C++ loader.
```
GET /api?action=check_key&license=WXR-001&product=esp
```
```json
{
  "valid": true,
  "product_access": true,
  "global_config": {
    "mode": 1,
    "dll": "https://cdn.example.com/esp.dll"
  }
}
```

---

### CREATE KEY
```
POST /api?action=create_key&key=wolfxworm7889
Content-Type: application/json

{
  "license":  "WXR-001",
  "client":   "PlayerX",
  "products": ["esp", "bypass"]
}
```
Products not listed → disabled automatically.

---

### UPDATE KEY
```
POST /api?action=update_key&key=wolfxworm7889
Content-Type: application/json

{
  "license":  "WXR-001",
  "client":   "PlayerX",
  "products": ["full", "esp"]
}
```

---

### DELETE KEY
```
POST /api?action=delete_key&key=wolfxworm7889
Content-Type: application/json

{ "license": "WXR-001" }
```

---

### GET GLOBAL DLL CONFIGS
```
GET /api?action=get_configs&key=wolfxworm7889
```

---

### SET GLOBAL DLL CONFIGS
```
POST /api?action=set_configs&key=wolfxworm7889
Content-Type: application/json

{
  "configs": {
    "esp": {
      "mode": 1,
      "dll": "https://cdn.example.com/esp.dll"
    },
    "full": {
      "mode": 3,
      "cimgui": "https://cdn.example.com/cimgui.dll",
      "Client": "https://cdn.example.com/client.dll",
      "AotBst": "https://cdn.example.com/aotbst.dll"
    }
  }
}
```

---

### EXPORT DATABASE
```
GET /api?action=export_db&key=wolfxworm7889
```
Returns full raw DB JSON — use this to back up before redeployment.

---

### IMPORT DATABASE
```
POST /api?action=import_db&key=wolfxworm7889
Content-Type: application/json

{ "data": { ...your exported db... } }
```

---

### WIPE DATABASE
```
POST /api?action=wipe_db&key=wolfxworm7889
Content-Type: application/json

{ "confirm": "WIPE_EVERYTHING" }
```

---

## curl Cheatsheet

```bash
BASE="https://your-project.vercel.app/api"
KEY="wolfxworm7889"

# Ping
curl "$BASE?action=ping&key=$KEY"

# List keys
curl "$BASE?action=list_keys&key=$KEY"

# Create key
curl -X POST "$BASE?action=create_key&key=$KEY" \
  -H "Content-Type: application/json" \
  -d '{"license":"WXR-001","client":"Wolf","products":["esp","bypass"]}'

# Delete key
curl -X POST "$BASE?action=delete_key&key=$KEY" \
  -H "Content-Type: application/json" \
  -d '{"license":"WXR-001"}'

# Check key (from loader, no admin key)
curl "$BASE?action=check_key&license=WXR-001&product=esp"

# Export backup
curl "$BASE?action=export_db&key=$KEY" > backup.json

# Import backup
curl -X POST "$BASE?action=import_db&key=$KEY" \
  -H "Content-Type: application/json" \
  -d "{\"data\": $(cat backup.json)}"
```

---

## Product Slugs
`free` · `basic` · `full` · `complex` · `esp` · `bypass`
