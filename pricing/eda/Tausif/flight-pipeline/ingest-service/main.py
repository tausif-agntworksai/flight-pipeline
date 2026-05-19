from fastapi import FastAPI, Request
from google.cloud import storage, tasks_v2
import pandas as pd
import sqlalchemy
import json, os

app = FastAPI()

# ── Endpoint 1: Eventarc calls this on file drop ──
@app.post("/ingest-flight-data")
async def ingest_flight_data(request: Request):
    body = await request.json()
    bucket = body["bucket"]
    name   = body["name"]

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
            "url": os.environ["PROCESS_ENDPOINT_URL"],  # URL of endpoint 2
            "headers": {"Content-Type": "application/json"},
            "body": payload,
        }
    }
    client.create_task(parent=queue, task=task)
    return {"status": "queued"}   # returns 200 immediately


# ── Endpoint 2: Cloud Tasks calls this asynchronously ──
@app.post("/process-flight-data")
async def process_flight_data(request: Request):
    body   = await request.json()
    bucket = body["bucket"]
    name   = body["name"]

    # 1. Fetch the Parquet file from GCS
    gcs    = storage.Client()
    blob   = gcs.bucket(bucket).blob(name)
    data   = blob.download_as_bytes()
    df     = pd.read_parquet(pd.io.common.BytesIO(data))

    # 2. Insert into raw.flown_flights (Cloud SQL)
    engine = get_db_engine()
    df.to_sql("flown_flights", engine, schema="raw",
              if_exists="append", index=False)

    # 3. Write audit record
    write_audit(engine, "raw_flown_flights_import", "success")

    # 4. Enqueue Cloud Task for enrichment stage
    enqueue_enrich_task()

    return {"status": "raw insert complete"}


def get_db_engine():
    db_url = os.environ["DATABASE_URL"]  # postgresql://user:pass@host/dbname
    return sqlalchemy.create_engine(db_url)

def write_audit(engine, script_name: str, status: str):
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(
            "INSERT INTO audit (script_name, status, run_at) "
            "VALUES (:s, :st, NOW())"
        ), {"s": script_name, "st": status})
        conn.commit()

def enqueue_enrich_task():
    client = tasks_v2.CloudTasksClient()
    queue  = client.queue_path(
        os.environ["GCP_PROJECT"],
        os.environ["GCP_REGION"],
        "enrich-queue"
    )
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": os.environ["ENRICH_ENDPOINT_URL"],
            "headers": {"Content-Type": "application/json"},
            "body": b"{}",
        }
    }
    client.create_task(parent=queue, task=task)