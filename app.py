# app.py
import streamlit as st
import sys

sys.path.append('utils')

from database import init_db, load_events_from_csv, load_products_from_csv, get_all_events, get_products_for_event

# ==================== НАСТРОЙКИ ====================
st.set_page_config(
    page_title="Календарь фермера — Своё Родное",
    page_icon="🌾",
    layout="wide"
)

# ==================== CSS ДИЗАЙН ====================
st.markdown("""
<style>
    /* Импорт шрифтов */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Базовые настройки */
    .stApp {
        background: linear-gradient(160deg, #fef9f0 0%, #f5f1e4 30%, #edf5e6 70%, #e8f4e3 100%);
        font-family: 'Inter', sans-serif;
    }

    /* Главный заголовок */
    .main-header {
        background: linear-gradient(135deg, #3d5a1e 0%, #4a7c2e 40%, #5a8f3a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 4.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0;
        padding-top: 0.5rem;
    }

    .sub-header {
        color: #5a6b4a;
        font-size: 1.1rem;
        font-weight: 400;
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
    }

    /* Вкладки */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: transparent;
        padding: 8px 0;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 14px;
        padding: 10px 24px;
        font-weight: 600;
        font-size: 0.95rem;
        background: #ffffffcc;
        backdrop-filter: blur(10px);
        border: 1.5px solid #d4c9a8;
        color: #5a4a2f;
        transition: all 0.25s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: #ffffff;
        border-color: #8b7a5a;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        transform: translateY(-1px);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #4a7c2e, #5a8f3a) !important;
        color: white !important;
        border-color: #4a7c2e !important;
        box-shadow: 0 4px 20px rgba(74,124,46,0.3) !important;
    }

    /* Карточки событий */
    .event-card {
        background: linear-gradient(180deg, #ffffff 0%, #fefcf7 100%);
        border-radius: 20px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        border: 1px solid #e5ddc8;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1.2);
        position: relative;
        overflow: hidden;
    }

    .event-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #c8a96e, #e8d5a3, #c8a96e);
    }

    .event-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 16px 40px rgba(0,0,0,0.12);
        border-color: #c8a96e;
    }

    .event-type-badge {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .badge-holiday {
        background: #fff0f0;
        color: #c0392b;
    }

    .badge-seasonal {
        background: #f0f7ed;
        color: #3d5a1e;
    }

    .badge-event {
        background: #eef4ff;
        color: #2c5282;
    }

    /* Кнопки */
    .stButton > button {
        background: linear-gradient(135deg, #4a7c2e 0%, #5a8f3a 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 10px 28px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 14px rgba(74,124,46,0.25) !important;
        letter-spacing: 0.01em !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #3d5a1e 0%, #4a7c2e 100%) !important;
        box-shadow: 0 8px 24px rgba(74,124,46,0.4) !important;
        transform: translateY(-2px) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
        box-shadow: 0 2px 8px rgba(74,124,46,0.3) !important;
    }

    /* Кнопка закрыть */
    .close-btn > button {
        background: transparent !important;
        color: #8b7a5a !important;
        border: 1.5px solid #d4c9a8 !important;
        box-shadow: none !important;
    }

    .close-btn > button:hover {
        background: #f5f0e5 !important;
        border-color: #8b7a5a !important;
        color: #5a4a2f !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06) !important;
    }

    /* Панель деталей */
    .detail-panel {
        background: linear-gradient(180deg, #ffffff 0%, #fdfaf3 100%);
        border-radius: 24px;
        padding: 2.5rem;
        margin: 1.5rem 0;
        border: 2px solid #e5ddc8;
        box-shadow: 0 8px 40px rgba(0,0,0,0.08);
        animation: slideUp 0.4s ease;
    }

    @keyframes slideUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Карточки товаров */
    .product-card {
        background: white;
        border-radius: 16px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        border: 1px solid #e5ddc8;
        transition: all 0.2s ease;
    }

    .product-card:hover {
        border-color: #c8a96e;
        box-shadow: 0 6px 20px rgba(0,0,0,0.06);
    }

    /* Текст поста */
    .post-text {
        background: linear-gradient(135deg, #fefdf8 0%, #f8f4e8 100%);
        border-left: 5px solid #c8a96e;
        border-radius: 0 16px 16px 0;
        padding: 1.5rem 2rem;
        font-size: 1rem;
        line-height: 1.7;
        color: #3a3020;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    }

    /* Подвал */
    .footer {
        text-align: center;
        padding: 2rem 0 1rem;
        color: #8b7a5a;
        font-size: 0.85rem;
        opacity: 0.8;
    }

    /* Разделитель */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #d4c9a8, transparent);
        margin: 2rem 0;
    }

    /* Hover-подсказка для дат */
    .date-text {
        color: #6b5d3e;
        font-weight: 500;
    }

    /* Ссылки */
    a {
        color: #4a7c2e !important;
        text-decoration: none !important;
        font-weight: 500 !important;
    }

    a:hover {
        color: #3d5a1e !important;
        text-decoration: underline !important;
    }

    /* Инфо-блок */
    .stAlert {
        border-radius: 16px !important;
        border: none !important;
        background: #fdfaf3 !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
    }

    /* Спиннер загрузки */
    .stSpinner > div {
        border-color: #4a7c2e transparent transparent transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
if 'db_initialized' not in st.session_state:
    with st.spinner("🌱 Загружаем данные фермерского календаря..."):
        init_db()
        load_events_from_csv()
        load_products_from_csv()
        st.session_state['db_initialized'] = True

# ==================== ЗАГОЛОВОК ====================
st.markdown('<p class="main-header">🌾 Календарь фермера</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Кликните на событие, чтобы увидеть рекомендации по продвижению, товары и готовый пост</p>',
    unsafe_allow_html=True)

# ==================== ВКЛАДКИ ====================
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Все события",
    "🎉 Праздники",
    "🌱 Сезонность",
    "⚡ Ивенты"
])

all_events = get_all_events()


def show_events(events, tab_name="all"):
    """Отрисовка сетки карточек событий с фото-фоном и российскими датами"""
    if not events:
        st.info("🌿 Пока нет событий в этой категории. Загляните позже!")
        return

    # Картинки — ПРЯМЫЕ ССЫЛКИ (открой любую в браузере — работает)
    images = {
        "праздник": "https://images.unsplash.com/photo-1464349095431-e9a21285b5f3?w=600&h=400&fit=crop",
        "сезонность": "https://images.unsplash.com/photo-1523348837708-15d4a09cfac2?w=600&h=400&fit=crop",
        "ивент": "https://images.unsplash.com/photo-1559223607-a43c990c692c?w=600&h=400&fit=crop",
    }

    emoji = {"праздник": "🎉", "сезонность": "🌱", "ивент": "⚡"}

    cols = st.columns(3)

    for idx, event in enumerate(events):
        col = cols[idx % 3]
        with col:

            # === ФОРМАТ ДАТЫ ===
            from datetime import datetime

            def format_date(date_str):
                """Преобразует 2026-02-20 в 20.02.2026"""
                try:
                    dt = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
                    return dt.strftime("%d.%m.%Y")
                except:
                    return date_str

            start = format_date(event['start_date'])
            end = format_date(event['end_date'])

            em = emoji.get(event['event_type'], "📅")
            bg = images.get(event['event_type'], images["сезонность"])

            # === КАРТОЧКА ===
            st.markdown(f"""
            <div style="
                background: linear-gradient(180deg, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.75) 100%), url('{bg}');
                background-size: cover;
                background-position: center;
                border-radius: 20px;
                padding: 30px 22px;
                margin: 6px 0;
                color: #ffffff;
                min-height: 260px;
                display: flex;
                flex-direction: column;
                justify-content: flex-end;
                box-shadow: 0 8px 28px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
                border: 1px solid rgba(255,255,255,0.15);
            "
                onmouseover="this.style.transform='translateY(-6px)'; this.style.boxShadow='0 18px 40px rgba(0,0,0,0.35)';"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 8px 28px rgba(0,0,0,0.2)';"
            >
                <span style="
                    display: inline-block;
                    padding: 6px 16px;
                    border-radius: 20px;
                    font-size: 0.78rem;
                    font-weight: 600;
                    background: rgba(255,255,255,0.2);
                    backdrop-filter: blur(8px);
                    border: 1px solid rgba(255,255,255,0.3);
                    width: fit-content;
                    margin-bottom: 14px;
                ">{em} {event['event_type'].capitalize()}</span>
                <h3 style="
                    margin: 0 0 8px 0;
                    font-size: 1.25rem;
                    font-weight: 700;
                    text-shadow: 0 2px 6px rgba(0,0,0,0.5);
                    line-height: 1.3;
                ">{event['event_name']}</h3>
                <p style="
                    margin: 3px 0;
                    font-size: 0.88rem;
                    opacity: 0.92;
                    text-shadow: 0 1px 3px rgba(0,0,0,0.5);
                ">📆 {start} — {end}</p>
                <p style="
                    margin: 3px 0 0 0;
                    font-size: 0.82rem;
                    opacity: 0.8;
                    text-shadow: 0 1px 3px rgba(0,0,0,0.5);
                ">👥 {event['target_audience']}</p>
            </div>
            """, unsafe_allow_html=True)

            # Кнопка
            button_key = f"btn_{tab_name}_{event['event_id']}_{idx}"
            if st.button("📌 Подробнее", key=button_key, use_container_width=True):
                st.session_state['selected_event'] = event
                st.rerun()


# ==================== ОТРИСОВКА ВКЛАДОК ====================
with tab1:
    show_events(all_events, "all")

with tab2:
    holidays = [e for e in all_events if e['event_type'] == 'праздник']
    show_events(holidays, "holidays")

with tab3:
    seasonal = [e for e in all_events if e['event_type'] == 'сезонность']
    show_events(seasonal, "seasonal")

with tab4:
    ivents = [e for e in all_events if e['event_type'] == 'ивент']
    show_events(ivents, "ivents")

# ==================== ДЕТАЛИ СОБЫТИЯ ====================
if 'selected_event' in st.session_state and st.session_state['selected_event'] is not None:
    event = st.session_state['selected_event']

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)

    # Заголовок
    emoji = {"праздник": "🎉", "сезонность": "🌱", "ивент": "⚡"}
    em = emoji.get(event['event_type'], "📅")
    st.markdown(f"## {em} {event['event_name']}")

    # Инфо-блок
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📆 Начало", event['start_date'])
    with col2:
        st.metric("📆 Конец", event['end_date'])
    with col3:
        st.metric("👥 Аудитория", event['target_audience'])

    st.caption(f"📦 **Категории товаров:** `{event['category_tags']}`")

    # Готовый пост
    st.markdown("---")
    st.markdown("### 📝 Готовый текст для поста")
    st.markdown(f'<div class="post-text">{event["base_post_text"]}</div>', unsafe_allow_html=True)

    col_copy, col_empty = st.columns([1, 3])
    with col_copy:
        st.button("📋 Скопировать текст", key="copy_post", use_container_width=True)

    # Подходящие товары
    st.markdown("---")
    st.markdown("### 🛒 Товары для продвижения")

    products = get_products_for_event(event)

    if products:
        for p in products:
            with st.container():
                st.markdown(f"""
                <div class="product-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="font-size: 1.05rem; color: #2d1f0e;">{p['name_product']}</strong>
                            <p style="margin: 4px 0; color: #6b5d3e; font-size: 0.85rem;">
                                🏪 {p['shop_name']} &nbsp;|&nbsp; 📂 {p['category']} &nbsp;|&nbsp; 📍 {p['region']}
                            </p>
                            <p style="color: #8b7a5a; font-size: 0.83rem;">{p['product_description'][:120]}...</p>
                        </div>
                        <a href="{p['url_product']}" target="_blank" style="
                            background: #f5f0e5;
                            padding: 8px 18px;
                            border-radius: 10px;
                            font-weight: 600;
                            font-size: 0.85rem;
                        ">🔗 Открыть</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Товары не найдены. Проверьте категории в файлах событий и товаров.")

    # Закрыть
    st.markdown("<br>", unsafe_allow_html=True)
    col_close, _ = st.columns([1, 3])
    with col_close:
        st.markdown('<div class="close-btn">', unsafe_allow_html=True)
        if st.button("❌ Закрыть детали", use_container_width=True):
            st.session_state['selected_event'] = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ==================== ПОДВАЛ ====================
st.markdown('<p class="footer">🍃 Календарь событийного маркетинга для фермеров | Платформа «Своё Родное» | 2026</p>',
            unsafe_allow_html=True)