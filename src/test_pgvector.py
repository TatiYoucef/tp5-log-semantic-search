import psycopg
from sentence_transformers import SentenceTransformer

DB_URL = "postgresql://tp5:tp5pass@localhost:5432/logsdb"

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

logs = [
    "critical disk failure on node 4",
    "disk error detected on server node",
    "user logged in successfully",
    "authentication failed for root user",
]

embeddings = model.encode(logs, normalize_embeddings=True)

with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM logs;")

        for msg, emb in zip(logs, embeddings):
            cur.execute(
                """
                INSERT INTO logs (source, level, raw_message, normalized_message, embedding)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ("test", "ERROR" if "fail" in msg or "error" in msg else "INFO", msg, msg.lower(), emb.tolist()),
            )

        query = "hard drive failure on a machine"
        query_emb = model.encode([query], normalize_embeddings=True)[0].tolist()

        cur.execute(
            """
            SELECT raw_message, 1 - (embedding <=> %s::vector) AS similarity
            FROM logs
            ORDER BY embedding <=> %s::vector
            LIMIT 3;
            """,
            (query_emb, query_emb),
        )

        for row in cur.fetchall():
            print(row)
