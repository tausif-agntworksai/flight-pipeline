from google.cloud.sql.connector import Connector, IPTypes
import pg8000
import sqlalchemy
import pandas as pd
import os
import datetime


# ── DB engine via IAM auth ──
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


# ── Write audit record ──
def write_audit(engine, script_name: str, status: str, message: str = ""):
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(
            "INSERT INTO audit (script_name, status, message, run_at) "
            "VALUES (:s, :st, :msg, NOW())"
        ), {"s": script_name, "st": status, "msg": message})
        conn.commit()


def main():
    engine = get_db_engine()

    try:
        with engine.connect() as conn:
            # ── Read from analytics schema ──
            df = pd.read_sql("SELECT * FROM analytics.flown_flights", conn)
            print(f"[metrics] Read {len(df)} rows from analytics.flown_flights")

            if df.empty:
                print("[metrics] No data to process")
                write_audit(engine, "metrics_job", "skipped", "No data in analytics.flown_flights")
                return

            # ── Compute metrics ──
            metrics = compute_metrics(df)

            # ── Write metrics back to SQL ──
            metrics.to_sql("flight_metrics", engine, schema="analytics",
                           if_exists="replace", index=False)
            print(f"[metrics] Written {len(metrics)} metric rows to analytics.flight_metrics")

            write_audit(engine, "metrics_job", "success",
                        f"Computed {len(metrics)} metrics from {len(df)} rows")

    except Exception as e:
        print(f"[metrics] ERROR: {e}")
        write_audit(engine, "metrics_job", "failed", str(e))
        raise


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    # Standardize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # ── Add your metric computations here ──
    # Example generic metrics:
    metrics = pd.DataFrame([{
        "computed_at": datetime.datetime.utcnow(),
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns_list": ", ".join(df.columns.tolist()),
    }])

    return metrics


if __name__ == "__main__":
    main()