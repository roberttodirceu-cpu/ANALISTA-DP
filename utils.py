import pandas as pd
import numpy as np

def formatar_moeda(valor):
    """Formata um valor numérico para o padrão de moeda (R$ com separador de milhar e duas casas decimais)."""
    if pd.isna(valor):
        return ''
    return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def inferir_e_converter_tipos(df, colunas_texto=None, colunas_moeda=None):
    df_copy = df.copy()
    # Processa Colunas de Moeda (Força para float64)
    if colunas_moeda:
        for col in colunas_moeda:
            if col in df_copy.columns:
                try:
                    s = df_copy[col].astype(str).str.replace(r'[R$]', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                    df_copy[col] = pd.to_numeric(s, errors='coerce').astype('float64')
                except Exception as e:
                    print(f"Erro ao converter coluna moeda {col}: {e}")
    # Processa Colunas de Texto (Força para string)
    if colunas_texto:
        for col in colunas_texto:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].fillna('').astype(str)
    # Inferência de Data/Hora e String para o restante
    for col in df_copy.columns:
        if col not in (colunas_moeda or []) and col not in (colunas_texto or []):
            if df_copy[col].dtype == 'object':
                try:
                    df_temp = pd.to_datetime(df_copy[col], errors='coerce', dayfirst=True)
                    if df_temp.notna().sum() > len(df_copy) * 0.5:
                        df_copy[col] = df_temp
                    else:
                        df_copy[col] = df_copy[col].astype(str).fillna('')
                except Exception as e:
                    print(f"Erro ao converter coluna data/texto {col}: {e}")
                    df_copy[col] = df_copy[col].astype(str).fillna('')
    return df_copy

def encontrar_colunas_tipos(df):
    colunas_numericas = df.select_dtypes(include=np.number).columns.tolist()
    colunas_data = df.select_dtypes(include=['datetime64']).columns.tolist()
    return colunas_numericas, colunas_data

def verificar_ausentes(df, colunas):
    resultado = {}
    for col in colunas:
        if col in df.columns:
            ausentes = df[col].isna().sum()
            total = len(df)
            if ausentes > 0:
                resultado[col] = (ausentes, total)
    return resultado
