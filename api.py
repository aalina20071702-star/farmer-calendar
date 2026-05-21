from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.append('utils')
from database import (init_db, load_events_from_csv, load_products_from_csv, get_all_events, get_products_for_event,
                      get_all_products)
import os

# Ключи для Яндекс.Облака
FOLDER_ID = os.getenv("YC_FOLDER_ID", "b1geruhtjdh8rdonf9m9")
API_KEY = os.getenv("YC_API_KEY", "AQVNxM4Y1Wk3qYM2Nb2umPY1phdkgneEToFt0NOT")

import uvicorn

SEASONALITY_MAP = {
    "молочная продукция": {"low": [12, 1, 2], "note": "Зимой спрос стабилен"},
    "ягоды": {"low": [11, 12, 1, 2, 3], "note": "Зимой только заморозка"},
    "мёд": {"low": [], "note": "Стабильный спрос круглый год"},
    "овощи": {"low": [12, 1, 2, 3], "note": "Зимой спрос на соленья"},
    "фрукты": {"low": [12, 1, 2, 3, 4], "note": "Зимой цитрусовые и сухофрукты"},
    "мясная продукция": {"low": [], "note": "Стабильный спрос круглый год"},
    "сыр": {"low": [], "note": "Стабильный спрос круглый год"},
    "кондитерские изделия": {"low": [6, 7, 8], "note": "Летом спрос ниже"},
    "чай": {"low": [6, 7, 8], "note": "Летом спрос на холодные напитки"},
    "травы": {"low": [11, 12, 1, 2], "note": "Зимой спрос на сушёные травы"},
    "орехи": {"low": [], "note": "Стабильный спрос круглый год"},
    "варенье": {"low": [6, 7, 8], "note": "Летом спрос на свежие ягоды"},
    "соленья": {"low": [5, 6, 7, 8], "note": "Летом спрос ниже"},
    "соки": {"low": [11, 12, 1, 2], "note": "Зимой спрос на согревающие напитки"},
    "сухофрукты": {"low": [6, 7, 8], "note": "Летом спрос на свежие фрукты"},
    "яйцо": {"low": [], "note": "Стабильный спрос круглый год"},
    "выпечка": {"low": [6, 7, 8], "note": "Летом спрос чуть ниже"},
    "зефир": {"low": [6, 7, 8], "note": "Летом спрос ниже"},
}

app = FastAPI(title="Календарь фермера API")

# Разрешаем запросы из браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация при старте
init_db()
load_events_from_csv()
load_products_from_csv()

@app.get("/api/events")
def events():
    """Возвращает все события"""
    return get_all_events()


import random

random.seed(42)


@app.get("/api/events/{event_id}")
def event_detail(event_id: int, farmer_id: str = None):
    """Возвращает событие + товары + паровоз + ROI"""
    events = get_all_events()
    event = next((e for e in events if e['event_id'] == event_id), None)
    if not event:
        return {"error": "Событие не найдено"}

    products = get_products_for_event(event)

    import random
    random.seed(event_id)
    for p in products:
        p['stock'] = random.randint(0, 100)
        p['popularity'] = round(random.uniform(0.1, 1.0), 2)

    # === МЕХАНИКА ПАРОВОЗА ===
    locomotive = None

    if len(products) >= 2:
        # Группируем товары по фермерам
        farmer_products = {}
        for p in products:
            fid = str(p['organization_id'])
            if fid not in farmer_products:
                farmer_products[fid] = []
            farmer_products[fid].append(p)

        # Если выбран конкретный фермер — работаем только с ним
        if farmer_id and farmer_id != 'all' and farmer_id != 'null':
            target_farmers = {farmer_id: farmer_products.get(farmer_id, [])}
        else:
            target_farmers = farmer_products

        best_set = None
        best_score = 0

        for fid, items in target_farmers.items():
            if len(items) < 2:
                continue

            heroes = sorted([p for p in items if p['popularity'] > 0.6],
                            key=lambda x: x['popularity'], reverse=True)
            trailers = sorted([p for p in items if p['popularity'] < 0.4 and p['stock'] > 30],
                              key=lambda x: x['popularity'])

            if heroes and trailers:
                hero = heroes[0]
                trailer = trailers[0]
                score = hero['popularity'] * trailer['stock']
                if score > best_score:
                    best_score = score
                    best_set = (hero, trailer, fid)

        if best_set:
            hero, trailer, fid = best_set
            discount = random.choice([10, 15, 20, 25])
            farmer_name = hero.get('shop_name', 'фермера')
            old_price = round(random.randint(400, 900) + random.randint(300, 700))
            new_price = round(old_price * (1 - discount / 100))

            locomotive = {
                "hero_product": hero,
                "trailer_product": trailer,
                "discount": discount,
                "farmer_id": fid,
                "farmer_name": farmer_name,
                "set_name": f"Набор «{hero['name_product']} + {trailer['name_product']}»",
                "description": f"Увеличьте продажи в своём хозяйстве! Популярный товар «{hero['name_product']}» (⭐{round(hero['popularity'] * 100)}%) поможет продать «{trailer['name_product']}», которого на складе {trailer['stock']} шт. Предложите покупателям набор со скидкой {discount}% — и остатки уйдут быстрее.",
                "old_price": old_price,
                "new_price": new_price
            }

    # === ROI-РАСЧЁТ ===
    avg_check = 1309  # из данных кейса
    base_orders = 10000  # заказов в месяц
    repeat_rate = 0.20  # текущая доля повторных

    # Гипотеза: событийный маркетинг повышает повторные заказы на 10%
    new_repeat_rate = repeat_rate * 1.10
    additional_repeat_orders = int(base_orders * (new_repeat_rate - repeat_rate))
    additional_revenue = additional_repeat_orders * avg_check

    # Конверсия набора-паровоза
    locomotive_conversion = 0.08  # 8% покупателей возьмут набор
    locomotive_orders = int(base_orders * locomotive_conversion * 0.05)  # 5% от базы увидят набор
    locomotive_revenue = locomotive_orders * (locomotive['new_price'] if locomotive else avg_check * 1.3)

    roi = {
        "expected_views_range": "100–500",
        "expected_clicks_range": "10–50",
        "expected_orders_range": "1–5",
        "based_on": "Средние показатели фермеров на платформе за 2025 г.",
        "note": "Реальные значения зависят от вашей аудитории, качества фото и текста. Это ориентир, а не гарантия.",
        "repeat_note": "Повторные заказы растут в среднем на 5–10% при регулярном событийном маркетинге (данные платформы)"
    }

    return {
        "event": event,
        "products": products,
        "locomotive": locomotive,
        "roi": roi
    }

from datetime import date, datetime, timedelta
import requests

@app.get("/api/ai/ask")
def ask_ai(query: str):
    """ИИ-агент через YandexGPT с учётом только будущих событий"""

    products = get_all_products()
    all_events = get_all_events()

    import random
    random.seed(42)
    for p in products:
        p['stock'] = random.randint(0, 100)

    # ===== ТЕКУЩАЯ ДАТА =====
    today = date.today()
    current_date = today.strftime("%d.%m.%Y")

    # ===== ОТБИРАЕМ ТОЛЬКО БУДУЩИЕ СОБЫТИЯ =====
    future_events = []
    for e in all_events:
        try:
            event_start = datetime.strptime(e['start_date'], "%Y-%m-%d").date()
            # Включаем события, которые начнутся в течение 60 дней ИЛИ ещё не закончились
            event_end = datetime.strptime(e['end_date'], "%Y-%m-%d").date()
            if event_start <= today + timedelta(days=60) and event_end >= today:
                start_fmt = event_start.strftime("%d.%m.%Y")
                end_fmt = event_end.strftime("%d.%m.%Y")
                future_events.append({
                    "name": e['event_name'],
                    "start": start_fmt,
                    "end": end_fmt,
                    "type": e['event_type'],
                    "category_tags": e['category_tags']
                })
        except:
            pass

    # ===== ФОРМИРУЕМ КОНТЕКСТ =====
    if future_events:
        events_block = "БЛИЖАЙШИЕ БУДУЩИЕ СОБЫТИЯ (только те, что ещё не прошли):\n"
        for e in future_events:
            events_block += f"- {e['name']} ({e['start']} — {e['end']}, тип: {e['type']})\n"
    else:
        events_block = "Ближайших событий нет.\n"

    # Товары с сортировкой: сначала с малым остатком
    low_stock = [p for p in products if p['stock'] < 15]
    normal_stock = [p for p in products if p['stock'] >= 15]

    context = f"""
Ты — ИИ-агент маркетплейса «Своё Родное». Твоя задача — помогать российским фермерам планировать продажи.

!!! СЕГОДНЯ {current_date}. ВСЕ ДАТЫ УКАЗЫВАЙ В ФОРМАТЕ ДД.ММ.ГГГГ !!!

!!! ЗАПРЕЩЕНО упоминать события, которые уже прошли (до {current_date}). Предлагай только будущие события из списка ниже. !!!

{events_block}

ТОВАРЫ С МАЛЫМ ОСТАТКОМ (залежавшиеся, нужно срочно продавать):
{chr(10).join([f"- {p['name_product']} (категория: {p['category']}, остаток: {p['stock']} шт.)" for p in low_stock[:10]])}

ОСТАЛЬНЫЕ ТОВАРЫ:
{chr(10).join([f"- {p['name_product']} (категория: {p['category']}, остаток: {p['stock']} шт.)" for p in normal_stock[:10]])}

ВОПРОС ФЕРМЕРА: {query}

ИНСТРУКЦИЯ ДЛЯ ОТВЕТА:
1. Сразу после приветствия укажи: «Сегодня {current_date}.»
2. Предлагай только события, которые ещё не прошли (из списка выше).
3. Для каждой рекомендации указывай даты в формате ДД.ММ.ГГГГ.
4. Если спрашивают про «ближайший месяц» — учитывай только события в течение 30 дней от сегодня.
5. Если товар с малым остатком — предложи срочную акцию или включи в набор-паровоз.
6. Будь конкретным: называй товары и даты.
"""

    # ===== YandexGPT API =====
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": "600"
        },
        "messages": [
            {"role": "system",
             "text": "Ты — эксперт по фермерскому маркетингу. Отвечаешь строго по инструкции. Не упоминаешь прошедшие даты. Всегда указываешь текущую дату в начале ответа."},
            {"role": "user", "text": context}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        answer = result['result']['alternatives'][0]['message']['text']
        return {"query": query, "answer": answer}
    except Exception as e:
        return {"query": query, "answer": f"⚠️ Ошибка: {str(e)}"}


@app.get("/api/ai/content")
def generate_content(event_id: int, channel: str):
    """Генерирует контент для разных каналов коммуникации"""
    events = get_all_events()
    event = next((e for e in events if e['event_id'] == event_id), None)
    if not event:
        return {"error": "Событие не найдено"}

    products = get_products_for_event(event)
    products_text = "\n".join([f"- {p['name_product']} ({p['category']})" for p in products[:5]])

    # Промпты под разные каналы
    prompts = {
        "post": f"Напиши пост для соцсетей (ВКонтакте/Telegram) о событии '{event['event_name']}' ({event['start_date']} — {event['end_date']}). Товары: {products_text}. Аудитория: {event['target_audience']}. Используй российский формат дат ДД.ММ.ГГГГ. Добавь эмодзи. Длина: 3-5 предложений.",

        "stories": f"Напиши текст для сторис в Instagram/ВКонтакте о событии '{event['event_name']}'. Товары: {products_text}. Коротко, ярко, с вопросом к аудитории. Добавь хештеги. Длина: 2-3 предложения.",

        "push": f"Напиши короткий текст для push-уведомления о событии '{event['event_name']}'. Товары: {products_text}. Уложись в 120 символов с пробелами. Добавь эмодзи и призыв к действию.",

        "blog": f"Напиши тему и краткий план статьи для блога «Своё Родное» о событии '{event['event_name']}'. Товары: {products_text}. Тема должна быть полезной для аудитории: {event['target_audience']}. Длина: заголовок + 3-4 пункта плана.",

        "email": f"Напиши тему и текст для email-рассылки о событии '{event['event_name']}' ({event['start_date']} — {event['end_date']}). Товары: {products_text}. Включи призыв перейти на маркетплейс. Длина: тема письма + 3-4 предложения."
    }

    if channel not in prompts:
        return {"error": f"Неизвестный канал. Доступны: {', '.join(prompts.keys())}"}

    today = date.today()
    current_date = today.strftime("%d.%m.%Y")

    context = f"Сегодня {current_date}.\n{prompts[channel]}"

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    headers = {
        "Authorization": "Api-Key AQVNxM4Y1Wk3qYM2Nb2umPY1phdkgneEToFt0NOT",
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": "gpt://b1geruhtjdh8rdonf9m9/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.8,
            "maxTokens": "400"
        },
        "messages": [
            {"role": "system", "text": "Ты — маркетолог и копирайтер для фермерского маркетплейса."},
            {"role": "user", "text": context}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        content = result['result']['alternatives'][0]['message']['text']
        return {"event_id": event_id, "channel": channel, "content": content}
    except Exception as e:
        return {"event_id": event_id, "channel": channel, "content": f"Ошибка генерации: {str(e)}"}

@app.get("/api/regions")
def get_regions():
    """Возвращает список всех регионов из базы"""
    products = get_all_products()
    regions = list(set(p['region'] for p in products if p.get('region')))
    regions.sort()
    return regions

@app.get("/api/farmers")
def get_farmers():
    """Возвращает список фермеров"""
    products = get_all_products()
    farmers = {}
    for p in products:
        fid = p['organization_id']
        if fid not in farmers:
            farmers[fid] = {
                'organization_id': fid,
                'shop_name': p['shop_name'],
                'region': p['region'],
                'farmer_description': p.get('farmer_description', ''),
                'product_count': 0
            }
        farmers[fid]['product_count'] += 1

    return list(farmers.values())


@app.get("/api/farmer/{farmer_id}/products")
def farmer_products(farmer_id: str):
    """Возвращает товары конкретного фермера"""
    products = get_all_products()

    # Пробуем сравнить и как строку, и как число
    farmer_products = []
    for p in products:
        pid = str(p['organization_id']).strip()
        if pid == str(farmer_id).strip():
            farmer_products.append(p)

    import random
    random.seed(hash(str(farmer_id)) % 10000)
    for p in farmer_products:
        p['stock'] = random.randint(0, 100)
        p['popularity'] = round(random.uniform(0.1, 1.0), 2)

    return farmer_products


@app.get("/api/events/{event_id}/checklist")
def event_checklist(event_id: int):
    """Возвращает чек-лист действий для фермера"""
    events = get_all_events()
    event = next((e for e in events if e['event_id'] == event_id), None)
    if not event:
        return {"error": "Событие не найдено"}

    products = get_products_for_event(event)

    from datetime import datetime, timedelta
    start_date = datetime.strptime(event['start_date'], "%Y-%m-%d")
    end_date = datetime.strptime(event['end_date'], "%Y-%m-%d")

    checklist = [
        {
            "step": 1,
            "action": "📦 Собрать тематическую подборку",
            "detail": f"Отберите товары категорий: {event['category_tags']}. У вас {len(products)} подходящих товаров.",
            "deadline": (start_date - timedelta(days=14)).strftime("%d.%m.%Y"),
            "channel": "Витрина svoe-rodnoe.ru"
        },
        {
            "step": 2,
            "action": "🏷️ Создать скидку или промокод",
            "detail": f"Рекомендуем скидку 10-15% на товары к событию «{event['event_name']}». Создайте в разделе «Скидки» личного кабинета.",
            "deadline": (start_date - timedelta(days=10)).strftime("%d.%m.%Y"),
            "channel": "Витрина svoe-rodnoe.ru"
        },
        {
            "step": 3,
            "action": "📝 Опубликовать пост в соцсетях",
            "detail": "Используйте готовый текст поста. Добавьте фото вашей продукции.",
            "deadline": (start_date - timedelta(days=7)).strftime("%d.%m.%Y"),
            "channel": "Соцсети фермера"
        },
        {
            "step": 4,
            "action": "📱 Опубликовать сторис",
            "detail": "Короткое видео или фото товаров с вопросом к аудитории. Используйте сгенерированный текст.",
            "deadline": (start_date - timedelta(days=5)).strftime("%d.%m.%Y"),
            "channel": "Соцсети фермера"
        },
        {
            "step": 5,
            "action": "🔔 Запросить push-уведомление",
            "detail": "Отправьте запрос через личный кабинет на рассылку push-уведомлений покупателям.",
            "deadline": (start_date - timedelta(days=3)).strftime("%d.%m.%Y"),
            "channel": "Каналы маркетплейса"
        },
        {
            "step": 6,
            "action": "📊 Отследить результаты",
            "detail": f"После {end_date.strftime('%d.%m.%Y')} "
                      f"проверьте статистику продаж в разделе «Клиенты» → «Сводка». Сравните с предыдущим периодом.",
            "deadline": end_date.strftime("%d.%m.%Y"),
            "channel": "Личный кабинет"
        }
    ]

    return {
        "event_id": event_id,
        "event_name": event['event_name'],
        "checklist": checklist
    }


@app.get("/api/events/{event_id}/impact")
def event_impact(event_id: int):
    events = get_all_events()
    event = next((e for e in events if e['event_id'] == event_id), None)
    if not event:
        return {"error": "Событие не найдено"}

    products = get_products_for_event(event)
    farmer_count = len(set(p['organization_id'] for p in products))

    if len(products) > 50:
        level = "высокое"
        recommendation = "Рекомендуем готовиться за 2 недели"
    elif len(products) > 10:
        level = "среднее"
        recommendation = "Можно запустить точечную акцию"
    else:
        level = "низкое"
        recommendation = "Подходит узкой аудитории, акция по желанию"

    return {
        "level": level,
        "matching_products": len(products),
        "matching_farmers": farmer_count,
        "recommendation": recommendation
    }


@app.get("/api/events/{event_id}/season")
def event_season(event_id: int):
    events = get_all_events()
    event = next((e for e in events if e['event_id'] == event_id), None)
    if not event:
        return {"error": "Событие не найдено"}

    month = int(event['start_date'].split('-')[1])
    tags = [t.strip() for t in event['category_tags'].split(',')]

    notes = []
    for tag in tags:
        if tag in SEASONALITY_MAP:
            info = SEASONALITY_MAP[tag]
            if month in info["low"]:
                notes.append(f"⚠️ {tag}: {info['note']} — подсветите альтернативы")
            else:
                notes.append(f"✅ {tag}: сезон высокого спроса")

    return {"month": month, "notes": notes}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)