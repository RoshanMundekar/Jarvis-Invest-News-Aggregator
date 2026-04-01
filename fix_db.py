from sqlalchemy import create_engine, text

# Manually execute the patch bypassing any FastAPI startup issues
db_url = "mysql+pymysql://root:root@localhost:3306/jarvis_news?charset=utf8"
engine = create_engine(db_url)

with engine.begin() as conn:
    print("Executing ALTER TABLE statements to fix DataErrors...")
    conn.execute(text("ALTER TABLE news_articles MODIFY source_name VARCHAR(512);"))
    conn.execute(text("ALTER TABLE news_articles MODIFY author VARCHAR(512);"))
    conn.execute(text("ALTER TABLE news_articles MODIFY title TEXT;"))
    conn.execute(text("ALTER TABLE news_articles MODIFY description TEXT;"))
    conn.execute(text("ALTER TABLE news_articles MODIFY url_to_image TEXT;"))
    conn.execute(text("ALTER TABLE news_articles MODIFY content MEDIUMTEXT;"))
    
    # Let's also verify the schema
    result = conn.execute(text("SHOW COLUMNS FROM news_articles;"))
    print("\n--- Current Schema ---")
    for row in result:
        print(f"{row[0]}: {row[1]}")
    
print("Success!")
