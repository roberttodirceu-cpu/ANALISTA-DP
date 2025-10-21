import pandas as pd
import numpy as np
from datetime import datetime

def formatar_moeda(valor):
    """Formata um valor numérico para o formato de moeda brasileira (R$)."""
    if pd.isna(valor):
        return ""
    # Formatação para o padrão BR: ponto como separador de milhares e vírgula como decimal
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return str(valor)

def inferir_e_converter_tipos(df, colunas_texto, colunas_moeda):
    """
    Tenta converter colunas para os tipos corretos (texto para string, moeda para float).
    Inclui limpeza robusta para números em formato BR (1.000,00).
    """
    df_copia = df.copy()

    # 1. Colunas de Texto/ID
    for col in colunas_texto:
        if col in df_copia.columns:
            df_copia[col] = df_copia[col].astype(str).str.strip().fillna('N/A')

    # 2. Colunas de Moeda (Valor) - CORREÇÃO DE LIMPEZA
    for col in colunas_moeda:
        if col in df_copia.columns:
            if df_copia[col].dtype == 'object' or (df_copia[col].dtype != np.number):
                # 1. Remove pontos de milhares
                # 2. Substitui vírgula por ponto decimal
                df_copia[col] = (
                    df_copia[col].astype(str)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)
                )

            # Tenta forçar para numérico. 
            df_copia[col] = pd.to_numeric(df_copia[col], errors='coerce')

    # 3. Colunas Categóricas
    for col in df_copia.select_dtypes(include=['object']).columns:
        if col not in colunas_texto: 
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
            n_ausentes = df[col].isnull().sum() + (df[col].astype(str).str.strip() == '').sum()
            if n_ausentes > 0:
                ausentes[col] = (n_ausentes, len(df))
    return ausentes
