# app.py - Versão FINAL com Limpeza Agressiva de Colunas e APENAS Filtros Categóricos (Multiselect)

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime
from io import BytesIO
import pickle 

# ==============================================================================
# IMPORTAÇÃO DE FUNÇÕES ESSENCIAIS DO UTILS.PY
# ==============================================================================
try:
    from utils import (
        formatar_moeda, 
        inferir_e_converter_tipos, 
        encontrar_colunas_tipos, 
        verificar_ausentes,
        gerar_rotulo_filtro 
    )
except ImportError:
    st.error("ERRO CRÍTICO: O arquivo 'utils.py' não foi encontrado. Certifique-se de que ele está no mesmo diretório do 'app.py' e que copiou o código completo fornecido.")
    st.stop()
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
        os.makedirs(os.path.dirname(PERSISTENCE_PATH), exist_ok=True)
        with open(PERSISTENCE_PATH, 'wb') as f:
            pickle.dump(catalog, f)
    except Exception as e:
        st.sidebar.error(f"Erro ao salvar dados: {e}")

def limpar_filtros_salvos():
    """Limpa o estado de todos os filtros, forçando os widgets a resetarem ao default."""
    st.session_state.active_filters_base = {}
    st.session_state.active_filters_comp = {}
    
    st.session_state['filtro_reset_trigger'] += 1
    
    chaves_a_limpar = [
        key for key in st.session_state.keys() 
        if key.startswith('filtro_key_base_') or key.startswith('date_range_key_base_') or 
           key.startswith('filtro_key_comp_') or key.startswith('date_range_key_comp_')
    ]
    for key in chaves_a_limpar:
        try:
            if key.startswith('filtro_key_'):
                 st.session_state[key] = []
            elif key.startswith('date_range_key_'):
                 # Garante que os estados do slider de data são removidos
                 del st.session_state[key]
        except:
            pass
            
    st.rerun() 

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
    else:
        st.error(f"Dataset '{dataset_name}' não encontrado.")

def show_reconfig_panel():
    st.session_state.show_reconfig_section = True
    
def processar_dados_atuais(df_novo, colunas_filtros, colunas_valor, dataset_name):
    base_name = dataset_name if dataset_name else f"Dataset Processado ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        
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


# --- Aplicação de Filtros (Função Caching) ---
@st.cache_data(show_spinner="Aplicando filtros de Base e Comparação...")
def aplicar_filtros_comparacao(df_base, col_filtros, filtros_ativos_base, filtros_ativos_comp, col_data, data_range_base, data_range_comp, trigger):
    
    # OBS: data_range_base e data_range_comp serão None, pois o slider foi removido.
    # O filtro de data só será aplicado se os filtros categóricos MES e ANO forem usados.

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
        
        # O filtro de Data (Slider) foi removido, então não há aplicação de data_range aqui.
        return df_filtrado_temp
    
    # Passamos apenas as listas de filtros categóricos
    df_base_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_base)
    df_comp_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_comp)
    
    # Retornamos os DataFrames filtrados e None para os ranges de data, que não são usados
    return df_base_filtrado, df_comp_filtrado


# --- FUNÇÃO PARA TABELA DE RESUMO E MÉTRICAS "EXPERT" ---

def gerar_analise_expert(df_completo, df_base, df_comp, filtros_ativos_base, filtros_ativos_comp, colunas_data, data_range_base, data_range_comp):
    
    colunas_valor_salvas = st.session_state.colunas_valor_salvas
    
    # -------------------------------------------------------------
    # 1. ANÁLISE DE CONTEXTO E RÓTULOS DETALHADOS
    # -------------------------------------------------------------
    st.markdown("#### 📝 Contexto do Filtro Ativo")
    
    # A função gerar_rotulo_filtro foi ajustada para aceitar None para data_range
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
    
    col_tipo_evento = 't' 
    col_valor = 'valor' 
    col_func = 'nome_funcionario' # Chave para Funcionário Único
    
    # VERIFICAÇÃO CRÍTICA DE COLUNAS
    if col_tipo_evento not in df_completo.columns or col_valor not in df_completo.columns:
        st.error(f"Erro de Análise: Colunas '{col_tipo_evento}' ou '{col_valor}' não encontradas no DataFrame. Verifique a configuração de colunas.")
        return
        
    # VERIFICAÇÃO DE FUNCIONÁRIOS ÚNICOS
    if col_func not in df_completo.columns:
        st.error(f"Erro Crítico: A coluna '{col_func}' não foi encontrada no DataFrame. O pré-processamento de nomes de coluna falhou. Limpe o cache e tente novamente. Colunas atuais: {df_completo.columns.tolist()}")
        return

    def calcular_venc_desc(df):
        if df.empty:
            return 0, 0, 0, 0
            
        df_clean = df.dropna(subset=[col_valor, col_tipo_evento])

        vencimentos = df_clean[df_clean[col_tipo_evento] == 'C'][col_valor].sum()
        descontos = df_clean[df_clean[col_tipo_evento] == 'D'][col_valor].sum()
        liquido = vencimentos - descontos
        
        # Lógica de contagem de Funcionários Únicos (tratando vazios)
        func_count = df[col_func].astype(str).str.strip().replace('', np.nan).dropna().nunique()

        return vencimentos, descontos, liquido, func_count

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
            return '<span style="color: gray;">N/A</span>'
        
        val_str = f"{val:,.2f} %".replace(",", "X").replace(".", ",").replace("X", ".")
        
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
        
        keys_to_clear = [k for k in st.session_state.keys() if not k.startswith('_')]
        for key in keys_to_clear:
            if key not in ['data_sets_catalog', 'dados_atuais']:
                try:
                    del st.session_state[key]
                except:
                    pass
        st.info("Estado da sessão limpo! Recarregando...")
        st.rerun()

    if st.session_state.data_sets_catalog:
        st.header("1. Trocar Dataset Ativo")
        dataset_names = list(st.session_state.data_sets_catalog.keys())
        
        current_index = dataset_names.index(st.session_state.current_dataset_name) if st.session_state.current_dataset_name in dataset_names else 0
        
        selected_name = st.selectbox(
            "Selecione o Dataset Ativo:", 
            options=dataset_names, 
            index=current_index,
            key='sidebar_dataset_selector'
        )
        
        if selected_name != st.session_state.current_dataset_name:
            switch_dataset(selected_name)
            
    # Seção 2: Upload e Processamento
    st.header("2. Upload e Processamento")
    
    with st.form("file_upload_form", clear_on_submit=True):
        uploaded_files_new = st.file_uploader(
            "📥 Carregar Novo(s) CSV/XLSX", 
            type=['csv', 'xlsx'], 
            accept_multiple_files=True,
            key="file_uploader_widget"
        )
        
        default_dataset_name = f"Dataset Processado ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        dataset_name_input = st.text_input("Nome para o Dataset Processado:", value=default_dataset_name)
        
        submit_upload = st.form_submit_button("Adicionar Arquivo(s) à Lista")
        
        if submit_upload and uploaded_files_new:
            newly_added = []
            for file in uploaded_files_new:
                st.session_state.uploaded_files_data[file.name] = file.read()
                newly_added.append(file.name)
            st.success(f"Arquivos adicionados: {', '.join(newly_added)}. Clique em 'Processar' abaixo.")
            st.session_state.show_reconfig_section = True 
            st.session_state.current_dataset_name_input = dataset_name_input
            st.rerun()

    if st.session_state.uploaded_files_data:
        st.markdown("---")
        st.markdown("##### Arquivos Pendentes para Processamento:")
        st.button("🔁 Reconfigurar e Processar", 
                  on_click=show_reconfig_panel,
                  key='reconfig_btn_sidebar',
                  use_container_width=True,
                  type='primary')
        st.markdown("---")
        
        if st.session_state.show_reconfig_section:
            df_novo = pd.DataFrame()
            all_dataframes = []
            
            for file_name, file_bytes in st.session_state.uploaded_files_data.items():
                try:
                    uploaded_file_stream = BytesIO(file_bytes)
                    if file_name.endswith('.csv'):
                        try:
                            # Tenta ler com separador ';', decimal ','
                            df_temp = pd.read_csv(uploaded_file_stream, sep=';', decimal=',', encoding='utf-8')
                        except Exception:
                            uploaded_file_stream.seek(0)
                            # Tenta ler com separador ',', decimal '.'
                            df_temp = pd.read_csv(uploaded_file_stream, sep=',', decimal='.', encoding='utf-8')
                    elif file_name.endswith('.xlsx'):
                        df_temp = pd.read_excel(uploaded_file_stream)
                    
                    if not df_temp.empty:
                        all_dataframes.append(df_temp)
                        
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo {file_name}: {e}")
                    pass 

            if all_dataframes:
                df_novo = pd.concat(all_dataframes, ignore_index=True)
            
            if df_novo.empty:
                st.error("O conjunto de dados consolidado está vazio.")
                st.session_state.dados_atuais = pd.DataFrame() 
            else:
                
                # --- CORREÇÃO DE LIMPEZA MAIS ROBUSTA (Padronização de Colunas) ---
                raw_columns = df_novo.columns.copy()
                
                # Limpeza agressiva: strip, lower, remover acentos e substituir tudo que não é letra/número por underscore
                cleaned_columns = (
                    raw_columns.astype(str)
                    .str.strip()
                    .str.lower()
                    .str.normalize('NFKD')
                    .str.encode('ascii', 'ignore').str.decode('utf-8')
                    .str.replace(r'[^a-z0-9]+', '_', regex=True) 
                    .str.strip('_') 
                )
                df_novo.columns = cleaned_columns
                colunas_disponiveis = df_novo.columns.tolist()

                # --- VERIFICAÇÃO E RENOMEAÇÃO FORÇADA DE 'NOME FUNCIONARIO' ---
                target_col = 'nome_funcionario'
                
                if target_col not in colunas_disponiveis:
                    employee_col_candidates = [col for col in colunas_disponiveis if 'nome' in col and 'func' in col]

                    if employee_col_candidates:
                        original_candidate = employee_col_candidates[0]
                        df_novo.rename(columns={original_candidate: target_col}, inplace=True)
                        st.sidebar.info(f"Col. de Funcionário renomeada: '{original_candidate}' -> '{target_col}'")
                        colunas_disponiveis = df_novo.columns.tolist() 
                    else:
                        st.sidebar.warning("Aviso: Não foi possível identificar a coluna de nome de funcionário automaticamente.")
                        
                # --- FIM DA CORREÇÃO CRÍTICA ---
                
                st.info(f"Total de {len(df_novo)} linhas para configurar.")
                
                moeda_default = [col for col in colunas_disponiveis if any(word in col for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
                if 'moeda_select' not in st.session_state: initialize_widget_state('moeda_select', moeda_default)
                
                
                # --- DEFINIÇÃO DE COLUNAS TEXTO (INCLUINDO MÊS E ANO) ---
                texto_default_base = ['nr_func', 'nome_funcionario', 'emp', 'eve', 'seq', 't', 'tip', 'descricao_evento', 'tipo_processo']
                
                if 'mes' in colunas_disponiveis: texto_default_base.append('mes')
                if 'ano' in colunas_disponiveis: texto_default_base.append('ano')
                
                # Remove colunas que podem ser erroneamente inferidas como data/numérico, mas que devem ser texto
                for col_name in ['mes', 'ano']:
                    if col_name in colunas_disponiveis and col_name not in texto_default_base:
                        texto_default_base.append(col_name)

                texto_default = [col for col in colunas_disponiveis if col in texto_default_base]

                if 'texto_select' not in st.session_state: 
                    initialize_widget_state('texto_select', texto_default)
                else:
                    current_list = st.session_state.texto_select
                    for col in texto_default:
                        if col in colunas_disponiveis and col not in current_list:
                             current_list.append(col)
                    st.session_state.texto_select = list(set(current_list)) 

                
                st.markdown("##### 💰 Colunas de VALOR (R$)")
                colunas_moeda = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.moeda_select, key='moeda_select', label_visibility="collapsed")
                
                st.markdown("---")
                st.markdown("##### 📝 Colunas TEXTO/ID")
                colunas_texto = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.texto_select, key='texto_select', label_visibility="collapsed")
                st.markdown("---")
                
                # O df_processado agora terá mes e ano como Object/Category
                df_processado = inferir_e_converter_tipos(df_novo, colunas_texto, colunas_moeda)
                
                colunas_para_filtro_options = df_processado.select_dtypes(include=['object', 'category']).columns.tolist()
                
                # --- DEFINIÇÃO DE FILTROS PADRÃO (INCLUINDO MÊS E ANO) ---
                filtro_default_base = ['t', 'descricao_evento', 'nome_funcionario', 'emp', 'tipo_processo']
                if 'mes' in colunas_para_filtro_options: filtro_default_base.append('mes')
                if 'ano' in colunas_para_filtro_options: filtro_default_base.append('ano')
                
                filtro_default = [c for c in colunas_para_filtro_options if c in filtro_default_base]
                
                if 'filtros_select' not in st.session_state:
                    initialize_widget_state('filtros_select', filtro_default)
                
                st.markdown("##### ⚙️ Colunas para FILTROS")
                colunas_para_filtro = st.multiselect("Selecione:", options=colunas_para_filtro_options, default=st.session_state.filtros_select, key='filtros_select', label_visibility="collapsed")
                
                colunas_valor_dashboard = df_processado.select_dtypes(include=np.number).columns.tolist()
                st.markdown("---")
                
                if st.button("✅ Processar e Exibir Dados Atuais", key='processar_sidebar_btn'): 
                    if df_processado.empty:
                        st.error("O DataFrame está vazio após o processamento.")
                    elif not colunas_para_filtro:
                        st.warning("Selecione pelo menos uma coluna na seção 'Colunas para FILTROS'.")
                    else:
                        dataset_name_to_save = st.session_state.get('current_dataset_name_input', default_dataset_name)
                        sucesso, df_processado_salvo = processar_dados_atuais(df_processado, colunas_para_filtro, colunas_valor_dashboard, dataset_name_to_save)
                        if sucesso:
                            st.success(f"Dataset '{st.session_state.current_dataset_name}' processado e salvo no catálogo!")
                            st.session_state.uploaded_files_data = {} 
                            st.session_state.show_reconfig_section = False
                            st.balloons()
                            limpar_filtros_salvos() 
                            st.rerun() 
            
    else: 
        st.session_state.show_reconfig_section = False
        if not st.session_state.data_sets_catalog:
             st.info("Sistema pronto. O Dashboard será exibido após carregar, processar e selecionar um Dataset.")


# --- Dashboard Principal ---

st.markdown("---") 

if st.session_state.dados_atuais.empty: 
    st.info("Sistema pronto. O Dashboard será exibido após carregar, processar e selecionar um Dataset.")
else:
    df_analise_completo = st.session_state.dados_atuais.copy()
    st.header(f"📊 Dashboard Expert de Análise de Indicadores ({st.session_state.current_dataset_name})")
    
    colunas_categoricas_filtro = st.session_state.colunas_filtros_salvas
    
    # Colunas de data não são mais usadas para o SLIDER, mas ainda são necessárias para o rótulo
    _, colunas_data = encontrar_colunas_tipos(df_analise_completo) 
    
    st.markdown("#### 🔍 Configuração de Análise de Variação")
    col_reset_btn = st.columns([4, 1])[1]
    with col_reset_btn:
        st.button("🗑️ Resetar Filtros", on_click=limpar_filtros_salvos, use_container_width=True)
    
    tab_base, tab_comparacao = st.tabs(["Filtros da BASE (Referência)", "Filtros de COMPARAÇÃO (Alvo)"])

    def render_filter_panel(tab_container, suffix, colunas_filtro_a_exibir, df_analise_base):
        
        current_active_filters_dict = {}
        data_range = None # Garantimos que data_range seja None
        df_base_temp = df_analise_base.copy()
        
        with tab_container:
            
            # BLOCO DE FILTRO DE DATA (SLIDER) REMOVIDO PARA USAR APENAS MULTISELECTS
            
            st.markdown("##### Filtros Categóricos")
            cols_container = st.columns(3) 
            
            # Definição da ordem de prioridade para melhor visualização
            colunas_ordenadas = []
            priority_cols = ['emp', 'tipo_processo', 't', 'ano', 'mes'] 
            employee_col = 'nome_funcionario' 
            
            for col in colunas_filtro_a_exibir:
                if col in priority_cols: colunas_ordenadas.append(col)
            if employee_col in colunas_filtro_a_exibir: colunas_ordenadas.append(employee_col)
            for col in colunas_filtro_a_exibir:
                if col not in priority_cols and col != employee_col: colunas_ordenadas.append(col)
            
            colunas_ordenadas = list(dict.fromkeys(colunas_ordenadas)) 

            
            for i, col in enumerate(colunas_ordenadas):
                if col not in df_analise_base.columns: continue

                with cols_container[i % 3]:
                    filtro_key = f'filtro_key_{suffix}_{col}'
                    
                    # Usamos o DF COMPLETO para obter as opções únicas para que o filtro não "suma"
                    opcoes_unicas_full = sorted(df_analise_base[col].astype(str).fillna('N/A').unique().tolist())
                    
                    if filtro_key not in st.session_state:
                         st.session_state[filtro_key] = [] 
                    
                    current_default = st.session_state.get(filtro_key, [])
                    
                    safe_default = [opt for opt in current_default if opt in opcoes_unicas_full]
                    st.session_state[filtro_key] = safe_default 

                    is_filtered = len(safe_default) > 0
                    is_all_selected = len(safe_default) == len(opcoes_unicas_full)
                    
                    label_status = "- ATIVO" if is_filtered and not is_all_selected else ("- INATIVO" if not is_filtered else "- TOTAL")

                    with st.expander(f"**{col.replace('_', ' ').title()}** ({len(opcoes_unicas_full)} opções) {label_status}", expanded=False):
                        col_sel_btn, col_clr_btn = st.columns(2)
                        with col_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda c=col, s=suffix, ops=opcoes_unicas_full: set_multiselect_all(c, s, ops), key=f'select_all_btn_{suffix}_{col}', use_container_width=True)
                        with col_clr_btn: st.button("🗑️ Limpar (Nenhum)", on_click=lambda c=col, s=suffix: set_multiselect_none(c, s), key=f'select_none_btn_{suffix}_{col}', use_container_width=True)
                        st.markdown("---") 
                        
                        # Ordenação numérica para Mês e Ano
                        if col in ['mes', 'ano'] and all(item.isdigit() or item == 'N/A' for item in opcoes_unicas_full):
                            opcoes_unicas_full.sort(key=lambda x: int(x) if x.isdigit() else float('inf'))
                        
                        selecao_form = st.multiselect("Selecione:", options=opcoes_unicas_full, default=safe_default, key=filtro_key, label_visibility="collapsed")
                        current_active_filters_dict[col] = selecao_form
            
            return current_active_filters_dict, data_range # data_range é None
    
    # data_range_base_render e data_range_comp_render serão None
    filtros_ativos_base_render, data_range_base_render = render_filter_panel(tab_base, 'base', colunas_categoricas_filtro, df_analise_completo)
    filtros_ativos_comp_render, data_range_comp_render = render_filter_panel(tab_comparacao, 'comp', colunas_categoricas_filtro, df_analise_completo)
    
    st.session_state.active_filters_base = filtros_ativos_base_render
    st.session_state.active_filters_comp = filtros_ativos_comp_render
    
    st.markdown("---")
    submitted = st.button("✅ Aplicar Filtros e Rodar Comparação", use_container_width=True, type='primary')
    if submitted:
        st.session_state['filtro_reset_trigger'] += 1 
        st.rerun() 
        
    filtros_ativos_base_cache = st.session_state.active_filters_base
    filtros_ativos_comp_cache = st.session_state.active_filters_comp
    
    # Passamos None para data_range_base_cache e data_range_comp_cache
    df_analise_base_filtrado, df_analise_comp_filtrado = aplicar_filtros_comparacao(
        df_analise_completo, 
        colunas_categoricas_filtro, 
        filtros_ativos_base_cache, 
        filtros_ativos_comp_cache, 
        colunas_data, 
        None, # data_range_base_cache 
        None, # data_range_comp_cache
        st.session_state['filtro_reset_trigger']
    )
    st.session_state.df_filtrado_base = df_analise_base_filtrado
    st.session_state.df_filtrado_comp = df_analise_comp_filtrado
    
    df_base_safe = st.session_state.df_filtrado_base.copy() if not st.session_state.df_filtrado_base.empty else pd.DataFrame(columns=df_analise_completo.columns)
    df_comp_safe = st.session_state.df_filtrado_comp.copy() if not st.session_state.df_filtrado_comp.empty else pd.DataFrame(columns=df_analise_completo.columns)


    st.subheader("🌟 Resumo de Métricas e Análise de Variação - Visão Expert")
    
    if not df_base_safe.empty or not df_comp_safe.empty:
        gerar_analise_expert(
            df_analise_completo, 
            df_base_safe, 
            df_comp_safe, 
            filtros_ativos_base_cache, 
            filtros_ativos_comp_cache, 
            colunas_data, 
            None, # data_range_base_cache
            None  # data_range_comp_cache
        )
    else:
        st.warning("Um ou ambos os DataFrames (Base/Comparação) estão vazios após a aplicação dos filtros. Ajuste seus critérios e clique em 'Aplicar Filtros'.")

    st.markdown("---")
    
    st.subheader("📚 Detalhe dos Dados Filtrados (Base)")
    st.dataframe(df_base_safe, use_container_width=True)
