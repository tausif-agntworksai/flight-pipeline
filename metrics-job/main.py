from google.cloud.sql.connector import Connector, IPTypes
import pg8000
import sqlalchemy

def get_db_engine():
    connector = Connector()
    
    def getconn():
        conn = connector.connect(
            "agntworks-dev:us-central1:agntworks-sql-dev",
            "pg8000",
            user="61681111552-compute@developer.gserviceaccount.com",
            db="wheelsup",
            enable_iam_auth=True,
            ip_type=IPTypes.PRIVATE,
        )
        return conn

    engine = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
    )
    return engine