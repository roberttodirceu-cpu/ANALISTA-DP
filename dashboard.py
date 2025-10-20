import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime
from io import BytesIO

# Importa as funções do utils.py
from utils import formatar_moeda, inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes

# --- Configuração da Página e Persistência de Dados ---
st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")

# Aviso sobre persistência (Streamlit Cloud/Share reinicia o app e limpa o estado)
st.sidebar.warning("⚠️ **Persistência de Dados:** Em ambientes como Streamlit Cloud, o estado da sessão pode ser limpo após 10 minutos de inatividade ou reinicialização. Use o botão 'Limpar Cache de Dados' apenas se necessário.")

# --- Inicialização de Estado da Sessão ---

# 2. PERSISTÊNCIA: A chave 'data_sets_catalog' e 'uploaded_files_data' agora são as chaves de dados persistentes.
if 'data_sets_catalog' not in st.session_state:
    st.session_state.data_sets_catalog = {} # Armazena {nome_do_dataset: {'df': df, 'filtros': [], 'valores': []}}
if 'uploaded_files_data' not in st.session_state:
    st.session_state.uploaded_files_data = {} # Armazena {file_name: bytes_do_arquivo}

# As demais chaves de estado (variáveis de trabalho da sessão atual)
if 'dados_atuais' not in st.session_state:
    st.session_state.dados_atuais = pd.DataFrame() 
if 'df_filtrado' not in st.session_state:
    st.session_state.df_filtrado = pd.DataFrame() 
if 'colunas_filtros_salvas' not in st.session_state:
    st.session_state.colunas_filtros_salvas = []
if 'colunas_valor_salvas' not in st.session_state:
    st.session_state.colunas_valor_salvas = []
if 'filtro_reset_trigger' not in st.session_state:
    st.session_state['filtro_reset_trigger'] = 0
if 'current_dataset_name' not in st.session_state:
    st.session_state.current_dataset_name = ""
if 'show_reconfig_section' not in st.session_state:
    st.session_state.show_reconfig_section = False

# --- Funções de Lógica ---

def limpar_filtros_salvos():
    """Limpa o estado dos widgets de filtro e do DataFrame filtrado."""
    if 'df_filtrado' in st.session_state:
        del st.session_state['df_filtrado'] 
        
    st.session_state['filtro_reset_trigger'] += 1
    
    chaves_a_limpar = [
        key for key in st.session_state.keys() 
        if key.startswith('filtro_key_') or key.startswith('date_range_key_') or key.startswith('grafico_key_')
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
    
    if st.session_state.uploaded_files_data:
        file_names = list(st.session_state.uploaded_files_data.keys())
        if len(file_names) == 1:
            base_name = os.path.splitext(file_names[0])[0]
        else:
             base_name = dataset_name
    else:
        base_name = dataset_name
        
    # Salva o resultado no catálogo persistente
    st.session_state.data_sets_catalog[base_name] = {
        'df': df_novo,
        'colunas_filtros_salvas': colunas_filtros,
        'colunas_valor_salvas': colunas_valor,
    }
    # Define o novo catálogo como o conjunto de dados atual
    st.session_state.dados_atuais = df_novo 
    st.session_state.colunas_filtros_salvas = colunas_filtros
    st.session_state.colunas_valor_salvas = colunas_valor
    st.session_state.current_dataset_name = base_name 
    return True, df_novo

def remove_file(file_name):
    """Remove um arquivo da lista de uploads pendentes."""
    if file_name in st.session_state.uploaded_files_data:
        del st.session_state.uploaded_files_data[file_name]
        st.session_state.dados_atuais = pd.DataFrame()
        st.session_state.current_dataset_name = ""
        st.session_state.show_reconfig_section = False
        st.rerun()

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

# --- SIDEBAR (CONFIGURAÇÕES E UPLOAD) ---

with st.sidebar:
    st.markdown("# 📊")
    st.title("⚙️ Configurações do Expert")
    
    # Adicionando botão de limpeza para o catálogo de dados (para corrigir erros)
    if st.button("Limpar Cache de Dados"):
        st.cache_data.clear()
        # Limpa todas as chaves, incluindo os catálogos
        keys_to_clear = [k for k in st.session_state.keys() if not k.startswith('_')]
        for key in keys_to_clear:
            del st.session_state[key]
        st.info("Cache de dados e estado da sessão limpos! Recarregando...")
        st.rerun()

    st.header("1. Upload e Gerenciamento de Dados")
    
    # Form para adicionar arquivos e nomear o dataset 
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
                          on_click=remove_file, 
                          args=(file_name,), 
                          use_container_width=True)
        
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
                
                # --- Seleção de Colunas ---
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
    # Limita a 4 colunas para manter o layout
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

    # --- NOVO: Configuração Multi-Dimensional dos Gráficos ---
    col_config_x, col_config_color = st.columns(2)
    
    colunas_categoricas_para_grafico = ['Nenhuma (Total)'] + colunas_categoricas_filtro
    
    with col_config_x:
        # Coluna para Agrupamento (Eixo X ou Categorias Principais)
        coluna_x_fixa = st.selectbox(
            "Agrupar/Comparar por (Eixo X):", 
            options=colunas_categoricas_para_grafico, 
            index=colunas_categoricas_para_grafico.index(coluna_agrupamento_principal) if coluna_agrupamento_principal in colunas_categoricas_para_grafico else 0,
            key='grafico_key_eixo_x'
        )
    
    with col_config_color:
        # Coluna para Quebra/Cor (Análise em Múltiplas Referências)
        colunas_quebra_opcoes = ['Nenhuma'] + [c for c in colunas_categoricas_filtro if c != coluna_x_fixa and c != 'Nenhuma (Total)']
        coluna_quebra_cor = st.selectbox(
            "Quebrar Análise/Cor por:", 
            options=colunas_quebra_opcoes, 
            index=0,
            key='grafico_key_quebra_cor',
            help="Use para comparar a métrica principal entre diferentes grupos (ex: Centro de Custo em diferentes Empresas)."
        )

    st.markdown("---") 

    # --- Gráfico 1 (Comparação/Distribuição) ---
    col_graph_1, col_graph_2 = st.columns(2)
    
    with col_graph_1:
        st.markdown(f"##### Gráfico 1: Comparação por **{coluna_x_fixa}**")
        opcoes_grafico_1 = ['Comparação (Barra)', 'Composição (Pizza)', 'Estatística Descritiva (Box Plot)']
        
        # Remove opções que exigem coluna numérica se a métrica for Contagem
        if coluna_metrica_principal == 'Contagem de Registros':
            opcoes_grafico_1 = [o for o in opcoes_grafico_1 if 'Box Plot' not in o]

        tipo_grafico_1 = st.selectbox("Tipo de Visualização (Gráfico 1):", options=opcoes_grafico_1, index=0, key='tipo_grafico_1')

        if not df_analise.empty:
            eixo_x_real = None if coluna_x_fixa == 'Nenhuma (Total)' else coluna_x_fixa
            color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
            
            fig = None
            try:
                # Lógica de Agregação
                if eixo_x_real:
                    if coluna_metrica_principal == 'Contagem de Registros':
                        agg_cols = [eixo_x_real]
                        if color_real: agg_cols.append(color_real)
                        df_agg = df_analise.groupby(agg_cols, as_index=False).size().rename(columns={'size': 'Contagem'})
                        y_col_agg = 'Contagem'
                    else:
                        agg_cols = [eixo_x_real]
                        if color_real: agg_cols.append(color_real)
                        df_agg = df_analise.groupby(agg_cols, as_index=False)[coluna_metrica_principal].sum()
                        y_col_agg = coluna_metrica_principal
                else: # Nenhuma (Total) - Usar a cor como eixo X, se existir
                    if color_real:
                        if coluna_metrica_principal == 'Contagem de Registros':
                            df_agg = df_analise.groupby(color_real, as_index=False).size().rename(columns={'size': 'Contagem'})
                            y_col_agg = 'Contagem'
                        else:
                            df_agg = df_analise.groupby(color_real, as_index=False)[coluna_metrica_principal].sum()
                            y_col_agg = coluna_metrica_principal
                        eixo_x_real = color_real
                        color_real = None # Se a quebra virou o eixo X, a cor não se aplica
                    elif coluna_metrica_principal != 'Contagem de Registros':
                        # Para Box Plot ou Histograma (Gráfico 2) sem agrupamento/quebra, não precisa de agregação
                        eixo_x_real = None 
                        y_col_agg = coluna_metrica_principal
                    else:
                        st.info("Selecione um agrupamento ou quebra para este tipo de gráfico.")
                        st.stop()
                
                # Geração do Gráfico
                if tipo_grafico_1 == 'Comparação (Barra)' and eixo_x_real:
                    fig = px.bar(df_agg, x=eixo_x_real, y=y_col_agg, color=color_real, 
                                 title=f'Soma de {y_col_agg} por {eixo_x_real}{" e " + color_real if color_real else ""}')
                elif tipo_grafico_1 == 'Composição (Pizza)' and eixo_x_real:
                    fig = px.pie(df_agg, names=eixo_x_real, values=y_col_agg, color=color_real, 
                                 title=f'Composição de {y_col_agg} por {eixo_x_real}', hole=0.3)
                elif tipo_grafico_1 == 'Estatística Descritiva (Box Plot)' and eixo_x_real:
                    fig = px.box(df_analise, x=eixo_x_real, y=coluna_metrica_principal, color=color_real,
                                 title=f'Distribuição de {coluna_metrica_principal} por {eixo_x_real}')
                
                if fig:
                    fig.update_layout(hovermode="x unified", title_x=0.5, margin=dict(t=50, b=50, l=50, r=50))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Gráfico não gerado. Verifique as configurações de Eixo X e Tipo de Gráfico.")

            except Exception as e:
                st.error(f"Erro ao gerar o Gráfico 1: {e}")
        else:
            st.warning("O DataFrame está vazio após a aplicação dos filtros.")
            
    # --- Gráfico 2 (Série Temporal/Distribuição/Dispersão) ---
    with col_graph_2:
        st.markdown(f"##### Gráfico 2: Foco em **{coluna_metrica_principal}**")
        opcoes_grafico_2 = ['Distribuição (Histograma)']
        
        if colunas_data:
            opcoes_grafico_2.append('Série Temporal (Linha)')
            
        if coluna_metrica_principal != 'Contagem de Registros' and len(colunas_numericas_salvas) > 1:
            opcoes_grafico_2.append('Relação (Dispersão)')
            
        tipo_grafico_2 = st.selectbox("Tipo de Visualização (Gráfico 2):", options=opcoes_grafico_2, index=0, key='tipo_grafico_2')
        
        if not df_analise.empty:
            fig = None
            try:
                if tipo_grafico_2 == 'Série Temporal (Linha)' and colunas_data:
                    eixo_x_data = colunas_data[0]
                    color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
                    
                    if coluna_metrica_principal == 'Contagem de Registros':
                         agg_cols = [eixo_x_data]
                         if color_real: agg_cols.append(color_real)
                         df_agg = df_analise.groupby(agg_cols, as_index=False).size().rename(columns={'size': 'Contagem'})
                         y_col_agg = 'Contagem'
                    else:
                         agg_cols = [eixo_x_data]
                         if color_real: agg_cols.append(color_real)
                         df_agg = df_analise.groupby(agg_cols, as_index=False)[coluna_metrica_principal].sum()
                         y_col_agg = coluna_metrica_principal
                         
                    fig = px.line(df_agg, x=eixo_x_data, y=y_col_agg, color=color_real,
                                  title=f'Tendência Temporal: Soma de {y_col_agg}{" por " + color_real if color_real else ""}')
                    
                elif tipo_grafico_2 == 'Distribuição (Histograma)':
                    if coluna_metrica_principal != 'Contagem de Registros':
                        color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
                        fig = px.histogram(df_analise, x=coluna_metrica_principal, color=color_real,
                                           title=f'Distribuição de {coluna_metrica_principal}{" por " + color_real if color_real else ""}')
                    else:
                        st.warning("Selecione Coluna de Valor Numérica para Histograma.")
                        
                elif tipo_grafico_2 == 'Relação (Dispersão)' and coluna_metrica_principal != 'Contagem de Registros':
                    colunas_para_dispersao = [c for c in colunas_numericas_salvas if c != coluna_metrica_principal]
                    if colunas_para_dispersao:
                        coluna_x_disp = st.selectbox("Selecione o Eixo X para Dispersão:", options=colunas_para_dispersao, key='col_x_disp')
                        color_real = None if coluna_quebra_cor == 'Nenhuma' else coluna_quebra_cor
                        fig = px.scatter(df_analise, x=coluna_x_disp, y=coluna_metrica_principal, color=color_real,
                                         title=f'Relação entre {coluna_x_disp} e {coluna_metrica_principal}{" por " + color_real if color_real else ""}')
                    else:
                         st.warning("Necessário outra coluna numérica para Gráfico de Dispersão.")

                if fig:
                    fig.update_layout(hovermode="x unified", title_x=0.5, margin=dict(t=50, b=50, l=50, r=50))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Gráfico não gerado. Verifique as configurações de Eixo X e Tipo de Gráfico.")
                    
            except Exception as e:
                st.error(f"Erro ao gerar o Gráfico 2: {e}")
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
