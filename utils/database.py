import pandas as pd
import sqlite3

# Единое постоянное соединение
conn = sqlite3.connect(':memory:', check_same_thread=False)
conn.row_factory = sqlite3.Row

def init_db():
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            event_type TEXT NOT NULL,
            category_tags TEXT,
            target_audience TEXT,
            base_post_text TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            organization_id TEXT,
            shop_name TEXT,
            farmer_description TEXT,
            region TEXT,
            category TEXT,
            name_product TEXT,
            product_description TEXT,
            url_product TEXT,
            url_farmer TEXT
        )
    ''')
    conn.commit()
    print("✅ База данных инициализирована")

def load_events_from_csv(csv_path="data/events.csv"):
    try:
        df = pd.read_csv(csv_path)
    except:
        df = pd.read_csv('/function/code/data/events.csv')
    if 'event_id' not in df.columns:
        df.insert(0, 'event_id', range(1, len(df) + 1))
    df.to_sql('events', conn, if_exists='replace', index=False)
    conn.commit()
    print(f"✅ Загружено {len(df)} событий")

def load_products_from_csv(csv_path="data/farmer_sku.csv"):
    try:
        df = pd.read_csv(csv_path)
    except:
        df = pd.read_csv('/function/code/data/farmer_sku.csv')
    df.to_sql('products', conn, if_exists='replace', index=False)
    conn.commit()
    print(f"✅ Загружено {len(df)} товаров")

def get_all_events():
    c = conn.cursor()
    c.execute("SELECT * FROM events ORDER BY start_date")
    return [dict(row) for row in c.fetchall()]

def get_all_products():
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    return [dict(row) for row in c.fetchall()]

def get_products_for_event(event):
    tags_raw = event['category_tags']
    tags = [t.strip().lower() for t in tags_raw.split(',')]
    all_products = get_all_products()
    matched = []
    for p in all_products:
        product_category = p['category'].lower().strip()
        product_name = p['name_product'].lower().strip()
        product_desc = p['product_description'].lower().strip()
        for tag in tags:
            if tag in product_category or tag in product_name or tag in product_desc:
                matched.append(p)
                break
    return matched