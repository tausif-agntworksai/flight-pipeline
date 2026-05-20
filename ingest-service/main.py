from fastapi import FastAPI, Request
from google.cloud import storage, tasks_v2
from google.cloud.sql.connector import Connector, IPTypes
import pandas as pd
import sqlalchemy
import pg8000
import json, os, io

app = FastAPI()


# ── Shared: DB engine via IAM auth ──
def get_db_engine():
    connector = Connector()

    def getconn():
        return connector.connect(
            os.environ["CLOUD_SQL_INSTANCE"],   # agntworks-dev:us-central1:agntworks-sql-dev
            "pg8000",
            user=os.environ["DB_USER"],          # 61681111552-compute@developer.gserviceaccount.com
            db=os.environ["DB_NAME"],            # wheelsup
            enable_iam_auth=True,
            ip_type=IPTypes.PUBLIC,              # Public IP — no VPC needed
        )

    return sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)


# ── Shared: Read file from GCS — auto-detects CSV or Parquet ──
def read_gcs_file(bucket_name: str, file_name: str) -> pd.DataFrame:
    gcs  = storage.Client()
    blob = gcs.bucket(bucket_name).blob(file_name)
    data = blob.download_as_bytes()

    lower = file_name.lower()

    if lower.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(data))

    elif lower.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))

    elif lower.endswith(".csv.zip") or lower.endswith(".zip"):
        return pd.read_csv(io.BytesIO(data), compression="zip")

    else:
        # Try parquet first, fall back to CSV
        try:
            return pd.read_parquet(io.BytesIO(data))
        except Exception:
            return pd.read_csv(io.BytesIO(data))


# ── Shared: Write audit record ──
def write_audit(engine, script_name: str, status: str, message: str = ""):
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(
            "INSERT INTO audit (script_name, status, message, run_at) "
            "VALUES (:s, :st, :msg, NOW())"
        ), {"s": script_name, "st": status, "msg": message})
        conn.commit()


# ── Endpoint 1: Eventarc calls this on file drop ──
@app.post("/ingest-flight-data")
async def ingest_flight_data(request: Request):
    body   = await request.json()
    bucket = body.get("bucket") or body.get("name", "").split("/")[0]
    name   = body.get("name", "")

    # Enqueue a Cloud Task — pass only the references, not the file
    client = tasks_v2.CloudTasksClient()
    queue  = client.queue_path(
        os.environ["GCP_PROJECT"],
        os.environ["GCP_REGION"],
        "process-flight-queue"
    )
    payload = json.dumps({"bucket": bucket, "name": name}).encode()
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": os.environ["PROCESS_ENDPOINT_URL"],
            "headers": {"Content-Type": "application/json"},
            "body": payload,
            "oidc_token": {
                "service_account_email": os.environ["SERVICE_ACCOUNT"],
            },
        }
    }
    client.create_task(parent=queue, task=task)
    return {"status": "queued", "file": name}


# ── Endpoint 2: Cloud Tasks calls this asynchronously ──
@app.post("/process-flight-data")
async def process_flight_data(request: Request):
    body   = await request.json()
    bucket = body["bucket"]
    name   = body["name"]

    engine = get_db_engine()

    try:
        # 1. Fetch file from GCS — auto-detects CSV or Parquet
        df = read_gcs_file(bucket, name)
        print(f"[ingest] Loaded {len(df)} rows from gs://{bucket}/{name}")

        # 2. Derive table name from file name (e.g. flown_flights.csv → flown_flights)
        table_name = os.path.basename(name).split(".")[0].lower().replace("-", "_")

        # 3. Insert into raw schema
        df.to_sql(table_name, engine, schema="raw", if_exists="append", index=False)
        print(f"[ingest] Inserted {len(df)} rows into raw.{table_name}")

        # 4. Write audit record
        write_audit(engine, "raw_import", "success", f"gs://{bucket}/{name} → raw.{table_name} ({len(df)} rows)")

        # 5. Enqueue Cloud Task for enrichment
        enqueue_enrich_task(table_name)

        return {"status": "raw insert complete", "table": table_name, "rows": len(df)}

    except Exception as e:
        write_audit(engine, "raw_import", "failed", str(e))
        raise


# ── Enqueue enrichment task ──
def enqueue_enrich_task(table_name: str):
    client = tasks_v2.CloudTasksClient()
    queue  = client.queue_path(
        os.environ["GCP_PROJECT"],
        os.environ["GCP_REGION"],
        "enrich-queue"
    )
    payload = json.dumps({"table_name": table_name}).encode()
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": os.environ["ENRICH_ENDPOINT_URL"],
            "headers": {"Content-Type": "application/json"},
            "body": payload,
            "oidc_token": {
                "service_account_email": os.environ["SERVICE_ACCOUNT"],
            },
        }
    }
    client.create_task(parent=queue, task=task)