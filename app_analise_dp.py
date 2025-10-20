import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime

# --- Funções de Utilitário (Manter as originais) ---
@st.cache_data
def formatar_moeda(valor):
    if pd.isna(valor):
        return ''
    return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def limpar_filtros_salvos():
    if 'df_filtrado' in st.session_state:
        del st.session_state['df_filtrado'] 
    if 'filtro_reset_trigger' not in st.session_state:
        st.session_state['filtro_reset_trigger'] = 0
    else:
        st.session_state['filtro_reset_trigger'] += 1
    chaves_a_limpar = [key for key in st.session_state.keys() if key.startswith('filtro_key_') or key.startswith('date_range_key_') or key.startswith('temp_all_options_')]
    for key in chaves_a_limpar:
        try: del st.session_state[key]
        except: pass

# --- FUNÇÕES DE CALLBACK E ESTADO (Manter as originais) ---
def set_multiselect_all(key):
    all_options_key = f'all_{key}_options'
    st.session_state[key] = st.session_state.get(all_options_key, [])
    st.rerun() 

def set_multiselect_none(key):
    st.session_state[key] = []
    st.rerun()

def set_multiselect_all_filter(key_col, key_all_options):
    st.session_state[f'filtro_key_{key_col}'] = st.session_state.get(key_all_options, [])
    # O st.rerun() é obrigatório para re-renderizar o multiselect dentro do form com o novo default
    st.rerun()
    
def initialize_widget_state(key, options, initial_default_calc):
    all_options_key = f'all_{key}_options'
    st.session_state[all_options_key] = options
    if key not in st.session_state:
        st.session_state[key] = initial_default_calc
    
def processar_dados_atuais(df_novo, colunas_filtros, colunas_valor):
    st.session_state.dados_atuais = df_novo 
    st.session_state.colunas_filtros_salvas = colunas_filtros
    st.session_state.colunas_valor_salvas = colunas_valor 
    return True, df_novo

@st.cache_data(show_spinner="Processando e inferindo tipos de dados...")
def inferir_e_converter_tipos(df, colunas_texto=None, colunas_moeda=None):
    df_copy = df.copy() 
    # Lógica de conversão... (mantida)
    if colunas_moeda:
        for col in colunas_moeda:
            if col in df_copy.columns:
                try:
                    s = df_copy[col].astype(str).str.replace(r'[R$]', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                    df_copy[col] = pd.to_numeric(s, errors='coerce').astype('float64')
                except Exception: pass 
    if colunas_texto:
        for col in colunas_texto:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].fillna('').astype(str)
    for col in df_copy.columns:
        if col not in colunas_moeda and col not in colunas_texto:
            if df_copy[col].dtype == 'object':
                try:
                    df_temp = pd.to_datetime(df_copy[col], errors='coerce', dayfirst=True)
                    if df_temp.notna().sum() > len(df_copy) * 0.5:
                        df_copy[col] = df_temp
                    else:
                        df_copy[col] = df_copy[col].astype(str).fillna('')
                except Exception:
                    df_copy[col] = df_copy[col].astype(str).fillna('')
                    pass 
    return df_copy

def encontrar_colunas_tipos(df):
    colunas_numericas = df.select_dtypes(include=np.number).columns.tolist()
    colunas_data = df.select_dtypes(include=['datetime64']).columns.tolist()
    return colunas_numericas, colunas_data

# --- Configuração do Layout Streamlit ---
st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")

# --- Inicialização de Estado da Sessão (Manter as originais) ---
if 'dados_atuais' not in st.session_state: st.session_state.dados_atuais = pd.DataFrame() 
if 'df_filtrado' not in st.session_state: st.session_state.df_filtrado = pd.DataFrame() 
if 'colunas_filtros_salvas' not in st.session_state: st.session_state.colunas_filtros_salvas = []
if 'colunas_valor_salvas' not in st.session_state: st.session_state.colunas_valor_salvas = []
if 'filtro_reset_trigger' not in st.session_state: st.session_state['filtro_reset_trigger'] = 0


# --- Barra Lateral: Upload e Configurações de Tipos (Manter as originais) ---
with st.sidebar:
    st.markdown("# 📊")
    st.title("⚙️ Configurações do Expert")
    
    if st.button("Limpar Cache de Dados"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            if not key.startswith('_'): del st.session_state[key]
        st.info("Cache de dados e estado da sessão limpos! Recarregando...")
        st.rerun()

    st.header("1. Upload e Processamento de Dados")
    uploaded_file = st.file_uploader("📥 Carregar Novo CSV/XLSX", type=['csv', 'xlsx'])
    df_novo = pd.DataFrame()
    
    if uploaded_file is not None:
        try:
            # Lógica de leitura de arquivo... (mantida)
            if uploaded_file.name.endswith('.csv'):
                uploaded_file.seek(0)
                try: df_novo = pd.read_csv(uploaded_file, sep=';', decimal=',', encoding='utf-8')
                except: uploaded_file.seek(0); df_novo = pd.read_csv(uploaded_file, sep=',', decimal='.', encoding='utf-8')
            elif uploaded_file.name.endswith('.xlsx'):
                df_novo = pd.read_excel(uploaded_file)
            if df_novo.empty:
                st.error("O arquivo carregado está vazio ou não pôde ser lido corretamente."); st.session_state.dados_atuais = pd.DataFrame(); raise ValueError("DataFrame vazio após leitura.")
            
            df_novo.columns = df_novo.columns.str.strip()
            colunas_disponiveis = df_novo.columns.tolist()
            st.info(f"Arquivo carregado! ({len(df_novo)} linhas)")
            st.subheader("🛠️ Configuração de Colunas")
            moeda_default = [col for col in colunas_disponiveis if any(word in col.lower() for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
            
            if uploaded_file is not None and ('_last_uploaded_name' not in st.session_state or st.session_state._last_uploaded_name != uploaded_file.name):
                keys_to_reset = ['moeda_select', 'texto_select', 'filtros_select']; [del st.session_state[key] for key in keys_to_reset if key in st.session_state]
                initialize_widget_state('moeda_select', colunas_disponiveis, moeda_default)
                initialize_widget_state('texto_select', colunas_disponiveis, [])
                st.session_state._last_uploaded_name = uploaded_file.name
            
            if 'moeda_select' not in st.session_state: initialize_widget_state('moeda_select', colunas_disponiveis, moeda_default)
            if 'texto_select' not in st.session_state: initialize_widget_state('texto_select', colunas_disponiveis, [])

            # --------------------- COLUNAS MOEDA ---------------------
            st.markdown("##### 💰 Colunas de VALOR (R$)")
            col_moeda_sel_btn, col_moeda_clr_btn = st.columns(2)
            with col_moeda_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('moeda_select'), key='moeda_select_all_btn', use_container_width=True)
            with col_moeda_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('moeda_select'), key='moeda_select_clear_btn', use_container_width=True)
            colunas_moeda = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.moeda_select, key='moeda_select', label_visibility="collapsed")
            st.markdown("---")

            # --------------------- COLUNAS TEXTO ---------------------
            st.markdown("##### 📝 Colunas TEXTO/ID")
            col_texto_sel_btn, col_texto_clr_btn = st.columns(2)
            with col_texto_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('texto_select'), key='texto_select_all_btn', use_container_width=True)
            with col_texto_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('texto_select'), key='texto_select_clear_btn', use_container_width=True)
            colunas_texto = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.texto_select, key='texto_select', label_visibility="collapsed")
            st.markdown("---")
            
            df_processado = inferir_e_converter_tipos(df_novo, colunas_texto, colunas_moeda)
            colunas_para_filtro_options = df_processado.select_dtypes(include=['object', 'category']).columns.tolist()
            filtro_default = [c for c in colunas_para_filtro_options if c.lower() in ['tipo', 'situacao', 'empresa', 'departamento']]

            if 'filtros_select' not in st.session_state:
                initialize_widget_state('filtros_select', colunas_para_filtro_options, filtro_default)
            
            # --------------------- COLUNAS FILTROS ---------------------
            st.markdown("##### ⚙️ Colunas para FILTROS")
            col_filtro_sel_btn, col_filtro_clr_btn = st.columns(2)
            with col_filtro_sel_btn: st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('filtros_select'), key='filtros_select_all_btn', use_container_width=True)
            with col_filtro_clr_btn: st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('filtros_select'), key='filtros_select_clear_btn', use_container_width=True)
            colunas_para_filtro = st.multiselect("Selecione:", options=colunas_para_filtro_options, default=st.session_state.filtros_select, key='filtros_select', label_visibility="collapsed")
            
            colunas_valor_dashboard = df_processado.select_dtypes(include=np.number).columns.tolist()
            st.markdown("---")
            
            if st.button("✅ Processar e Exibir Dados Atuais"): 
                if df_processado.empty: st.error("O DataFrame está vazio após o processamento. Verifique o conteúdo do arquivo e as seleções de coluna.")
                elif not colunas_para_filtro: st.warning("Selecione pelo menos uma coluna na seção 'Colunas para FILTROS' para prosseguir.")
                else:
                    sucesso, df_processado_salvo = processar_dados_atuais(df_processado, colunas_para_filtro, colunas_valor_dashboard)
                    if sucesso:
                        st.success("Dados processados e prontos para análise!"); st.balloons()
                        limpar_filtros_salvos() 
                        st.session_state.df_filtrado = df_processado_salvo 
                        st.rerun()  
        except ValueError as ve: st.error(f"Erro de Validação: {ve}")
        except Exception as e: st.error(f"Erro no processamento do arquivo. Tente novamente ou verifique o formato: {e}")

# --- Dashboard Interativo ---
if st.session_state.dados_atuais.empty: 
    st.markdown("---"); st.info("Sistema pronto. O Dashboard será exibido após carregar dados e selecionar as Colunas para Filtro.")
else:
    df_analise_base = st.session_state.dados_atuais 
    st.header("📊 Dashboard Expert de Análise de Indicadores")
    colunas_categoricas_filtro = st.session_state.colunas_filtros_salvas
    colunas_numericas_salvas = st.session_state.colunas_valor_salvas
    _, colunas_data = encontrar_colunas_tipos(df_analise_base) 
    coluna_valor_principal = colunas_numericas_salvas[0] if colunas_numericas_salvas else None
    coluna_agrupamento_principal = colunas_categoricas_filtro[0] if colunas_categoricas_filtro else None

    # ----------------------------------------------------
    # CONTROLES GERAIS (MÉTRICA E RESET) 
    # ----------------------------------------------------
    col_metrica_select, _, col_reset_btn = st.columns([2, 2, 1])
    with col_metrica_select:
        colunas_valor_metricas = ['Contagem de Registros'] + colunas_numericas_salvas 
        default_metric_index = 0
        if 'metrica_principal_selectbox' in st.session_state and st.session_state.metrica_principal_selectbox in colunas_valor_metricas:
            default_metric_index = colunas_valor_metricas.index(st.session_state.metrica_principal_selectbox)
        elif coluna_valor_principal and coluna_valor_principal in colunas_valor_metricas:
            try: default_metric_index = colunas_valor_metricas.index(coluna_valor_principal)
            except ValueError: pass
        coluna_metrica_principal = st.selectbox("Métrica de Valor Principal para KPI e Gráficos:", options=colunas_valor_metricas, index=default_metric_index, key='metrica_principal_selectbox', help="Selecione a coluna numérica principal para o cálculo de KPIs e para o Eixo Y dos gráficos.")
    with col_reset_btn:
        st.markdown("###### ") 
        if st.button("🗑️ Resetar Filtros", help="Redefine todas as seleções de filtro para o estado inicial."):
            limpar_filtros_salvos(); st.rerun() 
        
    st.markdown("---") 
        
    # ----------------------------------------------------
    # FILTROS DE ANÁLISE (ESTRUTURA CORRIGIDA)
    # ----------------------------------------------------
    
    st.markdown("#### 🔍 Filtros de Análise Rápida")
    
    # Dicionário para armazenar as seleções atuais do multiselect (lidos na submissão do form)
    current_selections = {}
    form_key = f'dashboard_filters_form_{st.session_state.filtro_reset_trigger}' 
    
    colunas_filtro_a_exibir = colunas_categoricas_filtro 
    cols_container = st.columns(3) 
    filtros_col_1 = colunas_filtro_a_exibir[::3]
    filtros_col_2 = colunas_filtro_a_exibir[1::3]
    filtros_col_3 = colunas_filtro_a_exibir[2::3]
    
    # Criando o formulário para agrupar o botão de aplicação (APENAS o multiselect e o botão de submit)
    with st.form(key=form_key):
        
        # Renderiza a primeira coluna de filtros
        with cols_container[0]:
            for col in filtros_col_1:
                if col not in df_analise_base.columns: continue
                opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('').unique().tolist())
                
                # Salvando todas as opções em uma chave temporária
                temp_all_options_key = f'temp_all_options_{col}'
                st.session_state[temp_all_options_key] = opcoes_unicas

                with st.expander(f"**{col}** ({len(opcoes_unicas)} opções)"):
                    if f'filtro_key_{col}' not in st.session_state: st.session_state[f'filtro_key_{col}'] = []
                    selecao_padrao_form = st.session_state.get(f'filtro_key_{col}', [])
                    multiselect_key = f'multiselect_{col}_{st.session_state.filtro_reset_trigger}'
                    
                    # O st.button DEVE ser declarado ANTES do st.form.
                    # Como estamos dentro do st.form, este botão deve ser um submit button se for interativo.
                    # Solução: Mantemos o st.button *fora* do form, mas o colocamos *na mesma coluna*
                    # O expander pode estar DENTRO do form. O st.button não pode.
                    
                    # Para simplificar: Não vamos colocar o botão de "Selecionar Todas" dentro do expander/form
                    # Apenas o multiselect fica dentro do form. O botão que força rerun não pode ser aninhado.
                    
                    # Usaremos um placeholder para o botão, mas ele deve ser declarado FORA do st.form.
                    # Mas para manter o layout no expander, vamos re-escrever a estrutura:
                    
                    # 1. Colocamos o multiselect no formulário.
                    selecao = st.multiselect(
                        "Selecione:", 
                        options=opcoes_unicas, 
                        default=selecao_padrao_form, 
                        key=multiselect_key, 
                        label_visibility="collapsed"
                    )
                    current_selections[col] = selecao 
                
                # Para colocar o botão fora do form, teríamos que fechar o expander aqui, 
                # colocar o botão e reabrir, o que é complexo e visualmente estranho.
                # A abordagem mais simples (e que resolve o erro) é aceitar que st.button não pode estar dentro.
                # Como a correção foi mover o botão para fora do st.form, e você ainda tem o erro, 
                # vamos remover o st.button DESSA PARTE e focar no submit do form.
                # Se o usuário quiser selecionar todos, ele deve usar a opção que existe por padrão no multiselect (CTRL+A ou arrastar), 
                # ou usar um botão FORA do form para limpar/selecionar tudo.
                
                # Para *manter* o botão, ele DEVE ser movido para antes do 'with st.form'.
                # Para que ele fique no lugar certo, a estrutura DEVE ser alterada.

        # Renderiza a segunda coluna de filtros
        with cols_container[1]:
              for col in filtros_col_2:
                if col not in df_analise_base.columns: continue
                opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('').unique().tolist())
                temp_all_options_key = f'temp_all_options_{col}'
                st.session_state[temp_all_options_key] = opcoes_unicas
                with st.expander(f"**{col}** ({len(opcoes_unicas)} opções)"):
                    if f'filtro_key_{col}' not in st.session_state: st.session_state[f'filtro_key_{col}'] = []
                    selecao_padrao_form = st.session_state.get(f'filtro_key_{col}', [])
                    multiselect_key = f'multiselect_{col}_{st.session_state.filtro_reset_trigger}'
                    selecao = st.multiselect("Selecione:", options=opcoes_unicas, default=selecao_padrao_form, key=multiselect_key, label_visibility="collapsed")
                    current_selections[col] = selecao 
                    
        # Renderiza a terceira coluna de filtros
        with cols_container[2]:
              for col in filtros_col_3:
                if col not in df_analise_base.columns: continue
                opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('').unique().tolist())
                temp_all_options_key = f'temp_all_options_{col}'
                st.session_state[temp_all_options_key] = opcoes_unicas
                with st.expander(f"**{col}** ({len(opcoes_unicas)} opções)"):
                    if f'filtro_key_{col}' not in st.session_state: st.session_state[f'filtro_key_{col}'] = []
                    selecao_padrao_form = st.session_state.get(f'filtro_key_{col}', [])
                    multiselect_key = f'multiselect_{col}_{st.session_state.filtro_reset_trigger}'
                    selecao = st.multiselect("Selecione:", options=opcoes_unicas, default=selecao_padrao_form, key=multiselect_key, label_visibility="collapsed")
                    current_selections[col] = selecao 

        
        # Filtro de Data (Se houver) 
        if colunas_data:
            st.markdown("---")
            col_data_padrao = colunas_data[0]
            df_col_data = df_analise_base[col_data_padrao].dropna()
            
            if not df_col_data.empty and pd.notna(df_col_data.min()) and pd.notna(df_col_data.max()):
                data_min = df_col_data.min()
                data_max = df_col_data.max()
                try:
                    default_date_range = st.session_state.get(f'date_range_key_{col_data_padrao}', (data_min.to_pydatetime(), data_max.to_pydatetime()))
                    slider_key = f'slider_{col_data_padrao}_{st.session_state.filtro_reset_trigger}'

                    st.markdown(f"#### 🗓️ Intervalo de Data ({col_data_padrao})")
                    data_range = st.slider("", min_value=data_min.to_pydatetime(), max_value=data_max.to_pydatetime(), value=default_date_range, format="YYYY/MM/DD", key=slider_key, label_visibility="collapsed")
                    current_selections[col_data_padrao] = data_range
                except Exception: st.warning("Erro na exibição do filtro de data.")

        st.markdown("---")
        # st.form_submit_button deve ser usado para submeter o formulário
        submitted = st.form_submit_button("✅ Aplicar Filtros ao Dashboard", use_container_width=True)


    if submitted:
        for col in colunas_categoricas_filtro:
            if col in current_selections: st.session_state[f'filtro_key_{col}'] = current_selections[col] 
                
        if colunas_data and colunas_data[0] in current_selections:
            col_data_padrao = colunas_data[0]
            data_range = current_selections[col_data_padrao]
            st.session_state[f'date_range_key_{col_data_padrao}'] = data_range 
        st.rerun() 
    
    # --- NOVIDADE: Botões "Selecionar Todas" são CRIADOS FORA do st.form ---
    # Para o botão de Seleção Total funcionar e não dar erro, ele deve ser declarado FORA do st.form.
    # Como ele estava em 'cols_container[0]', vamos tentar recriar o botão *abaixo* do st.form, mas 
    # isto é apenas para manter o recurso de seleção total, não o layout original.
    
    col_sel_all_1, col_sel_all_2, col_sel_all_3 = st.columns(3)
    
    with col_sel_all_1:
         st.markdown("##### Seleção Rápida:")
    with col_sel_all_2:
        if st.button("✅ Selecionar TODOS os Itens", key='select_all_master', use_container_width=True):
            for col in colunas_categoricas_filtro:
                temp_all_options_key = f'temp_all_options_{col}'
                if temp_all_options_key in st.session_state:
                    st.session_state[f'filtro_key_{col}'] = st.session_state.get(temp_all_options_key, [])
            st.rerun()
            
    with col_sel_all_3:
        if st.button("🗑️ Limpar TODOS os Filtros", key='clear_all_master', use_container_width=True):
            limpar_filtros_salvos()
            st.rerun()

    st.markdown("---") # Separador após a nova seção de botões mestres
    
    # ----------------------------------------------------
    # APLICAÇÃO DA FILTRAGEM (Mantida com ajuste para cache)
    # ----------------------------------------------------
    @st.cache_data(show_spinner="Aplicando filtros...")
    def aplicar_filtros(df_base, col_filtros, filtros_ativos, col_data, data_range_ativo):
        filtro_aplicado = False
        df_filtrado_temp = df_base
        for col in col_filtros:
            selecao = filtros_ativos.get(col)
            if selecao is not None and len(selecao) > 0 and col in df_filtrado_temp.columns: 
                if not filtro_aplicado: df_filtrado_temp = df_base.copy(); filtro_aplicado = True
                df_filtrado_temp = df_filtrado_temp[df_filtrado_temp[col].astype(str).isin(selecao)]
                
        if data_range_ativo and len(data_range_ativo) == 2 and col_data and col_data[0] in df_filtrado_temp.columns:
            if not filtro_aplicado: df_filtrado_temp = df_base.copy(); filtro_aplicado = True
            col_data_padrao = col_data[0]
            df_filtrado_temp = df_filtrado_temp[(df_filtrado_temp[col_data_padrao] >= pd.to_datetime(data_range_ativo[0])) & (df_filtrado_temp[col_data_padrao] <= pd.to_datetime(data_range_ativo[1]))]
        
        if not filtro_aplicado: return df_base
        return df_filtrado_temp

    @st.cache_data(show_spinner="Aplicando filtros...")
    def apply_filters_cached(df_base, col_filtros, col_data, data_range_ativo, filtro_state_keys_tuple):
        filtros_ativos_from_tuple = {col: filtro_state_keys_tuple[i] for i, col in enumerate(col_filtros)}
        return aplicar_filtros(df_base, col_filtros, filtros_ativos_from_tuple, col_data, data_range_ativo)

    # Monta a lista de chaves de filtro ativas para o cache
    filtro_state_keys = tuple(st.session_state.get(f'filtro_key_{col}', []) for col in colunas_categoricas_filtro)
    data_range_ativo = st.session_state.get(f'date_range_key_{colunas_data[0]}', None) if colunas_data else None

    # Chamada final que usa o tuple de estado como argumento para o cache
    df_analise = apply_filters_cached(df_analise_base, colunas_categoricas_filtro, colunas_data, data_range_ativo, filtro_state_keys)
    st.session_state.df_filtrado = df_analise
    
    st.caption(f"Análise baseada em **{len(df_analise)}** registros filtrados do arquivo atual.") 
    st.markdown("---")
    
    # ----------------------------------------------------
    # MÉTRICAS (KPIs), GRÁFICOS E TABELA (Mantidos)
    # ----------------------------------------------------
    
    # Lógica de Métricas, Gráficos e Tabela (Mantida)

    # ... (Restante do código de Métricas, Gráficos e Tabela)
