import os
import requests
import streamlit as st

server = os.getenv("LIGHTHOUSE_SERVER_HOST")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False


def authenticate(api_key):
    response = requests.get(server + "/admin/auth", headers={"api_key": api_key})
    if response.status_code == 200:
        return True
    else:
        return False


def add_product(api_key, product_name):
    response = requests.post(
        server + "/admin/add_product", params={"product_name": product_name}, headers={"api_key": api_key}
    )
    if response.status_code == 201:
        return response.json().get("api_key", "Не удалось получить ключ продукта")
    else:
        return "Ошибка при добавлении продукта"


def add_analyzer(api_key, analyzer_name, description, host, port, endpoint, analyzer_type):
    response = requests.post(
        server + "/admin/add_analyzer",
        json={
            "analyzer_name": analyzer_name,
            "description": description,
            "host": host,
            "port": int(port),
            "endpoint": endpoint,
            "type": analyzer_type,
        },
        headers={"api_key": api_key},
    )
    if response.status_code == 201:
        return "Анализатор успешно добавлен"
    else:
        return "Ошибка при добавлении анализатора"


st.header("Администраторская страница")
api_key = st.text_input("Введите ваш API ключ", type="password", value=st.session_state.get("api_key", ""))

if st.button("Подтвердить API ключ"):
    if authenticate(api_key):
        st.session_state["api_key"] = api_key
        st.session_state["authenticated"] = True
        st.success("API ключ подтвержден")
    else:
        st.error("Неверный API ключ")

if st.session_state.get("authenticated", False):
    st.write("API ключ подтвержден. Вы можете продолжать работу.")

if st.session_state.get("authenticated", False):
    st.header("Добавление продукта")
    product_name = st.text_input("Введите название продукта")

    if st.button("Добавить продукт"):
        product_api_key = add_product(st.session_state["api_key"], product_name)
        st.write(f"API ключ для продукта: {product_api_key}")

    st.header("Добавление анализатора")

    analyzer_name = st.text_input("Введите название анализатора")
    description = st.text_input("Введите описание анализатора")
    host = st.text_input("Введите host")
    port = st.text_input("Введите port")
    endpoint = st.text_input("Введите endpoint")

    analyzer_type = st.selectbox("Выберите тип", options=["input", "output"])

    if st.button("Добавить анализатор"):
        message = add_analyzer(
            st.session_state["api_key"], analyzer_name, description, host, port, endpoint, analyzer_type
        )
        st.success(message)

        st.session_state["analyzer_name"] = ""
        st.session_state["description"] = ""
        st.session_state["host"] = ""
        st.session_state["port"] = ""
        st.session_state["endpoint"] = ""
