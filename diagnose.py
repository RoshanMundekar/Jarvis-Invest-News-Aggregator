from app.database import engine
from sqlalchemy import text
from datetime import datetime

print("Connecting to database...")
with engine.begin() as conn:
    print("\n--- SCHEMA FOR news_articles ---")
    res = conn.execute(text("SHOW FULL COLUMNS FROM news_articles;"))
    for r in res:
        print(r)
        
    print("\n--- TRYING TO INSERT EXACT TRACE PARAMS ---")
    params = {
        'source_name': 'Idnes.cz', 
        'author': 'https://www.idnes.cz/novinari/vladimir-lobl.N4732', 
        'title': 'Čína vyhlásila válku autům bez tlačítek, s volanto-řídítky a výsuvnými klikami', 
        'description': 'Země, která byla symbolem digitální ofenzivy...', 
        'url': 'https://www.idnes.cz/auto/zpravodajstvi/cina-nove-test1-' + str(datetime.now().timestamp()), 
        'url_to_image': 'https://1gr.cz/tempimg/fb/2026/2/LOB4d30b2fa60_BadApple_v1.jpg', 
        'published_at': datetime(2026, 3, 1, 23, 0), 
        'content': 'Automobilový svt...', 
        'fetched_at': datetime.now()
    }
    
    try:
        conn.execute(text("""
            INSERT INTO news_articles 
            (source_name, author, title, description, url, url_to_image, published_at, content, fetched_at) 
            VALUES 
            (:source_name, :author, :title, :description, :url, :url_to_image, :published_at, :content, :fetched_at)
        """), params)
        print("Success! The exact parameters from the trace successfully inserted.")
    except Exception as e:
        print(f"FAILED WITH EXACT TRACE: {e}")
