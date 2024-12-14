# Realização das tarefas do AT de Desenvolvimento de Data-Driven Apps com Python

## Rodar o projeto 

Crie um .env e coloque sua GEMINI_KEY.

As pastas streamlit não estão paginadas então terá que rodar 1 por 1.

Crie um venv e baixe os requirements necessários para rodar o projeto.

## Estrutura do projeto

AT  

    API_FAST  
        main.py  
    data  
        detalhes.ipynb  
        narracao_personalizada_llm.py  
    streamlit  
        api_st.py  
        lang_llm.py  
        main_st.py  
        narracao_personalizada_st.py  

## Detalhação de cada arquivo

### API_FAST/main.py realizda a terefa API FAST contendo:

/match_summary: Retorna a sumarização de uma partida.

/player_profile: Retorna o perfil detalhado de um jogador.

/team_events: Retorna uma narrativa de uma partida com a escolha do usuário (Formal, técnico e humoristico)

### data/detalhes.py realiza tarefa simples de confirmação de criação uma função simples que receba uma ID de partida e retorne os dados brutos dessa partida utilizando a API do statsbombpy, Sumarização de Partidas com LLM e Criação de Perfil de Jogador.

### data/narracao_personalizada_llm.py realizada tarefa de criar uma função para criar uma narração personalizada de uma partida.

### streamlit/api_st.py utiliza streamlit com os dados da API_FAST local (match_summary, player_profile, team_events)

### streamlit/lang_llm.py com streamlit realiza uma tarefa de LLM com langchain que retorna detalhes de uma partida, jogador entre outros.

### streamlit/main_st.py com streamlit retorna detalhes de uma partida e faz comparações entre jogadores.
