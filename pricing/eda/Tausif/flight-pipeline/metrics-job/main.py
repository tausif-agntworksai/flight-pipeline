import pandas as pd
import sqlalchemy
import os

def main():
    engine = sqlalchemy.create_engine(os.environ["DATABASE_URL"])

    with engine.connect() as conn:
        # Read analytics data, compute metrics
        df = pd.read_sql("SELECT * FROM analytics.flown_flights", conn)
        metrics_df = compute_metrics(df)

        # Write to app schema
        metrics_df.to_sql("unit_toggles", engine, schema="app",
                          if_exists="replace", index=False)

        write_audit(conn, "app_toggle_metrics_publish", "success")

    print("Metrics publish complete")


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    # Add your metrics computation logic here
    # Example: df["metric_col"] = df["some_col"].sum()
    return df


def write_audit(conn, script_name: str, status: str):
    conn.execute(sqlalchemy.text(
        "INSERT INTO audit (script_name, status, run_at) "
        "VALUES (:s, :st, NOW())"
    ), {"s": script_name, "st": status})
    conn.commit()


if __name__ == "__main__":
    main()