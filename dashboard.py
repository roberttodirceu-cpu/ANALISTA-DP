import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime
from io import BytesIO

# Importa as funções do utils.py
from utils import formatar_moeda, inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes

st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")

# --- Inicialização de Estado da Sessão ---

# Dados atualmente exibidos no Dashboard
if 'dados_atuais' not in st.session_state:
    st.session_state.dados_atuais = pd.DataFrame() 
if 'df_filtrado' not in st.session_state:
    st.session_state.df_filtrado = pd.DataFrame() 

# Configurações de coluna do dataset ativo
if 'colunas_filtros_salvas' not in st.session_state:
    st.session_state.colunas_filtros_salvas = []
if 'colunas_valor_salvas' not in st.session_state:
    st.session_state.colunas_valor_salvas = []

# Trigger para forçar o reset dos widgets de filtro (multiselect/date slider)
if 'filtro_reset_trigger' not in st.session_state:
    st.session_state['filtro_reset_trigger'] = 0
    
# Catálogo de arquivos BINÁRIOS (para uploads) - Persistência dos arquivos subidos
if 'uploaded_files_data' not in st.session_state:
    st.session_state.uploaded_files_data = {} # Armazena {file_name: bytes_do_arquivo}

# Catálogo de DataFrames PROCESSADOS (para troca rápida) - NOVA FUNÇÃO
if 'data_sets_catalog' not in st.session_state:
    st.session_state.data_sets_catalog = {} # Armazena {nome_do_dataset: {'df': df, 'filtros': [], 'valores': []}}
    
# Nome do dataset ativo no dashboard
if 'current_dataset_name' not in st.session_state:
    st.session_state.current_dataset_name = ""

# --- Funções de Lógica ---

def limpar_filtros_salvos():
    """Limpa o estado dos widgets de filtro e do DataFrame filtrado."""
    if 'df_filtrado' in st.session_state:
        del st.session_state['df_filtrado'] 
        
    st.session_state['filtro_reset_trigger'] += 1
    
    # Limpa as chaves de sessão dos multiselects/sliders
    chaves_a_limpar = [
        key for key in st.session_state.keys() 
        if key.startswith('filtro_key_') or key.startswith('date_range_key_')
    ]
    for key in chaves_a_limpar:
        try:
            del st.session_state[key]
        except:
            pass

def set_multiselect_all(key):
    """Callback para o botão 'Selecionar Tudo'."""
    all_options_key = f'all_{key}_options'
    st.session_state[key] = st.session_state.get(all_options_key, [])
    st.rerun() 

def set_multiselect_none(key):
    """Callback para o botão 'Limpar'."""
    st.session_state[key] = []
    st.rerun()

def initialize_widget_state(key, options, initial_default_calc):
    """Inicializa o estado dos multiselects de coluna no sidebar."""
    all_options_key = f'all_{key}_options'
    st.session_state[all_options_key] = options
    if key not in st.session_state:
        st.session_state[key] = initial_default_calc

def processar_dados_atuais(df_novo, colunas_filtros, colunas_valor, dataset_name):
    """Salva o dataset processado no catálogo e define como ativo."""
    # Salva o resultado no catálogo
    st.session_state.data_sets_catalog[dataset_name] = {
        'df': df_novo,
        'colunas_filtros_salvas': colunas_filtros,
        'colunas_valor_salvas': colunas_valor,
    }
    # Define o novo catálogo como o conjunto de dados atual
    st.session_state.dados_atuais = df_novo 
    st.session_state.colunas_filtros_salvas = colunas_filtros
    st.session_state.colunas_valor_salvas = colunas_valor
    st.session_state.current_dataset_name = dataset_name # Salva o nome do dataset ativo
    return True, df_novo

def remove_file(file_name):
    """Remove um arquivo da lista de uploads pendentes."""
    if file_name in st.session_state.uploaded_files_data:
        del st.session_state.uploaded_files_data[file_name]
        st.session_state.dados_atuais = pd.DataFrame()
        st.session_state.current_dataset_name = ""
        st.rerun()

def switch_dataset(dataset_name):
    """Troca o dataset ativo no dashboard."""
    if dataset_name in st.session_state.data_sets_catalog:
        data = st.session_state.data_sets_catalog[dataset_name]
        st.session_state.dados_atuais = data['df']
        st.session_state.colunas_filtros_salvas = data['colunas_filtros_salvas']
        st.session_state.colunas_valor_salvas = data['colunas_valor_salvas']
        st.session_state.current_dataset_name = dataset_name
        limpar_filtros_salvos() # Reseta apenas os filtros de seleção
        st.rerun()
    else:
        st.error(f"Dataset '{dataset_name}' não encontrado.")


# --- SIDEBAR (CONFIGURAÇÕES E UPLOAD) ---

with st.sidebar:
    st.markdown("# 📊")
    st.title("⚙️ Configurações do Expert")
    if st.button("Limpar Cache de Dados"):
        st.cache_data.clear()
        keys_to_clear = [k for k in st.session_state.keys() if not k.startswith('_')]
        for key in keys_to_clear:
            del st.session_state[key]
        st.info("Cache de dados e estado da sessão limpos! Recarregando...")
        st.rerun()

    st.header("1. Upload e Gerenciamento de Dados")
    
    # Form para adicionar arquivos e nomear o dataset (limpa o uploader após submeter)
    with st.form("file_upload_form", clear_on_submit=True):
        uploaded_files_new = st.file_uploader(
            "📥 Carregar Novo(s) CSV/XLSX", 
            type=['csv', 'xlsx'], 
            accept_multiple_files=True,
            key="file_uploader_widget"
        )
        default_dataset_name = f"Dataset Consolidado ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        dataset_name_input = st.text_input("Nome para o Dataset Processado:", value=default_dataset_name)
        
        submit_upload = st.form_submit_button("Adicionar Arquivo(s) à Lista")
        
        if submit_upload and uploaded_files_new:
            newly_added = []
            for file in uploaded_files_new:
                st.session_state.uploaded_files_data[file.name] = file.read()
                newly_added.append(file.name)
            st.success(f"Arquivos adicionados: {', '.join(newly_added)}. Clique em 'Processar' abaixo.")
            st.rerun()

    # Exibir e Remover Arquivos Pendentes
    if st.session_state.uploaded_files_data:
        st.markdown("---")
        st.markdown("##### Arquivos Pendentes para Processamento:")
        
        for file_name in st.session_state.uploaded_files_data.keys():
            col_file, col_remove = st.columns([4, 1])
            with col_file:
                st.caption(f"- **{file_name}**")
            with col_remove:
                st.button("Remover", 
                          key=f"remove_file_btn_{file_name}", 
                          on_click=remove_file, 
                          args=(file_name,), 
                          use_container_width=True)
        
        st.markdown("---")

    # --- Lógica de Processamento e Consolidação ---
    df_novo = pd.DataFrame() 
    
    if st.session_state.uploaded_files_data:
        
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
            
            # Seleção de Colunas (Moeda, Texto, Filtro) - Lógica de estado mantida
            moeda_default = [col for col in colunas_disponiveis if any(word in col for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
            
            if 'moeda_select' not in st.session_state: initialize_widget_state('moeda_select', colunas_disponiveis, moeda_default)
            if 'texto_select' not in st.session_state: initialize_widget_state('texto_select', colunas_disponiveis, [])
            
            st.markdown("##### 💰 Colunas de VALOR (R$)")
            col_moeda_sel_btn, col_moeda_clr_btn = st.columns(2)
            with col_moeda_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('moeda_select'), key='moeda_select_all_btn', use_container_width=True)
            with col_moeda_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('moeda_select'), key='moeda_select_clear_btn', use_container_width=True)
            colunas_moeda = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.moeda_select, key='moeda_select', label_visibility="collapsed")
            
            st.markdown("---")
            st.markdown("##### 📝 Colunas TEXTO/ID")
            col_texto_sel_btn, col_texto_clr_btn = st.columns(2)
            with col_texto_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('texto_select'), key='texto_select_all_btn', use_container_width=True)
            with col_texto_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('texto_select'), key='texto_select_clear_btn', use_container_width=True)
            colunas_texto = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.texto_select, key='texto_select', label_visibility="collapsed")
            st.markdown("---")
            
            df_processado = inferir_e_converter_tipos(df_novo, colunas_texto, colunas_moeda)
            colunas_para_filtro_options = df_processado.select_dtypes(include=['object', 'category']).columns.tolist()
            filtro_default = [c for c in colunas_para_filtro_options if c in ['tipo', 'situacao', 'empresa', 'departamento']]
            if 'filtros_select' not in st.session_state:
                initialize_widget_state('filtros_select', colunas_para_filtro_options, filtro_default)
            
            st.markdown("##### ⚙️ Colunas para FILTROS")
            col_filtro_sel_btn, col_filtro_clr_btn = st.columns(2)
            with col_filtro_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('filtros_select'), key='filtros_select_all_btn', use_container_width=True)
            with col_filtro_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('filtros_select'), key='filtros_select_clear_btn', use_container_width=True)
            colunas_para_filtro = st.multiselect("Selecione:", options=colunas_para_filtro_options, default=st.session_state.filtros_select, key='filtros_select', label_visibility="collapsed")
            
            colunas_valor_dashboard = df_processado.select_dtypes(include=np.number).columns.tolist()
            st.markdown("---")
            
            # Botão de Processamento
            if st.button("✅ Processar e Exibir Dados Atuais"): 
                if df_processado.empty:
                    st.error("O DataFrame está vazio após o processamento.")
                elif not colunas_para_filtro:
                    st.warning("Selecione pelo menos uma coluna na seção 'Colunas para FILTROS'.")
                else:
                    sucesso, df_processado_salvo = processar_dados_atuais(df_processado, colunas_para_filtro, colunas_valor_dashboard, dataset_name_input)
                    if sucesso:
                        # Chamada para a função CORRIGIDA
                        ausentes = verificar_ausentes(df_processado_salvo, colunas_para_filtro)
                        
                        if ausentes: 
                            for col, (n, t) in ausentes.items():
                                st.warning(f"A coluna '{col}' possui {n} valores ausentes (em um total de {t} registros). O filtro pode não funcionar corretamente.")
                        st.success(f"Dataset '{dataset_name_input}' processado e salvo no catálogo!")
                        
                        st.session_state.uploaded_files_data = {} 
                        
                        st.balloons()
                        limpar_filtros_salvos() 
                        st.rerun() 
            
    else: 
        st.info("Carregue um ou mais arquivos CSV/XLSX para iniciar o processamento e salvamento do dataset.")


# --- Dashboard Principal ---

st.markdown("---") 

# NOVO: Geração dos Botões de Troca de Dataset
if st.session_state.data_sets_catalog:
    st.subheader("🔁 Datasets Salvos")
    
    dataset_names = list(st.session_state.data_sets_catalog.keys())
    cols = st.columns(min(len(dataset_names), 4))
    
    for i, name in enumerate(dataset_names):
        is_active = name == st.session_state.current_dataset_name
        
        button_label = f"📁 {name}" if not is_active else f"✅ {name} (Atual)"
        button_type = "primary" if is_active else "secondary"
        
        with cols[i % 4]:
            st.button(
                button_label,
                key=f"dataset_switch_{name}",
                on_click=switch_dataset,
                args=(name,),
                type=button_type,
                use_container_width=True,
                help=f"Clique para carregar e analisar o dataset '{name}'."
            )
    st.markdown("---") 


if st.session_state.dados_atuais.empty: 
    st.info("Sistema pronto. O Dashboard será exibido após carregar, processar e selecionar um Dataset.")
else:
    df_analise_base = st.session_state.dados_atuais 
    st.header(f"📊 Dashboard Expert de Análise de Indicadores ({st.session_state.current_dataset_name})")
    colunas_categoricas_filtro = st.session_state.colunas_filtros_salvas
    colunas_numericas_salvas = st.session_state.colunas_valor_salvas
    _, colunas_data = encontrar_colunas_tipos(df_analise_base) 
    coluna_valor_principal = colunas_numericas_salvas[0] if colunas_numericas_salvas else None
    coluna_agrupamento_principal = colunas_categoricas_filtro[0] if colunas_categoricas_filtro else None

    # --- Métricas e Reset ---
    col_metrica_select, _, col_reset_btn = st.columns([2, 2, 1])
    with col_metrica_select:
        colunas_valor_metricas = ['Contagem de Registros'] + colunas_numericas_salvas 
        default_metric_index = 0
        if 'metrica_principal_selectbox' in st.session_state and st.session_state.metrica_principal_selectbox in colunas_valor_metricas:
            default_metric_index = colunas_valor_metricas.index(st.session_state.metrica_principal_selectbox)
        elif coluna_valor_principal and coluna_valor_principal in colunas_valor_metricas:
            try:
                default_metric_index = colunas_valor_metricas.index(coluna_valor_principal)
            except ValueError:
                pass
        coluna_metrica_principal = st.selectbox("Métrica de Valor Principal para KPI e Gráficos:", options=colunas_valor_metricas, index=default_metric_index, key='metrica_principal_selectbox', help="Selecione a coluna numérica principal para o cálculo de KPIs e para o Eixo Y dos gráficos.")
    with col_reset_btn:
        st.markdown("###### ") 
        if st.button("🗑️ Resetar Filtros", help="Redefine todas as seleções de filtro para o estado inicial."):
            limpar_filtros_salvos()
            st.rerun() 
    st.markdown("---") 

    # --- Filtros de Análise Rápida ---
    st.markdown("#### 🔍 Filtros de Análise Rápida")
    cols_container = st.columns(3) 
    colunas_filtro_a_exibir = colunas_categoricas_filtro 
    filtros_col_1 = colunas_filtro_a_exibir[::3]
    filtros_col_2 = colunas_filtro_a_exibir[1::3]
    filtros_col_3 = colunas_filtro_a_exibir[2::3]

    for idx, filtros_col in enumerate([filtros_col_1, filtros_col_2, filtros_col_3]):
        with cols_container[idx]:
            for col in filtros_col:
                if col not in df_analise_base.columns: continue
                opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('').unique().tolist())
                filtro_key = f'filtro_key_{col}'
                initialize_widget_state(filtro_key, opcoes_unicas, []) 
                
                with st.expander(f"**{col}** ({len(opcoes_unicas)} opções)"):
                    col_sel_btn, col_clr_btn = st.columns(2)
                    with col_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda c=filtro_key: set_multiselect_all(c), key=f'select_all_btn_{col}', use_container_width=True)
                    with col_clr_btn: st.button("🗑️ Limpar", on_click=lambda c=filtro_key: set_multiselect_none(c), key=f'select_none_btn_{col}', use_container_width=True)
                    st.markdown("---") 
                    selecao_padrao_form = st.session_state.get(filtro_key, [])
                    st.multiselect("Selecione:", options=opcoes_unicas, default=selecao_padrao_form, key=filtro_key, label_visibility="collapsed")


    # --- Filtro de Data ---
    st.markdown("---") 
    if colunas_data:
        col_data_padrao = colunas_data[0]
        df_col_data = df_analise_base[col_data_padrao].dropna()
        if not df_col_data.empty and pd.notna(df_col_data.min()) and pd.notna(df_col_data.max()):
            data_min = df_col_data.min()
            data_max = df_col_data.max()
            try:
                default_date_range = st.session_state.get(f'date_range_key_{col_data_padrao}', (data_min.to_pydatetime(), data_max.to_pydatetime()))
                st.markdown(f"#### 🗓️ Intervalo de Data ({col_data_padrao})")
                st.slider("", min_value=data_min.to_pydatetime(), max_value=data_max.to_pydatetime(), 
                          value=default_date_range, format="YYYY/MM/DD", key=f'date_range_key_{col_data_padrao}', label_visibility="collapsed")
            except Exception:
                st.warning("Erro na exibição do filtro de data.")
    
    st.markdown("---")
    submitted = st.button("✅ Aplicar Filtros ao Dashboard", use_container_width=True)
    if submitted:
        st.rerun() 

    # --- Aplicação dos Filtros ---
    @st.cache_data(show_spinner="Aplicando filtros...")
    def aplicar_filtros(df_base, col_filtros, filtros_ativos, col_data, data_range_ativo):
        filtro_aplicado = False
        df_filtrado_temp = df_base
        for col in col_filtros:
            selecao = filtros_ativos.get(col)
            if selecao and col in df_filtrado_temp.columns: 
                if not filtro_aplicado:
                    df_filtrado_temp = df_base.copy()
                    filtro_aplicado = True
                df_filtrado_temp = df_filtrado_temp[df_filtrado_temp[col].astype(str).isin(selecao)]
        if data_range_ativo and len(data_range_ativo) == 2 and col_data and col_data[0] in df_filtrado_temp.columns:
            if not filtro_aplicado:
                df_filtrado_temp = df_base.copy()
                filtro_aplicado = True
            col_data_padrao = col_data[0]
            df_filtrado_temp = df_filtrado_temp[
                (df_filtrado_temp[col_data_padrao] >= pd.to_datetime(data_range_ativo[0])) &
                (df_filtrado_temp[col_data_padrao] <= pd.to_datetime(data_range_ativo[1]))
            ]
        return df_filtrado_temp if filtro_aplicado else df_base

    filtros_ativos = {col: st.session_state.get(f'filtro_key_{col}') for col in colunas_categoricas_filtro if st.session_state.get(f'filtro_key_{col}')}
    data_range_ativo = st.session_state.get(f'date_range_key_{colunas_data[0]}', None) if colunas_data else None
    
    df_analise = aplicar_filtros(df_analise_base, colunas_categoricas_filtro, filtros_ativos, colunas_data, data_range_ativo)
    st.session_state.df_filtrado = df_analise

    st.caption(f"Análise baseada em **{len(df_analise)}** registros filtrados do dataset **{st.session_state.current_dataset_name}**.") 
    st.markdown("---")
    
    # --- KPIs ---
    st.subheader("🌟 Métricas Chave")
    col_metric_1, col_metric_2, col_metric_3, col_metric_4 = st.columns(4)
    coluna_metrica_principal = st.session_state.get('metrica_principal_selectbox')
    
    if not df_analise.empty:
        contagem = len(df_analise)
        col_metric_3.metric("Registros Filtrados", f"{contagem:,.0f}".replace(',', '.'))
        
        if coluna_metrica_principal != 'Contagem de Registros' and coluna_metrica_principal in colunas_numericas_salvas:
            total_valor = df_analise[coluna_metrica_principal].sum()
            media_valor = df_analise[coluna_metrica_principal].mean()
            col_metric_1.metric(f"Total Acumulado", formatar_moeda(total_valor))
            col_metric_2.metric(f"Média por Registro", formatar_moeda(media_valor))
            col_metric_4.metric("Col. Principal", coluna_metrica_principal)
        else:
            col_metric_1.metric("Total Acumulado (Contagem)", f"{contagem:,.0f}".replace(',', '.'))
            col_metric_2.metric("Média por Registro: N/A", "R$ 0,00") 
            col_metric_4.metric("Col. Principal", "Contagem")
    else:
        col_metric_1.warning("Dados não carregados ou vazios.")
        
    st.markdown("---")
    st.subheader("📈 Análise Visual (Gráficos) ")

    # --- Gráficos (Lógica mantida) ---
    col_graph_1, col_graph_2 = st.columns(2)
    opcoes_graficos_base = ['Comparação (Barra)', 'Composição (Pizza)', 'Série Temporal (Linha)', 'Distribuição (Histograma)', 'Estatística Descritiva (Box Plot)']
    coluna_x_fixa = coluna_agrupamento_principal if coluna_agrupamento_principal else 'Nenhuma Chave Categórica Encontrada' 
    coluna_y_fixa = coluna_metrica_principal
    
    with col_graph_1:
        st.markdown(f"##### Agrupamento por: **{coluna_x_fixa}**")
        tipo_grafico_1 = st.selectbox("Tipo de Visualização (Gráfico 1):", options=[o for o in opcoes_graficos_base if 'Dispersão' not in o and 'Série Temporal' not in o], index=0, key='tipo_grafico_1')
        if coluna_x_fixa not in ['Nenhuma Chave Categórica Encontrada'] and not df_analise.empty:
            eixo_x_real = coluna_x_fixa
            fig = None
            try:
                if tipo_grafico_1 in ['Comparação (Barra)', 'Composição (Pizza)']:
                    if coluna_y_fixa == 'Contagem de Registros':
                        df_agg = df_analise.groupby(eixo_x_real, as_index=False).size().rename(columns={'size': 'Contagem'})
                        y_col_agg = 'Contagem'
                    else:
                        df_agg = df_analise.groupby(eixo_x_real, as_index=False)[coluna_y_fixa].sum()
                        y_col_agg = coluna_y_fixa
                    if tipo_grafico_1 == 'Comparação (Barra)':
                        fig = px.bar(df_agg, x=eixo_x_real, y=y_col_agg, title=f'Total de {y_col_agg} por {eixo_x_real}')
                    elif tipo_grafico_1 == 'Composição (Pizza)':
                        fig = px.pie(df_agg, names=eixo_x_real, values=y_col_agg, title=f'Composição de {y_col_agg} por {eixo_x_real}')
                elif tipo_grafico_1 == 'Estatística Descritiva (Box Plot)':
                    if coluna_y_fixa != 'Contagem de Registros' and coluna_y_fixa in colunas_numericas_salvas:
                        fig = px.box(df_analise, x=eixo_x_real, y=coluna_y_fixa, title=f'Distribuição de {coluna_y_fixa} por {eixo_x_real}')
                    else:
                         st.warning("Selecione Coluna de Valor Numérica para Box Plot.")
                elif tipo_grafico_1 == 'Distribuição (Histograma)':
                    if coluna_y_fixa in colunas_numericas_salvas:
                         fig = px.histogram(df_analise, x=coluna_y_fixa, color=eixo_x_real, title=f'Distribuição de {coluna_y_fixa} por {eixo_x_real}')
                    else:
                         st.warning("Selecione Coluna de Valor Numérica para Histograma.")
                if fig:
                    fig.update_layout(hovermode="x unified", title_x=0.5, margin=dict(t=50, b=50, l=50, r=50)) 
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao gerar o Gráfico 1. Erro: {e}")
        else:
            st.warning("Dados não carregados ou Colunas de Filtro não selecionadas.")
            
    with col_graph_2:
        st.markdown(f"##### Métrica Principal: **{coluna_y_fixa}**")
        opcoes_grafico_2 = ['Série Temporal (Linha)', 'Distribuição (Histograma)']
        if coluna_y_fixa != 'Contagem de Registros' and coluna_y_fixa in colunas_numericas_salvas:
            opcoes_grafico_2.append('Relação (Dispersão)')
        if not colunas_data:
            opcoes_grafico_2 = [o for o in opcoes_grafico_2 if 'Série Temporal' not in o]
        tipo_grafico_2 = st.selectbox("Tipo de Visualização (Gráfico 2):", options=opcoes_grafico_2, index=0, key='tipo_grafico_2')
        
        if not df_analise.empty:
            fig = None
            try:
                if tipo_grafico_2 == 'Série Temporal (Linha)':
                    if colunas_data and colunas_data[0] in df_analise.columns:
                        eixo_x_data = colunas_data[0]
                        if coluna_y_fixa != 'Contagem de Registros':
                             df_agg = df_analise.groupby(eixo_x_data, as_index=False)[coluna_y_fixa].sum()
                             y_col_agg = coluna_y_fixa
                             fig = px.line(df_agg, x=eixo_x_data, y=y_col_agg, title=f'Tendência Temporal: Soma de {coluna_y_fixa}')
                        else:
                             df_agg = df_analise.groupby(eixo_x_data, as_index=False).size().rename(columns={'size': 'Contagem'})
                             y_col_agg = 'Contagem'
                             fig = px.line(df_agg, x=eixo_x_data, y=y_col_agg, title='Tendência Temporal: Contagem de Registros')
                    else:
                        st.warning("Coluna de Data/Hora não encontrada para Série Temporal.")
                elif tipo_grafico_2 == 'Distribuição (Histograma)':
                    if coluna_y_fixa in colunas_numericas_salvas:
                        fig = px.histogram(df_analise, x=coluna_y_fixa, title=f'Distribuição de Frequência de {coluna_y_fixa}')
                    else:
                        st.warning("Selecione Coluna de Valor Numérica para Histograma.")
                elif tipo_grafico_2 == 'Relação (Dispersão)':
                    if len(colunas_numericas_salvas) > 1 and coluna_y_fixa != 'Contagem de Registros':
                        colunas_para_dispersao = [c for c in colunas_numericas_salvas if c != coluna_y_fixa]
                        if colunas_para_dispersao:
                            coluna_x_disp = st.selectbox("Selecione o Eixo X para Dispersão:", options=colunas_para_dispersao, key='col_x_disp')
                            fig = px.scatter(df_analise, x=coluna_x_disp, y=coluna_y_fixa, title=f'Relação entre {coluna_x_disp} e {coluna_y_fixa}')
                        else:
                             st.warning("Necessário outra coluna numérica além da Métrica Principal para Dispersão.")
                    else:
                        st.warning("Necessário mais de uma coluna numérica para Gráfico de Dispersão.")
                if fig:
                    fig.update_layout(hovermode="x unified", title_x=0.5, margin=dict(t=50, b=50, l=50, r=50))
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao gerar o Gráfico 2. Erro: {e}")
        else:
            st.warning("O DataFrame está vazio após a aplicação dos filtros.")

    # --- Tabela e Download ---
    st.markdown("---")
    st.subheader("🔍 Detalhes dos Dados Filtrados")
    df_exibicao = df_analise.copy()
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

    csv_data = df_analise.to_csv(index=False, sep=';', decimal=',', encoding='utf-8')
    xlsx_output = BytesIO()
    try:
        # Tenta usar o openpyxl que é uma dependência comum para Streamlit
        import openpyxl 
        with pd.ExcelWriter(xlsx_output, engine='openpyxl') as writer:
            df_analise.to_excel(writer, index=False)
        xlsx_data = xlsx_output.getvalue()
    except ImportError:
        xlsx_data = None
        st.warning("A biblioteca 'openpyxl' não está instalada. O download em XLSX está desabilitado.")

    col_csv, col_xlsx, _ = st.columns([1, 1, 2])
    with col_csv:
        st.download_button(
            label="📥 Baixar Dados Tratados (CSV)",
            data=csv_data,
            file_name=f'dados_analise_exportados_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
            mime='text/csv',
            use_container_width=True
        )
    if xlsx_data:
        with col_xlsx:
            st.download_button(
                label="📥 Baixar Dados Tratados (XLSX)",
                data=xlsx_data,
                file_name=f'dados_analise_exportados_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
            )
