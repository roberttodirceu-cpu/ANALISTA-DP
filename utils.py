import pandas as pd
import numpy as np
import locale

# --- Configuração de Locale para Moeda (necessário para formatar_moeda) ---
# Tenta configurar o locale para Português do Brasil, necessário para formatar_moeda
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        # Tenta a alternativa comum no Windows
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        # Define um fallback, mas a formatação de moeda pode não ser a ideal
        print("Aviso: Não foi possível configurar o locale 'pt_BR.UTF-8' ou 'Portuguese_Brazil.1252'.")
        pass


def formatar_moeda(valor):
    """Formata um valor numérico para o padrão monetário brasileiro (R$)."""
    if pd.isna(valor) or not np.isfinite(valor):
        return "R$ 0,00"
    try:
        # Usa o locale configurado
        return locale.currency(valor, symbol='R$', grouping=True)
    except Exception:
        # Fallback manual em caso de falha de locale
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
            # Tenta converter para string, substitui vírgula por ponto, e converte para float
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
        # Colunas com poucos valores únicos (e que não são data, float ou int) viram 'category'
        if df_temp[col].dtype == 'object' or (df_temp[col].nunique() / len(df_temp) < 0.1 and df_temp[col].nunique() < 50 and df_temp[col].dtype != 'datetime64[ns]'):
            try:
                # Tenta conversão forçada para categoria para otimizar memória/filtros
                if df_temp[col].dtype != 'category':
                    df_temp[col] = df_temp[col].astype(str).astype('category')
            except:
                pass # Ignora se falhar
                
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
