import streamlit as st
from statsbombpy import sb
import pandas as pd
import os
from dotenv import load_dotenv
import google.generativeai as genai
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
load_dotenv('../.env')

def sb_eventos_partida(partida_id):
    eventos = sb.events(match_id=partida_id)
    if 'location' in eventos.columns:
        eventos_validos = eventos[eventos['location'].apply(lambda x: isinstance(x, list) and len(x) == 2)]
        if not eventos_validos.empty:
            eventos_validos.loc[:, ['localizacao_x', 'localizacao_y']] = pd.DataFrame(eventos_validos['location'].tolist(), index=eventos_validos.index)
            eventos = eventos_validos
    return eventos

def identificar_eventos_por_time(eventos_df):
    times = eventos_df['team'].unique()
    eventos_times = {}

    for time in times:
        eventos_time = eventos_df[eventos_df['team'] == time]

        gols = eventos_time[(eventos_time['type'] == 'Shot') & (eventos_time['shot_outcome'] == 'Goal')]
        gols_por_jogador = gols.groupby('player').size()

        assistencias = eventos_time[eventos_time['pass_goal_assist'] == True]
        assistencias_por_jogador = assistencias.groupby('player').size()

        cartoes_amarelos = eventos_time[
            (eventos_time['bad_behaviour_card'] == 'Yellow Card') | (eventos_time['foul_committed_card'] == 'Yellow Card')
        ]
        cartoes_vermelhos = eventos_time[
            (eventos_time['bad_behaviour_card'] == 'Red Card') | (eventos_time['foul_committed_card'] == 'Red Card')
        ]
        total_cartoes_amarelos = len(cartoes_amarelos)
        total_cartoes_vermelhos = len(cartoes_vermelhos)

        desarmes = eventos_time[eventos_time['type'] == 'Duel']
        duelos_ganhos = desarmes[desarmes['duel_outcome'] == 'Won'] if 'duel_outcome' in desarmes.columns else desarmes

        interceptacoes = eventos_time[eventos_time['type'] == 'Interception']
        interceptacoes_bem_sucedidas = interceptacoes[interceptacoes['interception_outcome'] == 'Won'] if 'interception_outcome' in interceptacoes.columns else interceptacoes

        recuperacoes_bola = eventos_time[eventos_time['type'] == 'Ball Recovery']
        falhas_recuperacao = recuperacoes_bola[recuperacoes_bola['ball_recovery_recovery_failure'] == True] if 'ball_recovery_recovery_failure' in recuperacoes_bola.columns else None

        eventos_times[time] = {
            "gols": gols_por_jogador,
            "jogadores_gols": gols['player'].unique(),
            "assistencias": assistencias_por_jogador,
            "jogadores_assistencias": assistencias['player'].unique(),
            "cartoes_amarelos": total_cartoes_amarelos,
            "cartoes_vermelhos": total_cartoes_vermelhos,
            "desarmes_totais": len(desarmes),
            "duelos_ganhos": len(duelos_ganhos),
            "interceptacoes_bem_sucedidas": len(interceptacoes_bem_sucedidas),
            "falhas_recuperacao_bola": len(falhas_recuperacao) if falhas_recuperacao is not None else 0
        }
    return eventos_times

st.title("Análise de Partida - StatsBomb")

partida_id = st.text_input("Digite o ID da partida:")
if partida_id:
    st.write(f"Analisando partida com ID {partida_id}...")
    eventos = sb_eventos_partida(partida_id)

    if not eventos.empty:
        eventos_resumo = identificar_eventos_por_time(eventos)

        for time, eventos_time in eventos_resumo.items():
            st.subheader(f"Time: {time}")
            st.write(f"Gols: {sum(eventos_time['gols'])} ({', '.join([f'{jogador}: {eventos_time['gols'][jogador]}' for jogador in eventos_time['gols'].index])})")
            st.write(f"Assistências: {sum(eventos_time['assistencias'])} ({', '.join([f'{jogador}: {eventos_time['assistencias'][jogador]}' for jogador in eventos_time['assistencias'].index])})")
            st.write(f"Cartões Amarelos: {eventos_time['cartoes_amarelos']}")
            st.write(f"Cartões Vermelhos: {eventos_time['cartoes_vermelhos']}")
            st.write(f"Desarmes Totais: {eventos_time['desarmes_totais']}")
            st.write(f"Duelos Ganhos: {eventos_time['duelos_ganhos']}")
            st.write(f"Interceptações Bem-sucedidas: {eventos_time['interceptacoes_bem_sucedidas']}")
            st.write(f"Falhas na Recuperação de Bola: {eventos_time['falhas_recuperacao_bola']}")

        narracao_tipo = st.radio("Escolha o tipo de narração:", ["Formal", "Humorístico", "Técnico"])

        prompt = f"{eventos_resumo} Com base nesses dados, faz uma narração de maneira {narracao_tipo} sobre a partida."

        if st.button("Gerar Narração"):
            genai.configure(api_key=os.environ['GEMINI_KEY'])
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            st.subheader("Narração Gerada:")
            st.write(response.text)
    else:
        st.error("Nenhum evento encontrado para a partida fornecida.")
