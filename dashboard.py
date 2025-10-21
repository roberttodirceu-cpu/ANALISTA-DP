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
    st.error("ERRO CRÍTICO: O arquivo 'utils.py' não foi encontrado ou está incompleto. Por favor, crie/verifique o arquivo 'utils.py' com o código completo fornecido.")
    st.stop()
# ==============================================================================

# --- Configuração da Página e Persistência ---
st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")
PERSISTENCE_PATH = 'data/data_sets_catalog.pkl'

# --- Funções Auxiliares de Estado e Catálogo ---

# [Manter funções load_catalog, save_catalog, processar_dados_atuais, switch_dataset, etc. da versão anterior]
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
    """Limpa o estado de todos os filtros e do DataFrame filtrado, e força recarga dos widgets de filtro."""
    st.session_state.active_filters_base = {}
    st.session_state.active_filters_comp = {}
    st.session_state.df_filtrado_base = st.session_state.dados_atuais.copy()
    st.session_state.df_filtrado_comp = st.session_state.dados_atuais.copy()
    st.session_state['filtro_reset_trigger'] += 1
    
    # Limpa chaves de estado de widgets específicos
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
    st.rerun() 

def set_multiselect_all(key, suffix, options_list):
    """Callback para o botão 'Selecionar Tudo'."""
    st.session_state[f'filtro_key_{suffix}_{key}'] = options_list
    st.rerun() 

def set_multiselect_none(key, suffix):
    """Callback para o botão 'Limpar'."""
    st.session_state[f'filtro_key_{suffix}_{key}'] = []
    st.rerun()
    
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

def initialize_widget_state(key, options, initial_default_calc):
    if key not in st.session_state:
        st.session_state[key] = initial_default_calc


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
    
    def _aplicar_filtro_single(df, col_filtros_list, filtros_ativos_dict, col_data, data_range):
        df_filtrado_temp = df.copy()
        
        # 1. Filtros Categóricos
        for col in col_filtros_list:
            selecao = filtros_ativos_dict.get(col)
            opcoes_unicas = df_base[col].astype(str).fillna('N/A').unique().tolist()
            
            # CORREÇÃO: Aplica filtro SOMENTE se a seleção não estiver vazia E não for total
            if selecao and col in df_filtrado_temp.columns and len(selecao) > 0 and len(selecao) < len(opcoes_unicas): 
                df_filtrado_temp = df_filtrado_temp[df_filtrado_temp[col].astype(str).isin(selecao)]
            # Se a seleção for vazia (default) ou total, o filtro é ignorado para essa coluna.
        
        # 2. Filtro de Data
        if data_range and len(data_range) == 2 and col_data and col_data[0] in df_filtrado_temp.columns:
            col_data_padrao = col_data[0]
            df_filtrado_temp[col_data_padrao] = pd.to_datetime(df_filtrado_temp[col_data_padrao], errors='coerce')
            
            data_min_df = df_base[col_data_padrao].min()
            data_max_df = df_base[col_data_padrao].max()
            
            # Aplica filtro de data APENAS se o intervalo selecionado for diferente do intervalo total do DF
            # A diferença de 1 segundo é usada para evitar problemas de precisão.
            if (pd.to_datetime(data_range[0]) > (pd.to_datetime(data_min_df) + pd.Timedelta(seconds=1))) or \
               (pd.to_datetime(data_range[1]) < (pd.to_datetime(data_max_df) - pd.Timedelta(seconds=1))):
                df_filtrado_temp = df_filtrado_temp[
                    (df_filtrado_temp[col_data_padrao] >= pd.to_datetime(data_range[0])) &
                    (df_filtrado_temp[col_data_padrao] <= pd.to_datetime(data_range[1]))
                ]
        return df_filtrado_temp
    
    df_base_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_base, col_data, data_range_base)
    df_comp_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_comp, col_data, data_range_comp)
    
    return df_base_filtrado, df_comp_filtrado


# --- FUNÇÃO PARA TABELA DE RESUMO E MÉTRICAS "EXPERT" (Mantida para visualização) ---

def gerar_analise_expert(df_completo, df_base, df_comp):
    """
    Gera uma apresentação visualmente atraente do resumo de métricas chave,
    focando na comparação Base vs. Comparação e no contexto do Total Geral.
    """
    
    colunas_valor_salvas = st.session_state.colunas_valor_salvas
    colunas_moeda = [col for col in colunas_valor_salvas if any(word in col for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
    colunas_referencia = [col for col in colunas_valor_salvas if col not in colunas_moeda]
    
    dados_resumo = []

    # 1. Métrica: Contagem de Registros
    len_completo = len(df_completo)
    len_base = len(df_base)
    len_comp = len(df_comp)
    
    variacao_len = ((len_comp - len_base) / len_base) * 100 if len_base > 0 else (0 if len_comp == 0 else np.inf)
    
    dados_resumo.append({
        'Métrica': 'CONTAGEM DE REGISTROS',
        'Total Geral': len_completo,
        'Base (Filtrado)': len_base,
        'Comparação (Filtrado)': len_comp,
        'Variação %': variacao_len,
        'Tipo': 'Contagem'
    })

    # 2. Métricas de Moeda (SOMA)
    for col in colunas_moeda:
        total_geral_soma = df_completo[col].sum()
        total_base_soma = df_base[col].sum()
        total_comp_soma = df_comp[col].sum()
        
        variacao_soma = ((total_comp_soma - total_base_soma) / total_base_soma) * 100 if total_base_soma != 0 else (0 if total_comp_soma == 0 else np.inf)

        dados_resumo.append({
            'Métrica': f"SOMA: {col.upper()}",
            'Total Geral': total_geral_soma,
            'Base (Filtrado)': total_base_soma,
            'Comparação (Filtrado)': total_comp_soma,
            'Variação %': variacao_soma,
            'Tipo': 'Moeda'
        })
        
    # 3. Métricas de Referência (Contagem de Únicos)
    for col in colunas_referencia:
        total_geral_count = df_completo[col].nunique(dropna=True)
        total_base_count = df_base[col].nunique(dropna=True)
        total_comp_count = df_comp[col].nunique(dropna=True)
        
        variacao_count = ((total_comp_count - total_base_count) / total_base_count) * 100 if total_base_count != 0 else (0 if total_comp_count == 0 else np.inf)

        dados_resumo.append({
            'Métrica': f"CONT. ÚNICOS: {col.upper()}",
            'Total Geral': total_geral_count,
            'Base (Filtrado)': total_base_count,
            'Comparação (Filtrado)': total_comp_count,
            'Variação %': variacao_count,
            'Tipo': 'Contagem'
        })
            
    df_resumo = pd.DataFrame(dados_resumo)

    # --- APRESENTAÇÃO VISUAL APRIMORADA ---
    
    # 3.1. Cards de Métricas (Foco na Contagem e Principal Valor)
    st.markdown("##### 🚀 Análise Rápida de Impacto")
    col_kpi = st.columns(len(colunas_moeda) + 1 if colunas_moeda else 2)
    
    # KPI 1: Contagem de Registros
    kpi1_data = df_resumo[df_resumo['Métrica'] == 'CONTAGEM DE REGISTROS'].iloc[0]
    
    delta_val = kpi1_data['Comparação (Filtrado)'] - kpi1_data['Base (Filtrado)']
    delta_str = f"{delta_val:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    col_kpi[0].metric(
        label="Total de Registros (Base)", 
        value=f"{kpi1_data['Base (Filtrado)']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."), 
        delta=f"Variação: {delta_str}"
    )
    col_kpi[0].caption(f"Total Geral: {kpi1_data['Total Geral']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # KPIs de Valor (Primeiro valor de moeda, se houver)
    if colunas_moeda:
        kpi_moeda_data = df_resumo[df_resumo['Métrica'] == f"SOMA: {colunas_moeda[0].upper()}"].iloc[0]
        
        delta_val = kpi_moeda_data['Comparação (Filtrado)'] - kpi_moeda_data['Base (Filtrado)']
        delta_str = formatar_moeda(delta_val).replace("R$", "") 
        
        col_kpi[1].metric(
            label=f"Soma Total ({colunas_moeda[0].replace('_', ' ').title()})", 
            value=formatar_moeda(kpi_moeda_data['Base (Filtrado)']), 
            delta=f"Variação: {delta_str}"
        )
        col_kpi[1].caption(f"Total Geral: {formatar_moeda(kpi_moeda_data['Total Geral'])}")
    
    st.markdown("---")

    # 3.2. Tabela Dinâmica de Variação (Visualização Expert)
    st.markdown("##### 🔍 Comparativo Detalhado de Métricas Chave")

    # Preparar DF para a tabela visual
    df_tabela = df_resumo.copy()
    
    # Formatação para o Total Geral
    df_tabela['TOTAL GERAL (Sem Filtro)'] = df_tabela.apply(
        lambda row: formatar_moeda(row['Total Geral']) if row['Tipo'] == 'Moeda' else f"{row['Total Geral']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."), 
        axis=1
    )

    # Formatação para Base (Filtrado)
    df_tabela['BASE (FILTRADO)'] = df_tabela.apply(
        lambda row: formatar_moeda(row['Base (Filtrado)']) if row['Tipo'] == 'Moeda' else f"{row['Base (Filtrado)']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."),
        axis=1
    )

    # Formatação para Comparação (Filtrado)
    df_tabela['COMPARAÇÃO (FILTRADO)'] = df_tabela.apply(
        lambda row: formatar_moeda(row['Comparação (Filtrado)']) if row['Tipo'] == 'Moeda' else f"{row['Comparação (Filtrado)']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."),
        axis=1
    )

    # Formatação da Variação com Iconografia e Cor
    def format_variacao_tabela(val):
        if not np.isfinite(val):
            return "N/A"
        
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
    
    # Selecionar e Renomear Colunas Finais
    df_final_exibicao = df_tabela[['Métrica', 'TOTAL GERAL (Sem Filtro)', 'BASE (FILTRADO)', 'COMPARAÇÃO (FILTRADO)', 'VARIAÇÃO BASE vs COMP (%)']]

    # Exibe a tabela final
    st.markdown(df_final_exibicao.to_html(escape=False, index=False), unsafe_allow_html=True)


# --- SIDEBAR (CONFIGURAÇÕES E UPLOAD) ---
with st.sidebar:
    # ... [Manter o código completo do sidebar da versão anterior aqui] ...
    st.markdown("# 📊")
    st.title("⚙️ Configurações do Expert")
    
    # Botão de Limpeza Completa
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

    # Exibe Datasets Salvos
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
            
    st.header("2. Upload e Processamento")
    
    # Form para adicionar arquivos
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

    # Exibir e Remover Arquivos Pendentes (e Lógica de Configuração/Processamento)
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
                            df_temp = pd.read_csv(uploaded_file_stream, sep=';', decimal=',', encoding='utf-8')
                        except Exception:
                            uploaded_file_stream.seek(0)
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
                df_novo.columns = df_novo.columns.str.strip().str.lower().str.replace(' ', '_', regex=False)
                colunas_disponiveis = df_novo.columns.tolist()
                st.info(f"Total de {len(df_novo)} linhas para configurar.")
                
                moeda_default = [col for col in colunas_disponiveis if any(word in col for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
                if 'moeda_select' not in st.session_state: initialize_widget_state('moeda_select', colunas_disponiveis, moeda_default)
                if 'texto_select' not in st.session_state: initialize_widget_state('texto_select', colunas_disponiveis, [])
                
                st.markdown("##### 💰 Colunas de VALOR (R$)")
                colunas_moeda = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.moeda_select, key='moeda_select', label_visibility="collapsed")
                
                st.markdown("---")
                st.markdown("##### 📝 Colunas TEXTO/ID")
                colunas_texto = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.texto_select, key='texto_select', label_visibility="collapsed")
                st.markdown("---")
                
                df_processado = inferir_e_converter_tipos(df_novo, colunas_texto, colunas_moeda)
                
                colunas_para_filtro_options = df_processado.select_dtypes(include=['object', 'category']).columns.tolist()
                filtro_default = [c for c in colunas_para_filtro_options if c in ['tipo', 'descricao_evento', 'nome_funcionario', 'emp', 'mes', 'ano']] 
                if 'filtros_select' not in st.session_state:
                    initialize_widget_state('filtros_select', colunas_para_filtro_options, filtro_default)
                
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
             st.info("Sistema pronto. Carregue um ou mais arquivos CSV/XLSX para iniciar o processamento e salvamento do dataset.")


# --- Dashboard Principal ---

st.markdown("---") 

if st.session_state.dados_atuais.empty: 
    st.info("Sistema pronto. O Dashboard será exibido após carregar, processar e selecionar um Dataset.")
else:
    df_analise_completo = st.session_state.dados_atuais.copy()
    st.header(f"📊 Dashboard Expert de Análise de Indicadores ({st.session_state.current_dataset_name})")
    
    colunas_categoricas_filtro = st.session_state.colunas_filtros_salvas
    _, colunas_data = encontrar_colunas_tipos(df_analise_completo) 
    
    # -------------------------------------------------------------
    # 1. Painel de Filtros Simplificado (Filtros Categóricos e Data)
    # -------------------------------------------------------------
    
    st.markdown("#### 🔍 Configuração de Análise de Variação")
    col_reset_btn = st.columns([4, 1])[1]
    with col_reset_btn:
        st.button("🗑️ Resetar Filtros", on_click=limpar_filtros_salvos, use_container_width=True)
    
    tab_base, tab_comparacao = st.tabs(["Filtros da BASE (Referência)", "Filtros de COMPARAÇÃO (Alvo)"])

    def render_filter_panel(tab_container, suffix, colunas_filtro_a_exibir, df_analise_base):
        current_active_filters_dict = {}
        data_range = None
        with tab_container:
            
            # --- Filtro de Data ---
            if colunas_data:
                col_data_padrao = colunas_data[0]
                df_col_data = df_analise_base[col_data_padrao].dropna()
                if not df_col_data.empty:
                    data_series = pd.to_datetime(df_col_data, errors='coerce').dropna()
                    data_min_df = data_series.min()
                    data_max_df = data_series.max()
                    
                    if pd.notna(data_min_df) and pd.notna(data_max_df):
                        data_range_key = f'date_range_key_{suffix}_{col_data_padrao}'
                        initial_default_range = (data_min_df.to_pydatetime(), data_max_df.to_pydatetime())
                        if data_range_key not in st.session_state: st.session_state[data_range_key] = initial_default_range
                        
                        data_range = st.slider(f"Data - {suffix.upper()}: {col_data_padrao.replace('_', ' ').title()}", 
                                                 min_value=data_min_df.to_pydatetime(), max_value=data_max_df.to_pydatetime(), 
                                                 value=st.session_state[data_range_key], format="YYYY/MM/DD", key=data_range_key)

            # --- Filtros Categóricos ---
            st.markdown("---")
            st.markdown("##### Filtros Categóricos")
            cols_container = st.columns(3) 
            
            for i, col in enumerate(colunas_filtro_a_exibir):
                if col not in df_analise_base.columns: continue
                
                with cols_container[i % 3]:
                    opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('N/A').unique().tolist())
                    filtro_key = f'filtro_key_{suffix}_{col}'
                    
                    # CORREÇÃO CRÍTICA: Inicializa com lista VAZIA se não houver estado anterior.
                    if filtro_key not in st.session_state:
                         st.session_state[filtro_key] = [] 

                    is_filtered = len(st.session_state.get(filtro_key, [])) > 0
                    is_all_selected = len(st.session_state.get(filtro_key, [])) == len(opcoes_unicas)
                    
                    label_status = "- ATIVO" if is_filtered and not is_all_selected else ("- INATIVO" if not is_filtered else "- TOTAL")

                    with st.expander(f"**{col.replace('_', ' ').title()}** ({len(opcoes_unicas)} opções) {label_status}", expanded=False):
                        col_sel_btn, col_clr_btn = st.columns(2)
                        with col_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda c=col, s=suffix, ops=opcoes_unicas: set_multiselect_all(c, s, ops), key=f'select_all_btn_{suffix}_{col}', use_container_width=True)
                        with col_clr_btn: st.button("🗑️ Limpar (Nenhum)", on_click=lambda c=col, s=suffix: set_multiselect_none(c, s), key=f'select_none_btn_{suffix}_{col}', use_container_width=True)
                        st.markdown("---") 
                        
                        # Usa o estado da sessão como valor padrão (inicia vazio)
                        selecao_form = st.multiselect("Selecione:", options=opcoes_unicas, default=st.session_state.get(filtro_key, []), key=filtro_key, label_visibility="collapsed")
                        current_active_filters_dict[col] = selecao_form
            
            return current_active_filters_dict, data_range

    filtros_ativos_base_render, data_range_base_render = render_filter_panel(tab_base, 'base', colunas_categoricas_filtro, df_analise_completo)
    filtros_ativos_comp_render, data_range_comp_render = render_filter_panel(tab_comparacao, 'comp', colunas_categoricas_filtro, df_analise_completo)
    
    st.session_state.active_filters_base = filtros_ativos_base_render
    st.session_state.active_filters_comp = filtros_ativos_comp_render
    
    st.markdown("---")
    submitted = st.button("✅ Aplicar Filtros e Rodar Comparação", use_container_width=True, type='primary')
    if submitted:
        st.session_state['filtro_reset_trigger'] += 1 
        st.rerun() 
        
    # --- Coleta de Filtros para Aplicação (usando o estado da sessão) ---
    filtros_ativos_base_cache = st.session_state.active_filters_base
    filtros_ativos_comp_cache = st.session_state.active_filters_comp
    
    data_range_base_cache = data_range_base_render
    data_range_comp_cache = data_range_comp_render

    # -------------------------------------------------------------
    # 2. Aplicação do Filtro (Cache)
    # -------------------------------------------------------------
    df_analise_base_filtrado, df_analise_comp_filtrado = aplicar_filtros_comparacao(
        df_analise_completo, 
        colunas_categoricas_filtro, 
        filtros_ativos_base_cache, 
        filtros_ativos_comp_cache, 
        colunas_data, 
        data_range_base_cache, 
        data_range_comp_cache,
        st.session_state['filtro_reset_trigger']
    )
    st.session_state.df_filtrado_base = df_analise_base_filtrado
    st.session_state.df_filtrado_comp = df_analise_comp_filtrado
    
    # Previne erros de DataFrame vazio
    df_base_safe = st.session_state.df_filtrado_base.copy() if not st.session_state.df_filtrado_base.empty else pd.DataFrame(columns=df_analise_completo.columns)
    df_comp_safe = st.session_state.df_filtrado_comp.copy() if not st.session_state.df_filtrado_comp.empty else pd.DataFrame(columns=df_analise_completo.columns)


    # -------------------------------------------------------------
    # 3. Exibição da Análise Expert Aprimorada
    # -------------------------------------------------------------
    st.subheader("🌟 Resumo de Métricas e Análise de Variação - Visão Expert")
    
    # Rótulos de contexto
    rotulo_base = gerar_rotulo_filtro(df_analise_completo, filtros_ativos_base_cache, colunas_data, data_range_base_cache)
    rotulo_comp = gerar_rotulo_filtro(df_analise_completo, filtros_ativos_comp_cache, colunas_data, data_range_comp_cache)

    st.markdown(f"""
        <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 15px; background-color: #f8f9fa;">
            <p style="margin: 0; font-weight: bold; font-size: 14px;"><span style="color: #007bff;">BASE (Ref.):</span> {rotulo_base}</p>
            <p style="margin: 0; font-weight: bold; font-size: 14px;"><span style="color: #6f42c1;">COMPARAÇÃO (Alvo):</span> {rotulo_comp}</p>
        </div>
    """, unsafe_allow_html=True)
    
    if not df_base_safe.empty or not df_comp_safe.empty:
        gerar_analise_expert(df_analise_completo, df_base_safe, df_comp_safe)
    else:
        st.warning("Um ou ambos os DataFrames (Base/Comparação) estão vazios após a aplicação dos filtros. Ajuste seus critérios e clique em 'Aplicar Filtros'.")

    st.markdown("---")
    
    # -------------------------------------------------------------
    # 4. Detalhe dos Dados
    # -------------------------------------------------------------
    st.subheader("📚 Detalhe dos Dados Filtrados (Base)")
    st.dataframe(df_base_safe, use_container_width=True)
