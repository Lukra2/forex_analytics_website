PAINEL OURO (XAUUSD)

1) Requisitos: Windows, Python 3.10+, MetaTrader 5 aberto e logado na sua conta (demo ou real).
   No MT5, confira se o símbolo aparece no Market Watch (na sua corretora pode ser XAUUSD, GOLD, XAUUSD.a...).

2) Instalar (PowerShell, dentro da pasta):
   pip install -r requirements.txt

3) Configurar o arquivo .env na pasta do projeto:
   OPENAI_API_KEY=sua-chave
   OPENAI_MODEL=gpt-6-luna
   SYMBOL=XAUUSD
   Use o nome exato do símbolo na sua corretora. Variáveis já definidas no ambiente têm prioridade sobre o .env.

4) Rodar:
   uvicorn server:app --host 0.0.0.0 --port 8000

5) Abrir: http://localhost:8000
   No celular (mesmo Wi-Fi): http://IP-DO-SEU-PC:8000

Notas:
- Sem OPENAI_API_KEY o painel funciona, só sem a análise de IA.
- O calendário vem do feed semanal do Forex Factory (não oficial). Pode mudar ou sair do ar.
- Não use como gatilho automático. Teste em conta demo.

Eventos USD e cenários:
- O painel mostra até 8 eventos recentes (últimas 48 horas) e 8 próximos (até 72 horas) disponíveis no calendário semanal.
- Com OPENAI_API_KEY, a IA considera esses eventos e cria cenários condicionais para o XAUUSD. A análise é atualizada a cada consulta de notícias quando os dados mudam.
- O resultado divulgado só aparece se estiver disponível no feed; dados ausentes não são estimados. Em caso de falha, o último calendário disponível pode permanecer na tela.
- O calendário é consultado a cada 5 minutos. A IA é atualizada quando os dados mudam e, mesmo sem mudanças, aproximadamente a cada 15 minutos; essas consultas usam a API da OpenAI.

Estrutura do projeto:
- server.py: inicializa a API e coordena as atualizações em segundo plano.
- backend/indicators.py: calcula indicadores e padrões de candles.
- backend/news_fetch.py: consulta notícias e calendário econômico.
- backend/ai_analysis.py: prepara eventos e solicita a análise de IA.
- frontend/index.html e static/main.css / static/main.js: interface do painel.
