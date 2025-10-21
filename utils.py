# utils.py

import pandas as pd
import numpy as np
from datetime import datetime

def formatar_moeda(valor):
    """Formata um valor float ou int para o formato monetário BRL."""
    if pd.isna(valor) or valor is None:
        return "R$ 0,00"
    # Garante que o valor é um float antes de formatar
    try:
        valor = float(valor)
    except:
        return "R$ N/A"
        
    # Formatação com ponto como separador de milhar e vírgula como decimal
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
            # CRÍTICO: Conversão explícita de string para número (tratando vírgula decimal)
            try:
                # Remove espaços, remove separador de milhar (ponto), troca separador decimal (vírgula por ponto)
                df_novo[col] = df_novo[col].astype(str).str.strip().str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df_novo[col] = pd.to_numeric(df_novo[col], errors='coerce')
            except Exception:
                df_novo[col] = pd.to_numeric(df_novo[col], errors='coerce')
        
        # Converte colunas explicitamente marcadas para string/object
        elif col in colunas_texto:
            df_novo[col] = df_novo[col].astype('object')
        
        # Tenta converter colunas numéricas restantes para int/float se não forem datas
        elif df_novo[col].dtype not in ['datetime64[ns]']:
            try:
                # Verifica se são todos inteiros, se sim, converte para inteiro
                if df_novo[col].dropna().apply(lambda x: float(x).is_integer()).all():
                    df_novo[col] = pd.to_numeric(df_novo[col], errors='coerce', downcast='integer')
                else:
                    df_novo[col] = pd.to_numeric(df_novo[col], errors='coerce')
            except:
                pass

    # 2. Conversão de Colunas de Data (Se for ANO e MES)
    if 'ano' in df_novo.columns and 'mes' in df_novo.columns:
        try:
            # Cria uma coluna de data única para filtragem
            df_novo['data_referencia'] = pd.to_datetime(df_novo['ano'].astype(str) + '-' + df_novo['mes'].astype(str) + '-01', format='%Y-%m-%d', errors='coerce')
        except Exception:
            pass
            
    # 3. Conversão final para categorias e remoção de espaços
    for col in df_novo.select_dtypes(include=['object']):
        df_novo[col] = df_novo[col].astype(str).str.strip().str.upper() # Padronização para UPPERCASE
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
        if col not in df_completo.columns: continue
        opcoes_unicas = df_completo[col].astype(str).fillna('N/A').unique().tolist()
        
        # Só mostra se o filtro estiver ativo (len > 0 e len < total de opções)
        if selecoes and len(selecoes) > 0 and len(selecoes) < len(opcoes_unicas):
            rotulos.append(f"**{col.replace('_', ' ').title()}**: ({len(selecoes)} opções)")
    
    # Rótulos de Data
    if data_range and colunas_data:
        data_col = colunas_data[0]
        # Converte para datetime e remove NaT antes de calcular min/max
        data_series = pd.to_datetime(df_completo[data_col], errors='coerce').dropna()
        if not data_series.empty:
            data_min_df = data_series.min().to_pydatetime()
            data_max_df = data_series.max().to_pydatetime()
            
            data_range_start = pd.to_datetime(data_range[0]).to_pydatetime()
            data_range_end = pd.to_datetime(data_range[1]).to_pydatetime()
            
            # Compara se o intervalo selecionado é diferente do intervalo total do DF (com tolerância de 1 dia)
            is_start_filtered = (data_range_start - data_min_df).days > 0
            is_end_filtered = (data_max_df - data_range_end).days > 0

            if is_start_filtered or is_end_filtered:
                data_inicio = data_range_start.strftime('%Y-%m-%d')
                data_fim = data_range_end.strftime('%Y-%m-%d')
                rotulos.append(f"**Data ({data_col.title()})**: {data_inicio} até {data_fim}")
            
    if not rotulos:
        return "Nenhum Filtro Ativo. (Análise no Total Geral)"
        
    return " | ".join(rotulos)
