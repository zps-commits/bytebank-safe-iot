"""Execute na raiz: python -m streamlit run dashboard/app.py"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import sqlite3
from urllib.error import URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import streamlit as st
import altair as alt
from dashboard.data import snapshot, send_command

st.set_page_config(page_title='ByteBank Safe', page_icon='📦', layout='wide')
st.title('ByteBank Safe')
st.caption('Monitoramento da ESP32 · Envelopes, sensor e comandos remotos')
DB=os.environ.get('SAFE_DB','bytebank-safe.sqlite3')
BASE=os.environ.get('SAFE_API_BASE','http://127.0.0.1:8000')
st.sidebar.header('Conexão local')
st.sidebar.caption('Banco SQLite: '+str(Path(DB).resolve()))
st.sidebar.caption('API: '+BASE)
st.sidebar.info('Dados atualizados a cada 2 s enquanto esta página estiver aberta. Sem valores financeiros.')

def show_distance(history):
    st.subheader('Distância do sensor')
    recent = history.tail(30).reset_index()
    valid = recent.dropna(subset=['distance_cm'])
    current = recent.iloc[-1]['distance_cm']
    a, b, c = st.columns(3)
    a.metric('Distância atual', f'{current:.1f} cm' if pd.notna(current) else '—')
    b.metric('Média recente', f"{valid['distance_cm'].mean():.1f} cm" if not valid.empty else '—')
    c.metric('Leituras com eco', f'{len(valid)} / {len(recent)}')
    if valid.empty:
        st.info('Sem distância disponível nas leituras recentes. Confira se o modo sensor está ativo e se há um alvo à frente.')
        return
    bars = alt.Chart(recent).mark_bar(color='#08968d', cornerRadiusEnd=3).encode(
        x=alt.X('id:O', sort='ascending', axis=alt.Axis(title='Leituras recentes', labels=False, ticks=False)),
        y=alt.Y('distance_cm:Q', title='Distância (cm)', scale=alt.Scale(zero=True)),
        tooltip=[
            alt.Tooltip('recebido_em:N', title='Horário (UTC)'),
            alt.Tooltip('distance_cm:Q', title='Distância (cm)', format='.1f'),
        ],
    ).properties(height=224)
    st.altair_chart(bars, use_container_width=True)
    st.caption('Até 30 amostras. Lacunas indicam ausência de leitura. A média usa somente leituras com eco.')

@st.fragment(run_every='2s')
def live():
    try:
        first=snapshot(DB)
        if not first['devices']:
            st.info('Nenhum dispositivo registrado. Inicie a ESP32 ou o simulador de PC para receber telemetria.')
            return
        device=st.selectbox('Dispositivo',first['devices'],key='device')
        data=snapshot(DB,device)
    except (sqlite3.Error,OSError) as exc:
        st.error('Banco indisponível. Inicie a API e confira SAFE_DB. '+str(exc))
        return
    last=data['telemetry'][0] if data['telemetry'] else None
    if last:
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(last['recebido_em']).replace(tzinfo=timezone.utc)).total_seconds()
        if last['source']=='simulator_pc': st.warning('SIMULAÇÃO NO PC — estes dados não comprovam funcionamento da ESP32 física.')
        else: st.caption('Origem informada pelo firmware: '+last['source']+' · a identificação não é autenticação de hardware.')
        if age <= 15: st.success(f'Comunicação recente · última telemetria há {max(0,int(age))} s')
        else: st.warning(f'Sem atualização há {int(age)} s. Verifique a conexão do dispositivo.')
    else: st.warning('Há eventos no banco, mas ainda não chegou telemetria da Parcial 4.')
    counts={r['estado']:r['quantidade'] for r in data['lots']}
    a,b,c,d=st.columns(4)
    a.metric('Pendentes no banco',counts.get('pendente',0))
    b.metric('Confirmados no banco',counts.get('confirmado',0))
    c.metric('Cancelados no banco',counts.get('cancelado',0))
    d.metric('Contador de diagnóstico',last['diagnostic_count'] if last else '—')
    if last:
        st.caption(f"ESP32 informa: {last['pending_count']} pendentes · fila HTTP: {last['queue_size']} · uptime: {last['uptime_ms']//1000} s")
        history=pd.DataFrame(data['telemetry']).sort_values('id').set_index('id')
        show_distance(history)
    st.subheader('Comando remoto')
    st.write('Zerar o contador de detecções da sessão. Preserva depósitos pendentes, confirmações e auditoria.')
    if 'command_request_id' not in st.session_state: st.session_state.command_request_id=str(uuid4())
    if st.button('Resetar contador no dispositivo',key='reset_counter',disabled=not bool(last)):
        try:
            result=send_command(BASE,device,st.session_state.command_request_id)
            st.session_state.command_request_id=str(uuid4())
            st.success('Comando registrado: '+result['command_id']+'. Aguarde o ACK do dispositivo na tabela abaixo.')
        except (URLError,OSError,ValueError) as exc:
            st.error('Não foi possível confirmar o envio. O mesmo identificador será reutilizado ao tentar novamente. '+str(exc))
    st.caption('pending = aguardando execução; applied = execução confirmada pelo dispositivo; failed = falha reportada.')
    st.dataframe(pd.DataFrame(data['commands']),hide_index=True,use_container_width=True)
    left,right=st.columns(2)
    with left:
        st.subheader('Histórico da contagem')
        if last:
            st.line_chart(history[['diagnostic_count','pending_count']])
    with right:
        st.subheader('Últimos eventos persistidos')
        st.dataframe(pd.DataFrame(data['events']),hide_index=True,use_container_width=True)
    st.caption('Atualizado em '+datetime.now(timezone.utc).strftime('%H:%M:%S UTC'))

live()
