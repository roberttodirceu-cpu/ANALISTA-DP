import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime
from io import BytesIO
import pickle 

# Importa as funções do utils.py
# Certifique-se de que o 'utils.py' está no mesmo diretório
try:
    from utils import formatar_moeda, inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes
except ImportError:
    st.error("Erro: O arquivo 'utils.py' não foi encontrado. Certifique-se de que ele está no mesmo diretório.")
    st.stop()

st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")

# --- Configuração de Persistência em Disco ---
PERSISTENCE_PATH = 'data/data_sets_catalog.pkl'

def load_catalog():
    """Tenta carregar o catálogo de datasets do arquivo de persistência."""
    if os.path.exists(PERSISTENCE_PATH):
        try:
            with open(PERSISTENCE_PATH, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            st.sidebar.error(f"Erro ao carregar dados salvos: {e}. Inicializando vazio.")
            return {}
    return {}

def save_catalog(catalog):
    """Salva o catálogo de datasets no arquivo de persistência."""
    try:
        # Cria a pasta 'data' se não existir
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


# --- Funções de Lógica ---

def limpar_filtros_salvos():
    """Limpa o estado de todos os filtros e do DataFrame filtrado."""
    if 'df_filtrado_base' in st.session_state: del st.session_state['df_filtrado_base'] 
    if 'df_filtrado_comp' in st.session_state: del st.session_state['df_filtrado_comp'] 
        
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
    
def set_multiselect_all(key, suffix):
    """Callback para o botão 'Selecionar Tudo'."""
    # A chave de opções foi ajustada para ser única: all_options_[suffix]_[coluna]
    all_options_key = f'all_options_{suffix}_{key}'
    st.session_state[f'filtro_key_{suffix}_{key}'] = st.session_state.get(all_options_key, [])
    st.rerun() 

def set_multiselect_none(key, suffix):
    """Callback para o botão 'Limpar'."""
    st.session_state[f'filtro_key_{suffix}_{key}'] = []
    st.rerun()

def initialize_widget_state(key, options, initial_default_calc):
    """Inicializa o estado dos multiselects de coluna no sidebar (para configuração)."""
    all_options_key = f'all_{key}_options'
    st.session_state[all_options_key] = options
    if key not in st.session_state:
        st.session_state[key] = initial_default_calc

def processar_dados_atuais(df_novo, colunas_filtros, colunas_valor, dataset_name):
    """Salva o dataset processado no catálogo, define como ativo e SALVA EM DISCO."""
    
    if st.session_state.uploaded_files_data:
        file_names = list(st.session_state.uploaded_files_data.keys())
        base_name = dataset_name if len(file_names) > 1 else os.path.splitext(file_names[0])[0]
    else:
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
        st.rerun()
    else:
        st.error(f"Dataset '{dataset_name}' não encontrado.")
        
def show_reconfig_panel():
    """Define o estado para exibir a seção de configuração de colunas."""
    st.session_state.show_reconfig_section = True
    
# --- CORREÇÃO DO ERRO: Nova função auxiliar para DEL ---
def remove_uploaded_file(file_name):
    """Remove um arquivo da lista de uploads pendentes e reinicializa o estado."""
    if file_name in st.session_state.uploaded_files_data:
        del st.session_state.uploaded_files_data[file_name]
        
        # Reinicializa as variáveis de trabalho
        st.session_state.dados_atuais = pd.DataFrame()
        st.session_state.current_dataset_name = ""
        st.session_state.show_reconfig_section = False
        st.rerun() 


# --- Aplicação de Filtros (Aprimorada para Base e Comparação) ---
@st.cache_data(show_spinner="Aplicando filtros de Base e Comparação...")
def aplicar_filtros_comparacao(df_base, col_filtros, filtros_ativos_base, filtros_ativos_comp, col_data, data_range_base, data_range_comp):
    
    def _aplicar_filtro_single(df, col_filtros_list, filtros_ativos_dict, data_range):
        df_filtrado_temp = df.copy()
        # 1. Filtros Categóricos
        for col in col_filtros_list:
            selecao = filtros_ativos_dict.get(col)
            if selecao and col in df_filtrado_temp.columns: 
                df_filtrado_temp = df_filtrado_temp[df_filtrado_temp[col].astype(str).isin(selecao)]
        
        # 2. Filtro de Data
        if data_range and len(data_range) == 2 and col_data and col_data[0] in df_filtrado_temp.columns:
            col_data_padrao = col_data[0]
            df_filtrado_temp = df_filtrado_temp[
                (df_filtrado_temp[col_data_padrao] >= pd.to_datetime(data_range[0])) &
                (df_filtrado_temp[col_data_padrao] <= pd.to_datetime(data_range[1]))
            ]
        return df_filtrado_temp
    
    # Aplica filtros para Base e Comparação
    df_base_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_base, data_range_base)
    df_comp_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_comp, data_range_comp)
    
    return df_base_filtrado, df_comp_filtrado


# --- SIDEBAR (CONFIGURAÇÕES E UPLOAD) ---
with st.sidebar:
    st.markdown("# 📊")
    st.title("⚙️ Configurações do Expert")
    
    st.info("💡 **Carga Inicial Salva:** Os datasets processados são salvos em um arquivo de persistência (`data/data_sets_catalog.pkl`).")

    # Botão de Limpeza Completa
    if st.button("Limpar Cache de Dados"):
        st.cache_data.clear()
        if os.path.exists(PERSISTENCE_PATH):
            try:
                os.remove(PERSISTENCE_PATH)
                st.sidebar.success("Arquivo de persistência limpo.")
            except Exception as e:
                st.sidebar.error(f"Erro ao remover arquivo de persistência: {e}")
        keys_to_clear = [k for k in st.session_state.keys() if not k.startswith('_')]
        for key in keys_to_clear:
            del st.session_state[key]
        st.info("Cache de dados e estado da sessão limpos! Recarregando...")
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
                # Botão de Remover com a função auxiliar (CORREÇÃO)
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
                        
                except Exception:
                    pass 

            if all_dataframes:
                df_novo = pd.concat(all_dataframes, ignore_index=True)
            
            if df_novo.empty:
                st.error("O conjunto de dados consolidado está vazio.")
                st.session_state.dados_atuais = pd.DataFrame() 
            else:
                df_novo.columns = df_novo.columns.str.strip().str.lower()
                colunas_disponiveis = df_novo.columns.tolist()
                st.info(f"Dados consolidados de {len(st.session_state.uploaded_files_data)} arquivos. Total de {len(df_novo)} linhas.")
                
                # --- Seleção de Colunas (Moeda, Texto, Filtros) ---
                moeda_default = [col for col in colunas_disponiveis if any(word in col for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
                
                if 'moeda_select' not in st.session_state: initialize_widget_state('moeda_select', colunas_disponiveis, moeda_default)
                if 'texto_select' not in st.session_state: initialize_widget_state('texto_select', colunas_disponiveis, [])
                
                st.markdown("##### 💰 Colunas de VALOR (R$)")
                col_moeda_sel_btn, col_moeda_clr_btn = st.columns(2)
                with col_moeda_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('moeda_select', 'config'), key='moeda_select_all_btn', use_container_width=True)
                with col_moeda_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('moeda_select', 'config'), key='moeda_select_clear_btn', use_container_width=True)
                colunas_moeda = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.moeda_select, key='moeda_select', label_visibility="collapsed")
                
                st.markdown("---")
                st.markdown("##### 📝 Colunas TEXTO/ID")
                col_texto_sel_btn, col_texto_clr_btn = st.columns(2)
                with col_texto_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('texto_select', 'config'), key='texto_select_all_btn', use_container_width=True)
                with col_texto_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('texto_select', 'config'), key='texto_select_clear_btn', use_container_width=True)
                colunas_texto = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.texto_select, key='texto_select', label_visibility="collapsed")
                st.markdown("---")
                
                df_processado = inferir_e_converter_tipos(df_novo, colunas_texto, colunas_moeda)
                colunas_para_filtro_options = df_processado.select_dtypes(include=['object', 'category']).columns.tolist()
                filtro_default = [c for c in colunas_para_filtro_options if c in ['tipo', 'situacao', 'empresa', 'departamento']]
                if 'filtros_select' not in st.session_state:
                    initialize_widget_state('filtros_select', colunas_para_filtro_options, filtro_default)
                
                st.markdown("##### ⚙️ Colunas para FILTROS")
                col_filtro_sel_btn, col_filtro_clr_btn = st.columns(2)
                with col_filtro_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('filtros_select', 'config'), key='filtros_select_all_btn', use_container_width=True)
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
                        sucesso, df_processado_salvo = processar_dados_atuais(df_processado, colunas_para_filtro, colunas_valor_dashboard, dataset_name_input)
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
             st.info("Carregue um ou mais arquivos CSV/XLSX para iniciar o processamento e salvamento do dataset.")


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
            elif colunas_numericas_salvas:
                default_metric_index = colunas_valor_metricas.index(colunas_numericas_salvas[0])
        except ValueError:
             pass

        coluna_metrica_principal = st.selectbox("Métrica de Valor Principal para KPI e Gráficos:", 
                                                options=colunas_valor_metricas, 
                                                index=default_metric_index, 
                                                key='metrica_principal_selectbox', 
                                                help="Selecione a coluna numérica principal para o cálculo de KPIs e para o Eixo Y dos gráficos.")
    with col_reset_btn:
        st.markdown("###### ") 
        if st.button("🗑️ Resetar Filtros", help="Redefine todas as seleções de filtro para o estado inicial."):
            limpar_filtros_salvos()
            st.rerun() 
    
    st.markdown("---") 
    
    # --- Painel de Filtros Duplo (Base e Comparação) ---
    st.markdown("#### 🔍 Configuração de Análise de Variação")
    
    tab_base, tab_comparacao = st.tabs(["Filtros da BASE (Referência)", "Filtros de COMPARAÇÃO (Alvo)"])
    
    def render_filter_panel(tab_container, suffix, colunas_filtro_a_exibir, colunas_data, df_analise_base):
        with tab_container:
            st.markdown(f"**Defina os filtros para o conjunto {suffix.upper()}**")
            
            # Divide os filtros em 3 colunas
            cols_container = st.columns(3) 
            filtros_col_1 = colunas_filtro_a_exibir[::3]
            filtros_col_2 = colunas_filtro_a_exibir[1::3]
            filtros_col_3 = colunas_filtro_a_exibir[2::3]

            for idx, filtros_col in enumerate([filtros_col_1, filtros_col_2, filtros_col_3]):
                with cols_container[idx]:
                    for col in filtros_col:
                        if col not in df_analise_base.columns: continue
                        opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('').unique().tolist())
                        filtro_key = f'filtro_key_{suffix}_{col}'
                        
                        if filtro_key not in st.session_state:
                             st.session_state[filtro_key] = []
                             
                        all_options_key = f'all_options_{suffix}_{col}'
                        st.session_state[all_options_key] = opcoes_unicas

                        with st.expander(f"**{col}** ({len(opcoes_unicas)} opções)"):
                            col_sel_btn, col_clr_btn = st.columns(2)
                            with col_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda c=col, s=suffix: set_multiselect_all(c, s), key=f'select_all_btn_{suffix}_{col}', use_container_width=True)
                            with col_clr_btn: st.button("🗑️ Limpar", on_click=lambda c=col, s=suffix: set_multiselect_none(c, s), key=f'select_none_btn_{suffix}_{col}', use_container_width=True)
                            st.markdown("---") 
                            
                            selecao_padrao_form = st.session_state.get(filtro_key, [])
                            st.multiselect("Selecione:", options=opcoes_unicas, default=selecao_padrao_form, key=filtro_key, label_visibility="collapsed")

            # Filtro de Data
            if colunas_data:
                col_data_padrao = colunas_data[0]
                df_col_data = df_analise_base[col_data_padrao].dropna()
                if not df_col_data.empty and pd.notna(df_col_data.min()) and pd.notna(df_col_data.max()):
                    data_min = df_col_data.min()
                    data_max = df_col_data.max()
                    try:
                        date_key = f'date_range_key_{suffix}_{col_data_padrao}'
                        default_date_range = st.session_state.get(date_key, (data_min.to_pydatetime(), data_max.to_pydatetime()))
                        
                        st.markdown(f"#### 🗓️ Intervalo de Data ({col_data_padrao})")
                        st.slider(f"Data {suffix.upper()}", 
                                  min_value=data_min.to_pydatetime(), 
                                  max_value=data_max.to_pydatetime(), 
                                  value=default_date_range, 
                                  format="YYYY/MM/DD", 
                                  key=date_key)
                    except Exception:
                        st.warning(f"Erro na exibição do filtro de data para {suffix}.")


    # Renderiza os dois painéis de filtro
    render_filter_panel(tab_base, 'base', colunas_categoricas_filtro, colunas_data, df_analise_base)
    render_filter_panel(tab_comparacao, 'comp', colunas_categoricas_filtro, colunas_data, df_analise_base)

    st.markdown("---")
    submitted = st.button("✅ Aplicar Filtros e Rodar Comparação", use_container_width=True)
    if submitted:
        st.rerun() 

    # --- Coletar Filtros Ativos ---
    filtros_ativos_base = {col: st.session_state.get(f'filtro_key_base_{col}') for col in colunas_categoricas_filtro if st.session_state.get(f'filtro_key_base_{col}')}
    filtros_ativos_comp = {col: st.session_state.get(f'filtro_key_comp_{col}') for col in colunas_categoricas_filtro if st.session_state.get(f'filtro_key_comp_{col}')}

    data_range_base = st.session_state.get(f'date_range_key_base_{colunas_data[0]}', None) if colunas_data and colunas_data[0] in df_analise_base.columns else None
    data_range_comp = st.session_state.get(f'date_range_key_comp_{colunas_data[0]}', None) if colunas_data and colunas_data[0] in df_analise_base.columns else None
    
    # Aplica os filtros e salva nos session_state
    df_analise_base_filtrado, df_analise_comp_filtrado = aplicar_filtros_comparacao(
        df_analise_base, 
        colunas_categoricas_filtro, 
        filtros_ativos_base, 
        filtros_ativos_comp, 
        colunas_data, 
        data_range_base, 
        data_range_comp
    )
    st.session_state.df_filtrado_base = df_analise_base_filtrado
    st.session_state.df_filtrado_comp = df_analise_comp_filtrado


    # --- Métricas Chave de Variação (KPIs Aprimorados) ---
    st.subheader("🌟 Métricas Chave de Variação")
    
    df_base = st.session_state.df_filtrado_base
    df_comp = st.session_state.df_filtrado_comp
    coluna_metrica_principal = st.session_state.get('metrica_principal_selectbox')
    
    # Calcula os valores base e comparação
    if coluna_metrica_principal == 'Contagem de Registros':
        valor_base = len(df_base)
        valor_comp = len(df_comp)
        metric_label = "Registros"
    elif coluna_metrica_principal and coluna_metrica_principal in colunas_numericas_salvas and not df_base.empty and not df_comp.empty:
        valor_base = df_base[coluna_metrica_principal].sum()
        valor_comp = df_comp[coluna_metrica_principal].sum()
        metric_label = coluna_metrica_principal.replace('_', ' ').title()
    else:
        valor_base = 0
        valor_comp = 0
        metric_label = "Valor (N/A)"

    # Cálculo da Variação
    if valor_base != 0 and valor_base is not None:
        variacao_abs = valor_comp - valor_base
        variacao_perc = (variacao_abs / valor_base) * 100
        delta_perc = f"{variacao_perc:.2f}%"
        # Inverte a cor delta se a métrica não for contagem e o valor for negativo
        delta_color = 'inverse' if variacao_perc < 0 and coluna_metrica_principal != 'Contagem de Registros' else 'normal'
    else:
        variacao_abs = 0
        variacao_perc = 0
        delta_perc = "0.00%"
        delta_color = 'off'

    col_kpi_base, col_kpi_comp, col_kpi_abs, col_kpi_perc = st.columns(4)
    
    if coluna_metrica_principal == 'Contagem de Registros':
        col_kpi_base.metric(f"Base Registros", f"{valor_base:,.0f}".replace(',', '.'))
        col_kpi_comp.metric(f"Comp. Registros", f"{valor_comp:,.0f}".replace(',', '.'))
        # Para Contagem, o delta é 'normal' (verde se positivo, vermelho se negativo)
        col_kpi_abs.metric(f"Δ Absoluta", f"{variacao_abs:,.0f}".replace(',', '.'), delta=f"{variacao_abs:,.0f}".replace(',', '.'))
        col_kpi_perc.metric(f"Δ Percentual", f"{variacao_perc:.2f}%", delta=delta_perc)
    else:
        col_kpi_base.metric(f"Total {metric_label} (Base)", formatar_moeda(valor_base))
        col_kpi_comp.metric(f"Total {metric_label} (Comparação)", formatar_moeda(valor_comp))
        col_kpi_abs.metric("Δ Absoluta", formatar_moeda(variacao_abs), delta=formatar_moeda(variacao_abs), delta_color=delta_color)
        col_kpi_perc.metric("Δ Percentual", f"{variacao_perc:.2f}%", delta=delta_perc, delta_color=delta_color)

    st.caption(f"**Base (Referência):** {len(df_base)} registros. **Comparação (Alvo):** {len(df_comp)} registros.")
    st.markdown("---")
    
    # --- Análise Visual (Gráficos Aprimorados) ---
    st.subheader("📈 Análise Visual (Gráficos) ")

    # Configuração Multi-Dimensional dos Gráficos (Eixo X e Quebra/Cor)
    col_config_x, col_config_color = st.columns(2)
    
    colunas_categoricas_para_grafico = ['Nenhuma (Total)'] + colunas_categoricas_filtro
    coluna_agrupamento_principal = colunas_categoricas_filtro[0] if colunas_categoricas_filtro else 'Nenhuma (Total)'
    
    with col_config_x:
        coluna_x_fixa = st.selectbox(
            "Agrupar/Comparar por (Eixo X):", 
            options=colunas_categoricas_para_grafico, 
            index=colunas_categoricas_para_grafico.index(coluna_agrupamento_principal) if coluna_agrupamento_principal in colunas_categoricas_para_grafico else 0,
            key='grafico_key_eixo_x'
        )
    
    with col_config_color:
        colunas_quebra_opcoes = ['Nenhuma'] + [c for c in colunas_categoricas_filtro if c != coluna_x_fixa and c != 'Nenhuma (Total)']
        coluna_quebra_cor = st.selectbox(
            "Quebrar Análise/Cor por:", 
            options=colunas_quebra_opcoes, 
            index=0,
            key='grafico_key_quebra_cor',
            help="Use para quebrar a métrica principal por uma dimensão adicional."
        )

    st.markdown("---") 

    # --- GRÁFICO 1: Comparação de Valor BASE vs. COMPARAÇÃO ---
    col_graph_1, col_graph_2 = st.columns(2)
    
    with col_graph_1:
        st.markdown(f"##### Gráfico 1: Comparação BASE vs. COMPARAÇÃO por **{coluna_x_fixa}**")
        
        opcoes_grafico_1 = ['Barra Agrupada (Comparação)']
        if coluna_metrica_principal != 'Contagem de Registros':
             opcoes_grafico_1.append('Dispersão (Box Plot)')
             
        tipo_grafico_1 = st.selectbox("Tipo de Visualização (Gráfico 1):", options=opcoes_grafico_1, key='tipo_grafico_1')

        eixo_x_real = None if coluna_x_fixa == 'Nenhuma (Total)' else coluna_x_fixa
        color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
        
        df_plot_base = df_base
        df_plot_comp = df_comp
        
        y_col_agg = 'Valor Métrica'
        
        if not df_plot_base.empty and not df_plot_comp.empty:
            
            try:
                if eixo_x_real:
                    if tipo_grafico_1 == 'Barra Agrupada (Comparação)':
                        agg_cols = [eixo_x_real]
                        if color_real: agg_cols.append(color_real)

                        if coluna_metrica_principal == 'Contagem de Registros':
                            agg_func = lambda df: df.groupby(agg_cols, as_index=False).size().rename(columns={'size': y_col_agg})
                        else:
                            agg_func = lambda df: df.groupby(agg_cols, as_index=False)[coluna_metrica_principal].sum().rename(columns={coluna_metrica_principal: y_col_agg})
                            
                        df_agg_base = agg_func(df_plot_base)
                        df_agg_comp = agg_func(df_plot_comp)
                        
                        df_agg_base['Conjunto'] = 'BASE'
                        df_agg_comp['Conjunto'] = 'COMPARAÇÃO'
                        df_final = pd.concat([df_agg_base, df_agg_comp], ignore_index=True)

                        fig = px.bar(df_final, x=eixo_x_real, y=y_col_agg, color='Conjunto', 
                                     pattern_shape=color_real,
                                     barmode='group',
                                     title=f'Comparação de {y_col_agg} por {eixo_x_real}')
                        fig.update_layout(xaxis={'categoryorder': 'total descending'}, title_x=0.5)
                        st.plotly_chart(fig, use_container_width=True)
                        
                    elif tipo_grafico_1 == 'Dispersão (Box Plot)' and coluna_metrica_principal != 'Contagem de Registros':
                        df_plot_base['Conjunto'] = 'BASE'
                        df_plot_comp['Conjunto'] = 'COMPARAÇÃO'
                        df_dispersao = pd.concat([df_plot_base, df_plot_comp], ignore_index=True)
                        
                        fig = px.box(df_dispersao, x='Conjunto', y=coluna_metrica_principal, color=color_real,
                                     title=f'Distribuição de {coluna_metrica_principal} entre Base e Comparação')
                        fig.update_layout(title_x=0.5)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    else:
                        st.info("Gráfico não gerado. Verifique a seleção de Eixo X e Tipo de Gráfico.")
                        
                else:
                    st.info("Selecione uma coluna para o Eixo X para gerar o Gráfico de Comparação.")

            except Exception as e:
                st.error(f"Erro ao gerar o Gráfico 1: {e}")
        else:
            st.warning("Um ou ambos os conjuntos de dados (Base/Comparação) estão vazios após a aplicação dos filtros.")
            
    # --- Gráfico 2: (Base) Série Temporal/Distribuição/Dispersão ---
    with col_graph_2:
        st.markdown(f"##### Gráfico 2: Foco em **{coluna_metrica_principal}** (Conjunto Base)")
        opcoes_grafico_2 = ['Distribuição (Histograma)']
        
        if colunas_data:
            opcoes_grafico_2.append('Série Temporal (Linha)')
            
        if coluna_metrica_principal != 'Contagem de Registros' and len(colunas_numericas_salvas) > 1:
            opcoes_grafico_2.append('Relação (Dispersão)')
            
        tipo_grafico_2 = st.selectbox("Tipo de Visualização (Gráfico 2):", options=opcoes_grafico_2, key='tipo_grafico_2')
        
        if not df_base.empty:
            fig = None
            try:
                if tipo_grafico_2 == 'Série Temporal (Linha)' and colunas_data:
                    eixo_x_data = colunas_data[0]
                    color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
                    
                    agg_cols = [eixo_x_data]
                    if color_real: agg_cols.append(color_real)
                    
                    if coluna_metrica_principal == 'Contagem de Registros':
                         df_agg = df_base.groupby(agg_cols, as_index=False).size().rename(columns={'size': 'Contagem'})
                         y_col_agg = 'Contagem'
                    else:
                         df_agg = df_base.groupby(agg_cols, as_index=False)[coluna_metrica_principal].sum()
                         y_col_agg = coluna_metrica_principal
                         
                    fig = px.line(df_agg, x=eixo_x_data, y=y_col_agg, color=color_real,
                                  title=f'Tendência Temporal (Base): Soma de {y_col_agg}{" por " + color_real if color_real else ""}')
                    
                elif tipo_grafico_2 == 'Distribuição (Histograma)':
                    if coluna_metrica_principal != 'Contagem de Registros':
                        color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
                        fig = px.histogram(df_base, x=coluna_metrica_principal, color=color_real,
                                           title=f'Distribuição (Base) de {coluna_metrica_principal}{" por " + color_real if color_real else ""}')
                    else:
                        st.warning("Selecione Coluna de Valor Numérica para Histograma.")
                        
                elif tipo_grafico_2 == 'Relação (Dispersão)' and coluna_metrica_principal != 'Contagem de Registros':
                    colunas_para_dispersao = [c for c in colunas_numericas_salvas if c != coluna_metrica_principal]
                    if colunas_para_dispersao:
                        coluna_x_disp = st.selectbox("Selecione o Eixo X para Dispersão:", options=colunas_para_dispersao, key='col_x_disp_2')
                        color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
                        fig = px.scatter(df_base, x=coluna_x_disp, y=coluna_metrica_principal, color=color_real,
                                         title=f'Relação (Base) entre {coluna_x_disp} e {coluna_metrica_principal}{" por " + color_real if color_real else ""}')
                    else:
                         st.warning("Necessário outra coluna numérica para Gráfico de Dispersão.")

                if fig:
                    fig.update_layout(hovermode="x unified", title_x=0.5, margin=dict(t=50, b=50, l=50, r=50))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Gráfico não gerado. Verifique as configurações.")
                    
            except Exception as e:
                st.error(f"Erro ao gerar o Gráfico 2: {e}")
        else:
            st.warning("O DataFrame Base está vazio após a aplicação dos filtros.")

    # --- Tabela e Download ---
    st.markdown("---")
    st.subheader("🔍 Detalhes dos Dados Filtrados (Base)")
    
    df_exibicao = df_base.copy()
    for col in colunas_numericas_salvas: 
        if col in df_exibicao.columns:
            if any(word in col for word in ['valor', 'salario', 'custo', 'receita']):
                df_exibicao[col] = df_exibicao[col].apply(formatar_moeda)
                
    max_linhas_exibidas = 1000
    if len(df_exibicao) > max_linhas_exibidas:
        df_exibicao_limitado = df_exibicao.head(max_linhas_exibidas)
        st.info(f"Exibindo apenas as primeiras {max_linhas_exibidas} linhas. Baixe o CSV/XLSX para ver todos os {len(df_exibicao)} registros.")
    else:
        df_exibicao_limitado = df_exibicao

    st.dataframe(df_exibicao_limitado, use_container_width=True, hide_index=True)

    csv_data = df_base.to_csv(index=False, sep=';', decimal=',', encoding='utf-8')
    xlsx_output = BytesIO()
    xlsx_data = None
    try:
        # Tenta importar openpyxl
        import openpyxl 
        with pd.ExcelWriter(xlsx_output, engine='openpyxl') as writer:
            df_base.to_excel(writer, index=False)
        xlsx_data = xlsx_output.getvalue()
    except ImportError:
        st.warning("A biblioteca 'openpyxl' não está instalada. O download em XLSX está desabilitado.")
    except Exception as e:
         st.error(f"Erro ao criar o arquivo XLSX: {e}")

        
    col_csv, col_xlsx, _ = st.columns([1, 1, 2])
    with col_csv:
        st.download_button(
            label="📥 Baixar Dados Base (CSV)",
            data=csv_data,
            file_name=f'dados_base_exportados_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
            mime='text/csv',
            use_container_width=True
        )
    if xlsx_data:
        with col_xlsx:
            st.download_button(
                label="📥 Baixar Dados Base (XLSX)",
                data=xlsx_data,
                file_name=f'dados_base_exportados_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
            )
