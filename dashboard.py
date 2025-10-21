import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime
from io import BytesIO
import pickle
import csv # Necessário para usar o quoting

# IMPORTAÇÃO DO UTILS.PY CORRIGIDO
from utils import formatar_moeda, inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes

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
    data_entry = st.session_state.data_sets_catalog[last_name]
    initial_df = data_entry.get('df', pd.DataFrame())
    initial_filters = data_entry.get('colunas_filtros_salvas', [])
    initial_values = data_entry.get('colunas_valor_salvas', [])
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

# --- Funções de Lógica (Inalteradas) ---
def limpar_filtros_salvos():
    if 'df_filtrado_base' in st.session_state: del st.session_state['df_filtrado_base'] 
    if 'df_filtrado_comp' in st.session_state: del st.session_state['df_filtrado_comp'] 
    
    st.session_state.active_filters_base = {}
    st.session_state.active_filters_comp = {}
        
    st.session_state['filtro_reset_trigger'] += 1
    
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
    st.session_state[f'filtro_key_{suffix}_{key}'] = options_list
    pass

def set_multiselect_none(key, suffix):
    st.session_state[f'filtro_key_{suffix}_{key}'] = []
    pass

def initialize_widget_state(key, options, initial_default_calc):
    if key not in st.session_state:
        st.session_state[key] = initial_default_calc

def processar_dados_atuais(df_novo, colunas_filtros, colunas_valor, dataset_name):
    if st.session_state.uploaded_files_data:
        file_names = list(st.session_state.uploaded_files_data.keys())
        base_name = dataset_name if len(file_names) > 1 or not file_names else os.path.splitext(file_names[0])[0]
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
    st.session_state.show_reconfig_section = True
    
def remove_uploaded_file(file_name):
    if file_name in st.session_state.uploaded_files_data:
        del st.session_state.uploaded_files_data[file_name]
        
        st.session_state.dados_atuais = pd.DataFrame()
        st.session_state.current_dataset_name = ""
        st.session_state.show_reconfig_section = False
        st.rerun() 

@st.cache_data(show_spinner="Aplicando filtros de Base e Comparação...")
def aplicar_filtros_comparacao(df_base, col_filtros, filtros_ativos_base, filtros_ativos_comp, col_data, data_range_base, data_range_comp, trigger):
    
    def _aplicar_filtro_single(df, col_filtros_list, filtros_ativos_dict, col_data, data_range):
        df_filtrado_temp = df.copy()
        
        # 1. Filtros Categóricos
        for col in col_filtros_list:
            selecao = filtros_ativos_dict.get(col)
            if selecao and col in df_filtrado_temp.columns and selecao != []: 
                df_filtrado_temp = df_filtrado_temp[df_filtrado_temp[col].astype(str).isin(selecao)]
        
        # 2. Filtro de Data
        if data_range and len(data_range) == 2 and col_data and col_data[0] in df_filtrado_temp.columns:
            col_data_padrao = col_data[0]
            df_filtrado_temp[col_data_padrao] = pd.to_datetime(df_filtrado_temp[col_data_padrao], errors='coerce')
            
            df_filtrado_temp = df_filtrado_temp[
                (df_filtrado_temp[col_data_padrao] >= pd.to_datetime(data_range[0])) &
                (df_filtrado_temp[col_data_padrao] <= pd.to_datetime(data_range[1]))
            ]
        return df_filtrado_temp
    
    df_base_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_base, col_data, data_range_base)
    df_comp_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_comp, col_data, data_range_comp)
    
    return df_base_filtrado, df_comp_filtrado

def gerar_rotulo_filtro(filtros_ativos, col_data, data_range, all_options_count):
    rotulo_filtros = []
    
    for col in filtros_ativos.keys():
        valores = filtros_ativos[col]
        
        if col == 'data_range': continue 
        
        total_opcoes = all_options_count.get(col, 0)
        
        if valores and len(valores) > 0 and len(valores) < total_opcoes: 
            
            if len(valores) == 1:
                rotulo_filtros.append(f"**{col.title().replace('_', ' ')}:** '{valores[0]}'")
            else:
                rotulo_filtros.append(f"**{col.title().replace('_', ' ')}:** {len(valores)} itens")
            
    if data_range and len(data_range) == 2 and col_data:
        data_min = data_range[0].strftime('%Y-%m-%d')
        data_max = data_range[1].strftime('%Y-%m-%d')
        rotulo_filtros.append(f"**Data:** {data_min} a {data_max}")
    
    if not rotulo_filtros:
        return "Nenhum Filtro Ativo (Total Geral)"
    
    resumo = " | ".join(rotulo_filtros[:4])
    if len(rotulo_filtros) > 4:
        resumo += " (...)"
        
    return resumo


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
            if key in st.session_state: 
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
                st.button("Remover", 
                          key=f"remove_file_btn_{file_name}", 
                          on_click=remove_uploaded_file, 
                          args=(file_name,), 
                          use_container_width=True)
        
        st.markdown("---")
        
        # --- Lógica de Configuração de Colunas (COM CORREÇÃO PARA LEITURA BR) ---
        if st.session_state.show_reconfig_section:
            
            df_novo = pd.DataFrame()
            all_dataframes = []
            
            for file_name, file_bytes in st.session_state.uploaded_files_data.items():
                
                df_temp = None 
                
                try:
                    uploaded_file_stream = BytesIO(file_bytes)
                    
                    if file_name.endswith('.csv'):
                        
                        # TENTATIVA 1: Formato BR (sep=';', decimal=',', thousands='.') + Codificação UTF-8
                        try:
                            uploaded_file_stream.seek(0)
                            df_temp = pd.read_csv(
                                uploaded_file_stream, 
                                sep=';', 
                                decimal=',', 
                                thousands='.', 
                                encoding='utf-8', 
                                skipinitialspace=True
                            )
                        except Exception as e1:
                            # TENTATIVA 2: Formato BR (sep=';', decimal=',', thousands='.') + Codificação Latin-1
                            try:
                                uploaded_file_stream.seek(0)
                                df_temp = pd.read_csv(
                                    uploaded_file_stream, 
                                    sep=';', 
                                    decimal=',', 
                                    thousands='.', 
                                    encoding='latin-1', 
                                    skipinitialspace=True
                                )
                            except Exception as e2:
                                # TENTATIVA 3: Formato US (sep=',', decimal='.') + Codificação UTF-8
                                try:
                                    uploaded_file_stream.seek(0)
                                    df_temp = pd.read_csv(
                                        uploaded_file_stream, 
                                        sep=',', 
                                        decimal='.', 
                                        encoding='utf-8',
                                        skipinitialspace=True
                                    )
                                except Exception as e3:
                                    
                                    # NOVA TENTATIVA 4 (Melhoria): BR, Python Engine, Quoting (força leitura como string/object)
                                    try:
                                        uploaded_file_stream.seek(0)
                                        df_temp = pd.read_csv(
                                            uploaded_file_stream, 
                                            sep=';', 
                                            encoding='utf-8', 
                                            skipinitialspace=True,
                                            engine='python', 
                                            quoting=csv.QUOTE_MINIMAL,
                                            # **IMPORTANTE**: Removendo 'decimal' e 'thousands' para que o util.py faça a limpeza
                                        )
                                    except Exception as e4:
                                        
                                        # NOVA TENTATIVA 5 (Melhoria): BR, Python Engine, Quoting, Latin-1 (força leitura como string/object)
                                        try:
                                            uploaded_file_stream.seek(0)
                                            df_temp = pd.read_csv(
                                                uploaded_file_stream, 
                                                sep=';', 
                                                encoding='latin-1', 
                                                skipinitialspace=True,
                                                engine='python', 
                                                quoting=csv.QUOTE_MINIMAL,
                                                # **IMPORTANTE**: Removendo 'decimal' e 'thousands' para que o util.py faça a limpeza
                                            )
                                        except Exception as e5:
                                            # Falha total
                                            st.error(f"""
                                                Falha total ao ler o arquivo {file_name}. Detalhes da última falha: {e5}.
                                                Seus dados estão sendo ignorados. Por favor, verifique o delimitador.
                                            """)
                                            df_temp = None
                                        
                    elif file_name.endswith('.xlsx'):
                        df_temp = pd.read_excel(uploaded_file_stream)
                        
                    if df_temp is not None and not df_temp.empty: 
                        all_dataframes.append(df_temp)
                        
                except Exception as e:
                    st.error(f"Erro inesperado ao processar o stream do arquivo {file_name}: {e}. O arquivo será ignorado.")
                    pass 

            if all_dataframes:
                df_novo = pd.concat(all_dataframes, ignore_index=True)
            
            if df_novo.empty:
                st.error("O conjunto de dados consolidado está vazio. Nenhum arquivo pôde ser lido com sucesso.")
                st.session_state.dados_atuais = pd.DataFrame() 
            else:
                # Normaliza colunas antes da inferência
                df_novo.columns = df_novo.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('ã', 'a').str.replace('ç', 'c')
                colunas_disponiveis = df_novo.columns.tolist()
                st.info(f"Dados consolidados de {len(all_dataframes)} arquivo(s) lido(s) com sucesso. Total de {len(df_novo)} linhas.")
                
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
                
                # O DataFrame precisa ser processado aqui para ter os tipos corretos para a seleção de filtros
                # ESTA CHAMADA USA O UTILS.PY CORRIGIDO E FAZ A LIMPEZA NUMÉRICA
                df_processado = inferir_e_converter_tipos(df_novo, colunas_texto, colunas_moeda)
                
                # Colunas de filtro são as categóricas (object ou category)
                colunas_para_filtro_options = df_processado.select_dtypes(include=['object', 'category']).columns.tolist()
                # Sugestão de filtros comuns
                filtro_default = [c for c in colunas_para_filtro_options if c in ['tipo', 'situacao', 'empresa', 'departamento', 'centro_de_custo', 'funcao']]
                if 'filtros_select' not in st.session_state:
                    initialize_widget_state('filtros_select', colunas_para_filtro_options, filtro_default)
                
                st.markdown("##### ⚙️ Colunas para FILTROS")
                col_filtro_sel_btn, col_filtro_clr_btn = st.columns(2)
                with col_filtro_sel_btn: 
                    st.button("✅ Selecionar Tudo", on_click=lambda ops=colunas_para_filtro_options: set_multiselect_all('filtros_select', 'config', ops), key='filtros_select_all_btn', use_container_width=True)
                with col_filtro_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('filtros_select', 'config'), key='filtros_select_clear_btn', use_container_width=True)
                colunas_para_filtro = st.multiselect("Selecione:", options=colunas_para_filtro_options, default=st.session_state.filtros_select, key='filtros_select', label_visibility="collapsed")
                
                # Colunas de valor para o dashboard (após inferência)
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
             st.info("Sistema pronto. Carregue um ou mais arquivos CSV/XLSX para iniciar o processamento e salvamento do dataset.")


# --- Dashboard Principal (Inalterado) ---

st.markdown("---") 

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
                                                 help="Selecione a coluna numérica principal para o cálculo de KPIs (Total e Média) e para o Eixo Y dos gráficos.")
    with col_reset_btn:
        st.markdown("###### ") 
        if st.button("🗑️ Resetar Filtros", help="Redefine todas as seleções de filtro para o estado inicial."):
            limpar_filtros_salvos()
            st.rerun() 
    
    st.markdown("---") 
    
    st.markdown("#### 🔍 Configuração de Análise de Variação")
    
    tab_base, tab_comparacao = st.tabs(["Filtros da BASE (Referência)", "Filtros de COMPARAÇÃO (Alvo)"])
    
    all_options_count = {col: len(df_analise_base[col].astype(str).fillna('N/A').unique().tolist()) 
                         for col in colunas_categoricas_filtro if col in df_analise_base.columns}

    def render_filter_panel(tab_container, suffix, colunas_filtro_a_exibir, df_analise_base):
        with tab_container:
            st.markdown(f"**Defina os filtros para o conjunto {suffix.upper()}**")
            
            cols_container = st.columns(3) 
            filtros_col_1 = colunas_filtro_a_exibir[::3]
            filtros_col_2 = colunas_filtro_a_exibir[1::3]
            filtros_col_3 = colunas_filtro_a_exibir[2::3]

            active_filters_dict = {}

            for idx, filtros_col in enumerate([filtros_col_1, filtros_col_2, filtros_col_3]):
                with cols_container[idx]:
                    for col in filtros_col:
                        if col not in df_analise_base.columns: continue
                        
                        opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('N/A').unique().tolist())
                        filtro_key = f'filtro_key_{suffix}_{col}'
                        
                        if filtro_key not in st.session_state:
                             st.session_state[filtro_key] = []
                             
                        current_selection = st.session_state.get(filtro_key, [])
                        is_filtered = len(current_selection) > 0 and len(current_selection) < len(opcoes_unicas)
                        
                        with st.expander(f"**{col.title().replace('_', ' ')}** ({len(opcoes_unicas)} opções) {'- ATIVO' if is_filtered else ''}", expanded=is_filtered):
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
                                                          default=current_selection, 
                                                          key=filtro_key, 
                                                          label_visibility="collapsed")
                            
                            if selecao_form and len(selecao_form) < len(opcoes_unicas):
                                active_filters_dict[col] = selecao_form

            return active_filters_dict

    st.session_state.active_filters_base = render_filter_panel(tab_base, 'base', colunas_categoricas_filtro, df_analise_base)
    st.session_state.active_filters_comp = render_filter_panel(tab_comparacao, 'comp', colunas_categoricas_filtro, df_analise_base)

    data_range_base = None
    data_range_comp = None
    if colunas_data:
        col_data_padrao = colunas_data[0]
        df_col_data = df_analise_base[col_data_padrao]

        data_min_global = df_col_data.min()
        data_max_global = df_col_data.max()
        
        if pd.notna(data_min_global) and pd.notna(data_max_global):
            
            with tab_base:
                st.markdown("---")
                st.subheader(f"📅 Filtro de Data da Base ({col_data_padrao.title().replace('_', ' ')})")
                date_key_base = f'date_range_key_base_{col_data_padrao}'
                
                if date_key_base not in st.session_state:
                    st.session_state[date_key_base] = (data_min_global.to_pydatetime().date(), data_max_global.to_pydatetime().date())
                
                date_range_selection_base = st.slider(
                    'Selecione o Intervalo:',
                    min_value=data_min_global.to_pydatetime().date(),
                    max_value=data_max_global.to_pydatetime().date(),
                    value=st.session_state[date_key_base],
                    key=date_key_base,
                    format="YYYY-MM-DD"
                )
                data_range_base = (datetime.combine(date_range_selection_base[0], datetime.min.time()),
                                   datetime.combine(date_range_selection_base[1], datetime.max.time()))
                
            with tab_comparacao:
                st.markdown("---")
                st.subheader(f"📅 Filtro de Data de Comparação ({col_data_padrao.title().replace('_', ' ')})")
                date_key_comp = f'date_range_key_comp_{col_data_padrao}'
                
                if date_key_comp not in st.session_state:
                    st.session_state[date_key_comp] = (data_min_global.to_pydatetime().date(), data_max_global.to_pydatetime().date())

                date_range_selection_comp = st.slider(
                    'Selecione o Intervalo:',
                    min_value=data_min_global.to_pydatetime().date(),
                    max_value=data_max_global.to_pydatetime().date(),
                    value=st.session_state[date_key_comp],
                    key=date_key_comp,
                    format="YYYY-MM-DD"
                )
                data_range_comp = (datetime.combine(date_range_selection_comp[0], datetime.min.time()),
                                   datetime.combine(date_range_selection_comp[1], datetime.max.time()))


    # --- EXECUÇÃO DO FILTRO COM CACHE ---
    st.session_state.df_filtrado_base, st.session_state.df_filtrado_comp = aplicar_filtros_comparacao(
        df_analise_base,
        colunas_categoricas_filtro,
        st.session_state.active_filters_base,
        st.session_state.active_filters_comp,
        colunas_data,
        data_range_base,
        data_range_comp,
        st.session_state.filtro_reset_trigger 
    )

    df_base = st.session_state.df_filtrado_base
    df_comp = st.session_state.df_filtrado_comp

    st.markdown("---") 
    st.subheader("💡 Resumo dos Filtros Aplicados")

    filtros_base_para_rotulo = st.session_state.active_filters_base.copy()
    filtros_comp_para_rotulo = st.session_state.active_filters_comp.copy()
    
    col_rotulo_base, col_rotulo_comp = st.columns(2)
    with col_rotulo_base:
        rotulo_base = gerar_rotulo_filtro(filtros_base_para_rotulo, colunas_data, data_range_base, all_options_count)
        st.markdown(f"**BASE (Referência):** {rotulo_base}")
    with col_rotulo_comp:
        rotulo_comp = gerar_rotulo_filtro(filtros_comp_para_rotulo, colunas_data, data_range_comp, all_options_count)
        st.markdown(f"**COMPARAÇÃO (Alvo):** {rotulo_comp}")

    st.markdown("---") 
    
    def calcular_kpi(df, coluna_metrica):
        if coluna_metrica == 'Contagem de Registros':
            valor = len(df)
            formatado = f"{valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return valor, formatado
        elif coluna_metrica in df.columns:
            valor = df[coluna_metrica].sum()
            formatado = formatar_moeda(valor)
            return valor, formatado
        return 0, "R$ 0,00"

    base_valor, base_formatado = calcular_kpi(df_base, coluna_metrica_principal)
    comp_valor, comp_formatado = calcular_kpi(df_comp, coluna_metrica_principal)

    variacao = comp_valor - base_valor
    if base_valor != 0 and base_valor is not None:
        percentual = (variacao / base_valor) * 100
        delta_text = f"{percentual:,.2f}%"
    else:
        delta_text = "N/A"

    col_kpi_base, col_kpi_comp, col_kpi_delta = st.columns(3)

    with col_kpi_base:
        st.metric(
            label=f"Total Base - {coluna_metrica_principal.title().replace('_', ' ')}",
            value=base_formatado,
            help=f"Total para o período/filtros de Base."
        )

    with col_kpi_comp:
        st.metric(
            label=f"Total Comparação - {coluna_metrica_principal.title().replace('_', ' ')}",
            value=comp_formatado,
            help=f"Total para o período/filtros de Comparação."
        )

    with col_kpi_delta:
        if coluna_metrica_principal == 'Contagem de Registros':
            delta_value = variacao
        else:
            delta_value = delta_text

        st.metric(
            label="Variação (COMP. vs BASE)",
            value=formatar_moeda(variacao) if coluna_metrica_principal != 'Contagem de Registros' else f"{variacao:,.0f}",
            delta=delta_value,
            delta_color="normal",
            help="Variação em valor e percentual (se aplicável) entre Comparação e Base."
        )

    st.markdown("---")
    
    st.subheader("📈 Análise Gráfica")
    
    col_group, col_chart_type, col_chart_dim = st.columns(3)
    
    with col_group:
        coluna_agrupamento = st.selectbox(
            "Agrupar por:",
            options=colunas_categoricas_filtro,
            key='grafico_key_agrupamento'
        )
    
    with col_chart_type:
        tipo_grafico = st.selectbox(
            "Tipo de Gráfico:",
            options=['Barras (Comparação)', 'Pizza', 'Tabela Detalhada'],
            key='grafico_key_tipo'
        )

    if tipo_grafico == 'Barras (Comparação)':
        
        if coluna_metrica_principal == 'Contagem de Registros':
            df_base_grouped = df_base.groupby(coluna_agrupamento).size().reset_index(name='Contagem de Registros')
            df_comp_grouped = df_comp.groupby(coluna_agrupamento).size().reset_index(name='Contagem de Registros')
        else:
            df_base_grouped = df_base.groupby(coluna_agrupamento)[coluna_metrica_principal].sum().reset_index(name=coluna_metrica_principal)
            df_comp_grouped = df_comp.groupby(coluna_agrupamento)[coluna_metrica_principal].sum().reset_index(name=coluna_metrica_principal)

        df_merged = pd.merge(df_base_grouped, df_comp_grouped, on=coluna_agrupamento, suffixes=('_Base', '_Comp'), how='outer').fillna(0)
        
        df_melted = df_merged.melt(
            id_vars=coluna_agrupamento,
            value_vars=[col for col in df_merged.columns if col != coluna_agrupamento],
            var_name='Conjunto',
            value_name=coluna_metrica_principal
        )
        
        df_melted['Conjunto'] = df_melted['Conjunto'].replace({
            f'{coluna_metrica_principal}_Base': 'Base (Referência)',
            f'{coluna_metrica_principal}_Comp': 'Comparação (Alvo)'
        })
        
        title = f"Total de {coluna_metrica_principal.title().replace('_', ' ')} por {coluna_agrupamento.title().replace('_', ' ')}"
        fig = px.bar(
            df_melted,
            x=coluna_agrupamento,
            y=coluna_metrica_principal,
            color='Conjunto',
            barmode='group',
            title=title,
            hover_data={coluna_metrica_principal: True, coluna_agrupamento: True}
        )
        
        if coluna_metrica_principal != 'Contagem de Registros':
             fig.update_layout(yaxis_tickprefix='R$ ')

        st.plotly_chart(fig, use_container_width=True)

    elif tipo_grafico == 'Pizza':
        
        if coluna_metrica_principal == 'Contagem de Registros':
            df_grouped = df_comp.groupby(coluna_agrupamento).size().reset_index(name='Contagem de Registros')
        else:
            df_grouped = df_comp.groupby(coluna_agrupamento)[coluna_metrica_principal].sum().reset_index(name=coluna_metrica_principal)
        
        df_grouped = df_grouped.sort_values(by=coluna_metrica_principal, ascending=False).head(10)

        title = f"Distribuição (Comparação) de {coluna_metrica_principal.title().replace('_', ' ')} por {coluna_agrupamento.title().replace('_', ' ')} (Top 10)"
        
        fig = px.pie(
            df_grouped,
            names=coluna_agrupamento,
            values=coluna_metrica_principal,
            title=title,
            hole=.3,
            hover_data={coluna_metrica_principal: True}
        )
        
        st.plotly_chart(fig, use_container_width=True)

    elif tipo_grafico == 'Tabela Detalhada':
        st.markdown("#### 📄 Tabela de Dados (Conjunto de Comparação)")

        colunas_tabela = [coluna_agrupamento] + colunas_numericas_salvas
        colunas_tabela = list(set(colunas_tabela) & set(df_comp.columns))

        df_tabela = df_comp[colunas_tabela]

        df_resumo = df_tabela.groupby(coluna_agrupamento).sum().reset_index()

        for col in colunas_numericas_salvas:
            if col in df_resumo.columns:
                df_resumo[col] = df_resumo[col].apply(formatar_moeda)

        st.dataframe(df_resumo, use_container_width=True)

    st.markdown("---")
    st.caption(f"Dados do Dataset: {st.session_state.current_dataset_name}")
