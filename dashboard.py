# app.py

# ... [Mantenha todas as importações e funções auxiliares (load_catalog, switch_dataset, limpar_filtros_salvos, etc.) da versão anterior] ...
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
from datetime import datetime
from io import BytesIO
import pickle 
# IMPORTAÇÃO DE FUNÇÕES ESSENCIAIS DO UTILS.PY
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

# ... [Mantenha a inicialização de Estado da Sessão] ...
if 'data_sets_catalog' not in st.session_state: st.session_state.data_sets_catalog = load_catalog()
if 'filtro_reset_trigger' not in st.session_state: st.session_state['filtro_reset_trigger'] = 0
# ... [Código de inicialização do estado omitido por brevidade] ...
# ... [Código de inicialização do estado omitido por brevidade] ...

# --- Aplicação de Filtros (Função Caching - Mantida) ---
@st.cache_data(show_spinner="Aplicando filtros de Base e Comparação...")
def aplicar_filtros_comparacao(df_base, col_filtros, filtros_ativos_base, filtros_ativos_comp, col_data, data_range_base, data_range_comp, trigger):
    # [Manter a função _aplicar_filtro_single e o corpo principal da função da versão anterior]
    def _aplicar_filtro_single(df, col_filtros_list, filtros_ativos_dict, col_data, data_range):
        df_filtrado_temp = df.copy()
        
        # 1. Filtros Categóricos
        for col in col_filtros_list:
            selecao = filtros_ativos_dict.get(col)
            # Garantir que só aplique se a coluna existir no DF
            if col not in df_filtrado_temp.columns: continue

            opcoes_unicas = df_base[col].astype(str).fillna('N/A').unique().tolist()
            
            # CORREÇÃO: Aplica filtro SOMENTE se a seleção não estiver vazia E não for total
            if selecao and len(selecao) > 0 and len(selecao) < len(opcoes_unicas): 
                df_filtrado_temp = df_filtrado_temp[df_filtrado_temp[col].astype(str).isin(selecao)]
        
        # 2. Filtro de Data
        if data_range and len(data_range) == 2 and col_data and col_data[0] in df_filtrado_temp.columns:
            col_data_padrao = col_data[0]
            df_filtrado_temp[col_data_padrao] = pd.to_datetime(df_filtrado_temp[col_data_padrao], errors='coerce')
            
            data_min_df = df_base[col_data_padrao].min()
            data_max_df = df_base[col_data_padrao].max()
            
            # Aplica filtro de data APENAS se o intervalo selecionado for diferente do intervalo total do DF
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


# --- NOVO: FUNÇÃO PARA TABELA DE RESUMO E MÉTRICAS "EXPERT" ---

def gerar_analise_expert(df_completo, df_base, df_comp, filtros_ativos_base, filtros_ativos_comp, colunas_data, data_range_base, data_range_comp):
    """
    Gera uma apresentação visualmente atraente do resumo de métricas chave,
    incluindo Contagem de Funcionários, Vencimentos e Descontos.
    """
    
    colunas_valor_salvas = st.session_state.colunas_valor_salvas
    
    # -------------------------------------------------------------
    # 1. ANÁLISE DE CONTEXTO E RÓTULOS DETALHADOS
    # -------------------------------------------------------------
    st.markdown("#### 📝 Contexto do Filtro Ativo")
    
    # Rótulos de contexto
    rotulo_base = gerar_rotulo_filtro(df_completo, filtros_ativos_base, colunas_data, data_range_base)
    rotulo_comp = gerar_rotulo_filtro(df_completo, filtros_ativos_comp, colunas_data, data_range_comp)

    st.markdown(f"""
        <div style="padding: 10px; border: 1px solid #007bff; border-radius: 5px; margin-bottom: 15px; background-color: #e9f7ff;">
            <p style="margin: 0; font-weight: bold; font-size: 16px;"><span style="color: #007bff;">BASE (Referência):</span></p>
            <p style="margin: 0; font-size: 14px;">{rotulo_base}</p>
        </div>
        <div style="padding: 10px; border: 1px solid #6f42c1; border-radius: 5px; margin-bottom: 20px; background-color: #f6f0ff;">
            <p style="margin: 0; font-weight: bold; font-size: 16px;"><span style="color: #6f42c1;">COMPARAÇÃO (Alvo):</span></p>
            <p style="margin: 0; font-size: 14px;">{rotulo_comp}</p>
        </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 2. CALCULO DE VENCIMENTOS E DESCONTOS
    # -------------------------------------------------------------
    
    # Assumimos que 'T' é a coluna de Tipo de Evento (C=Crédito/Vencimento, D=Débito/Desconto)
    col_tipo_evento = 't' # Ou 'tipo_evento' se o nome for alterado
    col_valor = 'valor' # Coluna principal de valor (que agora deve estar correta)
    col_func = 'nome_funcionario' # Coluna para contagem de únicos
    
    if col_tipo_evento not in df_completo.columns or col_valor not in df_completo.columns:
        st.error(f"Erro de Análise: Colunas '{col_tipo_evento}' ou '{col_valor}' não encontradas no DataFrame.")
        return

    def calcular_venc_desc(df):
        if df.empty:
            return 0, 0, 0
            
        # Filtra registros com valor e tipo definidos
        df_clean = df.dropna(subset=[col_valor, col_tipo_evento])

        # Vencimentos (T='C' - Crédito)
        vencimentos = df_clean[df_clean[col_tipo_evento] == 'C'][col_valor].sum()
        
        # Descontos (T='D' - Débito)
        # Usamos o valor absoluto pois os valores na planilha são geralmente positivos, 
        # e o tipo 'D' indica que é um desconto.
        descontos = df_clean[df_clean[col_tipo_evento] == 'D'][col_valor].sum()
        
        # Líquido (Vencimentos - Descontos)
        liquido = vencimentos - descontos

        return vencimentos, descontos, liquido

    # Base
    venc_base, desc_base, liq_base = calcular_venc_desc(df_base)
    func_base = df_base[col_func].nunique() if col_func in df_base.columns else 0
    
    # Comparação
    venc_comp, desc_comp, liq_comp = calcular_venc_desc(df_comp)
    func_comp = df_comp[col_func].nunique() if col_func in df_comp.columns else 0
    
    # Total Geral
    venc_total, desc_total, liq_total = calcular_venc_desc(df_completo)
    func_total = df_completo[col_func].nunique() if col_func in df_completo.columns else 0


    # -------------------------------------------------------------
    # 3. APRESENTAÇÃO DOS KPIS DE VENCIMENTOS E DESCONTOS (CARDS)
    # -------------------------------------------------------------
    st.markdown("##### 💰 Resumo Financeiro da BASE (Referência)")
    col1, col2, col3, col4 = st.columns(4)

    # KPI 1: Contagem de Funcionários (Base)
    col1.metric(
        label=f"Funcionários Únicos ({func_total})", 
        value=f"{func_base:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."), 
        delta=f"Variação: {func_comp - func_base:,.0f}"
    )

    # KPI 2: Total de Vencimentos (Base)
    col2.metric(
        label=f"Total Vencimentos ({formatar_moeda(venc_total)})", 
        value=formatar_moeda(venc_base), 
        delta=formatar_moeda(venc_comp - venc_base).replace('R$', '')
    )

    # KPI 3: Total de Descontos (Base)
    col3.metric(
        label=f"Total Descontos ({formatar_moeda(desc_total)})", 
        value=formatar_moeda(desc_base), 
        delta=formatar_moeda(desc_comp - desc_base).replace('R$', '')
    )
    
    # KPI 4: Líquido (Base)
    col4.metric(
        label=f"Valor Líquido ({formatar_moeda(liq_total)})", 
        value=formatar_moeda(liq_base), 
        delta=formatar_moeda(liq_comp - liq_base).replace('R$', '')
    )

    st.markdown("---")


    # -------------------------------------------------------------
    # 4. TABELA DE VARIAÇÃO DETALHADA (Inclui Vencimentos/Descontos)
    # -------------------------------------------------------------

    dados_resumo = []
    
    # 4.1. Adiciona Métricas Específicas
    
    # Contagem de Registros
    dados_resumo.append({'Métrica': 'CONT. DE REGISTROS', 'Total Geral': len(df_completo), 'Base (Filtrado)': len(df_base), 'Comparação (Filtrado)': len(df_comp), 'Tipo': 'Contagem'})
    
    # Contagem de Funcionários
    dados_resumo.append({'Métrica': 'CONT. DE FUNCIONÁRIOS ÚNICOS', 'Total Geral': func_total, 'Base (Filtrado)': func_base, 'Comparação (Filtrado)': func_comp, 'Tipo': 'Contagem'})

    # Vencimentos
    dados_resumo.append({'Métrica': 'TOTAL DE VENCIMENTOS (CRÉDITO)', 'Total Geral': venc_total, 'Base (Filtrado)': venc_base, 'Comparação (Filtrado)': venc_comp, 'Tipo': 'Moeda'})
    
    # Descontos
    dados_resumo.append({'Métrica': 'TOTAL DE DESCONTOS (DÉBITO)', 'Total Geral': desc_total, 'Base (Filtrado)': desc_base, 'Comparação (Filtrado)': desc_comp, 'Tipo': 'Moeda'})
    
    # Valor Líquido
    dados_resumo.append({'Métrica': 'VALOR LÍQUIDO (Venc - Desc)', 'Total Geral': liq_total, 'Base (Filtrado)': liq_base, 'Comparação (Filtrado)': liq_comp, 'Tipo': 'Moeda'})

    # 4.2. Adiciona Métricas Genéricas (Soma de Valores e Contagem Única) - Caso existam outras colunas de valor
    colunas_moeda = [col for col in colunas_valor_salvas if col not in ['valor']] # Exclui a principal para evitar duplicidade
    colunas_referencia = [col for col in colunas_valor_salvas if col not in colunas_moeda and col not in ['valor']] 

    for col in colunas_moeda:
        total_geral_soma = df_completo[col].sum()
        total_base_soma = df_base[col].sum()
        total_comp_soma = df_comp[col].sum()
        dados_resumo.append({'Métrica': f"SOMA: {col.upper()}", 'Total Geral': total_geral_soma, 'Base (Filtrado)': total_base_soma, 'Comparação (Filtrado)': total_comp_soma, 'Tipo': 'Moeda'})
        
    for col in colunas_referencia:
        total_geral_count = df_completo[col].nunique(dropna=True)
        total_base_count = df_base[col].nunique(dropna=True)
        total_comp_count = df_comp[col].nunique(dropna=True)
        dados_resumo.append({'Métrica': f"CONT. ÚNICOS: {col.upper()}", 'Total Geral': total_geral_count, 'Base (Filtrado)': total_base_count, 'Comparação (Filtrado)': total_comp_count, 'Tipo': 'Contagem'})
            
    df_resumo = pd.DataFrame(dados_resumo)
    
    # 4.3. Cálculo da Variação e Formatação da Tabela
    
    def calcular_variacao(row):
        base = row['Base (Filtrado)']
        comp = row['Comparação (Filtrado)']
        
        if base == 0:
            return 0 if comp == 0 else np.inf # N/A se ambos 0, Infinito se só a base 0
        return ((comp - base) / base) * 100

    df_resumo['Variação %'] = df_resumo.apply(calcular_variacao, axis=1)

    df_tabela = df_resumo.copy()
    
    # Formatação para o Total Geral e Filtrados
    def format_value(row, col_name):
        val = row[col_name]
        if row['Tipo'] == 'Moeda':
            return formatar_moeda(val)
        else:
            return f"{val:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
    df_tabela['TOTAL GERAL (Sem Filtro)'] = df_tabela.apply(lambda row: format_value(row, 'Total Geral'), axis=1)
    df_tabela['BASE (FILTRADO)'] = df_tabela.apply(lambda row: format_value(row, 'Base (Filtrado)'), axis=1)
    df_tabela['COMPARAÇÃO (FILTRADO)'] = df_tabela.apply(lambda row: format_value(row, 'Comparação (Filtrado)'), axis=1)

    # Formatação da Variação com Iconografia e Cor
    def format_variacao_tabela(val):
        if not np.isfinite(val):
            return '<span style="color: gray;">N/A</span>'
        
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

    st.markdown("##### 🔍 Comparativo Detalhado de Métricas Chave")
    st.markdown(df_final_exibicao.to_html(escape=False, index=False), unsafe_allow_html=True)


# --- Dashboard Principal (Fluxo de Chamadas) ---

# ... [Mantenha a estrutura do Dashboard Principal] ...

if st.session_state.dados_atuais.empty: 
    st.info("Sistema pronto. O Dashboard será exibido após carregar, processar e selecionar um Dataset.")
else:
    df_analise_completo = st.session_state.dados_atuais.copy()
    st.header(f"📊 Dashboard Expert de Análise de Indicadores ({st.session_state.current_dataset_name})")
    
    colunas_categoricas_filtro = st.session_state.colunas_filtros_salvas
    _, colunas_data = encontrar_colunas_tipos(df_analise_completo) 
    
    # -------------------------------------------------------------
    # 1. Painel de Filtros Simplificado (Render Filter Panel)
    # -------------------------------------------------------------
    # ... [Código de renderização dos filtros mantido] ...

    # [Código para chamar render_filter_panel e coletar filtros]
    st.markdown("#### 🔍 Configuração de Análise de Variação")
    col_reset_btn = st.columns([4, 1])[1]
    with col_reset_btn:
        st.button("🗑️ Resetar Filtros", on_click=limpar_filtros_salvos, use_container_width=True)
    
    tab_base, tab_comparacao = st.tabs(["Filtros da BASE (Referência)", "Filtros de COMPARAÇÃO (Alvo)"])

    # Chama a função de renderização (que define o estado dos filtros)
    filtros_ativos_base_render, data_range_base_render = render_filter_panel(tab_base, 'base', colunas_categoricas_filtro, df_analise_completo)
    filtros_ativos_comp_render, data_range_comp_render = render_filter_panel(tab_comparacao, 'comp', colunas_categoricas_filtro, df_analise_completo)
    
    st.session_state.active_filters_base = filtros_ativos_base_render
    st.session_state.active_filters_comp = filtros_ativos_comp_render
    
    st.markdown("---")
    submitted = st.button("✅ Aplicar Filtros e Rodar Comparação", use_container_width=True, type='primary')
    if submitted:
        st.session_state['filtro_reset_trigger'] += 1 
        st.rerun() 
        
    # Coleta de Filtros para Aplicação (usando o estado da sessão)
    filtros_ativos_base_cache = st.session_state.active_filters_base
    filtros_ativos_comp_cache = st.session_state.active_filters_comp
    
    data_range_base_cache = data_range_base_render
    data_range_comp_cache = data_range_comp_render

    # -------------------------------------------------------------
    # 2. Aplicação do Filtro (Cache)
    # -------------------------------------------------------------------------
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
    # 3. Exibição da Análise Expert Aprimorada (CHAMADA ATUALIZADA)
    # -------------------------------------------------------------
    st.subheader("🌟 Resumo de Métricas e Análise de Variação - Visão Expert")
    
    if not df_base_safe.empty or not df_comp_safe.empty:
        # Passa os filtros e ranges de data para a função de análise
        gerar_analise_expert(
            df_analise_completo, 
            df_base_safe, 
            df_comp_safe, 
            filtros_ativos_base_cache, 
            filtros_ativos_comp_cache, 
            colunas_data, 
            data_range_base_cache, 
            data_range_comp_cache
        )
    else:
        st.warning("Um ou ambos os DataFrames (Base/Comparação) estão vazios após a aplicação dos filtros. Ajuste seus critérios e clique em 'Aplicar Filtros'.")

    st.markdown("---")
    
    # -------------------------------------------------------------
    # 4. Detalhe dos Dados
    # -------------------------------------------------------------
    st.subheader("📚 Detalhe dos Dados Filtrados (Base)")
    st.dataframe(df_base_safe, use_container_width=True)
