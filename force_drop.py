from sqlalchemy import text
from app.database import engine

print("Connecting to the database to DROP the news_articles table...")
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS news_articles;"))
print("Successfully dropped. The legacy schema is completely gone!")
