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
    from utils import formatar_moeda, inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes
except ImportError:
    st.error("ERRO CRÍTICO: O arquivo 'utils.py' não foi encontrado. Por favor, crie o arquivo 'utils.py' com o código fornecido e coloque-o no mesmo diretório de 'app.py'.")
    st.stop()
# ==============================================================================

# --- Configuração da Página e Persistência ---
st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")
PERSISTENCE_PATH = 'data/data_sets_catalog.pkl'

def load_catalog():
    """Tenta carregar o catálogo de datasets do arquivo de persistência."""
    if os.path.exists(PERSISTENCE_PATH):
        try:
            with open(PERSISTENCE_PATH, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return {}
    return {}

def save_catalog(catalog):
    """Salva o catálogo de datasets no arquivo de persistência."""
    try:
        os.makedirs(os.path.dirname(PERSISTENCE_PATH), exist_ok=True)
        with open(PERSISTENCE_PATH, 'wb') as f:
            pickle.dump(catalog, f)
    except Exception as e:
        st.sidebar.error(f"Erro ao salvar dados: {e}")

# --- Inicialização de Estado da Sessão ---
if 'data_sets_catalog' not in st.session_state:
    st.session_state.data_sets_catalog = load_catalog()
    
# Tenta definir o último dataset salvo como o atual na inicialização
initial_df = pd.DataFrame()
initial_filters = []
initial_values = []
initial_name = ""
if st.session_state.data_sets_catalog:
    last_name = list(st.session_state.data_sets_catalog.keys())[-1]
    initial_df = st.session_state.data_sets_catalog[last_name]['df']
    initial_filters = st.session_state.data_sets_catalog[last_name]['colunas_filtros_salvas']
    initial_values = st.session_state.data_sets_catalog[last_name]['colunas_valor_salvas']
    initial_name = last_name

if 'dados_atuais' not in st.session_state: st.session_state.dados_atuais = initial_df
if 'colunas_filtros_salvas' not in st.session_state: st.session_state.colunas_filtros_salvas = initial_filters
if 'colunas_valor_salvas' not in st.session_state: st.session_state.colunas_valor_salvas = initial_values
if 'current_dataset_name' not in st.session_state: st.session_state.current_dataset_name = initial_name
    
if 'uploaded_files_data' not in st.session_state: st.session_state.uploaded_files_data = {} 
if 'df_filtrado_base' not in st.session_state: st.session_state.df_filtrado_base = pd.DataFrame() 
if 'df_filtrado_comp' not in st.session_state: st.session_state.df_filtrado_comp = pd.DataFrame() 
if 'filtro_reset_trigger' not in st.session_state: st.session_state['filtro_reset_trigger'] = 0
if 'show_reconfig_section' not in st.session_state: st.session_state.show_reconfig_section = False
if 'active_filters_base' not in st.session_state: st.session_state.active_filters_base = {} 
if 'active_filters_comp' not in st.session_state: st.session_state.active_filters_comp = {} 
if 'cols_to_exclude_analysis' not in st.session_state: st.session_state.cols_to_exclude_analysis = [] 

# --- Funções de Lógica ---

def limpar_filtros_salvos():
    """Limpa o estado de todos os filtros e do DataFrame filtrado."""
    st.session_state.active_filters_base = {}
    st.session_state.active_filters_comp = {}
    
    st.session_state.df_filtrado_base = st.session_state.dados_atuais.copy()
    st.session_state.df_filtrado_comp = st.session_state.dados_atuais.copy()
    
    st.session_state['filtro_reset_trigger'] += 1
    
    # Limpa chaves de estado de widgets específicos
    chaves_a_limpar = [
        key for key in st.session_state.keys() 
        if key.startswith('filtro_key_base_') or key.startswith('date_range_key_base_') or 
           key.startswith('filtro_key_comp_') or key.startswith('date_range_key_comp_') or
           key.startswith('grafico_key_') or key.startswith('all_options_')
    ]
    for key in chaves_a_limpar:
        try:
            del st.session_state[key]
        except:
            pass
    
def set_multiselect_all(key, suffix, options_list):
    """Callback para o botão 'Selecionar Tudo'."""
    st.session_state[f'filtro_key_{suffix}_{key}'] = options_list
    st.rerun() 

def set_multiselect_none(key, suffix):
    """Callback para o botão 'Limpar'."""
    st.session_state[f'filtro_key_{suffix}_{key}'] = []
    st.rerun()

def initialize_widget_state(key, options, initial_default_calc):
    """Inicializa o estado dos multiselects de coluna no sidebar (para configuração)."""
    if key not in st.session_state:
        st.session_state[key] = initial_default_calc

def processar_dados_atuais(df_novo, colunas_filtros, colunas_valor, dataset_name):
    """Salva o dataset processado no catálogo, define como ativo e SALVA EM DISCO."""
    
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
    
    # Define um default para as colunas a excluir na análise
    default_exclude = [col for col in df_novo.columns if col in ['emp', 'eve', 'seq', 'nr_func']]
    st.session_state.cols_to_exclude_analysis = default_exclude
    
    return True, df_novo

def switch_dataset(dataset_name):
    """Troca o dataset ativo no dashboard."""
    if dataset_name in st.session_state.data_sets_catalog:
        data = st.session_state.data_sets_catalog[dataset_name]
        st.session_state.dados_atuais = data['df']
        st.session_state.colunas_filtros_salvas = data['colunas_filtros_salvas']
        st.session_state.colunas_valor_salvas = data['colunas_valor_salvas']
        st.session_state.current_dataset_name = dataset_name
        limpar_filtros_salvos()
        st.session_state.show_reconfig_section = False
        
        # Atualiza o default de colunas a excluir para o novo dataset
        default_exclude = [col for col in data['df'].columns if col in ['emp', 'eve', 'seq', 'nr_func']]
        st.session_state.cols_to_exclude_analysis = default_exclude
        
        st.rerun()
    else:
        st.error(f"Dataset '{dataset_name}' não encontrado.")
        
def show_reconfig_panel():
    """Define o estado para exibir a seção de configuração de colunas."""
    st.session_state.show_reconfig_section = True
    
def remove_uploaded_file(file_name):
    """Remove um arquivo da lista de uploads pendentes e reinicializa o estado."""
    if file_name in st.session_state.uploaded_files_data:
        del st.session_state.uploaded_files_data[file_name]
        
        st.session_state.dados_atuais = pd.DataFrame()
        st.session_state.current_dataset_name = ""
        st.session_state.show_reconfig_section = False
        st.rerun() 


# --- Aplicação de Filtros (Aprimorada para Base e Comparação) ---
@st.cache_data(show_spinner="Aplicando filtros de Base e Comparação...")
def aplicar_filtros_comparacao(df_base, col_filtros, filtros_ativos_base, filtros_ativos_comp, col_data, data_range_base, data_range_comp, trigger):
    
    def _aplicar_filtro_single(df, col_filtros_list, filtros_ativos_dict, col_data, data_range):
        df_filtrado_temp = df.copy()
        
        # 1. Filtros Categóricos
        for col in col_filtros_list:
            selecao = filtros_ativos_dict.get(col)
            # O filtro só deve ocorrer se houver seleção e se não for igual a TODAS as opções
            if selecao and col in df_filtrado_temp.columns and selecao != []: 
                opcoes_unicas = df_base[col].astype(str).fillna('N/A').unique().tolist()
                if len(selecao) < len(opcoes_unicas):
                     df_filtrado_temp = df_filtrado_temp[df_filtrado_temp[col].astype(str).isin(selecao)]
        
        # 2. Filtro de Data
        if data_range and len(data_range) == 2 and col_data and col_data[0] in df_filtrado_temp.columns:
            col_data_padrao = col_data[0]
            df_filtrado_temp[col_data_padrao] = pd.to_datetime(df_filtrado_temp[col_data_padrao], errors='coerce')
            
            data_min_df = df_base[col_data_padrao].min()
            data_max_df = df_base[col_data_padrao].max()
            
            if pd.to_datetime(data_range[0]) > pd.to_datetime(data_min_df) or pd.to_datetime(data_range[1]) < pd.to_datetime(data_max_df):
                df_filtrado_temp = df_filtrado_temp[
                    (df_filtrado_temp[col_data_padrao] >= pd.to_datetime(data_range[0])) &
                    (df_filtrado_temp[col_data_padrao] <= pd.to_datetime(data_range[1]))
                ]
        return df_filtrado_temp
    
    df_base_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_base, col_data, data_range_base)
    df_comp_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_comp, col_data, data_range_comp)
    
    return df_base_filtrado, df_comp_filtrado


# --- Geração de Rótulos de Filtro (SIMPLIFICADO) ---

def gerar_rotulo_filtro(df_analise, filtros_ativos, col_data, data_range):
    """Gera uma string CONCISA para o cabeçalho do KPI."""
    rotulo_filtros = []
    
    # 1. Filtros Categóricos
    for col in filtros_ativos.keys():
        valores = filtros_ativos[col]
        if col in df_analise.columns:
            total_opcoes = len(df_analise[col].astype(str).fillna('N/A').unique().tolist())
            
            if valores and len(valores) > 0 and len(valores) < total_opcoes:
                
                col_display = col.replace('_', ' ').title()
                if len(valores) == 1:
                    rotulo_filtros.append(f"**{col_display}:** {valores[0]}")
                else:
                    rotulo_filtros.append(f"**{col_display}:** {len(valores)} itens")

    # 2. Filtro de Data
    if data_range and len(data_range) == 2 and col_data:
        col_data_padrao = colunas_data[0]
        data_min_df = df_analise[col_data_padrao].min()
        data_max_df = df_analise[col_data_padrao].max()

        if pd.to_datetime(data_range[0]) > pd.to_datetime(data_min_df) or pd.to_datetime(data_range[1]) < pd.to_datetime(data_max_df):
            data_min = data_range[0].strftime('%Y-%m-%d')
            data_max = data_range[1].strftime('%Y-%m-%d')
            rotulo_filtros.append(f"**Data:** {data_min} a {data_max}")
    
    if not rotulo_filtros:
        return "Nenhum Filtro Ativo (Total Geral do Dataset)"
    
    resumo = " | ".join(rotulo_filtros[:4])
    if len(rotulo_filtros) > 4:
        resumo += "..."
        
    return resumo


# --- NOVO: FUNÇÃO PARA ANÁLISE DINÂMICA DE VARIAÇÃO APRIMORADA ---

def analisar_variacao_dinamica(df_base, df_comp, colunas_para_analisar):
    """Calcula e exibe Contagem, Soma e Média para todas as colunas não excluídas."""
    
    st.subheader("📊 Análise Dinâmica de Variação (Detalhe)")
    st.caption(f"Valores calculados sobre {len(df_base):,.0f} linhas (Base) e {len(df_comp):,.0f} linhas (Comparação) após os filtros.")
    st.markdown("---")

    # Colunas de interesse principal para exibição formatada
    colunas_chave_display = {
        'valor': 'VALOR (R$)',
        'referencia': 'REFERÊNCIA',
    }
    
    # Colunas de análise: todas as colunas do DF, exceto as excluídas
    cols_a_analisar = [col for col in df_base.columns if col not in colunas_para_analisar]

    # Estrutura de exibição: 2 colunas principais (Base e Comparação)
    cols_principal = st.columns(2)
    
    # --- Painel de Análise BASE ---
    with cols_principal[0]:
        st.markdown("<h5 style='color: #28a745;'>BASE (Referência)</h5>", unsafe_allow_html=True)
        
        # Cabeçalho da tabela de análise (Contagem, Soma, Média)
        cols_header = st.columns([2, 1, 1, 1])
        cols_header[0].markdown("**MÉTRICA**")
        cols_header[1].markdown("**CONT. REGISTROS**")
        cols_header[2].markdown("**SOMA/CONT. ÚNICOS**")
        cols_header[3].markdown("**MÉDIA**")
        st.markdown("<div style='margin: 0 -15px;'>---</div>", unsafe_allow_html=True)

        
        for col in cols_a_analisar:
            
            nome_display = colunas_chave_display.get(col, col.replace('_', ' ').title())
            
            # 1. Contagem de Registros (para categóricas e numéricas)
            contagem_registros = len(df_base.dropna(subset=[col]))
            
            # 2. Cálculos Condicionais (Soma, Média, Contagem Única)
            if pd.api.types.is_numeric_dtype(df_base[col]):
                is_numeric = True
                contagem_unicos_ou_soma = df_base[col].sum()
                media = df_base[col].mean()
            else:
                is_numeric = False
                contagem_unicos_ou_soma = df_base[col].nunique(dropna=True)
                media = np.nan
            
            # Exibição
            cols = st.columns([2, 1, 1, 1])
            cols[0].write(nome_display)
            cols[1].write(f"{contagem_registros:,.0f}".replace(",", ".")) 
            
            if is_numeric:
                # Se for numérica, exibe Soma e Média
                if col in [c.lower() for c in colunas_chave_display.keys() if c in ['valor']]:
                    cols[2].write(formatar_moeda(contagem_unicos_ou_soma))
                    cols[3].write(formatar_moeda(media))
                else:
                    cols[2].write(f"{contagem_unicos_ou_soma:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    cols[3].write(f"{media:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            else:
                # Se não for numérica, exibe Contagem Única (no lugar da Soma)
                cols[2].write(f"{contagem_unicos_ou_soma:,.0f}".replace(",", "."))
                cols[3].write("N/A")

    # --- Painel de Análise COMPARAÇÃO ---
    with cols_principal[1]:
        st.markdown("<h5 style='color: #dc3545;'>COMPARAÇÃO (Alvo)</h5>", unsafe_allow_html=True)
        
        # Cabeçalho da tabela de análise
        cols_header = st.columns([2, 1, 1, 1])
        cols_header[0].markdown("**MÉTRICA**")
        cols_header[1].markdown("**CONT. REGISTROS**")
        cols_header[2].markdown("**SOMA/CONT. ÚNICOS**")
        cols_header[3].markdown("**MÉDIA**")
        st.markdown("<div style='margin: 0 -15px;'>---</div>", unsafe_allow_html=True)
        
        for col in cols_a_analisar:
            if col not in df_comp.columns: continue
            
            nome_display = colunas_chave_display.get(col, col.replace('_', ' ').title())
            
            # 1. Contagem de Registros
            contagem_registros = len(df_comp.dropna(subset=[col]))
            
            # 2. Cálculos Condicionais (Soma, Média, Contagem Única)
            if pd.api.types.is_numeric_dtype(df_comp[col]):
                is_numeric = True
                contagem_unicos_ou_soma = df_comp[col].sum()
                media = df_comp[col].mean()
            else:
                is_numeric = False
                contagem_unicos_ou_soma = df_comp[col].nunique(dropna=True)
                media = np.nan
            
            # Exibição
            cols = st.columns([2, 1, 1, 1])
            cols[0].write(nome_display)
            cols[1].write(f"{contagem_registros:,.0f}".replace(",", ".")) 
            
            if is_numeric:
                # Se for numérica, exibe Soma e Média
                if col in [c.lower() for c in colunas_chave_display.keys() if c in ['valor']]:
                    cols[2].write(formatar_moeda(contagem_unicos_ou_soma))
                    cols[3].write(formatar_moeda(media))
                else:
                    cols[2].write(f"{contagem_unicos_ou_soma:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    cols[3].write(f"{media:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            else:
                # Se não for numérica, exibe Contagem Única (no lugar da Soma)
                cols[2].write(f"{contagem_unicos_ou_soma:,.0f}".replace(",", "."))
                cols[3].write("N/A")

    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)


# --- SIDEBAR (CONFIGURAÇÕES E UPLOAD) ---
with st.sidebar:
    st.markdown("# 📊")
    st.title("⚙️ Configurações do Expert")
    
    st.info("💡 **Carga Inicial Salva:** Os datasets processados são salvos em um arquivo de persistência (`data/data_sets_catalog.pkl`).")

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

    st.header("1. Upload e Gerenciamento de Dados")
    
    # Form para adicionar arquivos
    with st.form("file_upload_form", clear_on_submit=True):
        uploaded_files_new = st.file_uploader(
            "📥 Carregar Novo(s) CSV/XLSX", 
            type=['csv', 'xlsx'], 
            accept_multiple_files=True,
            key="file_uploader_widget"
        )
        
        if st.session_state.data_sets_catalog:
            default_dataset_name = f"Dataset Complementar ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        else:
            default_dataset_name = f"Dataset Inicial ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
            
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

    # Exibir e Remover Arquivos Pendentes
    if st.session_state.uploaded_files_data:
        st.markdown("---")
        st.markdown("##### Arquivos Pendentes para Processamento:")
        
        st.button("🔁 Reconfigurar e Processar", 
                  on_click=show_reconfig_panel,
                  key='reconfig_btn_sidebar',
                  use_container_width=True,
                  type='primary')
        st.markdown("---")
        
        for file_name in st.session_state.uploaded_files_data.keys():
            col_file, col_remove = st.columns([4, 1])
            with col_file:
                st.caption(f"- **{file_name}**")
            with col_remove:
                st.button("Remover", 
                          key=f"remove_file_btn_{file_name}", 
                          on_click=remove_uploaded_file, 
                          args=(file_name,), 
                          use_container_width=True)
        
        st.markdown("---")
        
        # --- Lógica de Configuração de Colunas ---
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
                st.info(f"Dados consolidados de {len(st.session_state.uploaded_files_data)} arquivos. Total de {len(df_novo)} linhas.")
                
                # --- Seleção de Colunas (Moeda, Texto, Filtros) ---
                moeda_default = [col for col in colunas_disponiveis if any(word in col for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
                
                if 'moeda_select' not in st.session_state: initialize_widget_state('moeda_select', colunas_disponiveis, moeda_default)
                if 'texto_select' not in st.session_state: initialize_widget_state('texto_select', colunas_disponiveis, [])
                
                st.markdown("##### 💰 Colunas de VALOR (R$)")
                col_moeda_sel_btn, col_moeda_clr_btn = st.columns(2)
                with col_moeda_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda ops=colunas_disponiveis: set_multiselect_all('moeda_select', 'config', ops), key='moeda_select_all_btn', use_container_width=True)
                with col_moeda_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('moeda_select', 'config'), key='moeda_select_clear_btn', use_container_width=True)
                colunas_moeda = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.moeda_select, key='moeda_select', label_visibility="collapsed")
                
                st.markdown("---")
                st.markdown("##### 📝 Colunas TEXTO/ID")
                col_texto_sel_btn, col_texto_clr_btn = st.columns(2)
                with col_texto_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda ops=colunas_disponiveis: set_multiselect_all('texto_select', 'config', ops), key='texto_select_all_btn', use_container_width=True)
                with col_texto_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('texto_select', 'config'), key='texto_select_clear_btn', use_container_width=True)
                colunas_texto = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.texto_select, key='texto_select', label_visibility="collapsed")
                st.markdown("---")
                
                df_processado = inferir_e_converter_tipos(df_novo, colunas_texto, colunas_moeda)
                
                colunas_para_filtro_options = df_processado.select_dtypes(include=['object', 'category']).columns.tolist()
                filtro_default = [c for c in colunas_para_filtro_options if c in ['tipo', 'descricao_evento', 'nome_funcionario', 'emp', 'mes', 'ano']] 
                if 'filtros_select' not in st.session_state:
                    initialize_widget_state('filtros_select', colunas_para_filtro_options, filtro_default)
                
                st.markdown("##### ⚙️ Colunas para FILTROS")
                col_filtro_sel_btn, col_filtro_clr_btn = st.columns(2)
                with col_filtro_sel_btn: 
                    st.button("✅ Selecionar Tudo", on_click=lambda ops=colunas_para_filtro_options: set_multiselect_all('filtros_select', 'config', ops), key='filtros_select_all_btn', use_container_width=True)
                with col_filtro_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('filtros_select', 'config'), key='filtros_select_clear_btn', use_container_width=True)
                colunas_para_filtro = st.multiselect("Selecione:", options=colunas_para_filtro_options, default=st.session_state.filtros_select, key='filtros_select', label_visibility="collapsed")
                
                colunas_valor_dashboard = df_processado.select_dtypes(include=np.number).columns.tolist()
                st.markdown("---")
                
                # Botão de Processamento
                if st.button("✅ Processar e Exibir Dados Atuais", key='processar_sidebar_btn'): 
                    if df_processado.empty:
                        st.error("O DataFrame está vazio após o processamento.")
                    elif not colunas_para_filtro:
                        st.warning("Selecione pelo menos uma coluna na seção 'Colunas para FILTROS'.")
                    else:
                        dataset_name_to_save = st.session_state.get('current_dataset_name_input', default_dataset_name)
                        sucesso, df_processado_salvo = processar_dados_atuais(df_processado, colunas_para_filtro, colunas_valor_dashboard, dataset_name_to_save)
                        if sucesso:
                            ausentes = verificar_ausentes(df_processado_salvo, colunas_para_filtro)
                            if ausentes: 
                                for col, (n, t) in ausentes.items():
                                    st.warning(f"A coluna '{col}' possui {n} valores ausentes (em um total de {t} registros). O filtro pode não funcionar corretamente.")
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

# Geração dos Botões de Troca de Dataset
if st.session_state.data_sets_catalog:
    st.subheader("🔁 Datasets Salvos")
    dataset_names = list(st.session_state.data_sets_catalog.keys())
    cols = st.columns(min(len(dataset_names), 4)) 
    for i, name in enumerate(dataset_names):
        is_active = name == st.session_state.current_dataset_name
        button_label = f"📁 {name}" if not is_active else f"✅ {name} (Atual)"
        button_type = "primary" if is_active else "secondary"
        with cols[i % 4]:
            st.button(button_label, key=f"dataset_switch_{name}", on_click=switch_dataset, args=(name,), type=button_type, use_container_width=True)
    st.markdown("---") 


if st.session_state.dados_atuais.empty: 
    st.info("Sistema pronto. O Dashboard será exibido após carregar, processar e selecionar um Dataset.")
else:
    df_analise_base = st.session_state.dados_atuais 
    st.header(f"📊 Dashboard Expert de Análise de Indicadores ({st.session_state.current_dataset_name})")
    
    colunas_categoricas_filtro = st.session_state.colunas_filtros_salvas
    colunas_numericas_salvas = st.session_state.colunas_valor_salvas
    _, colunas_data = encontrar_colunas_tipos(df_analise_base) 
    
    # Seleção da Métrica Principal
    col_metrica_select, _, col_reset_btn = st.columns([2, 2, 1])
    with col_metrica_select:
        colunas_valor_metricas = ['Contagem de Registros'] + colunas_numericas_salvas 
        default_metric_index = 0
        try:
            if 'metrica_principal_selectbox' in st.session_state and st.session_state.metrica_principal_selectbox in colunas_valor_metricas:
                default_metric_index = colunas_valor_metricas.index(st.session_state.metrica_principal_selectbox)
            elif 'valor' in colunas_numericas_salvas:
                default_metric_index = colunas_valor_metricas.index('valor')
            elif colunas_numericas_salvas:
                default_metric_index = colunas_valor_metricas.index(colunas_numericas_salvas[0])
        except ValueError:
             pass

        coluna_metrica_principal = st.selectbox("Métrica de Valor Principal para KPI e Gráficos:", 
                                                 options=colunas_valor_metricas, 
                                                 index=default_metric_index, 
                                                 key='metrica_principal_selectbox', 
                                                 help="Selecione a coluna numérica principal para o cálculo de KPIs (Total e Média) e para o Eixo Y dos gráficos.")
    with col_reset_btn:
        st.markdown("###### ") 
        if st.button("🗑️ Resetar Filtros", help="Redefine todas as seleções de filtro para o estado inicial."):
            limpar_filtros_salvos()
            st.rerun() 
    
    st.markdown("---") 
    
    # --- Painel de Filtros Duplo (Base e Comparação) ---
    st.markdown("#### 🔍 Configuração de Análise de Variação")
    
    tab_base, tab_comparacao = st.tabs(["Filtros da BASE (Referência)", "Filtros de COMPARAÇÃO (Alvo)"])

    def render_filter_panel(tab_container, suffix, colunas_filtro_a_exibir, df_analise_base):
        
        current_active_filters_dict = {}
        
        with tab_container:
            st.markdown(f"**Defina os filtros para o conjunto {suffix.upper()}**")
            
            cols_container = st.columns(3) 
            filtros_col_1 = colunas_filtro_a_exibir[::3]
            filtros_col_2 = colunas_filtro_a_exibir[1::3]
            filtros_col_3 = colunas_filtro_a_exibir[2::3]


            for idx, filtros_col in enumerate([filtros_col_1, filtros_col_2, filtros_col_3]):
                with cols_container[idx]:
                    for col in filtros_col:
                        if col not in df_analise_base.columns: continue
                        
                        opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('N/A').unique().tolist())
                        filtro_key = f'filtro_key_{suffix}_{col}'
                        
                        if filtro_key not in st.session_state:
                             st.session_state[filtro_key] = opcoes_unicas
                            
                        is_filtered = len(st.session_state.get(filtro_key, [])) > 0 and len(st.session_state.get(filtro_key, [])) < len(opcoes_unicas)
                        
                        with st.expander(f"**{col.replace('_', ' ').title()}** ({len(opcoes_unicas)} opções) {'- ATIVO' if is_filtered else ''}", expanded=is_filtered):
                            col_sel_btn, col_clr_btn = st.columns(2)
                            
                            with col_sel_btn: 
                                st.button("✅ Selecionar Tudo", 
                                          on_click=lambda c=col, s=suffix, ops=opcoes_unicas: set_multiselect_all(c, s, ops), 
                                          key=f'select_all_btn_{suffix}_{col}', 
                                          use_container_width=True)
                            with col_clr_btn: 
                                st.button("🗑️ Limpar", 
                                          on_click=lambda c=col, s=suffix: set_multiselect_none(c, s), 
                                          key=f'select_none_btn_{suffix}_{col}', 
                                          use_container_width=True)
                            st.markdown("---") 
                            
                            selecao_form = st.multiselect("Selecione:", 
                                                          options=opcoes_unicas, 
                                                          default=st.session_state.get(filtro_key, opcoes_unicas), 
                                                          key=filtro_key, 
                                                          label_visibility="collapsed")
                            
                            current_active_filters_dict[col] = selecao_form

            return current_active_filters_dict

    # Renderiza os dois painéis de filtro
    filtros_ativos_base_render = render_filter_panel(tab_base, 'base', colunas_categoricas_filtro, df_analise_base)
    filtros_ativos_comp_render = render_filter_panel(tab_comparacao, 'comp', colunas_categoricas_filtro, df_analise_base)
    
    st.session_state.active_filters_base = filtros_ativos_base_render
    st.session_state.active_filters_comp = filtros_ativos_comp_render


    # --- Filtro de Data ---
    data_range_base = None
    data_range_comp = None
    if colunas_data:
        col_data_padrao = colunas_data[0]
        df_col_data = df_analise_base[col_data_padrao].dropna()
        
        if not df_col_data.empty:
            try:
                data_series = pd.to_datetime(df_col_data, errors='coerce').dropna()
                data_min_df = data_series.min()
                data_max_df = data_series.max()
                
                if pd.notna(data_min_df) and pd.notna(data_max_df):
                    st.markdown(f"#### 🗓️ Intervalo de Data ({col_data_padrao.replace('_', ' ').title()})")
                    col_date_base, col_date_comp = st.columns(2)
                    
                    data_range_base_key = f'date_range_key_base_{col_data_padrao}'
                    data_range_comp_key = f'date_range_key_comp_{col_data_padrao}'
                    
                    initial_default_range = (data_min_df.to_pydatetime(), data_max_df.to_pydatetime())
                    if data_range_base_key not in st.session_state:
                         st.session_state[data_range_base_key] = initial_default_range
                    if data_range_comp_key not in st.session_state:
                         st.session_state[data_range_comp_key] = initial_default_range
                    
                    with col_date_base:
                        data_range_base = st.slider("Data BASE", min_value=data_min_df.to_pydatetime(), max_value=data_max_df.to_pydatetime(), 
                                                     value=st.session_state[data_range_base_key], format="YYYY/MM/DD", key=data_range_base_key)
                        
                    with col_date_comp:
                        data_range_comp = st.slider("Data COMPARAÇÃO", min_value=data_min_df.to_pydatetime(), max_value=data_max_df.to_pydatetime(), 
                                                     value=st.session_state[data_range_comp_key], format="YYYY/MM/DD", key=data_range_comp_key)
                            
            except Exception:
                st.warning("Erro na exibição dos filtros de data.")


    st.markdown("---")
    
    # --- Seletor de Colunas a Excluir na Análise Dinâmica ---
    st.markdown("#### ⚙️ Configuração da Análise Dinâmica")
    colunas_disponiveis_analise = df_analise_base.columns.tolist()
    
    st.session_state.cols_to_exclude_analysis = st.multiselect(
        "**Colunas a EXCLUIR** da Análise Dinâmica (Geral):",
        options=colunas_disponiveis_analise,
        default=st.session_state.cols_to_exclude_analysis,
        key='multiselect_exclude_cols_analysis',
        help="Selecione colunas irrelevantes para métricas de contagem, soma ou média (ex: IDs internos)."
    )
    st.markdown("---")
    
    submitted = st.button("✅ Aplicar Filtros e Rodar Comparação", use_container_width=True)
    if submitted:
        st.session_state['filtro_reset_trigger'] += 1 
        st.rerun() 
    
    # --- Aplicação de Filtros (Cache) ---
    filtros_ativos_base_cache = {
        col: st.session_state.get(f'filtro_key_base_{col}') 
        for col in colunas_categoricas_filtro 
        if st.session_state.get(f'filtro_key_base_{col}') is not None
    }
    filtros_ativos_comp_cache = {
        col: st.session_state.get(f'filtro_key_comp_{col}') 
        for col in colunas_categoricas_filtro 
        if st.session_state.get(f'filtro_key_comp_{col}') is not None
    }

    data_range_base_cache = st.session_state.get(f'date_range_key_base_{colunas_data[0]}') if colunas_data and f'date_range_key_base_{colunas_data[0]}' in st.session_state else None
    data_range_comp_cache = st.session_state.get(f'date_range_key_comp_{colunas_data[0]}') if colunas_data and f'date_range_key_comp_{colunas_data[0]}' in st.session_state else None


    df_analise_base_filtrado, df_analise_comp_filtrado = aplicar_filtros_comparacao(
        df_analise_base, 
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


    # --- Métricas Chave de Variação (KPIs) ---
    st.subheader("🌟 Métricas Chave de Variação")
    
    rotulo_base = gerar_rotulo_filtro(df_analise_base, filtros_ativos_base_cache, colunas_data, data_range_base_cache)
    rotulo_comp = gerar_rotulo_filtro(df_analise_base, filtros_ativos_comp_cache, colunas_data, data_range_comp_cache)

    st.markdown(f"""
        <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 15px;">
            <p style="margin: 0; font-weight: bold;"><span style="color: #28a745;">BASE (Ref.):</span> {rotulo_base}</p>
            <p style="margin: 0; font-weight: bold;"><span style="color: #dc3545;">COMPARAÇÃO (Alvo):</span> {rotulo_comp}</p>
        </div>
    """, unsafe_allow_html=True)
    
    df_base_safe = st.session_state.df_filtrado_base.copy() if not st.session_state.df_filtrado_base.empty else pd.DataFrame(columns=df_analise_base.columns)
    df_comp_safe = st.session_state.df_filtrado_comp.copy() if not st.session_state.df_filtrado_comp.empty else pd.DataFrame(columns=df_analise_base.columns)
    coluna_metrica_principal = st.session_state.get('metrica_principal_selectbox')
    
    def format_delta(value):
        if np.isfinite(value):
            return f"{value:,.2f} %".replace(",", "X").replace(".", ",").replace("X", ".")
        return "N/A" if value == 0 else ("+Inf %" if value == np.inf else "-Inf %")

    if coluna_metrica_principal != 'Contagem de Registros':
        # Sums
        total_base = df_base_safe[coluna_metrica_principal].sum()
        total_comp = df_comp_safe[coluna_metrica_principal].sum()
        variacao_total = ((total_comp - total_base) / total_base) * 100 if total_base != 0 else (0 if total_comp == 0 else np.inf)

        # Means
        media_base = df_base_safe[coluna_metrica_principal].mean() if len(df_base_safe) > 0 else 0
        media_comp = df_comp_safe[coluna_metrica_principal].mean() if len(df_comp_safe) > 0 else 0
        variacao_media = ((media_comp - media_base) / media_base) * 100 if media_base != 0 else (0 if media_comp == 0 else np.inf)

        col_kpi_total, col_kpi_media = st.columns(2)
        
        with col_kpi_total:
            st.metric(
                label=f"SOMA {coluna_metrica_principal.upper()}",
                value=formatar_moeda(total_comp),
                delta=format_delta(variacao_total),
                delta_color=("inverse" if variacao_total < 0 else "normal") if np.isfinite(variacao_total) else "off"
            )
            st.caption(f"Valor BASE (Referência): {formatar_moeda(total_base)}")

        with col_kpi_media:
            st.metric(
                label=f"MÉDIA {coluna_metrica_principal.upper()}",
                value=formatar_moeda(media_comp),
                delta=format_delta(variacao_media),
                delta_color=("inverse" if variacao_media < 0 else "normal") if np.isfinite(variacao_media) else "off"
            )
            st.caption(f"Valor BASE (Referência): {formatar_moeda(media_base)}")
    else:
        # KPI Contagem de Registros
        cont_base = len(df_base_safe)
        cont_comp = len(df_comp_safe)
        variacao_cont = ((cont_comp - cont_base) / cont_base) * 100 if cont_base != 0 else (0 if cont_comp == 0 else np.inf)
        
        col_kpi_cont, _ = st.columns(2)
        with col_kpi_cont:
            st.metric(
                label="CONTAGEM DE REGISTROS",
                value=f"{cont_comp:,.0f}".replace(",", "."),
                delta=format_delta(variacao_cont),
                delta_color=("inverse" if variacao_cont < 0 else "normal") if np.isfinite(variacao_cont) else "off"
            )
            st.caption(f"Valor BASE (Referência): {cont_base:,.0f}".replace(",", "."))
    
    st.markdown("---")
    
    # CHAMADA DA FUNÇÃO DE ANÁLISE DINÂMICA
    analisar_variacao_dinamica(df_base_safe, df_comp_safe, st.session_state.cols_to_exclude_analysis)


    # --- Visualização do DataFrame (Detalhe) ---
    st.subheader("📚 Detalhe dos Dados Filtrados (Base)")
    st.dataframe(df_base_safe, use_container_width=True)
