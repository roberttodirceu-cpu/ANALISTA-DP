import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime

# --- Funções de Utilitário ---

@st.cache_data
def formatar_moeda(valor):
    """Formata um valor numérico para o padrão de moeda (R$ com separador de milhar e duas casas decimais)."""
    if pd.isna(valor):
        return ''
    return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

@st.cache_data
def formatar_numero(valor):
     if pd.isna(valor):
         return ''
     # Formatação de milhares sem casas decimais
     return f'{int(valor):,}'.replace(',', 'X').replace('.', ',').replace('X', '.')
     
def limpar_filtros_salvos():
    """Limpa TODAS as chaves de persistência dos filtros e reseta o trigger."""
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

# --- FUNÇÕES DE CALLBACK E ESTADO (MANTIDAS APENAS PARA OS FILTROS DO DASHBOARD) ---

def set_multiselect_all(col, options):
    """Callback para definir a seleção de um multiselect para TODAS as opções salvas e forçar rerun."""
    # Garante que a chave do filtro seja definida para todas as opções
    st.session_state[f'filtro_key_{col}'] = options
    st.rerun() 

def set_multiselect_none(col):
    """Callback para limpar a seleção de um multiselect (NENHUMA opção) e forçar rerun."""
    st.session_state[f'filtro_key_{col}'] = []
    st.rerun()
        
def processar_dados_atuais(df_novo, colunas_filtros, colunas_valor):
    """Salva o DataFrame processado e as colunas de filtro/valor na sessão."""
    st.session_state.dados_atuais = df_novo 
    st.session_state.colunas_filtros_salvas = colunas_filtros
    st.session_state.colunas_valor_salvas = colunas_valor # AQUI SALVAMOS AS COLUNAS NUMÉRICAS FINAIS
    return True, df_novo


# --- OTIMIZAÇÃO CHAVE DE PERFORMANCE: Cache para processamento de dados ---
@st.cache_data(show_spinner="Processando e inferindo tipos de dados...")
def inferir_e_converter_tipos(df, colunas_texto=None, colunas_moeda=None):
    df_copy = df.copy() 
    
    # Processa Colunas de Moeda (Força para float64)
    if colunas_moeda:
        for col in colunas_moeda:
            if col in df_copy.columns:
                try:
                    # Remove R$, ponto de milhar e substitui vírgula decimal por ponto
                    s = df_copy[col].astype(str).str.replace(r'[R$]', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                    df_copy[col] = pd.to_numeric(s, errors='coerce').astype('float64')
                except Exception:
                    pass 
    
    # Processa Colunas de Texto (Força para string)
    if colunas_texto:
        for col in colunas_texto:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].fillna('').astype(str)
                
    # Inferência de Data/Hora e String para o restante
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
    """Retorna as colunas numéricas e de data baseadas nos tipos de dados."""
    colunas_numericas = df.select_dtypes(include=np.number).columns.tolist()
    colunas_data = df.select_dtypes(include=['datetime64']).columns.tolist()
    return colunas_numericas, colunas_data

# --- Configuração do Layout Streamlit ---

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


# --- Barra Lateral: Upload e Configurações de Tipos (Layout Limpo e Funcional) ---
with st.sidebar:
    
    st.markdown("# 📊")
    st.title("⚙️ Configurações do Expert")
    
    if st.button("Limpar Cache de Dados"):
        st.cache_data.clear()
        # Limpa o estado da sessão completamente
        for key in list(st.session_state.keys()):
            if not key.startswith('_'): # Mantém chaves internas do Streamlit
                del st.session_state[key]
        st.info("Cache de dados e estado da sessão limpos! Recarregando...")
        st.rerun()

    st.header("1. Upload e Processamento de Dados")
    
    uploaded_file = st.file_uploader("📥 Carregar Novo CSV/XLSX", type=['csv', 'xlsx'])
    
    df_novo = pd.DataFrame()
    
    if uploaded_file is not None:
        try:
            # --- LEITURA DO ARQUIVO (ROBUSTA) ---
            if uploaded_file.name.endswith('.csv'):
                uploaded_file.seek(0)
                try:
                    df_novo = pd.read_csv(uploaded_file, sep=';', decimal=',', encoding='utf-8')
                except:
                    uploaded_file.seek(0)
                    df_novo = pd.read_csv(uploaded_file, sep=',', decimal='.', encoding='utf-8')
                    
            elif uploaded_file.name.endswith('.xlsx'):
                df_novo = pd.read_excel(uploaded_file)
            
            # VERIFICAÇÃO DE DADOS CARREGADOS
            if df_novo.empty:
                st.error("O arquivo carregado está vazio ou não pôde ser lido corretamente.")
                st.session_state.dados_atuais = pd.DataFrame() 
                raise ValueError("DataFrame vazio após leitura.")
            
            df_novo.columns = df_novo.columns.str.strip()
            colunas_disponiveis = df_novo.columns.tolist()
            st.info(f"Arquivo carregado! ({len(df_novo)} linhas)")
            
            # --- AJUSTE DE TIPOS E SELEÇÃO MANUAL DE COLUNAS ---
            st.subheader("🛠️ Configuração de Colunas")
            
            # Heurística inicial para Moeda
            moeda_default = [col for col in colunas_disponiveis if any(word in col.lower() for word in ['valor', 'salario', 'custo', 'receita', 'montante'])]
            
            # --------------------- COLUNAS MOEDA (VOLTA AO SIMPLES) ---------------------
            st.markdown("##### 💰 Colunas de VALOR (R$)")
            colunas_moeda = st.multiselect(
                "Selecione:", 
                options=colunas_disponiveis, 
                default=moeda_default,
                label_visibility="collapsed",
                key='moeda_select_config' # Nova chave para evitar conflito
            )
            st.markdown("---")

            # --------------------- COLUNAS TEXTO (VOLTA AO SIMPLES) ---------------------
            st.markdown("##### 📝 Colunas TEXTO/ID")
            colunas_texto = st.multiselect(
                "Selecione:", 
                options=colunas_disponiveis, 
                default=[],
                label_visibility="collapsed",
                key='texto_select_config' # Nova chave para evitar conflito
            )
            st.markdown("---")
                                           
            # Realiza o processamento e a conversão de tipos (usando cache)
            df_processado = inferir_e_converter_tipos(df_novo, colunas_texto, colunas_moeda)
            
            # SELEÇÃO MANUAL DAS COLUNAS DE FILTRO (Categóricas)
            colunas_para_filtro_options = df_processado.select_dtypes(include=['object', 'category']).columns.tolist()
            
            # Heurística inicial para filtros
            filtro_default = [c for c in colunas_para_filtro_options if c.lower() in ['tipo', 'situacao', 'empresa', 'departamento']]

            # --------------------- COLUNAS FILTROS (VOLTA AO SIMPLES) ---------------------
            st.markdown("##### ⚙️ Colunas para FILTROS")
            colunas_para_filtro = st.multiselect(
                "Selecione:",
                options=colunas_para_filtro_options,
                default=filtro_default,
                label_visibility="collapsed",
                key='filtros_select_config' # Nova chave para evitar conflito
            )
            
            # Encontra as colunas NUMÉRICAS REAIS APÓS A CONVERSÃO
            colunas_valor_dashboard = df_processado.select_dtypes(include=np.number).columns.tolist()
            
            st.markdown("---")
            
            if st.button("✅ Processar e Exibir Dados Atuais"): 
                # VERIFICAÇÃO PRINCIPAL PARA EVITAR A MENSAGEM DE ERRO
                if df_processado.empty:
                    st.error("O DataFrame está vazio após o processamento. Verifique o conteúdo do arquivo e as seleções de coluna.")
                elif not colunas_para_filtro:
                    st.warning("Selecione pelo menos uma coluna na seção 'Colunas para FILTROS' para prosseguir.")
                else:
                    sucesso, df_processado_salvo = processar_dados_atuais( 
                        df_processado, 
                        colunas_para_filtro, 
                        colunas_valor_dashboard 
                    )
                    
                    if sucesso:
                        st.success("Dados processados e prontos para análise!")
                        st.balloons()
                        
                        limpar_filtros_salvos() 
                        st.session_state.df_filtrado = df_processado_salvo 
                        st.rerun()  
        except ValueError as ve:
             st.error(f"Erro de Validação: {ve}")
        except Exception as e:
            st.error(f"Erro no processamento do arquivo. Tente novamente ou verifique o formato: {e}")

# --- Dashboard Interativo ---

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

    # ----------------------------------------------------
    # CONTROLES GERAIS (MÉTRICA E RESET) - OTIMIZAÇÃO VISUAL
    # ----------------------------------------------------
    
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
                
        coluna_metrica_principal = st.selectbox(
            "Métrica de Valor Principal para KPI e Gráficos:",
            options=colunas_valor_metricas,
            index=default_metric_index,
            key='metrica_principal_selectbox',
            help="Selecione a coluna numérica principal para o cálculo de KPIs e para o Eixo Y dos gráficos.",
        )
        
    with col_reset_btn:
        st.markdown("###### ") 
        if st.button("🗑️ Resetar Filtros", help="Redefine todas as seleções de filtro para o estado inicial."):
            limpar_filtros_salvos()
            st.rerun() 
        
    st.markdown("---") 
        
    # ----------------------------------------------------
    # FILTROS DE ANÁLISE (Otimizado com 3 Expanders por linha e Botões Selecionar Tudo)
    # ----------------------------------------------------
    
    st.markdown("#### 🔍 Filtros de Análise Rápida")
    
    current_selections = {}
    form_key = f'dashboard_filters_form_{st.session_state.filtro_reset_trigger}' 
    
    # Criando o formulário para agrupar o botão de aplicação
    with st.form(key=form_key):
        
        colunas_filtro_a_exibir = colunas_categoricas_filtro 
        
        cols_container = st.columns(3) 
        
        # Lógica para distribuir os filtros em 3 colunas
        filtros_col_1 = colunas_filtro_a_exibir[::3]
        filtros_col_2 = colunas_filtro_a_exibir[1::3]
        filtros_col_3 = colunas_filtro_a_exibir[2::3]
        
        # Função interna para renderizar o filtro com botões (para DRY e callbacks)
        def render_filter_with_buttons(col, container):
            if col not in df_analise_base.columns: return

            opcoes_unicas = sorted(df_analise_base[col].astype(str).fillna('').unique().tolist())
            
            with container.expander(f"**{col}** ({len(opcoes_unicas)} opções)"):
                
                # --- Botões Selecionar/Limpar (USAM OS CALLBACKS set_multiselect_all/none) ---
                col_sel, col_clr = st.columns(2)
                with col_sel:
                    # O CALLBACK set_multiselect_all SALVA A SELEÇÃO NO session_state E FORÇA UM RERUN
                    st.button("✅ Selecionar Tudo", 
                              on_click=set_multiselect_all, 
                              args=(col, opcoes_unicas), 
                              key=f'sel_all_{col}_{st.session_state.filtro_reset_trigger}', 
                              use_container_width=True)
                with col_clr:
                    # O CALLBACK set_multiselect_none LIMPA A SELEÇÃO NO session_state E FORÇA UM RERUN
                    st.button("🗑️ Limpar", 
                              on_click=set_multiselect_none, 
                              args=(col,), 
                              key=f'clr_{col}_{st.session_state.filtro_reset_trigger}', 
                              use_container_width=True)
                st.markdown("---")
                
                # Inicializa o estado se for a primeira vez
                if f'filtro_key_{col}' not in st.session_state: st.session_state[f'filtro_key_{col}'] = []
                
                # Usa o estado salvo para o default (importante para o rerun dos callbacks)
                selecao_padrao_form = st.session_state.get(f'filtro_key_{col}', [])
                multiselect_key = f'multiselect_{col}_{st.session_state.filtro_reset_trigger}'
                
                selecao = st.multiselect("Selecione:", 
                                         options=opcoes_unicas, 
                                         default=selecao_padrao_form, 
                                         key=multiselect_key, 
                                         label_visibility="collapsed")
                
                current_selections[col] = selecao 

        # Renderiza a primeira coluna de filtros
        with cols_container[0]:
            for col in filtros_col_1:
                render_filter_with_buttons(col, cols_container[0])

        # Renderiza a segunda coluna de filtros
        with cols_container[1]:
             for col in filtros_col_2:
                render_filter_with_buttons(col, cols_container[1])
                    
        # Renderiza a terceira coluna de filtros
        with cols_container[2]:
             for col in filtros_col_3:
                render_filter_with_buttons(col, cols_container[2])
                
        
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
                    data_range = st.slider("", 
                                           min_value=data_min.to_pydatetime(), 
                                           max_value=data_max.to_pydatetime(),
                                           value=default_date_range,
                                           format="YYYY/MM/DD",
                                           key=slider_key,
                                           label_visibility="collapsed")
                    current_selections[col_data_padrao] = data_range
                except Exception:
                    st.warning("Erro na exibição do filtro de data.")

        st.markdown("---")
        submitted = st.form_submit_button("✅ Aplicar Filtros ao Dashboard", use_container_width=True)


    if submitted:
        # Salva o estado dos filtros que foram alterados ou estão visíveis
        for col in colunas_categoricas_filtro:
            if col in current_selections:
                st.session_state[f'filtro_key_{col}'] = current_selections[col] 
                
        if colunas_data and colunas_data[0] in current_selections:
            col_data_padrao = colunas_data[0]
            data_range = current_selections[col_data_padrao]
            st.session_state[f'date_range_key_{col_data_padrao}'] = data_range 
        st.rerun() 

    # ----------------------------------------------------
    # APLICAÇÃO DA FILTRAGEM
    # ----------------------------------------------------
    
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

    # Monta a lista de filtros ativos (seleções atuais)
    filtros_ativos = {}
    for col in colunas_categoricas_filtro:
        selecao = st.session_state.get(f'filtro_key_{col}')
        if selecao is not None and len(selecao) > 0:
             filtros_ativos[col] = selecao
            
    data_range_ativo = st.session_state.get(f'date_range_key_{colunas_data[0]}', None) if colunas_data else None

    # Aplica os filtros (com cache)
    df_analise = aplicar_filtros(
        df_analise_base, 
        colunas_categoricas_filtro, 
        filtros_ativos, 
        colunas_data, 
        data_range_ativo
    )

    st.session_state.df_filtrado = df_analise
    
    st.caption(f"Análise baseada em **{len(df_analise)}** registros filtrados do arquivo atual.") 
    st.markdown("---")
    
    # ----------------------------------------------------
    # LÓGICA DE APROFUNDAMENTO DINÂMICO
    # ----------------------------------------------------
    
    # Encontra o filtro mais restrito (A Chave de Aprofundamento)
    chave_aprofundamento = None
    valor_aprofundamento = None
    
    # Lista de colunas que têm APENAS UM item selecionado (para foco)
    filtros_focados = []
    for col, selecao in filtros_ativos.items():
        if len(selecao) == 1:
            filtros_focados.append((col, selecao[0]))
    
    # Escolhe a primeira coluna focada como a Chave de Aprofundamento
    if filtros_focados:
        chave_aprofundamento, valor_aprofundamento = filtros_focados[0]
        
    # Coluna numérica para o resumo (Total de Salário/Valor)
    col_resumo_valor = coluna_valor_principal if coluna_valor_principal != 'Contagem de Registros' else None

    # ----------------------------------------------------
    # MÉTRICAS CHAVE (Gerais)
    # ----------------------------------------------------
    
    st.subheader("🌟 Métricas Chave")
    
    col_metric_1, col_metric_2, col_metric_3, col_metric_4 = st.columns(4)
    
    coluna_metrica_principal = st.session_state.get('metrica_principal_selectbox')
    
    if not df_analise.empty:
        contagem = len(df_analise)
        col_metric_3.metric("Registros Filtrados", formatar_numero(contagem))
        col_metric_4.metric("Col. Principal", coluna_metrica_principal)
        
        if coluna_metrica_principal != 'Contagem de Registros' and coluna_metrica_principal in colunas_numericas_salvas:
            total_valor = df_analise[coluna_metrica_principal].sum()
            col_metric_1.metric(f"Total Acumulado", formatar_moeda(total_valor), help=f"Soma total da coluna: {coluna_metrica_principal}")
            media_valor = df_analise[coluna_metrica_principal].mean()
            col_metric_2.metric(f"Média por Registro", formatar_moeda(media_valor))
        else:
            col_metric_1.metric("Total Acumulado", formatar_numero(contagem))
            col_metric_2.metric("Média por Registro", "N/A - Contagem") 
            
    else:
        col_metric_1.warning("Dados não carregados ou vazios.")
        st.markdown("---")


    # ----------------------------------------------------
    # MÉTRICAS AVANÇADAS (Aprofundamento Dinâmico)
    # ----------------------------------------------------

    if chave_aprofundamento and col_resumo_valor and not df_analise.empty:
        st.markdown("---")
        st.subheader(f"🧠 Análise Focada: {valor_aprofundamento} ({chave_aprofundamento})")
        
        df_foco = df_analise.copy()
        
        # 1. KPIs Focados
        contagem_foco = len(df_foco)
        total_foco = df_foco[col_resumo_valor].sum()
        media_foco = df_foco[col_resumo_valor].mean()
        
        col_foco_1, col_foco_2, col_foco_3, col_foco_4 = st.columns(4)
        
        col_foco_1.metric(f"Contagem em '{chave_aprofundamento}'", formatar_numero(contagem_foco))
        col_foco_2.metric(f"Total de {col_resumo_valor}", formatar_moeda(total_foco))
        col_foco_3.metric(f"Média de {col_resumo_valor}", formatar_moeda(media_foco))
        col_foco_4.metric(f"Outros Filtros Ativos", str(len(filtros_ativos) - len(filtros_focados)))
        
        st.markdown("---")
        
        # 2. Resumo por Sub-Agrupamento
        
        # Encontra a próxima coluna categórica mais relevante
        colunas_restantes = [c for c in colunas_categoricas_filtro if c != chave_aprofundamento]
        
        if colunas_restantes:
            col_sub_agrupamento = colunas_restantes[0]
            st.markdown(f"##### Detalhe por {col_sub_agrupamento}")

            # Agregação por Sub-Agrupamento
            df_resumo = df_foco.groupby(col_sub_agrupamento).agg(
                Contagem=('index', 'size'),
                Total_Valor=(col_resumo_valor, 'sum'),
                Media_Valor=(col_resumo_valor, 'mean')
            ).reset_index()
            
            # Ordenar pela maior Contagem ou Total
            df_resumo = df_resumo.sort_values(by='Total_Valor', ascending=False)
            
            # Formatação para exibição
            df_resumo['Total_Valor'] = df_resumo['Total_Valor'].apply(formatar_moeda)
            df_resumo['Media_Valor'] = df_resumo['Media_Valor'].apply(formatar_moeda)
            
            # Renomear colunas
            df_resumo.columns = [col_sub_agrupamento, 'Contagem', f'Total de {col_resumo_valor}', f'Média de {col_resumo_valor}']
            
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
            
        else:
            st.info(f"Nenhuma outra coluna de filtro disponível para detalhar {valor_aprofundamento}.")

    elif len(df_analise) < len(df_analise_base):
        st.markdown("---")
        st.info("Para ativar a **Análise Focada**, selecione **apenas um valor** em um dos filtros (ex: apenas 'Empresa X').")

    
    st.markdown("---")
    
    # ----------------------------------------------------
    # GRÁFICOS (Sem Alteração) 
    # ----------------------------------------------------
    
    st.subheader("📈 Análise Visual (Gráficos) ")

    col_graph_1, col_graph_2 = st.columns(2)
    
    opcoes_graficos_base = [
        'Comparação (Barra)', 'Composição (Pizza)', 'Série Temporal (Linha)', 'Distribuição (Histograma)', 'Estatística Descritiva (Box Plot)'
    ]
    
    coluna_x_fixa = coluna_agrupamento_principal if coluna_agrupamento_principal else 'Nenhuma Chave Categórica Encontrada' 
    coluna_y_fixa = coluna_metrica_principal
        
    
    # Gráfico 1 - Foco no Agrupamento
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

    # Gráfico 2 - Foco em Tendência ou Distribuição
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

    # --- Tabela Detalhada (Otimizada) ---
    st.markdown("---")
    st.subheader("🔍 Detalhes dos Dados Filtrados")
    
    df_exibicao = df_analise.copy()
    
    # Cria uma cópia e aplica a formatação APENAS nas colunas de moeda identificadas, para o dataframe de exibição
    df_exibicao_formatado = df_exibicao.copy()
    for col in colunas_numericas_salvas:
         if col in df_exibicao_formatado.columns and any(word in col.lower() for word in ['valor', 'salario', 'custo', 'receita', 'montante']):
            df_exibicao_formatado[col] = df_exibicao_formatado[col].apply(formatar_moeda)

    # CHAVE DE OTIMIZAÇÃO: LIMITAR O NÚMERO DE LINHAS EXIBIDAS
    max_linhas_exibidas = 1000
    if len(df_exibicao_formatado) > max_linhas_exibidas:
        df_exibicao_limitado = df_exibicao_formatado.head(max_linhas_exibidas)
        st.info(f"Exibindo apenas as primeiras {max_linhas_exibidas} linhas para evitar travamento. Baixe o CSV para ver todos os {len(df_exibicao_formatado)} registros.")
    else:
        df_exibicao_limitado = df_exibicao_formatado
        
    st.dataframe(df_exibicao_limitado, use_container_width=True, hide_index=True)

    # Botão de download (usa o DF COMPLETO, NÃO FORMATADO)
    csv_data = df_analise.to_csv(index=False, sep=';', decimal=',', encoding='utf-8')
    st.download_button(
        label="📥 Baixar Dados Tratados (CSV)",
        data=csv_data,
        file_name=f'dados_analise_exportados_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
        mime='text/csv',
    )