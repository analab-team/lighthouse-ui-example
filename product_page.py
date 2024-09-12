import os
import json
from ast import literal_eval
from datetime import datetime
from typing import Dict, List

import pandas as pd
import requests
import streamlit as st
from pydantic import BaseModel

server = os.getenv("LIGHTHOUSE_SERVER_HOST")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "selected_analyzer" not in st.session_state:
    st.session_state["selected_analyzer"] = None

if "analyzer_fields" not in st.session_state:
    st.session_state["analyzer_fields"] = None

if "monitoring_data" not in st.session_state:
    st.session_state["monitoring_data"] = None


class Reason(BaseModel):
    start: int
    stop: int
    additional_metric: float | None = None


class AnalyzerResult(BaseModel):
    timestamp: datetime
    text: str
    metric: float
    reject_flg: bool
    reasons: List[Reason] | None


class AnalysisResults(BaseModel):
    input: Dict[str, List[AnalyzerResult]]
    output: Dict[str, List[AnalyzerResult]]


def authenticate(api_key):
    response = requests.get(server + "/monitoring/auth", headers={"api_key": api_key})
    return response.status_code == 200


def change_mode(api_key, mode):
    response = requests.post(server + "/monitoring/change_mode", json={"mode": mode}, headers={"api_key": api_key})
    return response.status_code == 200


def get_monitoring_data(api_key):  # noqa C901
    response = requests.get(server + "/monitoring/data", headers={"api_key": api_key})
    if response.status_code == 200:
        data = response.json()
        for stream in data.keys():
            for analyzer in data[stream].keys():
                for i in range(len(data[stream][analyzer])):
                    try:
                        list_of_str = literal_eval(data[stream][analyzer][i]["reasons"])
                        if list_of_str is not None:
                            reasons = list()
                            for reason in list_of_str:
                                reasons.append(Reason(**json.loads(reason)))
                        else:
                            reasons = None
                    except SyntaxError:
                        reasons = None
                    data[stream][analyzer][i]["reasons"] = reasons
        return AnalysisResults(**data)
    else:
        st.error("Ошибка при загрузке данных мониторинга")
        return None


def get_all_analyzers(api_key):
    response = requests.get(server + "/vault/get_all_analyzers", headers={"api_key": api_key})
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Ошибка при загрузке анализаторов")
        return None


def get_example_fields(api_key, analyzer_name):
    response = requests.get(
        server + "/vault/example",
        params={"analyzer_name": analyzer_name},
        headers={"api_key": api_key},
    )
    if response.status_code == 200:
        return response.json().get("fields", "")
    else:
        st.error("Ошибка при загрузке данных анализатора")
        return None


def add_to_vault(api_key, analyzer_name, data):
    response = requests.post(
        server + "/vault/add",
        json={"analyzer_name": analyzer_name, "vault": data},
        headers={"api_key": api_key},
    )
    return response.status_code == 200


def highlight_text(text: str, reasons: List[Reason]):
    styled_text = ""
    last_index = 0

    for reason in reasons:
        styled_text += text[last_index : reason.start]
        styled_text += f"<span style='color:red'>{text[reason.start:reason.stop]}</span>"
        last_index = reason.stop

    styled_text += text[last_index:]

    return styled_text


st.header("Страница продукта")
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

if st.session_state.get("authenticated", False) and not st.session_state.get("selected_analyzer"):
    st.header("Изменение режима работы сервиса")
    mode = st.selectbox("Выберите режим работы", options=["sync", "async"])

    if st.button("Изменить режим"):
        if change_mode(st.session_state["api_key"], mode):
            st.success(f"Режим изменён на {mode}")
        else:
            st.error("Ошибка при изменении режима")

if st.session_state.get("authenticated", False):  # noqa C901
    if not st.session_state.get("selected_analyzer"):
        st.header("Список анализаторов")

        analyzers = get_all_analyzers(st.session_state["api_key"])

        if analyzers:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Input анализаторы")
                for analyzer in analyzers.get("input", []):
                    if st.button(analyzer):
                        fields = get_example_fields(st.session_state["api_key"], analyzer)
                        st.session_state["selected_analyzer"] = analyzer
                        st.session_state["analyzer_fields"] = fields

            with col2:
                st.subheader("Output анализаторы")
                for analyzer in analyzers.get("output", []):
                    if st.button(analyzer):
                        fields = get_example_fields(st.session_state["api_key"], analyzer)
                        st.session_state["selected_analyzer"] = analyzer
                        st.session_state["analyzer_fields"] = fields

    else:
        st.header(f"Добавление в Vault для {st.session_state['selected_analyzer']}")
        field_data = st.text_area("Данные для Vault", value=json.dumps(st.session_state["analyzer_fields"]))

        if st.button("Добавить Vault"):
            if add_to_vault(
                st.session_state["api_key"],
                st.session_state["selected_analyzer"],
                json.loads(field_data),
            ):
                st.success(f"Данные для {st.session_state['selected_analyzer']} успешно добавлены в Vault")
                st.session_state["selected_analyzer"] = None
                st.session_state["analyzer_fields"] = None
            else:
                st.error("Ошибка при добавлении данных в Vault")

if st.session_state.get("authenticated", False):
    st.header("Обновить данные мониторинга")

    if st.button("Загрузить данные мониторинга"):
        monitoring_data = get_monitoring_data(st.session_state["api_key"])

        if monitoring_data:
            st.session_state["monitoring_data"] = monitoring_data

            st.subheader("Пользователи")
            for key, results in monitoring_data.input.items():
                st.write(f"Анализатор: {key}")
                timestamps = [result.timestamp for result in results]
                metrics = [result.metric for result in results]

                df_input = pd.DataFrame({"timestamp": timestamps, "metric": metrics})
                df_input.set_index("timestamp", inplace=True)

                st.line_chart(df_input)

            st.subheader("Модель")
            for key, results in monitoring_data.output.items():
                st.write(f"Анализатор: {key}")
                timestamps = [result.timestamp for result in results]
                metrics = [result.metric for result in results]

                df_output = pd.DataFrame({"timestamp": timestamps, "metric": metrics})
                df_output.set_index("timestamp", inplace=True)

                st.line_chart(df_output)

if st.session_state.get("authenticated", False) and st.session_state.get("monitoring_data"):  # noqa C901
    st.header("Таблицы с отклонёнными записями")

    st.subheader("Пользователи")
    user_data = []
    for key, results in st.session_state["monitoring_data"].input.items():
        for result in results:
            if result.reject_flg:
                styled_text = highlight_text(result.text, result.reasons) if result.reasons is not None else result.text
                user_data.append(
                    {
                        "timestamp": result.timestamp,
                        "analyzer_name": key,
                        "metric": result.metric,
                        "text": styled_text,
                    }
                )
    if user_data:
        user_df = pd.DataFrame(user_data).sort_values(by="timestamp", ascending=False)
        st.write(user_df.to_html(escape=False), unsafe_allow_html=True)

    st.subheader("Модель")
    model_data = []
    for key, results in st.session_state["monitoring_data"].output.items():
        for result in results:
            if result.reject_flg:
                styled_text = highlight_text(result.text, result.reasons) if result.reasons is not None else result.text
                model_data.append(
                    {
                        "timestamp": result.timestamp,
                        "analyzer_name": key,
                        "metric": result.metric,
                        "text": styled_text,
                    }
                )
    if model_data:
        model_df = pd.DataFrame(model_data).sort_values(by="timestamp", ascending=False)
        st.write(model_df.to_html(escape=False), unsafe_allow_html=True)
