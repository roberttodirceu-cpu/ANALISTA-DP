# app.py - Versão FINAL e COMPLETA com Ajuste de Nomeação de Dataset

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime
from io import BytesIO
import pickle
import re
import unicodedata

# ==============================================================================
# FUNÇÕES ESSENCIAIS (Simuladas - Usar o utils.py se fosse ambiente de produção)
# ==============================================================================
def formatar_moeda(valor): 
    # Tenta lidar com NaN
    if pd.isna(valor): return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_string(text):
    if pd.isna(text): return 'N/A'
    return str(text).strip()

def limpar_nome_coluna(col):
    if not isinstance(col, str): return str(col).lower()
    
    col = col.strip().lower()
    # Remove acentos e caracteres especiais (e.g., \xa0)
    col = unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
    col = re.sub(r'[^a-z0-9]+', '_', col) 
    col = col.strip('_')
    return col

def inferir_e_converter_tipos(df, cols_texto, cols_valor): 
    df_clean = df.copy()

    # 1. Limpeza e Conversão de Colunas de Texto/Categoria
    for col in cols_texto:
        if col in df_clean.columns:
            # Aplica limpeza para remover espaços em branco invisíveis e padronizar
            df_clean[col] = df_clean[col].apply(limpar_string).astype('category')

    # 2. Conversão de Colunas de Valor (Numéricas)
    for col in cols_valor:
        if col in df_clean.columns:
            # Limpeza robusta para colunas de valor
            try:
                # Converte para string e remove todos os caracteres que não sejam dígitos, vírgula ou ponto
                df_clean[col] = df_clean[col].astype(str).str.replace(r'[^\d,\.-]', '', regex=True)
                
                # Tenta lidar com a notação brasileira (milhar=ponto, decimal=vírgula)
                if df_clean[col].str.contains(r','):
                    # Remove pontos (milhar) e substitui vírgulas (decimal) por ponto
                    df_clean[col] = df_clean[col].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                
                # Coerce to numeric (erros se tornam NaN)
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                df_clean[col].fillna(0, inplace=True) # Preenche NaN após coerção com 0
            except:
                st.warning(f"Aviso: Falha ao converter a coluna '{col}' para numérica.")
                
    return df_clean 

def encontrar_colunas_tipos(df): 
    # Simulação baseada em heurística para df já processado
    cols_date = []
    cols_numeric = df.select_dtypes(include=np.number).columns.tolist()
    
    # Heurística para colunas de data (se tiverem ano/mes, mas estão como categoria)
    if 'ano' in df.columns and 'mes' in df.columns and 'mes' in df.select_dtypes(include=['category', 'object']).columns:
        cols_date = ['ano', 'mes']

    return cols_numeric, cols_date

def gerar_rotulo_filtro(df_completo, filtros_ativos, colunas_data, data_range): 
    if not filtros_ativos: return "NENHUM FILTRO CATEGÓRICO ATIVO (Todos os dados estão inclusos)."
    
    rotulo = []
    for col, valores in filtros_ativos.items():
        if valores and len(valores) > 0:
            # Obter todas as opções únicas do DF completo para a coluna
            opcoes_unicas = df_completo[col].astype(str).fillna('N/A').unique().tolist()
            
            # Se a seleção for a totalidade das opções, ignora (não é um filtro)
            if len(valores) == len(opcoes_unicas):
                continue

            rotulo.append(f"**{col.title()}:** {', '.join(sorted(valores))[:100]}...") # Limita a 100 caracteres

    if not rotulo:
        return "NENHUM FILTRO CATEGÓRICO ATIVO (Todas as opções foram selecionadas)."

    return "<br>".join(rotulo)


# ==============================================================================

# --- Configuração da Página e Persistência ---
st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")
PERSISTENCE_PATH = 'data/data_sets_catalog.pkl' 

# ==============================================================================
# FUNÇÕES DE GERENCIAMENTO DE ESTADO E PERSISTÊNCIA
# ==============================================================================

def load_catalog():
    if os.path.exists(PERSISTENCE_PATH):
        try:
            with open(PERSISTENCE_PATH, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return {}
    return {}

def save_catalog(catalog):
    try:
        # Garante que o diretório exista
        os.makedirs(os.path.dirname(PERSISTENCE_PATH), exist_ok=True) 
        with open(PERSISTENCE_PATH, 'wb') as f:
            pickle.dump(catalog, f)
    except Exception as e:
        st.sidebar.error(f"Erro ao salvar dados de persistência: {e}")

def limpar_filtros_salvos():
    """Limpa o estado de todos os filtros, forcando os widgets a resetarem ao default."""
    st.session_state.active_filters_base = {}
    st.session_state.active_filters_comp = {}
    
    # Incrementa o trigger para forçar a reexecução e recálculo dos filtros cacheados
    if 'filtro_reset_trigger' not in st.session_state: st.session_state['filtro_reset_trigger'] = 0
    st.session_state['filtro_reset_trigger'] += 1
    
    # Limpa as chaves de sessão para os widgets de filtro e data
    chaves_a_limpar = [
        key for key in st.session_state.keys() 
        if key.startswith('filtro_key_base_') or key.startswith('date_range_key_base_') or 
           key.startswith('filtro_key_comp_') or key.startswith('date_range_key_comp_')
    ]
    for key in chaves_a_limpar:
        try:
            del st.session_state[key]
        except:
            pass
            
    #st.rerun() # O st.rerun só é necessário se esta função for chamada fora de um fluxo que já causa rerender

def set_multiselect_all(key, suffix, options_list):
    """Callback para o botão 'Selecionar Tudo'."""
    st.session_state[f'filtro_key_{suffix}_{key}'] = options_list
    

def set_multiselect_none(key, suffix):
    """Callback para o botão 'Limpar'."""
    st.session_state[f'filtro_key_{suffix}_{key}'] = []
    
def switch_dataset(dataset_name):
    """Troca o dataset ativo no dashboard."""
    if dataset_name in st.session_state.data_sets_catalog:
        data = st.session_state.data_sets_catalog[dataset_name]
        st.session_state.dados_atuais = data['df']
        st.session_state.colunas_filtros_salvas = data['colunas_filtros_salvas']
        st.session_state.colunas_valor_salvas = data['colunas_valor_salvas']
        st.session_state.current_dataset_name = dataset_name
        
        default_exclude = [col for col in data['df'].columns if col in ['emp', 'eve', 'seq', 'nr_func']]
        st.session_state.cols_to_exclude_analysis = default_exclude
        
        limpar_filtros_salvos()
        st.rerun() # Força a re-renderização com o novo dataset
    else:
        st.error(f"Dataset '{dataset_name}' não encontrado.")

def show_reconfig_panel():
    st.session_state.show_reconfig_section = True
    
def processar_dados_atuais(df_novo, colunas_filtros, colunas_valor, dataset_name):
    
    # CRÍTICO: Usa o nome passado, que já foi extraído do nome do arquivo
    base_name = dataset_name 
        
    st.session_state.data_sets_catalog[base_name] = {
        'df': df_novo,
        'colunas_filtros_salvas': colunas_filtros,
        'colunas_valor_salvas': colunas_valor,
    }
    
    save_catalog(st.session_state.data_sets_catalog)
    
    st.session_state.dados_atuais = df_novo 
    st.session_state.colunas_filtros_salvas = colunas_filtros
    st.session_state.colunas_valor_salvas = colunas_valor
    st.session_state.current_dataset_name = base_name 
    
    default_exclude = [col for col in df_novo.columns if col in ['emp', 'eve', 'seq', 'nr_func']]
    st.session_state.cols_to_exclude_analysis = default_exclude
    
    return True, df_novo

def initialize_widget_state(key, initial_default_calc):
    if key not in st.session_state:
        st.session_state[key] = initial_default_calc
# ==============================================================================

# --- Inicialização de Estado da Sessão ---
if 'data_sets_catalog' not in st.session_state: st.session_state.data_sets_catalog = load_catalog()
if 'filtro_reset_trigger' not in st.session_state: st.session_state['filtro_reset_trigger'] = 0

initial_df = pd.DataFrame()
initial_filters = []
initial_values = []
initial_name = ""
if st.session_state.data_sets_catalog:
    # Tenta carregar o último dataset salvo
    last_name = list(st.session_state.data_sets_catalog.keys())[-1]
    data = st.session_state.data_sets_catalog[last_name]
    initial_df = data['df']
    initial_filters = data['colunas_filtros_salvas']
    initial_values = data['colunas_valor_salvas']
    initial_name = last_name

if 'dados_atuais' not in st.session_state: st.session_state.dados_atuais = initial_df
if 'colunas_filtros_salvas' not in st.session_state: st.session_state.colunas_filtros_salvas = initial_filters
if 'colunas_valor_salvas' not in st.session_state: st.session_state.colunas_valor_salvas = initial_values
if 'current_dataset_name' not in st.session_state: st.session_state.current_dataset_name = initial_name
    
if 'uploaded_files_data' not in st.session_state: st.session_state.uploaded_files_data = {} 
if 'df_filtrado_base' not in st.session_state: st.session_state.df_filtrado_base = initial_df.copy()
if 'df_filtrado_comp' not in st.session_state: st.session_state.df_filtrado_comp = initial_df.copy()
if 'show_reconfig_section' not in st.session_state: st.session_state.show_reconfig_section = False
if 'active_filters_base' not in st.session_state: st.session_state.active_filters_base = {} 
if 'active_filters_comp' not in st.session_state: st.session_state.active_filters_comp = {} 
if 'cols_to_exclude_analysis' not in st.session_state: 
    st.session_state.cols_to_exclude_analysis = [col for col in initial_df.columns if col in ['emp', 'eve', 'seq', 'nr_func']]

# Variável de estado para armazenar o nome de entrada no formulário
if 'current_dataset_name_input' not in st.session_state:
     st.session_state.current_dataset_name_input = initial_name if initial_name else "Dataset (Novo)"


# --- Aplicação de Filtros (Função Caching) ---
@st.cache_data(show_spinner="Aplicando filtros de Base e Comparação...")
def aplicar_filtros_comparacao(df_base, col_filtros, filtros_ativos_base, filtros_ativos_comp, col_data, data_range_base, data_range_comp, trigger):
    
    def _aplicar_filtro_single(df, col_filtros_list, filtros_ativos_dict):
        df_filtrado_temp = df.copy()
        
        # 1. Filtros Categóricos
        for col in col_filtros_list:
            selecao = filtros_ativos_dict.get(col)
            if col not in df_filtrado_temp.columns: continue

            opcoes_unicas = df_base[col].astype(str).fillna('N/A').unique().tolist()
            
            # Aplica filtro SOMENTE se a seleção não estiver vazia E não for total
            if selecao and len(selecao) > 0 and len(selecao) < len(opcoes_unicas): 
                # Converte a coluna para string para garantir a filtragem categórica
                df_filtrado_temp = df_filtrado_temp[df_filtrado_temp[col].astype(str).isin(selecao)]
        
        return df_filtrado_temp
    
    # Passamos apenas as listas de filtros categóricos
    df_base_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_base)
    df_comp_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_comp)
    
    # Retornamos os DataFrames filtrados
    return df_base_filtrado, df_comp_filtrado


# --- FUNÇÃO PARA TABELA DE RESUMO E MÉTRICAS "EXPERT" ---

def calcular_venc_desc(df):
    col_tipo_evento = 't' 
    col_valor = 'valor' 
    col_func = 'nome_funcionario' # Chave para Funcionário Único

    if df.empty or col_valor not in df.columns or col_tipo_evento not in df.columns:
        return 0, 0, 0, 0
        
    df_clean = df.copy()

    # CRÍTICO: Garantir que a coluna 'valor' é numérica para a soma
    try:
        df_clean[col_valor] = pd.to_numeric(df_clean[col_valor], errors='coerce').fillna(0)
    except Exception as e:
        st.warning(f"Falha crítica ao forçar coluna 'valor' para numérico na análise: {e}")
        return 0, 0, 0, 0

    df_clean = df_clean.dropna(subset=[col_valor, col_tipo_evento])

    vencimentos = df_clean[df_clean[col_tipo_evento] == 'C'][col_valor].sum()
    descontos = df_clean[df_clean[col_tipo_evento] == 'D'][col_valor].sum()
    
    liquido = vencimentos - descontos 
    
    # Lógica de contagem de Funcionários Únicos (0 se a coluna não existir)
    if col_func not in df_clean.columns:
          func_count = 0
    else:
        # Contagem: garante que apenas valores não vazios e únicos sejam contados
        func_count = df_clean[col_func].astype(str).str.strip().replace('', np.nan).dropna().nunique()

    return vencimentos, descontos, liquido, func_count

def gerar_analise_expert(df_completo, df_base, df_comp, filtros_ativos_base, filtros_ativos_comp, colunas_data, data_range_base, data_range_comp):
    
    colunas_valor_salvas = st.session_state.colunas_valor_salvas
    
    # -------------------------------------------------------------
    # 0. VERIFICAÇÃO CRÍTICA DE COLUNA (Aviso Graceful)
    # -------------------------------------------------------------
    col_func = 'nome_funcionario'
    if col_func not in df_completo.columns:
        st.error(f"Aviso Crítico: A coluna '{col_func}' não foi encontrada no Dataset Ativo. A contagem de funcionários únicos será 0. Por favor, re-processe seu arquivo de Folha contendo esta coluna.")

    # -------------------------------------------------------------
    # 1. ANÁLISE DE CONTEXTO E RÓTULOS DETALHADOS
    # -------------------------------------------------------------
    st.markdown("#### 📝 Contexto do Filtro Ativo")
    
    rotulo_base = gerar_rotulo_filtro(df_completo, filtros_ativos_base, colunas_data, data_range_base)
    rotulo_comp = gerar_rotulo_filtro(df_completo, filtros_ativos_comp, colunas_data, data_range_comp)

    st.markdown(f"""
        <div style="padding: 10px; border: 1px solid #007bff; border-radius: 5px; margin-bottom: 15px; background-color: #e9f7ff;">
            <p style="margin: 0; font-weight: bold; font-size: 16px;"><span style="color: #007bff;">BASE (Referência):</span></p>
            <p style="margin: 0; font-size: 14px;">{rotulo_base}</p>
        </div>
        <div style="padding: 10px; border: 1px solid #6f42c1; border-radius: 5px; margin-bottom: 20px; background-color: #f6f0ff;">
            <p style="margin: 0; font-weight: bold; font-size: 16px;"><span style="color: #6f42c1;">COMPARAÇÃO (Alvo):</span></p>
            <p style="margin: 0; font-size: 14px;">{rotulo_comp}</p>
        </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 2. CALCULO DE VENCIMENTOS E DESCONTOS E FUNCIONÁRIOS ÚNICOS
    # -------------------------------------------------------------
    
    # Base
    venc_base, desc_base, liq_base, func_base = calcular_venc_desc(df_base)
    
    # Comparação
    venc_comp, desc_comp, liq_comp, func_comp = calcular_venc_desc(df_comp)
    
    # Total Geral
    venc_total, desc_total, liq_total, func_total = calcular_venc_desc(df_completo)


    # -------------------------------------------------------------
    # 3. APRESENTAÇÃO DOS KPIS DE VENCIMENTOS E DESCONTOS (CARDS)
    # -------------------------------------------------------------
    st.markdown("##### 💰 Resumo Financeiro da BASE (Referência)")
    col1, col2, col3, col4 = st.columns(4)

    # Função auxiliar para calcular e formatar a variação percentual
    def get_delta(comp, base, is_currency=True):
        diff = comp - base
        if base == 0:
            pct_diff = 0 if comp == 0 else np.inf
        else:
            pct_diff = (diff / base) * 100
            
        if is_currency:
            return formatar_moeda(diff).replace('R$', ''), f" ({pct_diff:,.2f}%)" if np.isfinite(pct_diff) else " (N/A)"
        else:
            return f"{diff:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."), f" ({pct_diff:,.2f}%)" if np.isfinite(pct_diff) else " (N/A)"


    # KPI 1: Contagem de Funcionários (Base)
    delta_func_val, delta_func_pct = get_delta(func_comp, func_base, is_currency=False)
    col1.metric(
        label=f"Funcionários Únicos (Total: {func_total})", 
        value=f"{func_base:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."), 
        delta=f"{delta_func_val} {delta_func_pct}"
    )

    # KPI 2: Total de Vencimentos (Base)
    delta_venc_val, delta_venc_pct = get_delta(venc_comp, venc_base, is_currency=True)
    col2.metric(
        label=f"Total Vencimentos (Total: {formatar_moeda(venc_total)})", 
        value=formatar_moeda(venc_base), 
        delta=f"{delta_venc_val} {delta_venc_pct}"
    )

    # KPI 3: Total de Descontos (Base)
    delta_desc_val, delta_desc_pct = get_delta(desc_comp, desc_base, is_currency=True)
    col3.metric(
        label=f"Total Descontos (Total: {formatar_moeda(desc_total)})", 
        value=formatar_moeda(desc_base), 
        delta=f"{delta_desc_val} {delta_desc_pct}"
    )
    
    # KPI 4: Líquido (Base)
    delta_liq_val, delta_liq_pct = get_delta(liq_comp, liq_base, is_currency=True)
    col4.metric(
        label=f"Valor Líquido (Total: {formatar_moeda(liq_total)})", 
        value=formatar_moeda(liq_base), 
        delta=f"{delta_liq_val} {delta_liq_pct}"
    )

    st.markdown("---")


    # -------------------------------------------------------------
    # 4. TABELA DE VARIAÇÃO DETALHADA
    # -------------------------------------------------------------

    dados_resumo = []
    
    # 4.1. Adiciona Métricas Específicas
    dados_resumo.append({'Métrica': 'CONT. DE REGISTROS', 'Total Geral': len(df_completo), 'Base (Filtrado)': len(df_base), 'Comparação (Filtrado)': len(df_comp), 'Tipo': 'Contagem'})
    dados_resumo.append({'Métrica': 'CONT. DE FUNCIONÁRIOS ÚNICOS', 'Total Geral': func_total, 'Base (Filtrado)': func_base, 'Comparação (Filtrado)': func_comp, 'Tipo': 'Contagem'})
    dados_resumo.append({'Métrica': 'TOTAL DE VENCIMENTOS (CRÉDITO)', 'Total Geral': venc_total, 'Base (Filtrado)': venc_base, 'Comparação (Filtrado)': venc_comp, 'Tipo': 'Moeda'})
    dados_resumo.append({'Métrica': 'TOTAL DE DESCONTOS (DÉBITO)', 'Total Geral': desc_total, 'Base (Filtrado)': desc_base, 'Comparação (Filtrado)': desc_comp, 'Tipo': 'Moeda'})
    dados_resumo.append({'Métrica': 'VALOR LÍQUIDO (Venc - Desc)', 'Total Geral': liq_total, 'Base (Filtrado)': liq_base, 'Comparação (Filtrado)': liq_comp, 'Tipo': 'Moeda'})

    colunas_moeda_outras = [col for col in st.session_state.colunas_valor_salvas if col not in ['valor']] 
    for col in colunas_moeda_outras:
        total_geral_soma = df_completo[col].sum()
        total_base_soma = df_base[col].sum()
        total_comp_soma = df_comp[col].sum()
        dados_resumo.append({'Métrica': f"SOMA: {col.upper().replace('_', ' ')}", 'Total Geral': total_geral_soma, 'Base (Filtrado)': total_base_soma, 'Comparação (Filtrado)': total_comp_soma, 'Tipo': 'Moeda'})
            
    df_resumo = pd.DataFrame(dados_resumo)
    
    def calcular_variacao(row):
        base = row['Base (Filtrado)']
        comp = row['Comparação (Filtrado)']
        
        if base == 0:
            return 0 if comp == 0 else np.inf
        return ((comp - base) / base) * 100

    df_resumo['Variação %'] = df_resumo.apply(calcular_variacao, axis=1)

    df_tabela = df_resumo.copy()
    
    def format_value(row, col_name):
        val = row[col_name]
        if row['Tipo'] == 'Moeda':
            return formatar_moeda(val)
        else:
            return f"{val:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
    df_tabela['TOTAL GERAL (Sem Filtro)'] = df_tabela.apply(lambda row: format_value(row, 'Total Geral'), axis=1)
    df_tabela['BASE (FILTRADO)'] = df_tabela.apply(lambda row: format_value(row, 'Base (Filtrado)'), axis=1)
    df_tabela['COMPARAÇÃO (FILTRADO)'] = df_tabela.apply(lambda row: format_value(row, 'Comparação (Filtrado)'), axis=1)

    def format_variacao_tabela(val):
        if not np.isfinite(val):
            return '<span style="color: gray;">— 0,00 %</span>' # Ajustado para exibir como na sua imagem
        
        val_str = f"{abs(val):,.2f} %".replace(",", "X").replace(".", ",").replace("X", ".")
        
        if val > 0:
            color = 'green'
            icon = '▲'
        elif val < 0:
            color = 'red'
            icon = '▼'
        else:
            color = 'gray'
            icon = '—'
            
        return f'<span style="color: {color}; font-weight: bold;">{icon} {val_str}</span>'

    df_tabela['VARIAÇÃO BASE vs COMP (%)'] = df_tabela['Variação %'].apply(format_variacao_tabela)
    
    df_final_exibicao = df_tabela[['Métrica', 'TOTAL GERAL (Sem Filtro)', 'BASE (FILTRADO)', 'COMPARAÇÃO (FILTRADO)', 'VARIAÇÃO BASE vs COMP (%)']]

    st.markdown("##### 🔍 Comparativo Detalhado de Métricas Chave")
    st.markdown(df_final_exibicao.to_html(escape=False, index=False), unsafe_allow_html=True)


# --- SIDEBAR (CONFIGURAÇÕES E UPLOAD) ---
with st.sidebar:
    st.markdown("# 📊")
    st.title("⚙️ Configurações do Expert")
    
    if st.button("Limpar Cache de Dados e Persistência"):
        st.cache_data.clear()
        if os.path.exists(PERSISTENCE_PATH):
            try:
                os.remove(PERSISTENCE_PATH)
                st.session_state.data_sets_catalog = {}
                st.session_state.dados_atuais = pd.DataFrame()
                st.sidebar.success("Cache e dados de persistência limpos.")
            except Exception as e:
                st.sidebar.error(f"Erro ao remover arquivo de persistência: {e}")
        
        # Limpa todas as chaves de sessão para um estado inicial limpo
        keys_to_clear = [k for k in st.session_state.keys() if not k.startswith('_')]
        for key in keys_to_clear:
            if key not in ['data_sets_catalog', 'dados_atuais']:
                try:
                    del st.session_state[key]
                except:
                    pass
        st.info("Estado da sessão limpo! Recarregando...")
        st.rerun()

    # ==========================================================================
    # SEÇÃO 1: TROCAR DATASET ATIVO (RESTAURADO PARA st.selectbox)
    # ==========================================================================
    if st.session_state.data_sets_catalog:
        st.header("1. Trocar Dataset Ativo")
        dataset_names = list(st.session_state.data_sets_catalog.keys())
        
        # Encontra o índice do dataset ativo para pré-seleção
        current_index = 0
        if st.session_state.current_dataset_name in dataset_names:
            current_index = dataset_names.index(st.session_state.current_dataset_name)
        
        # O selectbox é o widget mais limpo e que economiza espaço na sidebar
        selected_name = st.selectbox(
            "Selecione o Dataset Ativo:", 
            options=dataset_names, 
            index=current_index,
            key='sidebar_dataset_selector'
        )
        
        if selected_name != st.session_state.current_dataset_name:
            switch_dataset(selected_name)
            
    # ==========================================================================
        
    # Seção 2: Upload e Processamento
    st.header("2. Upload e Processamento")
    
    # Input para nome do Dataset (AGORA É USADO SOMENTE SE NÃO HOUVER ARQUIVO)
    if 'current_dataset_name_input' not in st.session_state:
        st.session_state.current_dataset_name_input = st.session_state.current_dataset_name if st.session_state.current_dataset_name else "Dataset (Novo)"
        
    with st.form("file_upload_form", clear_on_submit=True):
        uploaded_files_new = st.file_uploader(
            "📥 Carregar Novo(s) CSV/XLSX", 
            type=['csv', 'xlsx'], 
            accept_multiple_files=True,
            key="file_uploader_widget"
        )
        
        # Se um arquivo for carregado, este input será substituído pelo nome do arquivo
        dataset_name_input = st.text_input("Nome para o Novo Dataset (Se não for arquivo):", 
                                             value=st.session_state.current_dataset_name_input)
        st.session_state.current_dataset_name_input = dataset_name_input # Atualiza o estado

        submit_upload = st.form_submit_button("Adicionar Arquivo(s) à Lista")
        
        if submit_upload and uploaded_files_new:
            newly_added = []
            
            # CRÍTICO: Define o nome do dataset baseado no primeiro arquivo
            first_file_name = uploaded_files_new[0].name
            # Remove a extensão do arquivo
            base_name_from_file = os.path.splitext(first_file_name)[0] 
            st.session_state.current_dataset_name_input = base_name_from_file

            for file in uploaded_files_new:
                # Adiciona os arquivos à lista de pendentes para processamento
                st.session_state.uploaded_files_data[file.name] = file.read()
                newly_added.append(file.name)
                
            st.success(f"Arquivos adicionados: {', '.join(newly_added)}. Nome sugerido: {base_name_from_file}. Clique em 'Processar' abaixo.")
            
            # CRÍTICO: Força a exibição da seção de reconfiguração
            st.session_state.show_reconfig_section = True 
            st.rerun()

    
    # CRÍTICO: Esta seção agora é exibida se houver arquivos pendentes OU se o estado show_reconfig_section for True
    if st.session_state.uploaded_files_data or st.session_state.show_reconfig_section:
        
        # O botão de reconfiguração aparece se tivermos arquivos pendentes (uploaded_files_data)
        if st.session_state.uploaded_files_data:
            st.markdown("---")
            st.markdown("##### 📝 Arquivos Pendentes:")
            for file_name in st.session_state.uploaded_files_data.keys():
                st.markdown(f"- **{file_name}**")
            
            # Botão para forçar a reabertura do painel, caso tenha sido fechado
            st.button("🔁 Iniciar Configuração e Processamento", 
                      on_click=show_reconfig_panel,
                      key='reconfig_btn_sidebar',
                      use_container_width=True,
                      type='primary')
            st.markdown("---")
        
        # Este é o painel de configuração que aparece APÓS o clique no botão acima ou após um upload
        if st.session_state.show_reconfig_section:
            
            df_novo = pd.DataFrame()
            all_dataframes = []
            target_col = 'nome_funcionario' # Coluna alvo
            
            # Usa o nome definido (nome do arquivo, se houver, ou input manual)
            dataset_name_to_use = st.session_state.get('current_dataset_name_input')
            
            # Se não houver nome de entrada válido (o que não deve acontecer após o upload), usa o fallback
            if not dataset_name_to_use or dataset_name_to_use == "Dataset (Novo)":
                 dataset_name_to_use = f"Dataset Processado ({datetime.now().strftime('%Y-%m-%d %H:%M')})"


            # --- NOVO SELETOR PARA CONCATENAÇÃO ---
            st.markdown("##### ➕ Opção de Soma/Agregação")
            
            # Lista de datasets disponíveis
            catalog_names = ["Criar Novo Dataset (Substituir/Criar)"] + list(st.session_state.data_sets_catalog.keys())
            
            selected_dataset_to_sum = st.selectbox(
                "Somar arquivos carregados com qual Dataset existente?",
                options=catalog_names,
                index=0,
                key='dataset_to_sum_selector'
            )
            
            # Lógica para definir o nome final do dataset
            if selected_dataset_to_sum != "Criar Novo Dataset (Substituir/Criar)":
                # Se for somar a um existente, o nome do dataset ATIVO será mantido (o do dataset existente)
                dataset_name_to_use = selected_dataset_to_sum
                st.session_state.current_dataset_name_input = dataset_name_to_use 
                st.info(f"Os novos dados serão SOMADOS ao dataset **{dataset_name_to_use}**.")
            
            # 1. Tenta carregar o dataset ATIVO ESCOLHIDO para soma
            df_atual_base = pd.DataFrame()
            if selected_dataset_to_sum != "Criar Novo Dataset (Substituir/Criar)":
                if dataset_name_to_use in st.session_state.data_sets_catalog:
                    df_atual_base = st.session_state.data_sets_catalog[dataset_name_to_use]['df'].copy()
                    
                    # --- LIMPEZA E ALINHAMENTO DO DF BASE EXISTENTE ---
                    raw_columns_base = df_atual_base.columns.copy()
                    cleaned_columns_base = [limpar_nome_coluna(col) for col in raw_columns_base]
                    df_atual_base.columns = cleaned_columns_base
                    
                    # Checa e alinha o df base para nome_funcionario
                    if target_col not in df_atual_base.columns:
                          employee_col_candidates_base = [col for col in cleaned_columns_base if 'nome' in col and 'func' in col]
                          if employee_col_candidates_base:
                              df_atual_base.rename(columns={employee_col_candidates[0]: target_col}, inplace=True)
                          else:
                              df_atual_base[target_col] = np.nan 
                    # ----------------------------------------------------
                    
            # 2. Processa o(s) novo(s) arquivo(s)
            if not st.session_state.uploaded_files_data:
                st.warning("Nenhum novo arquivo detectado para processamento.")
                
            else:
                for file_name, file_bytes in st.session_state.uploaded_files_data.items():
                    df_temp = None 
                    
                    try:
                        uploaded_file_stream = BytesIO(file_bytes)
                        
                        if file_name.endswith('.csv'):
                            # Lógica de leitura robusta para CSV (tentativas com diferentes separadores e encodings)
                            reading_attempts = [
                                {'sep': ';', 'decimal': ',', 'encoding': 'utf-8', 'skipinitialspace': True, 'header': 'infer'},
                                {'sep': ';', 'decimal': ',', 'encoding': 'iso-8859-1', 'skipinitialspace': True, 'header': None, 'skiprows': 1},
                                {'sep': ',', 'decimal': '.', 'encoding': 'utf-8', 'skipinitialspace': True, 'header': None, 'skiprows': 1},
                                {'sep': ';', 'decimal': ',', 'encoding': 'latin-1', 'skipinitialspace': True, 'header': 'infer'},
                                {'sep': ',', 'decimal': '.', 'encoding': 'utf-8', 'skipinitialspace': True, 'header': 'infer'},
                            ]
                            
                            success = False
                            for attempt in reading_attempts:
                                try:
                                    uploaded_file_stream.seek(0)
                                    header_param = attempt.pop('header', 'infer')
                                    skiprows_param = attempt.pop('skiprows', 0)
                                    
                                    df_temp = pd.read_csv(
                                        uploaded_file_stream, 
                                        **attempt, 
                                        header=(0 if header_param == 'infer' else header_param),
                                        skiprows=skiprows_param
                                    )
                                    
                                    if df_temp.shape[1] > 1 and not df_temp.empty:
                                        if skiprows_param == 1 and header_param is None:
                                            df_temp.columns = [f'col_{i}' for i in range(len(df_temp.columns))]
                                            
                                        success = True
                                        break
                                    else:
                                        df_temp = None 
    
                                except Exception:
                                    pass 
                                    
                            if not success:
                                st.error(f"Falha CRÍTICA ao ler o arquivo CSV '{file_name}'. Ele será ignorado.")
    
                                    
                        elif file_name.endswith('.xlsx'):
                            try:
                                df_temp = pd.read_excel(uploaded_file_stream)
                                if df_temp is not None and not df_temp.empty: 
                                    success = True
                            except Exception as e:
                                st.error(f"Falha CRÍTICA ao ler o arquivo XLSX '{file_name}'. Ele será ignorado. Erro: {e}")
                        
                        
                        if df_temp is not None and not df_temp.empty:
                            # 3. Limpar colunas e tentar renomear nome_funcionario
                            raw_columns = df_temp.columns.copy()
                            cleaned_columns = [limpar_nome_coluna(col) for col in raw_columns]
                            df_temp.columns = cleaned_columns
                            
                            if target_col not in df_temp.columns:
                                employee_col_candidates = [col for col in cleaned_columns if 'nome' in col and 'func' in col]
                                if employee_col_candidates:
                                    df_temp.rename(columns={employee_col_candidates[0]: target_col}, inplace=True)
                                else:
                                    df_temp[target_col] = np.nan
                                    
                            all_dataframes.append(df_temp)

                    except Exception as e:
                        st.error(f"Erro no processamento do arquivo {file_name}: {e}")

                
                if all_dataframes:
                    # Concatena todos os novos arquivos
                    df_novo_uploads = pd.concat(all_dataframes, ignore_index=True)
                    
                    if selected_dataset_to_sum != "Criar Novo Dataset (Substituir/Criar)" and not df_atual_base.empty:
                        # 4. Concatena com o DataFrame base existente
                        # Usa append para garantir que a coluna 'nome_funcionario' esteja tratada e alinhada
                        df_final_concatenado = pd.concat([df_atual_base, df_novo_uploads], ignore_index=True, sort=False)
                        st.success(f"Concatenado com sucesso! {len(df_novo_uploads)} registros adicionados ao dataset '{dataset_name_to_use}'.")
                        df_novo = df_final_concatenado
                    else:
                        df_novo = df_novo_uploads
                        st.success("Novos arquivos carregados e combinados.")
                        
                elif selected_dataset_to_sum != "Criar Novo Dataset (Substituir/Criar)" and not df_atual_base.empty:
                    st.info(f"Nenhum novo arquivo válido foi carregado. Mantendo o dataset ativo: '{dataset_name_to_use}'.")
                    df_novo = df_atual_base
                    
                else:
                    st.error("Nenhum arquivo válido foi carregado e não há dataset para somar. Processamento abortado.")
                    st.session_state.show_reconfig_section = False
                    st.session_state.uploaded_files_data = {}
                    st.rerun()
                
                
                # --- Etapa de Configuração de Colunas ---
                st.markdown("---")
                st.markdown("##### 3. Confirmação de Colunas e Tipagem")
                
                
                # Lista de colunas do DataFrame combinado
                current_cols = df_novo.columns.tolist()
                
                # Heurística inicial para pré-seleção
                default_valor = [col for col in current_cols if 'valor' in col or 'total' in col or 'bruto' in col]
                default_filtros = [col for col in current_cols if len(df_novo[col].unique()) < 50 and col not in default_valor]
                
                # Se for uma concatenação, usar as colunas salvas se existirem
                if selected_dataset_to_sum != "Criar Novo Dataset (Substituir/Criar)" and dataset_name_to_use in st.session_state.data_sets_catalog:
                    saved_data = st.session_state.data_sets_catalog[dataset_name_to_use]
                    default_valor = saved_data['colunas_valor_salvas']
                    default_filtros = saved_data['colunas_filtros_salvas']


                colunas_valor_selecionadas = st.multiselect(
                    "💰 Selecione as Colunas de VALOR (Moeda/Numéricas):",
                    options=current_cols,
                    default=default_valor,
                    key='col_valor_multiselect'
                )

                colunas_filtros_selecionadas = st.multiselect(
                    "🏷️ Selecione as Colunas de FILTRO (Categoria/Texto):",
                    options=[col for col in current_cols if col not in colunas_valor_selecionadas],
                    default=default_filtros,
                    key='col_filtro_multiselect'
                )

                if st.button("✅ Processar e Ativar Dataset", type='primary', use_container_width=True):
                    
                    if not colunas_valor_selecionadas:
                        st.error("Selecione pelo menos uma coluna de valor para continuar.")
                        st.stop()
                        
                    with st.spinner("Realizando limpeza e inferência de tipos..."):
                        # 5. Aplicar tipagem e limpeza final
                        df_final_processado = inferir_e_converter_tipos(df_novo, colunas_filtros_selecionadas, colunas_valor_selecionadas)
                    
                        # 6. Salvar e ativar
                        success, df_novo_ativo = processar_dados_atuais(
                            df_final_processado, 
                            colunas_filtros_selecionadas, 
                            colunas_valor_selecionadas, 
                            dataset_name_to_use # CRÍTICO: Usa o nome do arquivo ou o nome do dataset somado
                        )
                        
                        if success:
                            st.session_state.show_reconfig_section = False
                            st.session_state.uploaded_files_data = {}
                            # Resetar o nome de entrada para a próxima vez (mas o ativo está correto)
                            st.session_state.current_dataset_name_input = st.session_state.current_dataset_name
                            st.success(f"Dataset '{dataset_name_to_use}' processado e ativo!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Falha ao salvar o dataset.")
                            
                    
# ==============================================================================
# --- DASHBOARD PRINCIPAL ---
# ==============================================================================

# Se não houver dados ativos, exibe uma tela de boas-vindas
if st.session_state.dados_atuais.empty:
    st.markdown("""
        # Sistema de Análise de Indicadores Expert
        
        Bem-vindo! Para começar, carregue e configure seu primeiro conjunto de dados na barra lateral à esquerda.
        
        1.  **Carregue** seus arquivos CSV/XLSX.
        2.  Clique em **"Iniciar Configuração e Processamento"**.
        3.  **Defina** as colunas de Valor e Filtro.
        4.  Clique em **"Processar e Ativar Dataset"**.
    """)
    st.stop()
    
# Se houver dados, exibe o dashboard
df = st.session_state.dados_atuais
colunas_filtros = st.session_state.colunas_filtros_salvas
colunas_valor = st.session_state.colunas_valor_salvas

# --- LAYOUT DE DESTAQUE DO DATASET ATIVO (BASEADO NA SUA IMAGEM) ---
st.markdown("##### 🗃️ Datasets Salvos")
st.markdown(
    f"""
    <div style="background-color: #ff4b4b; padding: 10px; border-radius: 5px; margin-bottom: 20px; text-align: center; color: white;">
        <span style="font-weight: bold; font-size: 18px;">
            ✅ {st.session_state.current_dataset_name} (Atual)
        </span>
    </div>
    """,
    unsafe_allow_html=True
)
# --- FIM DO LAYOUT DE DESTAQUE ---

# Agora o Título do Dashboard usa o nome do dataset
st.title(f"📊 Dashboard Expert de Análise de Indicadores ({st.session_state.current_dataset_name})")
st.markdown("Use os filtros na barra lateral para definir as bases de comparação.")

# ... (restante do código que está OK)

# Definindo colunas para data (simulação, se 'ano' e 'mes' existirem)
cols_numeric, cols_date = encontrar_colunas_tipos(df)
data_range_base = None
data_range_comp = None


# Geração dinâmica dos filtros
col_filtros_principais = [c for c in colunas_filtros if c not in st.session_state.cols_to_exclude_analysis]

with st.expander("🛠️ Configurar Filtros (Base vs. Comparação)"):
    
    col_base, col_comp = st.columns(2)
    
    # Resetar filtros
    if col_base.button("Limpar TODOS os Filtros (Base e Comparação)", use_container_width=True):
        limpar_filtros_salvos()
        st.rerun()

    
    with col_base.container(border=True):
        st.markdown("#### BASE (Referência)")
        
        # O estado de filtros ativos é mantido em session_state.active_filters_base
        active_filters_base = st.session_state.active_filters_base
        
        for col in col_filtros_principais:
            if col in df.columns:
                # Criar chave única para o widget
                widget_key = f'filtro_key_base_{col}'
                
                # Obter todas as opções únicas (tratando NaN como string para o multiselect)
                options = df[col].astype(str).fillna('N/A').unique().tolist()
                
                # Usar o estado de sessão para o valor do multiselect
                if col not in active_filters_base:
                    # Inicializar com todas as opções selecionadas por padrão
                    active_filters_base[col] = options
                
                # O valor padrão é puxado do st.session_state[widget_key] se existir
                selected_options = st.multiselect(
                    f"Selecione {col.title().replace('_', ' ')}:",
                    options=options,
                    default=active_filters_base[col],
                    key=widget_key
                )
                
                # Atualizar o filtro ativo na sessão, mesmo que seja a lista completa
                active_filters_base[col] = selected_options
                
                # Botões de controle (usando callbacks)
                col_btn1, col_btn2 = st.columns(2)
                col_btn1.button("Todos", key=f"all_base_{col}", on_click=set_multiselect_all, args=(col, 'base', options), use_container_width=True)
                col_btn2.button("Nenhum", key=f"none_base_{col}", on_click=set_multiselect_none, args=(col, 'base',), use_container_width=True)

        st.session_state.active_filters_base = active_filters_base
        
    with col_comp.container(border=True):
        st.markdown("#### COMPARAÇÃO (Alvo)")
        
        # O estado de filtros ativos é mantido em session_state.active_filters_comp
        active_filters_comp = st.session_state.active_filters_comp
        
        for col in col_filtros_principais:
            if col in df.columns:
                # Criar chave única para o widget
                widget_key = f'filtro_key_comp_{col}'
                
                # Obter todas as opções únicas
                options = df[col].astype(str).fillna('N/A').unique().tolist()
                
                # Usar o estado de sessão para o valor do multiselect
                if col not in active_filters_comp:
                    # Inicializar com todas as opções selecionadas por padrão
                    active_filters_comp[col] = options
                
                # O valor padrão é puxado do st.session_state[widget_key] se existir
                selected_options = st.multiselect(
                    f"Selecione {col.title().replace('_', ' ')}:",
                    options=options,
                    default=active_filters_comp[col],
                    key=widget_key
                )
                
                # Atualizar o filtro ativo na sessão, mesmo que seja a lista completa
                active_filters_comp[col] = selected_options
                
                # Botões de controle (usando callbacks)
                col_btn1, col_btn2 = st.columns(2)
                col_btn1.button("Todos", key=f"all_comp_{col}", on_click=set_multiselect_all, args=(col, 'comp', options), use_container_width=True)
                col_btn2.button("Nenhum", key=f"none_comp_{col}", on_click=set_multiselect_none, args=(col, 'comp',), use_container_width=True)
                
        st.session_state.active_filters_comp = active_filters_comp
        
    # Recarrega o estado de sessão, necessário após o expander fechar
    filtros_base_final = st.session_state.active_filters_base
    filtros_comp_final = st.session_state.active_filters_comp

# --- APLICAÇÃO E EXECUÇÃO DO CÁLCULO ---

# Chama a função cacheadada para aplicar os filtros
df_filtrado_base, df_filtrado_comp = aplicar_filtros_comparacao(
    df, 
    col_filtros_principais, 
    filtros_base_final, 
    filtros_comp_final, 
    cols_date, 
    data_range_base, 
    data_range_comp, 
    st.session_state.filtro_reset_trigger # Trigger para invalidar o cache
)

# Salva os resultados (apenas para exibição futura/depuração)
st.session_state.df_filtrado_base = df_filtrado_base
st.session_state.df_filtrado_comp = df_filtrado_comp

# Geração da Análise
gerar_analise_expert(
    df, 
    df_filtrado_base, 
    df_filtrado_comp, 
    filtros_base_final, 
    filtros_comp_final, 
    cols_date, 
    data_range_base, 
    data_range_comp
)
