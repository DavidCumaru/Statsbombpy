import streamlit as st
from statsbombpy import sb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def load_match_data(competition_id, season_id):
    try:
        matches = sb.matches(competition_id=competition_id, season_id=season_id)
        return matches
    except Exception as e:
        st.error(f"Erro ao carregar dados das partidas: {e}")
        return pd.DataFrame()

def load_events_data(match_id):
    try:
        events = sb.events(match_id=match_id)
        return events
    except Exception as e:
        st.error(f"Erro ao carregar dados dos eventos: {e}")
        return pd.DataFrame()

def display_match_summary(match):
    try:
        st.write(f"**Time da Casa:** {match['home_team']} (ID: {match['home_team']})")
        st.write(f"**Time Visitante:** {match['away_team']} (ID: {match['away_team']})")
        st.write(f"**Placar:** {match['home_score']} x {match['away_score']}")
        st.write(f"**Data:** {match['match_date']}")
        st.write(f"**Competição:** {match['competition']}")
        st.write(f"**Temporada:** {match['season']}")
    except KeyError as e:
        st.error(f"Erro ao acessar informações da partida: {str(e)}")
    except TypeError as e:
        st.error(f"Erro de tipo ao acessar informações da partida: {str(e)}")

def display_player_profile(events, player_id):
    try:
        player_events = events[events['player'] == player_id]
        
        passes = len(player_events[player_events['type'] == 'Pass'])
        shots = len(player_events[player_events['type'] == 'Shot'])
        tackles = len(player_events[player_events['type'] == 'Tackle'])
        
        goals = len(player_events[(player_events['type'] == 'Shot') & 
                                (player_events['shot_outcome'].notna()) & 
                                (player_events['shot_outcome'] == 'Goal')])
        
        yellow_cards = len(player_events[(player_events['type'] == 'Foul Committed') & 
                                        (player_events['foul_committed_card'] == 'Yellow Card')])
        red_cards = len(player_events[(player_events['type'] == 'Foul Committed') & 
                                    (player_events['foul_committed_card'] == 'Red Card')])

        minutes_played = player_events['minute'].max() - player_events['minute'].min() if len(player_events) > 0 else 0

        st.write(f"**Jogador:** {player_id}")
        st.write(f"**Passes:** {passes}")
        st.write(f"**Finalizações:** {shots}")
        st.write(f"**Gols:** {goals}")
        st.write(f"**Desarmes:** {tackles}")
        st.write(f"**C.Amarelos:** {yellow_cards}")
        st.write(f"**C.Vermelhos:** {red_cards}")
        st.write(f"**Min.Jogados:** {minutes_played}")
        
        stats = {
            'Passes': passes,
            'Finalizações': shots,
            'Gols': goals,
            'Desarmes': tackles,
            'C.Amarelos': yellow_cards,
            'C.Vermelhos': red_cards
        }
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(stats.keys(), stats.values(), color='skyblue')
        ax.set_ylabel('Número de Ações')
        ax.set_title(f'Estatísticas de {player_id}')
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Erro ao acessar o perfil do jogador: {str(e)}")

def compare_players(events, player1_id, player2_id):
    try:
        player1_events = events[events['player'] == player1_id]
        player2_events = events[events['player'] == player2_id]
        
        player1_stats = {
            'Passes': len(player1_events[player1_events['type'] == 'Pass']),
            'Finalizações': len(player1_events[player1_events['type'] == 'Shot']),
            'Gols': len(player1_events[(player1_events['type'] == 'Shot') & (player1_events['shot_outcome'] == 'Goal')]),
            'Desarmes': len(player1_events[player1_events['type'] == 'Tackle'])
        }

        player2_stats = {
            'Passes': len(player2_events[player2_events['type'] == 'Pass']),
            'Finalizações': len(player2_events[player2_events['type'] == 'Shot']),
            'Gols': len(player2_events[(player2_events['type'] == 'Shot') & (player2_events['shot_outcome'] == 'Goal')]),
            'Desarmes': len(player2_events[player2_events['type'] == 'Tackle'])
        }
        

        fig, ax = plt.subplots()
        width = 0.4
        x = range(len(player1_stats))
        
        ax.bar(x, player1_stats.values(), width, label=player1_id, color='lightcoral')
        ax.bar([p + width for p in x], player2_stats.values(), width, label=player2_id, color='skyblue')
        
        ax.set_ylabel('Número de Ações')
        ax.set_title('Comparação entre Jogadores')
        ax.set_xticks([p + width / 2 for p in x])
        ax.set_xticklabels(player1_stats.keys())
        ax.legend()
        st.pyplot(fig)    
    except Exception as e:
        st.error(f"Erro ao comparar os jogadores: {str(e)}")

def main():
    st.title("Interface Avançada - Análise de Partidas de Futebol")

    competition_id = st.number_input("ID da Competição:", min_value=1, step=1)
    season_id = st.number_input("ID da Temporada:", min_value=1, step=1)

    if "matches" not in st.session_state:
        st.session_state.matches = pd.DataFrame()

    if st.button("Carregar Partidas"):
        matches = load_match_data(competition_id, season_id)
        if not matches.empty:
            st.session_state.matches = matches
            matches['match_display'] = matches.apply(lambda x: f"{x['home_team']} x {x['away_team']} ({x['match_date']})", axis=1)
            match_dict = matches.set_index("match_id")['match_display'].to_dict()
            st.session_state.match_dict = match_dict

    if not st.session_state.matches.empty:
        match_id = st.selectbox("Selecione uma Partida:", options=list(st.session_state.match_dict.keys()), format_func=lambda x: st.session_state.match_dict[x])

        selected_match = st.session_state.matches[st.session_state.matches["match_id"] == match_id].iloc[0]
        st.subheader("Resumo da Partida")
        display_match_summary(selected_match)

        events = load_events_data(match_id)
        if not events.empty:
            players = events['player'].unique()
            player_id = st.selectbox("Selecione um Jogador:", options=players)

            if player_id:
                st.subheader("Perfil do Jogador")
                display_player_profile(events, player_id)

            st.subheader("Comparar Jogadores")
            player1_id = st.selectbox("Selecione o 1º Jogador para Comparação:", options=players)
            player2_id = st.selectbox("Selecione o 2º Jogador para Comparação:", options=players)

            if player1_id and player2_id:
                compare_players(events, player1_id, player2_id)

if __name__ == "__main__":
    main()