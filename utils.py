import pandas as pd
import numpy as np
from datetime import datetime

def formatar_moeda(valor):
    """Formata um valor numérico para o formato de moeda brasileira (R$)."""
    if pd.isna(valor):
        return ""
    # Evita problemas de arredondamento excessivo, mas permite valores grandes.
    try:
        # Formatação para o padrão BR: ponto como separador de milhares e vírgula como decimal
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return str(valor)

def inferir_e_converter_tipos(df, colunas_texto, colunas_moeda):
    """
    Tenta converter colunas para os tipos corretos (texto para string, moeda para float).
    """
    df_copia = df.copy()

    # 1. Colunas de Texto/ID
    for col in colunas_texto:
        if col in df_copia.columns:
            # Converte para string, remove espaços e trata NaN como 'N/A'
            df_copia[col] = df_copia[col].astype(str).str.strip().fillna('N/A')

    # 2. Colunas de Moeda (Valor)
    for col in colunas_moeda:
        if col in df_copia.columns:
            # Tenta forçar para numérico, convertendo valores que não podem ser lidos para NaN
            df_copia[col] = pd.to_numeric(df_copia[col], errors='coerce')

    # 3. Colunas Categóricas (Filtros)
    # Converte colunas de 'object' (que não são data/hora e têm baixa cardinalidade) para 'category'
    for col in df_copia.select_dtypes(include=['object']).columns:
        # Não converte colunas que o usuário marcou explicitamente como texto/ID
        if col not in colunas_texto: 
             # Critério de baixa cardinalidade (menos de 50% de valores únicos em relação ao total de linhas)
             if df_copia[col].nunique() < df_copia.shape[0] * 0.5: 
                df_copia[col] = df_copia[col].astype('category')

    return df_copia

def encontrar_colunas_tipos(df):
    """Retorna listas de colunas numéricas e de data/hora."""
    colunas_numericas = df.select_dtypes(include=np.number).columns.tolist()
    colunas_data = df.select_dtypes(include=['datetime64']).columns.tolist()
    return colunas_numericas, colunas_data

def verificar_ausentes(df, colunas_para_filtro):
    """Verifica e retorna um dicionário com colunas de filtro que contêm valores NaN ou vazios."""
    ausentes = {}
    for col in colunas_para_filtro:
        if col in df.columns:
            # Conta NaN/NaT e strings vazias (após remover espaços)
            n_ausentes = df[col].isnull().sum() + (df[col].astype(str).str.strip() == '').sum()
            if n_ausentes > 0:
                ausentes[col] = (n_ausentes, len(df)) # (Número de ausentes, Total de linhas)
    return ausentes

# Fim do utils.py
