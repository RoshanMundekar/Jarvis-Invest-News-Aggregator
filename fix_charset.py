from app.database import engine
from sqlalchemy import text

print("Converting the database character set to utf8mb4...")
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE news_articles CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
print("Successfully converted the table!")
