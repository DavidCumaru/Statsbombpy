import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import requests

def run_page():
    BASE_URL = "http://127.0.0.1:8000" 
    st.title("Interface Streamlit para FastAPI")
    menu = st.sidebar.selectbox(
        "Selecione a funcionalidade",
        ["Resumo da Partida", "Perfil do Jogador", "Eventos do Time"]
    )

    if menu == "Resumo da Partida":
        st.header("Resumo da Partida")
        competition_id = st.number_input("ID da Competição", min_value=1, step=1)
        season_id = st.number_input("ID da Temporada", min_value=1, step=1)
        match_id = st.number_input("ID da Partida", min_value=1, step=1)

        if st.button("Obter Resumo"):
            params = {
                "competition_id": competition_id,
                "season_id": season_id,
                "match_id": match_id
            }
            try:
                response = requests.get(f"{BASE_URL}/match_summary", params=params)
                if response.status_code == 200:
                    st.json(response.json())
                else:
                    st.error(f"Erro: {response.status_code} - {response.json()['detail']}")
            except Exception as e:
                st.error(f"Erro ao conectar com a API: {e}")

    elif menu == "Perfil do Jogador":
        st.header("Perfil do Jogador")
        match_id = st.number_input("ID da Partida", min_value=1, step=1)
        player_id = st.number_input("ID do Jogador", min_value=1, step=1)

        if st.button("Obter Perfil do Jogador"):
            params = {
                "match_id": match_id,
                "player_id": player_id
            }
            try:
                response = requests.get(f"{BASE_URL}/player_profile", params=params)
                if response.status_code == 200:
                    st.json(response.json())
                else:
                    st.error(f"Erro: {response.status_code} - {response.json()['detail']}")
            except Exception as e:
                st.error(f"Erro ao conectar com a API: {e}")

    elif menu == "Eventos do Time":
        st.header("Eventos do Time")
        match_id = st.number_input("ID da Partida", min_value=1, step=1)
        narration_style = st.selectbox(
            "Estilo da Narração",
            [("Formal", 1), ("Humorístico", 2), ("Técnico", 3)],
            format_func=lambda x: x[0]
        )[1]

        if st.button("Obter Eventos do Time"):
            params = {
                "match_id": match_id,
                "narration_style": narration_style
            }
            try:
                response = requests.get(f"{BASE_URL}/team_events", params=params)
                if response.status_code == 200:
                    data = response.json()
                    st.subheader("Resumo dos Eventos")
                    st.json(data["events_summary"])
                    st.subheader("Narração")
                    st.write(data["narration"])
                else:
                    st.error(f"Erro: {response.status_code} - {response.json()['detail']}")
            except Exception as e:
                st.error(f"Erro ao conectar com a API: {e}")
