import streamlit as st
from statsbombpy import sb
from langchain.schema import Document
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAI
from langchain.agents import initialize_agent, Tool, AgentType
import os
import pandas as pd
from dotenv import load_dotenv
load_dotenv('../.env')

llm = GoogleGenerativeAI(model="gemini-1.5-flash", api_key=os.environ['GEMINI_KEY'])

def matches(competition_id, season_id):
    partidas = sb.matches(competition_id=competition_id, season_id=season_id)
    return partidas

def events(match_id):
    event = sb.events(match_id=match_id)
    return event

def sb_eventos_partida(partida_id):
    eventos = sb.events(match_id=partida_id)
    if 'location' in eventos.columns:
        eventos_validos = eventos[eventos['location'].apply(lambda x: isinstance(x, list) and len(x) == 2)]
        if not eventos_validos.empty:
            eventos_validos.loc[:, ['localizacao_x', 'localizacao_y']] = pd.DataFrame(eventos_validos['location'].tolist(), index=eventos_validos.index)
            eventos = eventos_validos
    return eventos

def lineups(match_id):
    lineup = sb.lineups(match_id=match_id)
    return lineup

def identificar_eventos_por_time(eventos_df):
    times = eventos_df['team'].unique()
    eventos_times = {}

    for time in times:
        eventos_time = eventos_df[eventos_df['team'] == time]

        gols = eventos_time[(eventos_time['type'] == 'Shot') & (eventos_time['shot_outcome'] == 'Goal')]
        gols_por_jogador = gols.groupby('player').size()
        
        assistencias = eventos_time[eventos_time['pass_goal_assist'] == True]
        assistencias_por_jogador = assistencias.groupby('player').size()

        passes = eventos_time[eventos_time['type'] == 'Pass']
        passes_por_jogador = passes.groupby('player').size() if not passes.empty else {}

        finalizacoes = eventos_time[eventos_time['type'] == 'Shot']
        finalizacoes_por_jogador = finalizacoes.groupby('player').size()
        
        cartões_amarelos = eventos_time[ 
            (eventos_time['bad_behaviour_card'] == 'Yellow Card') | (eventos_time['foul_committed_card'] == 'Yellow Card')
        ]
        cartões_vermelhos = eventos_time[ 
            (eventos_time['bad_behaviour_card'] == 'Red Card') | (eventos_time['foul_committed_card'] == 'Red Card')
        ]
        total_cartoes_amarelos = len(cartões_amarelos)
        total_cartoes_vermelhos = len(cartões_vermelhos)

        desarmes = eventos_time[eventos_time['type'] == 'Duel']
        duelos_ganhos = desarmes[desarmes['duel_outcome'] == 'Won'] if 'duel_outcome' in desarmes.columns else desarmes
        interceptacoes = eventos_time[eventos_time['type'] == 'Interception']
        interceptacoes_bem_sucedidas = interceptacoes[interceptacoes['interception_outcome'] == 'Won'] if 'interception_outcome' in interceptacoes.columns else interceptacoes
        recuperacoes_bola = eventos_time[eventos_time['type'] == 'Ball Recovery']
        falhas_recuperacao = recuperacoes_bola[recuperacoes_bola['ball_recovery_recovery_failure'] == True] if 'ball_recovery_recovery_failure' in recuperacoes_bola.columns else None

        eventos_times[time] = {
            "gols": gols_por_jogador,
            "assistencias": assistencias_por_jogador,
            "passes": passes_por_jogador,
            "finalizacoes": finalizacoes_por_jogador,
            "cartoes_amarelos": total_cartoes_amarelos,
            "cartoes_vermelhos": total_cartoes_vermelhos,
            "desarmes_totais": len(desarmes),
            "duelos_ganhos": len(duelos_ganhos),
            "interceptacoes_bem_sucedidas": len(interceptacoes_bem_sucedidas),
            "falhas_recuperacao_bola": len(falhas_recuperacao) if falhas_recuperacao is not None else 0
        }
    
    return eventos_times

def partidas_para_texto(competition_id, season_id):
    partidas = matches(competition_id, season_id)
    if partidas.empty:
        return "Nenhuma partida encontrada para os parâmetros fornecidos."
    
    texto_partidas = ""
    for _, partida in partidas.iterrows():
        texto_partidas += (
            f"Partida ID: {partida['match_id']} - {partida['home_team']} vs {partida['away_team']} "
            f"no estádio {partida['stadium']} em {partida['match_date']}\n"
        )
    return texto_partidas

def gerar_resposta_com_agente(match_id, pergunta):
    eventos = sb_eventos_partida(match_id)
    eventos_times = identificar_eventos_por_time(eventos)
    passes_geral = {}
    gols_geral = {}
    finalizacao_geral = {}
    for time, dados in eventos_times.items():
        passes_geral[time] = dados['passes']
    for time, dados in eventos_times.items():
        gols_geral[time] = dados['gols']
    for time, dados in eventos_times.items():
        finalizacao_geral[time] = dados['finalizacoes']

    tools = [
        Tool(
            name="Analisar Passes",
            func=lambda input: passes_geral,
            description="Analisando os passes de todos os jogadores"
        ),
        Tool(
            name="Analisar Gols",
            func=lambda input: gols_geral,
            description="Analisando os gols feitos pelos jogadores"
        ),
        Tool(
            name="Analisar Finalizações",
            func=lambda input: finalizacao_geral,
            description="Analisando as finalizações feitas pelos jogadores"
        )
    ]
    
    agent = initialize_agent(
        tools, llm, agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True, max_iterations=20
    )
    resposta = agent.run(pergunta)
    return resposta

def gerar_resposta(competition_id, season_id, match_id, pergunta):
    palavras_chave_especificas = ["passes", "gols", "finalizações"]
    
    if any(palavra in pergunta.lower() for palavra in palavras_chave_especificas):
        return gerar_resposta_com_agente(match_id, pergunta)
    else:
        texto_partidas = partidas_para_texto(competition_id, season_id)
        lines = lineups(match_id)
        event = events(match_id)
        eventos = sb_eventos_partida(match_id)
        eventos_agrupados = identificar_eventos_por_time(eventos)
        
        prompt = PromptTemplate(
            input_variables=["dados_partidas"],
            template="Baseado nos seguintes dados:\n\n{dados_partidas}\n\nPergunta:{input}"
        )
        chain = LLMChain(llm=llm, prompt=prompt)
        resposta = chain.run(dados_partidas=[texto_partidas, lines, event, eventos_agrupados], input=pergunta)
        return resposta

def app():
    st.title("Análise de Partidas de Futebol")

    competition_id = st.number_input("ID da Competição", min_value=1, value=43, step=1)
    season_id = st.number_input("ID da Temporada", min_value=1, value=3, step=1)
    match_id = st.number_input("ID da partida", min_value=1, value=7585, step=1)
    pergunta = st.text_input("Digite sua pergunta sobre as partidas")

    if st.button("Gerar Resposta"):
        resposta = gerar_resposta(competition_id, season_id, match_id, pergunta)
        st.subheader("Resposta do Modelo:")
        st.write(resposta)

if __name__ == "__main__":
    app()