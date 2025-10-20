import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================================
# FUNÇÕES DE FORMATAÇÃO
# ==========================================================

def formatar_moeda(valor):
    """Formata um valor numérico para o padrão de moeda (BRL)."""
    if pd.isna(valor) or valor is None:
        return "R$ 0,00"
    try:
        # Garante que o valor é float antes de formatar
        valor = float(valor)
        return f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except (ValueError, TypeError):
        return "R$ Inválido"

# ==========================================================
# FUNÇÕES DE TRATAMENTO DE DADOS E TIPAGEM
# ==========================================================

def encontrar_colunas_tipos(df: pd.DataFrame) -> tuple[list, list]:
    """
    Identifica colunas que parecem ser de Data/Hora.
    Retorna uma tupla: (lista_colunas_string, lista_colunas_datetime).
    """
    colunas_data = []
    colunas_texto = []
    
    for col in df.columns:
        # Tenta identificar colunas de data/hora
        if df[col].dtype == 'object':
            # Tenta inferir se mais de 50% dos não-nulos são datas
            try:
                # Cria uma cópia temporária da série não-nula para evitar SettingWithCopyWarning
                s_temp = df[col].dropna().copy()
                s_temp = pd.to_datetime(s_temp, errors='coerce', dayfirst=True)
                
                # Se mais da metade dos valores foram convertidos com sucesso
                if s_temp.notna().sum() / len(df[col].dropna()) > 0.5:
                    colunas_data.append(col)
                else:
                    colunas_texto.append(col)
            except Exception:
                colunas_texto.append(col)
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            colunas_data.append(col)
        
    return colunas_texto, colunas_data

def inferir_e_converter_tipos(df: pd.DataFrame, colunas_texto: list, colunas_moeda: list) -> pd.DataFrame:
    """
    Converte colunas para os tipos inferidos (Moeda, Texto/ID, Data).
    """
    df_copia = df.copy()
    
    # 1. Converter colunas de Moeda para float (numérico)
    for col in colunas_moeda:
        if col in df_copia.columns:
            # Garante que números em formato texto (ex: '1.000,50') sejam lidos corretamente
            try:
                # Remove separador de milhar '.' e substitui vírgula ',' por ponto '.'
                df_copia[col] = df_copia[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df_copia[col] = pd.to_numeric(df_copia[col], errors='coerce')
            except Exception:
                df_copia[col] = pd.to_numeric(df_copia[col], errors='coerce')
    
    # 2. Converter colunas de Texto/ID para string (e depois category para otimização)
    for col in colunas_texto:
        if col in df_copia.columns:
            # Preenche NaN com string vazia e converte para category
            df_copia[col] = df_copia[col].astype(str).fillna('').str.strip().astype('category')

    # 3. Converter colunas de Data/Hora (inferir automaticamente)
    _, colunas_data = encontrar_colunas_tipos(df_copia)
    for col in colunas_data:
        if col in df_copia.columns:
            # Converte para datetime, forçando dia primeiro (padrão Brasil)
            df_copia[col] = pd.to_datetime(df_copia[col], errors='coerce', dayfirst=True)
            
    return df_copia

# ==========================================================
# FUNÇÕES DE VALIDAÇÃO E ERROS (CORREÇÃO DO VALUERROR)
# ==========================================================

def verificar_ausentes(df: pd.DataFrame, colunas_para_filtro: list) -> dict:
    """
    Verifica a contagem de valores ausentes (NaN/None) nas colunas de filtro.
    Retorna um dicionário {coluna: (n_ausentes, total_linhas)} para colunas com ausentes.
    
    CORREÇÃO: Retorna um dicionário, evitando o ValueError ambíguo do Pandas.
    """
    ausentes_info = {}
    total_linhas = len(df)
    
    for col in colunas_para_filtro:
        if col in df.columns:
            # Conta o número de NaNs
            n_ausentes = df[col].isnull().sum()
            
            if n_ausentes > 0:
                # Armazena o número de ausentes e o total de linhas para a mensagem de aviso
                ausentes_info[col] = (n_ausentes, total_linhas) 
                
    return ausentes_info
