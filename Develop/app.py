import streamlit as st
import pandas as pd
import db_utils
import logging
import sqlite3

logger = logging.getLogger(__name__)

st.title("VK-STATS-TG-BOT")

@st.cache_data(ttl=300)
def load_data():
    temp_df = None
    try:
        conn = db_utils.db_connect()
        stat_query = ('''
            SELECT post_stats.*, watchlist.category
            FROM post_stats
            JOIN watchlist ON post_stats.domain = watchlist.domain
            ORDER BY post_stats.collected_at DESC
            ''')


        temp_df = pd.read_sql_query(stat_query, conn)
        temp_df["collected_at"] = pd.to_datetime(temp_df["collected_at"])
        temp_df["post_date"] = pd.to_datetime(temp_df["post_date"])
    except sqlite3.OperationalError as e:
        logger.error(f"Ошибка при загрузке данных streamlit: {e}", exc_info=True)
        st.error("Не удалось поключиться к Базе Данных, попробуйте обновить страницу")

    return temp_df

temp_df = load_data()

if temp_df.empty:
    st.warning("База данных пуста! Добавьте пост через бота "
               "или дождитесь их автоматического добавления!")
else:
    st.subheader("Сырые данные из БД")
    st.dataframe(temp_df)

    categories = temp_df["category"].unique()
    selected_category = st.sidebar.selectbox("1. Выберите категорию", sorted(categories))
    df_by_category = temp_df[temp_df["category"] == selected_category]

    groups_by_category = df_by_category["domain"].unique()
    options = ["Все группы"] + sorted(groups_by_category)
    selected_domain = st.sidebar.selectbox("2. Выберите группу", options)
    if selected_domain == "Все группы":
        st.subheader(f"Сравнительная статистика категории: {selected_category}")
        df_by_category['er'] = (df_by_category['likes']+df_by_category['comments']
                                +df_by_category['reposts']) / df_by_category['members'] * 100
        er_by_group = (df_by_category.groupby('domain')['er'].mean())
        er_by_group = er_by_group.round(3)
        er_by_group = er_by_group.sort_values(ascending=False)


        st.bar_chart(er_by_group)

    else:
        df_final = df_by_category[df_by_category["domain"] == selected_domain].set_index("post_date")
        st.subheader(f"Аналитика для: {selected_domain}")

        st.line_chart(df_final[["views", "likes", "comments", "reposts"]])
