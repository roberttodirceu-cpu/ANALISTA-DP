import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime
from io import BytesIO
from utils import formatar_moeda, inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes

st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")

# Inicializa armazenamento de bases
if 'bases_carregadas' not in st.session_state:
    st.session_state['bases_carregadas'] = dict()     # key: nome do arquivo + timestamp, value: dict com df e metadados
if 'base_selecionada' not in st.session_state:
    st.session_state['base_selecionada'] = None

# --- Sidebar: Upload e gestão das bases ---
with st.sidebar:
    st.header("Bases de Dados Carregadas")
    # Mostra lista de bases com opção de seleção e exclusão
    bases = st.session_state['bases_carregadas']
    keys_list = list(bases.keys())
    if keys_list:
        for key in keys_list:
            base_info = bases[key]
            col1, col2, col3 = st.columns([6,1,1])
            with col1:
                if st.button(f"🔍 {base_info['nome']}", key=f"btn_select_{key}"):
                    st.session_state['base_selecionada'] = key
                    st.rerun()
            with col2:
                st.caption(base_info['tipo'].upper())
            with col3:
                if st.button("🗑️", key=f"btn_delete_{key}"):
                    del st.session_state['bases_carregadas'][key]
                    if st.session_state.get('base_selecionada') == key:
                        st.session_state['base_selecionada'] = None
                    st.rerun()
    else:
        st.info("Nenhuma base carregada. Faça upload abaixo.")

    st.markdown("---")
    st.header("Upload de Nova Base")
    uploaded_file = st.file_uploader("📥 Carregar Novo CSV/XLSX", type=['csv', 'xlsx'])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                uploaded_file.seek(0)
                try:
                    df_novo = pd.read_csv(uploaded_file, sep=';', decimal=',', encoding='utf-8')
                except:
                    uploaded_file.seek(0)
                    df_novo = pd.read_csv(uploaded_file, sep=',', decimal='.', encoding='utf-8')
                tipo_arquivo = 'csv'
            elif uploaded_file.name.endswith('.xlsx'):
                df_novo = pd.read_excel(uploaded_file)
                tipo_arquivo = 'xlsx'
            else:
                st.error("Tipo de arquivo não suportado.")
                df_novo = pd.DataFrame()
                tipo_arquivo = 'desconhecido'
            if df_novo.empty:
                st.error("O arquivo carregado está vazio ou não pôde ser lido corretamente.")
                raise ValueError("DataFrame vazio após leitura.")

            # Armazena base no session_state
            key_base = f"{uploaded_file.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state['bases_carregadas'][key_base] = {
                'nome': uploaded_file.name,
                'df': df_novo.copy(),
                'tipo': tipo_arquivo,
                'data_upload': datetime.now().strftime('%Y-%m-%d %H:%M'),
            }
            st.session_state['base_selecionada'] = key_base
            st.success(f"Base '{uploaded_file.name}' carregada e pronta para análise!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro no processamento do arquivo: {e}")

# --- Dashboard principal ---
if not st.session_state['base_selecionada']:
    st.info("Selecione ou carregue uma base de dados na barra lateral para iniciar a análise.")
else:
    # Recupera DataFrame e metadados da base selecionada
    base_info = st.session_state['bases_carregadas'][st.session_state['base_selecionada']]
    df_analise_base = base_info['df']
    nome_base = base_info['nome']
    st.header(f"📊 Dashboard - {nome_base} ({base_info['tipo'].upper()})")

    # Exemplo de processamento - você pode adaptar para seus filtros e gráficos
    colunas_disponiveis = df_analise_base.columns.tolist()
    colunas_numericas, colunas_data = encontrar_colunas_tipos(df_analise_base)

    st.caption(f"Base carregada em {base_info['data_upload']}, {len(df_analise_base)} registros, {len(colunas_disponiveis)} colunas.")

    # Filtros simples para análise
    st.markdown("### Filtros Rápidos")
    filtro_coluna = st.selectbox("Coluna para filtrar", colunas_disponiveis)
    opcoes_filtro = sorted(df_analise_base[filtro_coluna].astype(str).unique())
    valores_selecionados = st.multiselect("Valores para análise", opcoes_filtro)
    if valores_selecionados:
        df_filtrado = df_analise_base[df_analise_base[filtro_coluna].astype(str).isin(valores_selecionados)]
    else:
        df_filtrado = df_analise_base

    st.markdown("---")
    st.subheader("Visualização dos Dados")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    # Exemplo de gráfico
    if colunas_numericas:
        coluna_grafico = st.selectbox("Coluna numérica para gráfico", colunas_numericas)
        st.plotly_chart(px.histogram(df_filtrado, x=coluna_grafico, title=f"Histograma de {coluna_grafico}"), use_container_width=True)

    # Download da base selecionada
    csv_data = df_analise_base.to_csv(index=False, sep=';', decimal=',', encoding='utf-8')
    st.download_button(
        label=f"📥 Baixar {nome_base} (CSV)",
        data=csv_data,
        file_name=f'{nome_base}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
        mime='text/csv',
    )
