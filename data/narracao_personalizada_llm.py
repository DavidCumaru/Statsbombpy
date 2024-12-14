from statsbombpy import sb
import google.generativeai as genai
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import os
from dotenv import load_dotenv
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

def obter_narracao():
    opcoes_narracao = {
        1: "Formal: Narração técnica e objetiva, focada em detalhes táticos e estatísticas.",
        2: "Humorístico: Narração descontraída e criativa, com pitadas de humor e personalidade.",
        3: "Técnico: Análise detalhada dos eventos, focando em desempenho e estratégia dos jogadores."
    }

    while True:
        try:
            narracao = int(input("Qual narração você deseja?\n1 - Formal (técnico e objetivo)\n2 - Humorístico (descontraído e criativo)\n3 - Técnico (análise detalhada dos eventos)\nEscolha (1, 2 ou 3): "))
            if narracao in opcoes_narracao:
                return opcoes_narracao[narracao]
            else:
                print("Escolha inválida! Por favor, selecione uma opção válida (1, 2 ou 3).")
        except ValueError:
            print("Entrada inválida! Por favor, insira um número inteiro (1, 2 ou 3).")

partida_id = input("Qual é o id da partida? ")
narracao = obter_narracao()
eventos = sb_eventos_partida(partida_id)

eventos_resumo = identificar_eventos_por_time(eventos)

print("Resumo dos eventos principais por time:")
for time, eventos_time in eventos_resumo.items():
    print(f"\nTime: {time}")
    print(f"Gols: {sum(eventos_time['gols'])} ({', '.join([f'{jogador}: {eventos_time['gols'][jogador]}' for jogador in eventos_time['gols'].index])})")
    print(f"Assistências: {sum(eventos_time['assistencias'])} ({', '.join([f'{jogador}: {eventos_time['assistencias'][jogador]}' for jogador in eventos_time['assistencias'].index])})")
    print(f"Cartões: {eventos_time['cartoes_amarelos'] + eventos_time['cartoes_vermelhos']} (Amarelos: {eventos_time['cartoes_amarelos']}, Vermelhos: {eventos_time['cartoes_vermelhos']})")
    print(f"Desarmes Totais: {eventos_time['desarmes_totais']}")
    print(f"Duelos Ganhos: {eventos_time['duelos_ganhos']}")
    print(f"Interceptações Bem-sucedidas: {eventos_time['interceptacoes_bem_sucedidas']}")
    print(f"Falhas na Recuperação de Bola: {eventos_time['falhas_recuperacao_bola']}")

prompt = f"""
{eventos_resumo} Com base nesses dados, faz uma narração de maneira {narracao} sobre a partida.
"""

genai.configure(api_key=os.environ['GEMINI_KEY'])
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content(prompt)
print(response.text)