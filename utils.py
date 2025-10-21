import pandas as pd
import numpy as np
from datetime import datetime
import re # Adicionado para garantir que o 're' está disponível para a regex

# --- 1. Funções de Formatação e Auxílio ---

def formatar_moeda(valor):
    """
    Formata um valor numérico para o padrão de moeda (BRL)
    com separador de milhar e duas casas decimais.
    Retorna 'R$ 0,00' se o valor for nulo (NaN).
    """
    if pd.isna(valor):
        return "R$ 0,00"
    
    # Converte para float, formata para string e substitui os separadores
    # Usa 'X' temporariamente para evitar conflito na troca de ponto por vírgula
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def encontrar_colunas_tipos(df):
    """
    Identifica as colunas de Data e as demais (numéricas/categóricas).
    """
    colunas_data = []
    outras_colunas = []
    
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            colunas_data.append(col)
        else:
            outras_colunas.append(col)
            
    return outras_colunas, colunas_data


def verificar_ausentes(df, colunas):
    """
    Verifica e retorna um dicionário com a contagem de valores ausentes (NaN ou strings vazias)
    por coluna, apenas para as colunas listadas. 
    A correção garante que a verificação é robusta para strings vazias.
    """
    ausentes = {}
    total_linhas = len(df)
    
    # Itera apenas sobre as colunas que foram selecionadas para filtro
    for col in colunas:
        if col in df.columns:
            # Conta o número de NaNs (inclui NaT para datas)
            n_nan = df[col].isnull().sum()
            
            # Conta o número de strings vazias ou apenas espaços
            n_vazio = 0
            # Adicionado o check para evitar erro em dtypes numéricos sem o .astype(str)
            if df[col].dtype == 'object' or pd.api.types.is_categorical_dtype(df[col]):
                n_vazio = (df[col].astype(str).str.strip() == '').sum()
            
            n_ausentes = n_nan + n_vazio
            
            if n_ausentes > 0:
                ausentes[col] = (n_ausentes, total_linhas)
                
    return ausentes

# --- 2. Função Principal de Conversão de Tipos ---

def inferir_e_converter_tipos(df, colunas_texto, colunas_moeda):
    """
    Processa um DataFrame, convertendo tipos de dados com base nas seleções.
    
    Args:
        df (pd.DataFrame): DataFrame a ser processado.
        colunas_texto (list): Colunas a serem forçadas como string.
        colunas_moeda (list): Colunas a serem forçadas como numéricas (float).

    Returns:
        pd.DataFrame: DataFrame com tipos de dados convertidos.
    """
    df_copy = df.copy()
    
    # 1. Limpeza de Nomes de Coluna
    # Uso de re.sub para maior clareza, mantendo a lógica original
    def clean_col_name(col):
        return re.sub(r'[^a-z0-9_]', '', col.strip().lower())

    df_copy.columns = [clean_col_name(col) for col in df_copy.columns]
    
    # 2. Conversão de Colunas de TEXTO/ID (selecionadas pelo usuário)
    for col in colunas_texto:
        # A busca na coluna deve usar o nome limpo
        col_limpa = clean_col_name(col)
        if col_limpa in df_copy.columns:
            # Força para string, substitui nulos por 'N/A' e converte para categoria
            df_copy[col_limpa] = (df_copy[col_limpa].astype(str).fillna('N/A')
                                  .str.strip().astype('category'))
    
    # 3. Conversão de Colunas de MOEDA (selecionadas pelo usuário)
    for col in colunas_moeda:
        # A busca na coluna deve usar o nome limpo
        col_limpa = clean_col_name(col)
        if col_limpa in df_copy.columns:
            try:
                # Trata strings de moeda e converte para float
                if df_copy[col_limpa].dtype == 'object' or pd.api.types.is_numeric_dtype(df_copy[col_limpa]):
                    # Remove R$, ponto de milhar e substitui vírgula por ponto
                    # O regex é usado para remover caracteres não numéricos ou ponto/vírgula
                    df_copy[col_limpa] = (df_copy[col_limpa]
                                          .astype(str)
                                          .str.replace(r'[R$]', '', regex=True)
                                          .str.replace('.', '', regex=False)
                                          .str.replace(',', '.', regex=False)
                                          .str.strip()
                                          .replace('', np.nan)) # Trata string vazia como NaN
                
                df_copy[col_limpa] = pd.to_numeric(df_copy[col_limpa], errors='coerce').astype(float)
            except Exception:
                # Se falhar, mantém a coluna original
                pass 
                
    # 4. Inferência Automática para as Colunas Restantes
    colunas_selecionadas = [clean_col_name(c) for c in colunas_texto] + [clean_col_name(c) for c in colunas_moeda]
    
    for col in df_copy.columns:
        if col not in colunas_selecionadas:
            
            # Tenta converter para data
            try:
                df_temp = pd.to_datetime(df_copy[col], errors='coerce')
                # Se houver mais que 50% de valores válidos de data, converte
                if df_temp.notna().sum() / len(df_temp) > 0.5:
                    df_copy[col] = df_temp
                    continue
            except:
                pass

            # Tenta converter para numérico (int ou float)
            try:
                # Se já for numérico, passa
                if pd.api.types.is_numeric_dtype(df_copy[col]):
                    continue
                
                df_temp = pd.to_numeric(df_copy[col], errors='coerce')
                # Se houver mais que 50% de valores válidos numéricos, converte
                if df_temp.notna().sum() / len(df_temp) > 0.5:
                    df_copy[col] = df_temp
                    continue
            except:
                pass

            # Converte o restante para categórico (ideal para filtros)
            if df_copy[col].dtype == 'object' and df_copy[col].nunique() < 50:
                df_copy[col] = df_copy[col].astype(str).fillna('N/A').str.strip().astype('category')
            elif df_copy[col].dtype == 'object':
                # Se muitos valores únicos, mantém como string/object
                df_copy[col] = df_copy[col].astype(str).fillna('N/A').str.strip()

    return df_copy
