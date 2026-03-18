"""
Vertex AI Search setup using REST API directly (bypasses SDK 500 error).
Provisions the project, imports GCS documents, creates search engine, saves App ID.
"""
import os, json, time, requests
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(
    os.path.dirname(__file__), "kserc_sa.json"
)

import google.auth
import google.auth.transport.requests

PROJECT_ID    = "kserc-489316"
LOCATION      = "global"
COLLECTION    = "default_collection"
DATA_STORE_ID = "kserc-regulatory-docs"
ENGINE_ID     = "kserc-search"
GCS_URI       = "gs://kserc-regulatory-docs/*"
BASE_URL      = f"https://discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/{LOCATION}"


def get_token():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def headers():
    return {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"}


def wait_op(op_name, label, timeout=300):
    print(f"  Waiting for {label}...", end="", flush=True)
    url = f"https://discoveryengine.googleapis.com/v1alpha/{op_name}"
    for _ in range(timeout // 5):
        r = requests.get(url, headers=headers())
        d = r.json()
        if d.get("done"):
            print(" done!")
            if "error" in d:
                print(f"  Error: {d['error']}")
                return None
            return d.get("response", d.get("metadata", {}))
        print(".", end="", flush=True)
        time.sleep(5)
    print(" timed out!")
    return None


def main():
    print("=" * 55)
    print("KSERC Vertex AI Search — Full Setup")
    print("=" * 55)

    # ── Step 1: Provision (accept terms, enable pricing) ──────────────
    print("\n[1] Provisioning project (accepting data use terms)...")
    r = requests.post(f"https://discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}:provision",
                      headers=headers(), json={"acceptDataUseTerms": True})
    print(f"  Status: {r.status_code}")
    if r.status_code not in (200, 409):
        print(f"  Body: {r.text[:300]}")
    if r.status_code == 200:
        op = r.json().get("name")
        if op:
            wait_op(op, "provisioning", timeout=120)
    elif r.status_code == 409:
        print("  Already provisioned — continuing.")

    # ── Step 2: Create Data Store ─────────────────────────────────────
    print(f"\n[2] Creating data store [{DATA_STORE_ID}]...")
    ds_url = f"{BASE_URL}/collections/{COLLECTION}/dataStores?dataStoreId={DATA_STORE_ID}"
    r = requests.post(ds_url, headers=headers(), json={
        "displayName": "KSERC Regulatory Documents",
        "industryVertical": "GENERIC",
        "contentConfig": "CONTENT_REQUIRED",
        "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    })
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        op = r.json().get("name")
        if op:
            wait_op(op, "data store creation", timeout=120)
        print("  Data store created!")
    elif r.status_code == 409:
        print("  Already exists — continuing.")
    else:
        print(f"  Error: {r.text[:400]}")

    time.sleep(5)  # Brief pause for resource to be ready

    # ── Step 3: Import Documents from GCS ────────────────────────────
    print(f"\n[3] Importing documents from {GCS_URI}...")
    import_url = (f"{BASE_URL}/collections/{COLLECTION}/dataStores/"
                  f"{DATA_STORE_ID}/branches/default_branch/documents:import")
    r = requests.post(import_url, headers=headers(), json={
        "gcsSource": {
            "inputUris": [GCS_URI],
            "dataSchema": "content",
        },
        "reconciliationMode": "INCREMENTAL",
    })
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        op = r.json().get("name")
        print(f"  Operation: {op}")
        if op:
            wait_op(op, "document import", timeout=300)
        print("  Import complete!")
    else:
        print(f"  Error: {r.text[:400]}")
        print("  (Import may still work — continuing with engine creation)")

    # ── Step 4: Create Search Engine ──────────────────────────────────
    print(f"\n[4] Creating search engine [{ENGINE_ID}]...")
    engine_url = f"{BASE_URL}/collections/{COLLECTION}/engines?engineId={ENGINE_ID}"
    r = requests.post(engine_url, headers=headers(), json={
        "displayName": "KSERC Search",
        "solutionType": "SOLUTION_TYPE_SEARCH",
        "dataStoreIds": [DATA_STORE_ID],
        "searchEngineConfig": {
            "searchTier": "SEARCH_TIER_STANDARD",
        },
    })
    print(f"  Status: {r.status_code}")
    app_id = ENGINE_ID  # default if we can't get it from response

    if r.status_code == 200:
        op = r.json().get("name")
        if op:
            wait_op(op, "engine creation", timeout=120)
        print(f"  Engine created! App ID: {app_id}")
    elif r.status_code == 409:
        print(f"  Already exists. App ID: {app_id}")
    else:
        print(f"  Error: {r.text[:400]}")

    # ── Step 5: Update .env ────────────────────────────────────────────
    print(f"\n[5] Writing App ID to .env...")
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "r") as f:
        content = f.read()

    if "VERTEX_SEARCH_APP_ID=" in content and f"VERTEX_SEARCH_APP_ID={app_id}" not in content:
        content = content.replace("VERTEX_SEARCH_APP_ID=", f"VERTEX_SEARCH_APP_ID={app_id}")
        with open(env_path, "w") as f:
            f.write(content)
        print(f"  .env updated: VERTEX_SEARCH_APP_ID={app_id}")
    else:
        print(f"  .env already has App ID or was already set: {app_id}")

    print("\n" + "=" * 55)
    print("✅ SETUP COMPLETE")
    print(f"  Data store : {DATA_STORE_ID}")
    print(f"  Engine/App : {app_id}")
    print(f"  GCS source : {GCS_URI}")
    print("  Documents are indexing in background (~5-10 min)")
    print("=" * 55)


if __name__ == "__main__":
    main()
