from fastapi import FastAPI
import sqlalchemy
import pandas as pd
import os

app = FastAPI()

@app.post("/analytics-flown-enrich")
async def enrich():
    engine = get_db_engine()

    with engine.connect() as conn:
        # Read raw data
        raw_df = pd.read_sql("SELECT * FROM raw.flown_flights", conn)

        # Your analytics logic here
        analytics_df = transform(raw_df)

        # Write to analytics schema
        analytics_df.to_sql("flown_flights", engine, schema="analytics",
                             if_exists="replace", index=False)

        write_audit(conn, "analytics_flown_enrich", "success")

    return {"status": "enrichment complete"}


def get_db_engine():
    db_url = os.environ["DATABASE_URL"]
    return sqlalchemy.create_engine(db_url)


def write_audit(conn, script_name: str, status: str):
    conn.execute(sqlalchemy.text(
        "INSERT INTO audit (script_name, status, run_at) "
        "VALUES (:s, :st, NOW())"
    ), {"s": script_name, "st": status})
    conn.commit()


def transform(df: pd.DataFrame) -> pd.DataFrame:
    # Add your analytics transformation logic here
    # Example: df["new_col"] = df["existing_col"] * 2
    return df