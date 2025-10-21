import pandas as pd
import numpy as np
import locale

# --- Configuração de Locale para Moeda (necessário para formatar_moeda) ---
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        # Tenta a alternativa comum no Windows
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        print("Aviso: Não foi possível configurar o locale 'pt_BR.UTF-8' ou 'Portuguese_Brazil.1252'.")
        pass


def formatar_moeda(valor):
    """Formata um valor numérico para o padrão monetário brasileiro (R$)."""
    if pd.isna(valor) or not np.isfinite(valor):
        return "R$ 0,00"
    try:
        return locale.currency(valor, symbol='R$', grouping=True)
    except Exception:
        # Fallback manual
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def inferir_e_converter_tipos(df, colunas_texto_id, colunas_moeda):
    """
    Infernize os tipos de dados do DataFrame, convertendo colunas numéricas
    e garantindo que colunas de filtro sejam categóricas.
    """
    df_temp = df.copy()

    # 1. Converter Colunas de Moeda
    for col in colunas_moeda:
        if col in df_temp.columns:
            df_temp[col] = df_temp[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
            df_temp[col] = df_temp[col].fillna(0).astype(float) # Zera NaNs após conversão

    # 2. Converter Colunas de Texto/ID para string e depois para Categoria
    for col in colunas_texto_id:
        if col in df_temp.columns:
            df_temp[col] = df_temp[col].astype(str).str.strip()
            df_temp[col] = df_temp[col].astype('category')

    # 3. Inferência Geral e Conversão de Categóricos
    for col in df_temp.columns:
        if df_temp[col].dtype == 'object' or (df_temp[col].nunique() / len(df_temp) < 0.1 and df_temp[col].nunique() < 50 and df_temp[col].dtype != 'datetime64[ns]'):
            try:
                if df_temp[col].dtype != 'category':
                    df_temp[col] = df_temp[col].astype(str).astype('category')
            except:
                pass
                
    # 4. Ajuste Específico para MES/ANO: Devem ser categóricos/string para filtros
    for col in ['mes', 'ano']:
        if col in df_temp.columns:
            df_temp[col] = df_temp[col].astype(str).astype('category')


    return df_temp


def encontrar_colunas_tipos(df):
    """Identifica colunas numéricas e de data."""
    colunas_numericas = df.select_dtypes(include=np.number).columns.tolist()
    colunas_data = df.select_dtypes(include=['datetime64[ns]']).columns.tolist()
    return colunas_numericas, colunas_data


def verificar_ausentes(df, colunas_filtro):
    """Retorna um dicionário de colunas de filtro que contêm valores ausentes (NaN/None)."""
    ausentes = {}
    for col in colunas_filtro:
        if col in df.columns:
            nan_count = df[col].isnull().sum()
            if nan_count > 0:
                ausentes[col] = (nan_count, len(df))
    return ausentes

def gerar_rotulo_filtro(df_analise, filtros_ativos, col_data, data_range):
    """Gera uma string CONCISA para o cabeçalho do KPI."""
    rotulo_filtros = []
    
    # 1. Filtros Categóricos
    for col in filtros_ativos.keys():
        valores = filtros_ativos[col]
        if col in df_analise.columns:
            # Use the base DF to get all unique options correctly
            total_opcoes = len(df_analise[col].astype(str).fillna('N/A').unique().tolist())
            
            if valores and len(valores) > 0 and len(valores) < total_opcoes:
                
                col_display = col.replace('_', ' ').title()
                if len(valores) == 1:
                    rotulo_filtros.append(f"**{col_display}:** {valores[0]}")
                else:
                    rotulo_filtros.append(f"**{col_display}:** {len(valores)} itens")

    # 2. Filtro de Data
    if data_range and len(data_range) == 2 and col_data:
        # Assumindo col_data é uma lista com o nome da coluna de data
        col_data_padrao = col_data[0] 
        df_analise[col_data_padrao] = pd.to_datetime(df_analise[col_data_padrao], errors='coerce')
        
        data_min_df = df_analise[col_data_padrao].min()
        data_max_df = df_analise[col_data_padrao].max()

        # O rótulo só é adicionado se houver filtro de data
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
