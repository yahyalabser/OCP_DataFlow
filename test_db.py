from sqlalchemy import text
from config.db_config import engine

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'ocp_dataflow'
        ORDER BY table_name
    """))
    tables = [row[0] for row in result]
    print(f"{len(tables)} tables trouvées :")
    for t in tables:
        print(" -", t)