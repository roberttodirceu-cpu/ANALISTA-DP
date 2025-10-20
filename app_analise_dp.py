import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime
from io import BytesIO
from utils import formatar_moeda, inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes

st.set_page_config(layout="wide", page_title="Sistema de Análise de Indicadores Expert")

# --- Inicialização de Estado da Sessão ---
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

def limpar_filtros_salvos():
    if 'df_filtrado' in st.session_state:
        del st.session_state['df_filtrado'] 
    if 'filtro_reset_trigger' not in st.session_state:
        st.session_state['filtro_reset_trigger'] = 0
    else:
        st.session_state['filtro_reset_trigger'] += 1
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
    all_options_key = f'all_{key}_options'
    st.session_state[key] = st.session_state.get(all_options_key, [])
    st.rerun() 

def set_multiselect_none(key):
    st.session_state[key] = []
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

with st.sidebar:
    st.markdown("# 📊")
    st.title("⚙️ Configurações do Expert")
    if st.button("Limpar Cache de Dados"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            if not key.startswith('_'):
                del st.session_state[key]
        st.info("Cache de dados e estado da sessão limpos! Recarregando...")
        st.rerun()

    st.header("1. Upload e Processamento de Dados")
    uploaded_file = st.file_uploader("📥 Carregar Novo CSV/XLSX", type=['csv', 'xlsx'])
    df_novo = pd.DataFrame()
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                uploaded_file.seek(0)
                try:
                    df_novo = pd.read_csv(uploaded_file, sep=';', decimal=',', encoding='utf-8')
                except:
                    uploaded_file.seek(0)
                    df_novo = pd.read_csv(uploaded_file, sep=',', decimal='.', encoding='utf-8')
            elif uploaded_file.name.endswith('.xlsx'):
                df_novo = pd.read_excel(uploaded_file)
            if df_novo.empty:
                st.error("O arquivo carregado está vazio ou não pôde ser lido corretamente.")
                st.session_state.dados_atuais = pd.DataFrame() 
                raise ValueError("DataFrame vazio após leitura.")
            df_novo.columns = df_novo.columns.str.strip().str.lower()
            colunas_disponiveis = df_novo.columns.tolist()
            st.info(f"Arquivo carregado! ({len(df_novo)} linhas)")
            moeda_default = [col for col in colunas_disponiveis if any(word in col for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
            if uploaded_file is not None and ('_last_uploaded_name' not in st.session_state or st.session_state._last_uploaded_name != uploaded_file.name):
                keys_to_reset = ['moeda_select', 'texto_select', 'filtros_select']
                for key in keys_to_reset:
                    if key in st.session_state:
                        del st.session_state[key]
                initialize_widget_state('moeda_select', colunas_disponiveis, moeda_default)
                initialize_widget_state('texto_select', colunas_disponiveis, [])
                st.session_state._last_uploaded_name = uploaded_file.name
            if 'moeda_select' not in st.session_state: initialize_widget_state('moeda_select', colunas_disponiveis, moeda_default)
            if 'texto_select' not in st.session_state: initialize_widget_state('texto_select', colunas_disponiveis, [])
            st.markdown("##### 💰 Colunas de VALOR (R$)")
            col_moeda_sel_btn, col_moeda_clr_btn = st.columns(2)
            with col_moeda_sel_btn:
                st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('moeda_select'), key='moeda_select_all_btn', use_container_width=True)
            with col_moeda_clr_btn:
                st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('moeda_select'), key='moeda_select_clear_btn', use_container_width=True)
            colunas_moeda = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.moeda_select, key='moeda_select', label_visibility="collapsed")
            st.markdown("---")
            st.markdown("##### 📝 Colunas TEXTO/ID")
            col_texto_sel_btn, col_texto_clr_btn = st.columns(2)
            with col_texto_sel_btn:
                st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('texto_select'), key='texto_select_all_btn', use_container_width=True)
            with col_texto_clr_btn:
                st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('texto_select'), key='texto_select_clear_btn', use_container_width=True)
            colunas_texto = st.multiselect("Selecione:", options=colunas_disponiveis, default=st.session_state.texto_select, key='texto_select', label_visibility="collapsed")
            st.markdown("---")
            df_processado = inferir_e_converter_tipos(df_novo, colunas_texto, colunas_moeda)
            colunas_para_filtro_options = df_processado.select_dtypes(include=['object', 'category']).columns.tolist()
            filtro_default = [c for c in colunas_para_filtro_options if c in ['tipo', 'situacao', 'empresa', 'departamento']]
            if 'filtros_select' not in st.session_state:
                initialize_widget_state('filtros_select', colunas_para_filtro_options, filtro_default)
            st.markdown("##### ⚙️ Colunas para FILTROS")
            col_filtro_sel_btn, col_filtro_clr_btn = st.columns(2)
            with col_filtro_sel_btn:
                st.button("✅ Selecionar Tudo", on_click=lambda: set_multiselect_all('filtros_select'), key='filtros_select_all_btn', use_container_width=True)
            with col_filtro_clr_btn:
                st.button("🗑️ Limpar", on_click=lambda: set_multiselect_none('filtros_select'), key='filtros_select_clear_btn', use_container_width=True)
            colunas_para_filtro = st.multiselect("Selecione:", options=colunas_para_filtro_options, default=st.session_state.filtros_select, key='filtros_select', label_visibility="collapsed")
            colunas_valor_dashboard = df_processado.select_dtypes(include=np.number).columns.tolist()
            st.markdown("---")
            if st.button("✅ Processar e Exibir Dados Atuais"): 
                if df_processado.empty:
                    st.error("O DataFrame está vazio após o processamento. Verifique o conteúdo do arquivo e as seleções de coluna.")
                elif not colunas_para_filtro:
                    st.warning("Selecione pelo menos uma coluna na seção 'Colunas para FILTROS' para prosseguir.")
                else:
                    sucesso, df_processado_salvo = processar_dados_atuais(df_processado, colunas_para_filtro, colunas_valor_dashboard)
                    if sucesso:
                        ausentes = verificar_ausentes(df_processado_salvo, colunas_para_filtro)
                        if ausentes:
                            for col, (n, t) in ausentes.items():
                                st.warning(f"A coluna '{col}' possui {n} valores ausentes de {t}. O filtro pode não funcionar corretamente.")
                        st.success("Dados processados e prontos para análise!")
                        st.balloons()
                        limpar_filtros_salvos() 
                        st.session_state.df_filtrado = df_processado_salvo 
                        st.rerun()  
        except ValueError as ve:
             st.error(f"Erro de Validação: {ve}")
        except Exception as e:
            st.error(f"Erro no processamento do arquivo. Tente novamente ou verifique o formato: {e}")

if st.session_state.dados_atuais.empty: 
    st.markdown("---")
    st.info("Sistema pronto. O Dashboard será exibido após carregar dados e selecionar as Colunas para Filtro.")
else:
    df_analise_base = st.session_state.dados_atuais 
    st.header("📊 Dashboard Expert de Análise de Indicadores")
    colunas_categoricas_filtro = st.session_state.colunas_filtros_salvas
    colunas_numericas_salvas = st.session_state.colunas_valor_salvas
    _, colunas_data = encontrar_colunas_tipos(df_analise_base) 
    coluna_valor_principal = colunas_numericas_salvas[0] if colunas_numericas_salvas else None
    coluna_agrupamento_principal = colunas_categoricas_filtro[0] if colunas_categoricas_filtro else None

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

    st.markdown("#### 🔍 Filtros de Análise Rápida")
    current_selections = {}
    form_key = f'dashboard_filters_form_{st.session_state.filtro_reset_trigger}' 
    with st.form(key=form_key):
        colunas_filtro_a_exibir = colunas_categoricas_filtro 
        cols_container = st.columns(3) 
        filtros_col_1 = colunas_filtro_a_exibir[::3]
        filtros_col_2 = colunas_filtro_a_exibir[1::3]
        filtros_col_3 = colunas_filtro_a_exibir[2::3]
        # --- BLOCO DOS FILTROS CORRIGIDO PARA USAR CHECKBOXES DENTRO DO FORM ---
        for idx, filtros_col in enumerate([filtros_col_1, filtros_col_2, filtros_col_3]):
            with cols_container[idx]:
                for col in filtros_col:
                    if col not in df_analise_base.columns: continue
                    opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('').unique().tolist())
                    with st.expander(f"**{col}** ({len(opcoes_unicas)} opções)"):
                        if f'filtro_key_{col}' not in st.session_state:
                            st.session_state[f'filtro_key_{col}'] = []
                        selecao_padrao_form = st.session_state.get(f'filtro_key_{col}', [])
                        multiselect_key = f'multiselect_{col}_{st.session_state.filtro_reset_trigger}'

                        col1_btn, col2_btn = st.columns([1, 1])
                        select_all = col1_btn.checkbox("Selecionar Todos", key=f'select_all_{col}_{st.session_state.filtro_reset_trigger}')
                        clear_all = col2_btn.checkbox("Limpar", key=f'clear_{col}_{st.session_state.filtro_reset_trigger}')

                        if select_all:
                            selecao = opcoes_unicas
                        elif clear_all:
                            selecao = []
                        else:
                            selecao = st.multiselect(
                                "Selecione:",
                                options=opcoes_unicas,
                                default=st.session_state.get(multiselect_key, selecao_padrao_form),
                                key=multiselect_key,
                                label_visibility="collapsed"
                            )
                        current_selections[col] = selecao
        # --- FIM DO BLOCO DOS FILTROS ---

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
                except Exception:
                    st.warning("Erro na exibição do filtro de data.")
        st.markdown("---")
        submitted = st.form_submit_button("✅ Aplicar Filtros ao Dashboard", use_container_width=True)
    if submitted:
        for col in colunas_categoricas_filtro:
            if col in current_selections:
                st.session_state[f'filtro_key_{col}'] = current_selections[col] 
        if colunas_data and colunas_data[0] in current_selections:
            col_data_padrao = colunas_data[0]
            data_range = current_selections[col_data_padrao]
            st.session_state[f'date_range_key_{col_data_padrao}'] = data_range 
        st.rerun() 

    @st.cache_data(show_spinner="Aplicando filtros...")
    def aplicar_filtros(df_base, col_filtros, filtros_ativos, col_data, data_range_ativo):
        filtro_aplicado = False
        df_filtrado_temp = df_base
        for col in col_filtros:
            selecao = filtros_ativos.get(col)
            if selecao is not None and len(selecao) > 0 and col in df_filtrado_temp.columns: 
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
        if not filtro_aplicado:
            return df_base
        return df_filtrado_temp

    filtros_ativos = {}
    for col in colunas_categoricas_filtro:
        selecao = st.session_state.get(f'filtro_key_{col}')
        if selecao is not None:
            filtros_ativos[col] = selecao
    data_range_ativo = st.session_state.get(f'date_range_key_{colunas_data[0]}', None) if colunas_data else None
    df_analise = aplicar_filtros(df_analise_base, colunas_categoricas_filtro, filtros_ativos, colunas_data, data_range_ativo)
    st.session_state.df_filtrado = df_analise

    st.caption(f"Análise baseada em **{len(df_analise)}** registros filtrados do arquivo atual.") 
    st.markdown("---")
    st.subheader("🌟 Métricas Chave")
    col_metric_1, col_metric_2, col_metric_3, col_metric_4 = st.columns(4)
    coluna_metrica_principal = st.session_state.get('metrica_principal_selectbox')
    if coluna_metrica_principal != 'Contagem de Registros' and coluna_metrica_principal in colunas_numericas_salvas and not df_analise.empty:
        total_valor = df_analise[coluna_metrica_principal].sum()
        col_metric_1.metric(f"Total Acumulado", formatar_moeda(total_valor), help=f"Soma total da coluna: {coluna_metrica_principal}")
        media_valor = df_analise[coluna_metrica_principal].mean()
        col_metric_2.metric(f"Média por Registro", formatar_moeda(media_valor))
        contagem = len(df_analise)
        col_metric_3.metric("Registros Filtrados", f"{contagem:,.0f}".replace(',', '.'))
        col_metric_4.metric("Col. Principal", coluna_metrica_principal)
    elif not df_analise.empty:
        contagem = len(df_analise)
        col_metric_1.metric("Total Acumulado (Contagem)", f"{contagem:,.0f}".replace(',', '.'))
        col_metric_2.metric("Média por Registro: N/A", "R$ 0,00") 
        col_metric_3.metric("Registros Filtrados", f"{contagem:,.0f}".replace(',', '.'))
        col_metric_4.metric("Col. Principal", "Contagem")
    else:
        col_metric_1.warning("Dados não carregados ou vazios.")
    st.markdown("---")
    st.subheader("📈 Análise Visual (Gráficos) ")
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
        st.info(f"Exibindo apenas as primeiras {max_linhas_exibidas} linhas para evitar travamento. Baixe o CSV/XLSX para ver todos os {len(df_exibicao)} registros.")
    else:
        df_exibicao_limitado = df_exibicao

    st.dataframe(df_exibicao_limitado, use_container_width=True, hide_index=True)

    csv_data = df_analise.to_csv(index=False, sep=';', decimal=',', encoding='utf-8')
    st.download_button(
        label="📥 Baixar Dados Tratados (CSV)",
        data=csv_data,
        file_name=f'dados_analise_exportados_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
        mime='text/csv',
    )

    try:
        import openpyxl
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_analise.to_excel(writer, index=False)
        data_xlsx = output.getvalue()
        st.download_button(
            label="📥 Baixar Dados Tratados (XLSX)",
            data=data_xlsx,
            file_name=f'dados_analise_exportados_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except Exception:
        st.info("openpyxl não instalado. Apenas CSV disponível para download.")
