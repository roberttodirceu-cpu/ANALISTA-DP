import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime
from io import BytesIO
import pickle 

# Importa as funções do utils.py
try:
    # Assumindo que a função formatar_moeda, inferir_e_converter_tipos, etc, estão no utils.py
    # OBS: Se você não tiver o arquivo 'utils.py', substitua estas linhas pelas funções reais.
    # Caso o 'utils.py' esteja faltando, o Streamlit irá parar aqui.
    from utils import formatar_moeda, inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes
except ImportError:
    st.error("Erro: O arquivo 'utils.py' não foi encontrado. Certifique-se de que ele está no mesmo diretório.")
    st.stop()

# --- Configuração da Página e Persistência ---
st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")
PERSISTENCE_PATH = 'data/data_sets_catalog.pkl'

def load_catalog():
    """Tenta carregar o catálogo de datasets do arquivo de persistência."""
    if os.path.exists(PERSISTENCE_PATH):
        try:
            with open(PERSISTENCE_PATH, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            # st.sidebar.error(f"Erro ao carregar dados salvos: {e}. Inicializando vazio.")
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
    # Pega o último dataset carregado/salvo
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

# --- Funções de Lógica ---

def limpar_filtros_salvos():
    """Limpa o estado de todos os filtros e do DataFrame filtrado."""
    if 'df_filtrado_base' in st.session_state: del st.session_state['df_filtrado_base'] 
    if 'df_filtrado_comp' in st.session_state: del st.session_state['df_filtrado_comp'] 
    
    # Limpa filtros ativos no estado da sessão
    st.session_state.active_filters_base = {}
    st.session_state.active_filters_comp = {}
        
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
    pass

def set_multiselect_none(key, suffix):
    """Callback para o botão 'Limpar'."""
    st.session_state[f'filtro_key_{suffix}_{key}'] = []
    pass

def initialize_widget_state(key, options, initial_default_calc):
    """Inicializa o estado dos multiselects de coluna no sidebar (para configuração)."""
    if key not in st.session_state:
        st.session_state[key] = initial_default_calc

def processar_dados_atuais(df_novo, colunas_filtros, colunas_valor, dataset_name):
    """Salva o dataset processado no catálogo, define como ativo e SALVA EM DISCO."""
    
    # Define o nome do dataset baseado nos arquivos ou no input
    if st.session_state.uploaded_files_data:
        file_names = list(st.session_state.uploaded_files_data.keys())
        # Mantém o nome do input se houver múltiplos arquivos, senão usa o nome do arquivo único
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
def aplicar_filtros_comparacao(df_base, col_filtros, filtros_ativos_base, filtros_ativos_comp, col_data, data_range_base, data_range_comp, trigger):
    
    def _aplicar_filtro_single(df, col_filtros_list, filtros_ativos_dict, col_data, data_range):
        df_filtrado_temp = df.copy()
        
        # 1. Filtros Categóricos
        for col in col_filtros_list:
            selecao = filtros_ativos_dict.get(col)
            # Verifica se o filtro está ativo (não está vazio E não é 'Selecionar Tudo')
            if selecao and col in df_filtrado_temp.columns and selecao != []: 
                # Converte para string para lidar com 'N/A' e outros tipos de forma consistente
                df_filtrado_temp = df_filtrado_temp[df_filtrado_temp[col].astype(str).isin(selecao)]
        
        # 2. Filtro de Data
        if data_range and len(data_range) == 2 and col_data and col_data[0] in df_filtrado_temp.columns:
            col_data_padrao = col_data[0]
            # Garante que a coluna de data é datetime
            df_filtrado_temp[col_data_padrao] = pd.to_datetime(df_filtrado_temp[col_data_padrao], errors='coerce')
            
            df_filtrado_temp = df_filtrado_temp[
                (df_filtrado_temp[col_data_padrao] >= pd.to_datetime(data_range[0])) &
                (df_filtrado_temp[col_data_padrao] <= pd.to_datetime(data_range[1]))
            ]
        return df_filtrado_temp
    
    # Aplica filtros para Base e Comparação
    df_base_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_base, col_data, data_range_base)
    df_comp_filtrado = _aplicar_filtro_single(df_base, col_filtros, filtros_ativos_comp, col_data, data_range_comp)
    
    return df_base_filtrado, df_comp_filtrado


# --- Geração de Rótulos de Filtro (SIMPLIFICADO e DIDÁTICO) ---

def gerar_rotulo_filtro(filtros_ativos, col_data, data_range, all_options_count):
    """
    Gera uma string CONCISA para o cabeçalho do KPI, focando nas dimensões mais relevantes.
    """
    rotulo_filtros = []
    
    # 1. Processa Filtros Categóricos
    for col in filtros_ativos.keys():
        valores = filtros_ativos[col]
        
        # O filtro de data é tratado separadamente
        if col == 'data_range': continue 
        
        # Calcula quantas opções foram selecionadas em relação ao total
        total_opcoes = all_options_count.get(col, 0)
        
        # Ignora se o filtro é 'Selecionar Tudo' (lista vazia no estado 'ativos' ou se a contagem for igual ao total)
        if valores and len(valores) > 0 and len(valores) < total_opcoes: 
            
            if len(valores) == 1:
                # Caso de 1 item: exibe o item
                # Adiciona aspas se for string para melhor visualização
                rotulo_filtros.append(f"**{col.title().replace('_', ' ')}:** '{valores[0]}'")
            else:
                # Caso de múltiplos itens: exibe a contagem
                rotulo_filtros.append(f"**{col.title().replace('_', ' ')}:** {len(valores)} itens")
            
    # 2. Processa Filtro de Data (se houver)
    if data_range and len(data_range) == 2 and col_data:
        data_min = data_range[0].strftime('%Y-%m-%d')
        data_max = data_range[1].strftime('%Y-%m-%d')
        rotulo_filtros.append(f"**Data:** {data_min} a {data_max}")
    
    if not rotulo_filtros:
        return "Nenhum Filtro Ativo (Total Geral)"
    
    # Retorna o resumo, limitado a 3 ou 4 filtros para manter a concisão
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
            if key in st.session_state: # Verifica se a chave existe antes de deletar
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
        
        # --- Lógica de Configuração de Colunas (COM CORREÇÃO PARA O ERRO 'df_temp is not defined') ---
        if st.session_state.show_reconfig_section:
            
            df_novo = pd.DataFrame()
            all_dataframes = []
            
            for file_name, file_bytes in st.session_state.uploaded_files_data.items():
                
                # CORREÇÃO: Inicializa df_temp como None em cada iteração
                df_temp = None 
                
                try:
                    uploaded_file_stream = BytesIO(file_bytes)
                    
                    if file_name.endswith('.csv'):
                        # Primeira tentativa de leitura (separador ';')
                        try:
                            uploaded_file_stream.seek(0)
                            df_temp = pd.read_csv(uploaded_file_stream, sep=';', decimal=',', encoding='utf-8')
                        except Exception:
                            # Segunda tentativa (separador ',')
                            uploaded_file_stream.seek(0)
                            df_temp = pd.read_csv(uploaded_file_stream, sep=',', decimal='.', encoding='utf-8')
                            
                    elif file_name.endswith('.xlsx'):
                        df_temp = pd.read_excel(uploaded_file_stream)
                    
                    # CORREÇÃO: Apenas adiciona se df_temp foi definido (não é None) e não está vazio
                    if df_temp is not None and not df_temp.empty: 
                        all_dataframes.append(df_temp)
                        
                except Exception as e:
                    # Captura erros gerais de leitura e informa ao usuário
                    st.error(f"Erro ao ler o arquivo {file_name}: {e}. O arquivo será ignorado.")
                    pass 

            if all_dataframes:
                # Concatena todos os DataFrames que foram lidos com sucesso
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
                # (Assumindo que inferir_e_converter_tipos é robusta)
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
                            # Verifica e avisa sobre dados ausentes
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
    
    # Dicionário para armazenar a contagem total de opções por coluna (necessário para o rótulo conciso)
    all_options_count = {col: len(df_analise_base[col].astype(str).fillna('N/A').unique().tolist()) 
                         for col in colunas_categoricas_filtro if col in df_analise_base.columns}

    def render_filter_panel(tab_container, suffix, colunas_filtro_a_exibir, df_analise_base):
        with tab_container:
            st.markdown(f"**Defina os filtros para o conjunto {suffix.upper()}**")
            
            # Divide os filtros em 3 colunas para o layout expandido
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
                        
                        # Inicializa o estado do filtro como lista vazia (selecionar tudo por padrão)
                        if filtro_key not in st.session_state:
                             st.session_state[filtro_key] = []
                             
                        # Determina se o filtro está ativo (selecionou menos que o total)
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
                            
                            # O widget multiselect atualiza o estado da sessão automaticamente
                            selecao_form = st.multiselect("Selecione:", 
                                                          options=opcoes_unicas, 
                                                          default=current_selection, 
                                                          key=filtro_key, 
                                                          label_visibility="collapsed")
                            
                            # Se a seleção for ativa (não vazia e não tudo), armazena para uso no cache
                            if selecao_form and len(selecao_form) < len(opcoes_unicas):
                                active_filters_dict[col] = selecao_form

            return active_filters_dict

    # Renderiza os dois painéis de filtro
    st.session_state.active_filters_base = render_filter_panel(tab_base, 'base', colunas_categoricas_filtro, df_analise_base)
    st.session_state.active_filters_comp = render_filter_panel(tab_comparacao, 'comp', colunas_categoricas_filtro, df_analise_base)


    # --- Filtro de Data ---
    data_range_base = None
    data_range_comp = None
    if colunas_data:
        col_data_padrao = colunas_data[0]
        df_col_data = df_analise_base[col_data_padrao].dropna()
        
        if not df_col_data.empty:
            try:
                # Garante que as datas estão no formato correto para o slider
                data_series = pd.to_datetime(df_col_data, errors='coerce').dropna()
                data_min = data_series.min()
                data_max = data_series.max()
                
                if pd.notna(data_min) and pd.notna(data_max):
                    st.markdown(f"#### 🗓️ Intervalo de Data ({col_data_padrao.title().replace('_', ' ')})")
                    col_date_base, col_date_comp = st.columns(2)
                    
                    data_min_dt = data_min.to_pydatetime()
                    data_max_dt = data_max.to_pydatetime()
                    
                    # Lógica de data
                    data_range_base_key = f'date_range_key_base_{col_data_padrao}'
                    data_range_comp_key = f'date_range_key_comp_{col_data_padrao}'
                    
                    with col_date_base:
                        default_date_range_base = st.session_state.get(data_range_base_key, (data_min_dt, data_max_dt))
                        data_range_base = st.slider("Data BASE", 
                                                  min_value=data_min_dt, 
                                                  max_value=data_max_dt, 
                                                  value=default_date_range_base, 
                                                  format="YYYY/MM/DD", 
                                                  key=data_range_base_key)
                        # Salva o range no active_filters_base/comp SE ele for diferente do total
                        if data_range_base != (data_min_dt, data_max_dt):
                             st.session_state.active_filters_base['data_range'] = data_range_base
                        
                    with col_date_comp:
                        default_date_range_comp = st.session_state.get(data_range_comp_key, (data_min_dt, data_max_dt))
                        data_range_comp = st.slider("Data COMPARAÇÃO", 
                                                  min_value=data_min_dt, 
                                                  max_value=data_max_dt, 
                                                  value=default_date_range_comp, 
                                                  format="YYYY/MM/DD", 
                                                  key=data_range_comp_key)
                        if data_range_comp != (data_min_dt, data_max_dt):
                            st.session_state.active_filters_comp['data_range'] = data_range_comp
                            
            except Exception:
                st.warning("Erro na exibição dos filtros de data. Verifique se a coluna de data não possui valores incoerentes.")


    st.markdown("---")
    submitted = st.button("✅ Aplicar Filtros e Rodar Comparação", use_container_width=True)
    if submitted:
        # Força o rerun para garantir que o cache seja chamado com os novos filtros
        st.session_state['filtro_reset_trigger'] += 1 
        st.rerun() 

    # --- Coletar Filtros Ativos (Para a Função de Cache) ---
    # Coleta filtros categóricos que não são vazios
    filtros_ativos_base_cache = {
        col: st.session_state.get(f'filtro_key_base_{col}') 
        for col in colunas_categoricas_filtro 
        if st.session_state.get(f'filtro_key_base_{col}') is not None and st.session_state.get(f'filtro_key_base_{col}') != []
    }
    
    filtros_ativos_comp_cache = {
        col: st.session_state.get(f'filtro_key_comp_{col}') 
        for col in colunas_categoricas_filtro 
        if st.session_state.get(f'filtro_key_comp_{col}') is not None and st.session_state.get(f'filtro_key_comp_{col}') != []
    }
    
    # Adiciona o range de data (se estiver ativo)
    if 'data_range' in st.session_state.active_filters_base:
        data_range_base_cache = st.session_state.active_filters_base['data_range']
    else:
        data_range_base_cache = None
        
    if 'data_range' in st.session_state.active_filters_comp:
        data_range_comp_cache = st.session_state.active_filters_comp['data_range']
    else:
        data_range_comp_cache = None


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


    # --- Métricas Chave de Variação (KPIs Aprimorados COM RESUMO CLARO) ---
    st.subheader("🌟 Métricas Chave de Variação")
    
    # Geração dos rótulos de contexto SIMPLIFICADOS
    # Usa o state.active_filters, que é preenchido pelo render_filter_panel e pela lógica do data_range
    rotulo_base = gerar_rotulo_filtro(st.session_state.active_filters_base, colunas_data, data_range_base, all_options_count)
    rotulo_comp = gerar_rotulo_filtro(st.session_state.active_filters_comp, colunas_data, data_range_comp, all_options_count)

    # Exibe o RESUMO do Filtro com destaque (VISUAL MODERNO)
    st.markdown(f"""
        <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 15px;">
            <p style="margin: 0; font-weight: bold; color: #343a40;"><span style="color: #007bff;">BASE (Ref.):</span> {rotulo_base}</p>
            <p style="margin: 0; font-weight: bold; color: #dc3545;"><span style="color: #dc3545;">COMPARAÇÃO (Alvo):</span> {rotulo_comp}</p>
        </div>
    """, unsafe_allow_html=True)
    
    df_base = st.session_state.df_filtrado_base
    df_comp = st.session_state.df_filtrado_comp
    coluna_metrica_principal = st.session_state.get('metrica_principal_selectbox')
    
    # --- Funções de Cálculo ---
    def calculate_metrics(df, col_metrica):
        if df.empty: return 0, 0, 0
        count = len(df)
        if col_metrica == 'Contagem de Registros':
            total = count
            average = 1 if count > 0 else 0 
        elif col_metrica and col_metrica in df.columns:
            total = df[col_metrica].sum()
            average = df[col_metrica].mean() 
        else:
            return 0, 0, 0
        return total, average, count

    def format_value(value, is_currency):
        if value is None: return "0"
        if is_currency:
            # Reutiliza a função de utilidades para formatação de moeda
            return formatar_moeda(value) 
        else:
            return f"{value:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.') # Formato BR para int

    def calculate_delta(base, comp, is_currency):
        if base == 0 and comp == 0: return 0, "0.00%", "off"
        # Trata divisão por zero ou base zero
        if base == 0 and comp != 0: 
            return comp, "N/A (Base 0)", "normal" if comp > 0 else "inverse"
        
        delta_abs = comp - base
        delta_perc = (delta_abs / base) * 100
        delta_label = f"{delta_perc:+.2f}%"
        
        # Cor: POSITIVO = "normal" (verde), NEGATIVO = "inverse" (vermelho).
        delta_color = 'normal' if delta_abs >= 0 else 'inverse' 
        
        return delta_abs, delta_label, delta_color


    is_currency_metric = coluna_metrica_principal != 'Contagem de Registros'
    
    # 1. Cálculos para TOTAL
    total_base, media_calc_base, count_base = calculate_metrics(df_base, coluna_metrica_principal)
    total_comp, media_calc_comp, count_comp = calculate_metrics(df_comp, coluna_metrica_principal)
    
    delta_total_abs, delta_total_perc_label, delta_total_color = calculate_delta(total_base, total_comp, is_currency_metric)

    # 2. Cálculos para MÉDIA
    delta_media_abs, delta_media_perc_label, delta_media_color = calculate_delta(media_calc_base, media_calc_comp, is_currency_metric)

    # 3. Cálculos para CONTAGEM
    delta_count_abs, delta_count_perc_label, delta_count_color = calculate_delta(count_base, count_comp, is_currency=False)


    # --- Títulos das Colunas (Mais Compacto e Focado na Métrica) ---
    col_title_metric, col_title_base, col_title_comp, col_title_delta = st.columns([1.5, 1.5, 1.5, 1.5])
    col_title_metric.markdown("<h4 style='text-align: left; font-size: 1.1rem; color:#495057;'>Métrica</h4>", unsafe_allow_html=True)
    col_title_base.markdown("<h4 style='text-align: right; font-size: 1.1rem; color:#28a745;'>BASE (Ref.)</h4>", unsafe_allow_html=True)
    col_title_comp.markdown("<h4 style='text-align: right; font-size: 1.1rem; color:#dc3545;'>COMPARAÇÃO (Alvo)</h4>", unsafe_allow_html=True)
    col_title_delta.markdown("<h4 style='text-align: right; font-size: 1.1rem; color:#343a40;'>VARIAÇÃO (Δ)</h4>", unsafe_allow_html=True)
    
    st.markdown("---") 

    # Função auxiliar para exibir as métricas de forma limpa
    def display_kpi_row(label, base_val, comp_val, delta_abs, delta_perc_label, delta_color, is_currency):
        col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1.5])
        with col1:
            st.markdown(f"**{label}**")
        with col2:
            st.metric("", format_value(base_val, is_currency), help=f"Valor na BASE: {format_value(base_val, is_currency)}")
        with col3:
            st.metric("", format_value(comp_val, is_currency), help=f"Valor na COMPARAÇÃO: {format_value(comp_val, is_currency)}")
        with col4:
            # st.metric exibe o delta_abs no valor e o delta_perc no delta
            st.metric("", format_value(delta_abs, is_currency), delta_perc_label, delta_color, help=f"Variação: {delta_perc_label}")

    # --- Linha 1: TOTAL ---
    display_kpi_row(
        label=f"Total ({coluna_metrica_principal.replace('_', ' ').title()})",
        base_val=total_base,
        comp_val=total_comp,
        delta_abs=delta_total_abs,
        delta_perc_label=delta_total_perc_label,
        delta_color=delta_total_color,
        is_currency=is_currency_metric
    )

    st.markdown("---") 

    # --- Linha 2: MÉDIA (Apenas se for métrica numérica) ---
    if is_currency_metric:
        display_kpi_row(
            label=f"Média ({coluna_metrica_principal.replace('_', ' ').title()})",
            base_val=media_calc_base,
            comp_val=media_calc_comp,
            delta_abs=delta_media_abs,
            delta_perc_label=delta_media_perc_label,
            delta_color=delta_media_color,
            is_currency=is_currency_metric
        )
        st.markdown("---") 
    
    # --- Linha 3: CONTAGEM DE REGISTROS ---
    display_kpi_row(
        label="Nº de Registros (Contagem)",
        base_val=count_base,
        comp_val=count_comp,
        delta_abs=delta_count_abs,
        delta_perc_label=delta_count_perc_label,
        delta_color=delta_count_color,
        is_currency=False # Contagem nunca é moeda
    )

    st.markdown("---") 

    # --- Análise Visual (Gráficos) ---
    st.subheader("📈 Análise Visual (Gráficos) ")

    # Configuração Multi-Dimensional dos Gráficos (Eixo X e Quebra/Cor)
    col_config_x, col_config_color = st.columns(2)
    
    colunas_categoricas_para_grafico = ['Nenhuma (Total)'] + colunas_categoricas_filtro
    
    # Tenta usar a primeira coluna de filtro como padrão, senão usa 'Nenhuma (Total)'
    coluna_agrupamento_principal = colunas_categoricas_filtro[0] if colunas_categoricas_filtro else 'Nenhuma (Total)'
    default_x_index = colunas_categoricas_para_grafico.index(coluna_agrupamento_principal) if coluna_agrupamento_principal in colunas_categoricas_para_grafico else 0
    
    with col_config_x:
        coluna_x_fixa = st.selectbox(
            "Agrupar/Comparar por (Eixo X):", 
            options=colunas_categoricas_para_grafico, 
            index=default_x_index,
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
        st.markdown(f"##### Gráfico 1: Comparação BASE vs. COMPARAÇÃO por **{coluna_x_fixa.title().replace('_', ' ')}**")
        
        opcoes_grafico_1 = ['Barra Agrupada (Comparação Total)']
        if is_currency_metric:
             opcoes_grafico_1.append('Barra Agrupada (Comparação Média)')
             opcoes_grafico_1.append('Dispersão (Box Plot)')
             
        tipo_grafico_1 = st.selectbox("Tipo de Visualização (Gráfico 1):", options=opcoes_grafico_1, key='tipo_grafico_1')

        eixo_x_real = None if coluna_x_fixa == 'Nenhuma (Total)' else coluna_x_fixa
        color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
        
        df_plot_base = df_base
        df_plot_comp = df_comp
        
        y_col_agg_title = coluna_metrica_principal.replace('_', ' ').title() if coluna_metrica_principal != 'Contagem de Registros' else 'Nº de Registros'
        
        if not df_plot_base.empty and not df_plot_comp.empty:
            
            try:
                if eixo_x_real:
                    
                    if tipo_grafico_1.startswith('Barra Agrupada'):
                        agg_cols = [eixo_x_real]
                        if color_real: agg_cols.append(color_real)
                        
                        is_mean_agg = 'Média' in tipo_grafico_1
                        
                        def agg_func(df):
                            if coluna_metrica_principal == 'Contagem de Registros':
                                return df.groupby(agg_cols, as_index=False).size().rename(columns={'size': y_col_agg_title})
                            elif is_mean_agg:
                                return df.groupby(agg_cols, as_index=False)[coluna_metrica_principal].mean().rename(columns={coluna_metrica_principal: y_col_agg_title})
                            else:
                                return df.groupby(agg_cols, as_index=False)[coluna_metrica_principal].sum().rename(columns={coluna_metrica_principal: y_col_agg_title})
                            
                        df_agg_base = agg_func(df_plot_base)
                        df_agg_comp = agg_func(df_plot_comp)
                        
                        df_agg_base['Conjunto'] = 'BASE'
                        df_agg_comp['Conjunto'] = 'COMPARAÇÃO'
                        df_final = pd.concat([df_agg_base, df_agg_comp], ignore_index=True)

                        # Renomeia a coluna Y para o título
                        y_col_agg_name = y_col_agg_title if y_col_agg_title in df_final.columns else coluna_metrica_principal
                        
                        fig = px.bar(df_final, x=eixo_x_real, y=y_col_agg_name, color='Conjunto', 
                                     pattern_shape=color_real,
                                     barmode='group',
                                     title=f'{tipo_grafico_1} de {y_col_agg_title} por {eixo_x_real.title().replace("_", " ")}')
                        fig.update_layout(xaxis={'categoryorder': 'total descending'}, title_x=0.5)
                        st.plotly_chart(fig, use_container_width=True)
                        
                    elif tipo_grafico_1 == 'Dispersão (Box Plot)' and is_currency_metric:
                        df_plot_base['Conjunto'] = 'BASE'
                        df_plot_comp['Conjunto'] = 'COMPARAÇÃO'
                        df_dispersao = pd.concat([df_plot_base, df_plot_comp], ignore_index=True)
                        
                        fig = px.box(df_dispersao, x='Conjunto', y=coluna_metrica_principal, color=color_real,
                                     title=f'Distribuição de {coluna_metrica_principal.title().replace("_", " ")} entre Base e Comparação')
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
        st.markdown(f"##### Gráfico 2: Foco em **{coluna_metrica_principal.replace('_', ' ').title()}** (Conjunto Base)")
        opcoes_grafico_2 = ['Distribuição (Histograma)']
        
        if colunas_data:
            opcoes_grafico_2.append('Série Temporal (Linha - Total)')
            if is_currency_metric:
                opcoes_grafico_2.append('Série Temporal (Linha - Média)')
            
        if is_currency_metric and len(colunas_numericas_salvas) > 1:
            opcoes_grafico_2.append('Relação (Dispersão)')
            
        default_graph_2_index = 0
        if colunas_data and 'Série Temporal (Linha - Total)' in opcoes_grafico_2:
            default_graph_2_index = opcoes_grafico_2.index('Série Temporal (Linha - Total)')
            
        tipo_grafico_2 = st.selectbox("Tipo de Visualização (Gráfico 2):", options=opcoes_grafico_2, key='tipo_grafico_2', index=default_graph_2_index)
        
        if not df_base.empty:
            fig = None
            try:
                if tipo_grafico_2.startswith('Série Temporal (Linha)'):
                    eixo_x_data = colunas_data[0]
                    color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
                    is_mean_agg = 'Média' in tipo_grafico_2
                    
                    agg_cols = [eixo_x_data]
                    if color_real: agg_cols.append(color_real)
                    
                    y_col_agg_title = coluna_metrica_principal.replace('_', ' ').title() if coluna_metrica_principal != 'Contagem de Registros' else 'Nº de Registros'
                    
                    if coluna_metrica_principal == 'Contagem de Registros':
                         df_agg = df_base.groupby(agg_cols, as_index=False).size().rename(columns={'size': y_col_agg_title})
                         y_col_agg = y_col_agg_title
                    elif is_mean_agg:
                         df_agg = df_base.groupby(agg_cols, as_index=False)[coluna_metrica_principal].mean()
                         y_col_agg = coluna_metrica_principal
                    else:
                         df_agg = df_base.groupby(agg_cols, as_index=False)[coluna_metrica_principal].sum()
                         y_col_agg = coluna_metrica_principal
                         
                    fig = px.line(df_agg, x=eixo_x_data, y=y_col_agg, color=color_real,
                                  title=f'Tendência Temporal (Base): {tipo_grafico_2.split(" - ")[1]} de {y_col_agg_title}{" por " + color_real.title().replace("_", " ") if color_real else ""}')
                    
                elif tipo_grafico_2 == 'Distribuição (Histograma)':
                    if is_currency_metric:
                        color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
                        fig = px.histogram(df_base, x=coluna_metrica_principal, color=color_real,
                                           title=f'Distribuição (Base) de {coluna_metrica_principal.title().replace("_", " ")}{" por " + color_real.title().replace("_", " ") if color_real else ""}')
                    else:
                        st.warning("Selecione Coluna de Valor Numérica para Histograma.")
                        
                elif tipo_grafico_2 == 'Relação (Dispersão)' and is_currency_metric:
                    colunas_para_dispersao = [c for c in colunas_numericas_salvas if c != coluna_metrica_principal]
                    if colunas_para_dispersao:
                        coluna_x_disp = st.selectbox("Selecione o Eixo X para Dispersão:", options=colunas_para_dispersao, key='col_x_disp_2')
                        color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
                        fig = px.scatter(df_base, x=coluna_x_disp, y=coluna_metrica_principal, color=color_real,
                                         title=f'Relação (Base) entre {coluna_x_disp.title().replace("_", " ")} e {coluna_metrica_principal.title().replace("_", " ")}{" por " + color_real.title().replace("_", " ") if color_real else ""}')
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
    st.subheader(f"🔍 Detalhes dos Dados Filtrados (Base)")
    st.caption(f"Filtros Ativos: {rotulo_base}. Exibindo no máximo 1000 linhas.")
    
    df_exibicao = df_base.copy()
    
    # Formatação de colunas de valor para exibição
    for col in colunas_numericas_salvas: 
        if col in df_exibicao.columns:
            # Assume que a coluna é moeda se foi classificada como tal na configuração
            if is_currency_metric: # Usa a lógica da métrica principal para o formato, ou ajusta se necessário
                df_exibicao[col] = df_exibicao[col].apply(lambda x: formatar_moeda(x) if pd.notna(x) else '')
            else:
                df_exibicao[col] = df_exibicao[col].apply(lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(x) else '')
                
    max_linhas_exibidas = 1000
    if len(df_exibicao) > max_linhas_exibidas:
        df_exibicao_limitado = df_exibicao.head(max_linhas_exibidas)
    else:
        df_exibicao_limitado = df_exibicao

    st.dataframe(df_exibicao_limitado, use_container_width=True, hide_index=True)

    # --- Botões de Download ---
    
    # CSV para a base completa filtrada
    csv_data = df_base.to_csv(index=False, sep=';', decimal=',', encoding='utf-8')
    
    # XLSX para a base completa filtrada
    xlsx_output = BytesIO()
    xlsx_data = None
    try:
        # Importa openpyxl DENTRO do try/except, já que pode não estar instalado
        import openpyxl 
        with pd.ExcelWriter(xlsx_output, engine='openpyxl') as writer:
            df_base.to_excel(writer, index=False, sheet_name='Dados Filtrados')
        xlsx_data = xlsx_output.getvalue()
    except ImportError:
        st.caption("Instale 'openpyxl' (`pip install openpyxl`) para habilitar o download em XLSX.")
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
