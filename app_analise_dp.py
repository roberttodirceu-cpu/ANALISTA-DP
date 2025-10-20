import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
from utils import formatar_moeda, inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes

st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")

# Inicializa armazenamento de bases
if 'bases_carregadas' not in st.session_state:
    st.session_state['bases_carregadas'] = dict()
if 'base_selecionada' not in st.session_state:
    st.session_state['base_selecionada'] = None

# --- Sidebar: Upload, seleção e configuração de colunas ---
with st.sidebar:
    st.header("Bases de Dados Carregadas")
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

    if st.session_state['base_selecionada']:
        base_info = st.session_state['bases_carregadas'][st.session_state['base_selecionada']]
        df_analise_base = base_info['df']
        colunas_disponiveis = df_analise_base.columns.tolist()
        colunas_numericas, colunas_data = encontrar_colunas_tipos(df_analise_base)
        moeda_default = [col for col in colunas_disponiveis if any(word in col.lower() for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
        texto_default = [col for col in colunas_disponiveis if df_analise_base[col].dtype == 'object']
        st.markdown("### Configuração de Colunas")
        col_moeda = st.multiselect("Colunas de Moeda (R$)", options=colunas_disponiveis, default=moeda_default, key="col_moeda")
        col_texto = st.multiselect("Colunas de Texto/ID", options=colunas_disponiveis, default=texto_default, key="col_texto")
        col_filtros = st.multiselect("Colunas para Filtros", options=colunas_disponiveis, default=texto_default, key="col_filtros")

# --- Painel principal ---
if not st.session_state['base_selecionada']:
    st.info("Selecione ou carregue uma base de dados na barra lateral para iniciar a análise.")
else:
    base_info = st.session_state['bases_carregadas'][st.session_state['base_selecionada']]
    df_analise_base = base_info['df']
    nome_base = base_info['nome']
    st.header(f"📊 Dashboard - {nome_base} ({base_info['tipo'].upper()})")

    colunas_disponiveis = df_analise_base.columns.tolist()
    colunas_numericas, colunas_data = encontrar_colunas_tipos(df_analise_base)

    # Recupera configurações do sidebar
    col_moeda = st.session_state.get("col_moeda", [])
    col_texto = st.session_state.get("col_texto", [])
    col_filtros = st.session_state.get("col_filtros", [])
    df_tratado = inferir_e_converter_tipos(df_analise_base, col_texto, col_moeda)
    colunas_para_filtro = col_filtros if col_filtros else col_texto

    st.caption(f"Base carregada em {base_info['data_upload']}, {len(df_analise_base)} registros, {len(colunas_disponiveis)} colunas.")

    # -- FILTROS RÁPIDOS COM 'Selecionar Todos' --
    st.markdown("### Filtros de Análise Rápida")
    current_selections = {}
    for col in colunas_para_filtro:
        opcoes_unicas = sorted(df_tratado[col].astype(str).unique())
        with st.expander(f"{col} ({len(opcoes_unicas)} opções)"):
            col1_btn, col2_btn = st.columns([1,1])
            select_all = col1_btn.checkbox("Selecionar Todos", key=f"select_all_{col}")
            clear_all = col2_btn.checkbox("Limpar", key=f"clear_all_{col}")
            if select_all:
                selecao = opcoes_unicas
            elif clear_all:
                selecao = []
            else:
                selecao = st.multiselect("Selecione:", options=opcoes_unicas, key=f"multi_{col}")
            current_selections[col] = selecao

    # Aplica filtros
    df_filtrado = df_tratado.copy()
    for col, selecao in current_selections.items():
        if selecao:
            df_filtrado = df_filtrado[df_filtrado[col].astype(str).isin(selecao)]

    st.markdown("### Visualização dos Dados")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    # Exemplo de gráfico simples
    st.markdown("### Gráfico de Coluna Numérica")
    if colunas_numericas:
        coluna_grafico = st.selectbox("Coluna numérica para gráfico", colunas_numericas)
        st.plotly_chart(
            px.histogram(df_filtrado, x=coluna_grafico, title=f"Histograma de {coluna_grafico}"),
            use_container_width=True
        )

    # Download da base selecionada
    csv_data = df_analise_base.to_csv(index=False, sep=';', decimal=',', encoding='utf-8')
    st.download_button(
        label=f"📥 Baixar {nome_base} (CSV)",
        data=csv_data,
        file_name=f'{nome_base}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
        mime='text/csv',
    )
