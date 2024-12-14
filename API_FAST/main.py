from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from statsbombpy import sb
import google.generativeai as genai
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import os
from dotenv import load_dotenv
load_dotenv('../.env')

app = FastAPI()

class MatchSummaryResponse(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    competition: str
    competition_stage: str
    stadium: str
    referee: str
    home_managers: str
    away_managers: str
    season: str
    match_date: str
    kick_off: str

class PlayerProfileResponse(BaseModel):
    player_id: int
    player_name: str
    passes: int
    shots: int
    tackles: int
    minutes_played: int

class TeamEventsResponse(BaseModel):
    team: str
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    tackles: int
    goal_scorers: list[str]
    goal_count_per_player: dict
    assist_providers: list[str]

class TeamEventsNarrationResponse(BaseModel):
    events_summary: list[TeamEventsResponse]
    narration: str

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

@app.get("/match_summary", response_model=MatchSummaryResponse)
async def match_summary(
    competition_id: int = Query(..., description="ID da competição"),
    season_id: int = Query(..., description="ID da temporada"),
    match_id: int = Query(..., description="ID da partida")
):
    try:
        matches = sb.matches(competition_id=competition_id, season_id=season_id)
        match = matches[matches["match_id"] == match_id]
        if match.empty:
            raise HTTPException(status_code=404, detail="Partida não encontrada")

        match_data = match.iloc[0]
        return {
            "match_id": int(match_data["match_id"]),
            "home_team": match_data["home_team"],
            "away_team": match_data["away_team"],
            "home_score": int(match_data["home_score"]),
            "away_score": int(match_data["away_score"]),
            "competition": match_data["competition"],
            "competition_stage": match_data["competition_stage"],
            "stadium": match_data["stadium"],
            "referee": match_data["referee"],
            "home_managers": match_data["home_managers"],
            "away_managers": match_data["away_managers"],
            "season": match_data["season"],
            "match_date": match_data["match_date"],
            "kick_off": match_data["kick_off"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter resumo da partida: {str(e)}")

@app.get("/player_profile", response_model=PlayerProfileResponse)
async def player_profile(
    match_id: int = Query(..., description="ID da partida"),
    player_id: int = Query(..., description="ID do jogador")
):
    try:
        events = sb.events(match_id=match_id)

        player_events = events[events["player_id"] == player_id]
        if player_events.empty:
            raise HTTPException(status_code=404, detail="Jogador não encontrado na partida")
        
        passes = len(player_events[player_events["type"] == "Pass"])
        shots = len(player_events[player_events["type"] == "Shot"])
        tackles = len(player_events[player_events["type"] == "Tackle"])
        minutes_played = player_events["minute"].max() - player_events["minute"].min()

        player_name = player_events.iloc[0]["player"]
        return {
            "player_id": player_id,
            "player_name": player_name,
            "passes": passes,
            "shots": shots,
            "tackles": tackles,
            "minutes_played": minutes_played,
        }
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"Chave inválida: {e}")

@app.get("/team_events", response_model=TeamEventsNarrationResponse)
async def team_events(
    match_id: int = Query(..., description="ID da partida"),
    narration_style: int = Query(1, description="Estilo da narração: 1-Formal, 2-Humorístico, 3-Técnico")
):
    try:
        eventos = sb_eventos_partida(match_id)
        eventos_agrupados = identificar_eventos_por_time(eventos)
        team_events_summary = []

        for team, data in eventos_agrupados.items():
            team_events_summary.append({
                "team": team,
                "goals": sum(data["gols"]),
                "goal_scorers": list(data["jogadores_gols"]),
                "goal_count_per_player": data["gols"].to_dict(),
                "assists": sum(data["assistencias"]),
                "assist_providers": list(data["jogadores_assistencias"]),
                "yellow_cards": data["cartoes_amarelos"],
                "red_cards": data["cartoes_vermelhos"],
                "tackles": data["desarmes_totais"],
            })

        estilos_narracao = ["formal", "humorística", "técnica"]
        estilo_selecionado = estilos_narracao[narration_style - 1]
        
        genai.configure(api_key=os.environ["GEMINI_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"Resumo dos eventos: {team_events_summary}. Narre de forma {estilo_selecionado} os eventos da partida."
        response = model.generate_content(prompt)

        return {
            "events_summary": team_events_summary,
            "narration": response.text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar eventos da partida: {str(e)}")