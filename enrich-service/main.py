from fastapi import FastAPI, Request
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
import pandas as pd
import pg8000
import os

app = FastAPI()


# ── Shared: DB engine via IAM auth ──
def get_db_engine():
    connector = Connector()

    def getconn():
        return connector.connect(
            os.environ["CLOUD_SQL_INSTANCE"],
            "pg8000",
            user=os.environ["DB_USER"],
            db=os.environ["DB_NAME"],
            enable_iam_auth=True,
            ip_type=IPTypes.PUBLIC,
        )

    return sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)


# ── Shared: Write audit record ──
def write_audit(conn, script_name: str, status: str, message: str = ""):
    conn.execute(sqlalchemy.text(
        "INSERT INTO audit (script_name, status, message, run_at) "
        "VALUES (:s, :st, :msg, NOW())"
    ), {"s": script_name, "st": status, "msg": message})
    conn.commit()


# ── Endpoint: Enrich raw data → analytics schema ──
@app.post("/analytics-flown-enrich")
async def enrich(request: Request):
    body       = await request.json()
    table_name = body.get("table_name", "flown_flights")

    engine = get_db_engine()

    try:
        with engine.connect() as conn:
            # 1. Read from raw schema
            raw_df = pd.read_sql(f"SELECT * FROM raw.{table_name}", conn)
            print(f"[enrich] Read {len(raw_df)} rows from raw.{table_name}")

            if raw_df.empty:
                return {"status": "no data", "table": table_name}

            # 2. Transform
            analytics_df = transform(raw_df, table_name)
            print(f"[enrich] Transformed into {len(analytics_df)} rows")

        # 3. Write to analytics schema
        analytics_df.to_sql(
            table_name, engine,
            schema="analytics",
            if_exists="replace",
            index=False
        )
        print(f"[enrich] Written to analytics.{table_name}")

        # 4. Audit
        with engine.connect() as conn:
            write_audit(conn, "analytics_enrich", "success",
                        f"raw.{table_name} → analytics.{table_name} ({len(analytics_df)} rows)")

        return {"status": "enrichment complete", "table": table_name, "rows": len(analytics_df)}

    except Exception as e:
        with engine.connect() as conn:
            write_audit(conn, "analytics_enrich", "failed", str(e))
        raise


# ── Transform logic — add your business logic here ──
def transform(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    # Standardize column names
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]

    # Drop fully empty rows
    df = df.dropna(how="all")

    # Add metadata columns
    import datetime
    df["_enriched_at"] = datetime.datetime.utcnow()
    df["_source_table"] = table_name

    # ── Add table-specific transformations below ──
    # if table_name == "flown_flights":
    #     df["duration_hours"] = df["duration_minutes"] / 60

    return df