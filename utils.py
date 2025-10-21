# utils.py

import pandas as pd
import numpy as np

def formatar_moeda(valor):
    """Formata um valor float ou int para o formato monetário BRL."""
    if pd.isna(valor) or valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def inferir_e_converter_tipos(df, colunas_texto, colunas_moeda):
    """
    Tenta inferir e converter tipos de colunas em um DataFrame,
    priorizando as colunas de texto e moeda fornecidas.
    """
    df_novo = df.copy()
    
    # 1. Limpeza e Inferência Básica
    for col in df_novo.columns:
        # Tenta converter para float se for uma coluna de Moeda
        if col in colunas_moeda:
            # Tenta limpar o formato BRL (R$, ponto como separador de milhar e vírgula como decimal)
            try:
                # Conversão explícita de string para número (tratando vírgula decimal)
                df_novo[col] = df_novo[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df_novo[col] = pd.to_numeric(df_novo[col], errors='coerce')
            except Exception:
                # Se falhar, tenta conversão simples
                df_novo[col] = pd.to_numeric(df_novo[col], errors='coerce')
        
        # Converte colunas explicitamente marcadas para string/object
        elif col in colunas_texto:
            df_novo[col] = df_novo[col].astype('object').astype('category')
        
        # Tenta converter colunas numéricas restantes para int/float se não forem datas
        elif df_novo[col].dtype not in ['datetime64[ns]']:
            try:
                # Tenta Int
                if df_novo[col].dropna().apply(lambda x: float(x).is_integer()).all():
                    df_novo[col] = pd.to_numeric(df_novo[col], errors='coerce', downcast='integer')
                else:
                    df_novo[col] = pd.to_numeric(df_novo[col], errors='coerce')
            except:
                pass # Deixa como está se falhar

    # 2. Conversão de Colunas de Data (Se for ANO e MES)
    if 'ano' in df_novo.columns and 'mes' in df_novo.columns:
        try:
            # Cria uma coluna de data única para filtragem
            df_novo['data_referencia'] = pd.to_datetime(df_novo['ano'].astype(str) + '-' + df_novo['mes'].astype(str) + '-01', format='%Y-%m-%d', errors='coerce')
        except Exception:
            pass
            
    # 3. Conversão final para categorias e remoção de espaços
    for col in df_novo.select_dtypes(include=['object']):
        df_novo[col] = df_novo[col].astype(str).str.strip()
        df_novo[col] = df_novo[col].astype('category')

    return df_novo

def encontrar_colunas_tipos(df):
    """Retorna listas de colunas categoricas e de data."""
    colunas_categoricas = df.select_dtypes(include=['object', 'category']).columns.tolist()
    colunas_data = df.select_dtypes(include=['datetime64[ns]']).columns.tolist()
    return colunas_categoricas, colunas_data

def verificar_ausentes(df):
    """Retorna um DataFrame com a contagem e percentual de valores ausentes."""
    ausentes = df.isnull().sum()
    percentual = 100 * ausentes / len(df)
    df_ausentes = pd.DataFrame({'Contagem de Ausentes': ausentes, 'Percentual (%)': percentual})
    return df_ausentes[df_ausentes['Contagem de Ausentes'] > 0].sort_values(by='Contagem de Ausentes', ascending=False)

def gerar_rotulo_filtro(df_completo, filtros_ativos_dict, colunas_data, data_range):
    """Gera um rótulo resumido dos filtros aplicados."""
    rotulos = []
    
    # Rótulos Categóricos
    for col, selecoes in filtros_ativos_dict.items():
        opcoes_unicas = df_completo[col].astype(str).fillna('N/A').unique().tolist()
        
        # Só mostra se o filtro estiver ativo (len > 0 e len < total de opções)
        if selecoes and len(selecoes) > 0 and len(selecoes) < len(opcoes_unicas):
            rotulos.append(f"**{col.replace('_', ' ').title()}**: ({len(selecoes)} opções)")
    
    # Rótulos de Data
    if data_range and colunas_data:
        data_min_df = df_completo[colunas_data[0]].min()
        data_max_df = df_completo[colunas_data[0]].max()
        
        # Se o intervalo for diferente do total, mostra
        if pd.to_datetime(data_range[0]) > data_min_df or pd.to_datetime(data_range[1]) < data_max_df:
            data_inicio = data_range[0].strftime('%Y-%m-%d')
            data_fim = data_range[1].strftime('%Y-%m-%d')
            rotulos.append(f"**Data**: {data_inicio} até {data_fim}")
            
    if not rotulos:
        return "Nenhum Filtro Ativo. (Análise no Total Geral)"
        
    return " | ".join(rotulos)
