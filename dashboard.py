import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from utils import inferir_e_converter_tipos, encontrar_colunas_tipos, verificar_ausentes, formatar_moeda
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Dashboard de Análise de Dados")

# --- SIMULAÇÃO DE DADOS (SE NÃO HOUVER ARQUIVO) ---
def criar_df_simulado():
    """Cria um DataFrame simulado com 909 linhas, 383 funcionários únicos e 909 'nr' únicos."""
    np.random.seed(42)
    total_linhas = 909
    total_funcionarios = 383
    
    # Gera 383 nomes únicos
    nomes_unicos = [f"Funcionario_{i:03d}" for i in range(1, total_funcionarios + 1)]
    
    # Cria a coluna 'nomefuncionario' repetindo os 383 nomes até atingir 909 linhas
    nomes = np.resize(nomes_unicos, total_linhas)
    
    data = {
        'NR': [i + 1 for i in range(total_linhas)], # Coluna NR é única (909 opções)
        'NomeFuncionario': nomes, # 383 opções
        'Tipo': np.random.choice(['Salario', 'Beneficio', 'Férias'], total_linhas),
        'Empresa': np.random.choice(['Empresa A', 'Empresa B', 'Empresa C'], total_linhas),
        'DataPagamento': pd.to_datetime('2024-01-01') + pd.to_timedelta(np.random.randint(0, 365, total_linhas), unit='D'),
        'Valor': np.random.uniform(1000, 15000, total_linhas).round(2),
        'HorasTrabalhadas': np.random.randint(160, 220, total_linhas),
    }
    df = pd.DataFrame(data)
    # Introduzindo valores NaN em algumas colunas para testar a robustez
    df.loc[df.sample(frac=0.05).index, 'Tipo'] = np.nan
    df.loc[df.sample(frac=0.02).index, 'Valor'] = np.nan
    df.loc[df.sample(frac=0.03).index, 'Empresa'] = '' # String vazia
    return df

# --- CARREGAMENTO DE DADOS E PROCESSAMENTO INICIAL ---

if 'df_original' not in st.session_state:
    st.session_state.df_original = None
    st.session_state.df_processado = None

st.title("📊 Análise de Dados da Folha")

uploaded_file = st.sidebar.file_uploader(
    "1. Carregar Arquivo de Dados (CSV ou TXT)", 
    type=['csv', 'txt'],
    help="Use ponto e vírgula (;) como separador para arquivos de folha de pagamento."
)

if uploaded_file is not None:
    try:
        # Tenta carregar com ponto e vírgula (padrão de sistemas BRL)
        df_temp = pd.read_csv(uploaded_file, sep=';')
    except Exception:
        # Se falhar, tenta com vírgula
        uploaded_file.seek(0)
        df_temp = pd.read_csv(uploaded_file, sep=',')
    
    st.session_state.df_original = df_temp
    st.success(f"Arquivo carregado com sucesso! {len(df_temp)} linhas e {len(df_temp.columns)} colunas.")
else:
    if st.sidebar.checkbox("Usar dados de demonstração", value=True):
        st.session_state.df_original = criar_df_simulado()
        st.info("Usando dados de demonstração (909 registros).")
    else:
        st.warning("Por favor, carregue um arquivo para começar a análise.")

# --- BARRA LATERAL DE CONFIGURAÇÃO (AJUSTES CHAVE) ---
if st.session_state.df_original is not None:
    
    df = st.session_state.df_original.copy()
    colunas_originais = df.columns.tolist()
    
    st.sidebar.header("2. Configuração das Colunas")
    
    # AJUSTE CHAVE: Forçar 'NR' (ou 'nr' após limpeza) como ID/Texto
    col_nr_limpa = 'nr' 
    col_nome_limpa = 'nomefuncionario'
    
    # ----------------------------------------------------------------------
    # Seleção de Colunas para Tipagem
    # ----------------------------------------------------------------------
    
    st.sidebar.subheader("📝 Colunas TEXTO/ID")
    # Pré-seleção da coluna 'NR' (ou 'nr') para ser tratada como ID
    colunas_texto_default = [c for c in colunas_originais if c.lower().replace(' ', '') == 'nr']
    if not colunas_texto_default:
        colunas_texto_default = [] # Não encontrou o padrão 'NR'
        
    colunas_texto = st.sidebar.multiselect(
        "Colunas que devem ser tratadas como texto simples/ID (ex: NR, CPF, Nome):",
        colunas_originais,
        default=colunas_texto_default
    )

    st.sidebar.subheader("💰 Colunas MOEDA")
    colunas_moeda = st.sidebar.multiselect(
        "Colunas de valores monetários:",
        colunas_originais,
        default=[c for c in colunas_originais if 'valor' in c.lower() or 'salario' in c.lower()]
    )

    # --- PROCESSAR DADOS ---
    if st.sidebar.button("3. Processar e Converter Tipos"):
        with st.spinner("Processando dados e inferindo tipos..."):
            df_processado = inferir_e_converter_tipos(
                df, 
                colunas_texto, 
                colunas_moeda
            )
            st.session_state.df_processado = df_processado
        st.sidebar.success("Processamento concluído!")

# --- VISUALIZAÇÃO E FILTROS ---
if st.session_state.df_processado is not None:
    df_proc = st.session_state.df_processado.copy()
    
    # 1. ENCONTRAR COLUNAS PARA FILTRO
    outras_colunas, colunas_data = encontrar_colunas_tipos(df_proc)
    
    # Remove colunas classificadas como ID do pool de filtros categóricos/numéricos
    # A lista 'colunas_texto' aqui deve ser mapeada para os nomes limpos
    colunas_texto_limpas = [c.lower().strip().replace('[^a-z0-9_]', '', regex=True) for c in colunas_texto]
    colunas_filtragem = [col for col in outras_colunas if col not in colunas_texto_limpas]

    # --- MÉTRICAS DE RESUMO ---
    st.subheader("Resumo da Base de Dados Processada")
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total de Registros (Linhas)", len(df_proc))
    
    # AJUSTE DE CONTAGEM: Verifica o número de funcionários ÚNICOS
    if col_nome_limpa in df_proc.columns:
        n_funcionarios_unicos = df_proc[col_nome_limpa].nunique(dropna=True)
        col2.metric("Funcionários Únicos", n_funcionarios_unicos, 
                    delta=f"{len(df_proc) - n_funcionarios_unicos} Registros Repetidos", 
                    delta_color="off")
    else:
        col2.metric("Funcionários Únicos", "Coluna não encontrada")
        
    # Contagem da coluna 'nr' (apenas para referência)
    if col_nr_limpa in df_proc.columns:
         unicos_nr = df_proc[col_nr_limpa].nunique(dropna=True)
         col3.metric("Registros NR Únicos", unicos_nr)
    else:
        col3.metric("Registros NR Únicos", "Coluna não encontrada")
        
    # Exibe o total monetário (assumindo que há uma coluna 'valor' limpa)
    if 'valor' in df_proc.columns and pd.api.types.is_numeric_dtype(df_proc['valor']):
        total_valor = df_proc['valor'].sum()
        col4.metric("Total Monetário", formatar_moeda(total_valor))

    # --- FILTROS DINÂMICOS ---
    st.subheader("⚙️ Filtros da Base")
    
    colunas_para_exibir_filtros = [
        col for col in colunas_filtragem 
        if pd.api.types.is_categorical_dtype(df_proc[col]) or df_proc[col].nunique() < 200
    ]
    
    
    # Verifica valores ausentes na base de filtros
    ausentes_info = verificar_ausentes(df_proc, colunas_para_exibir_filtros)

    filtros_aplicados = {}
    
    # Cria os expanders de filtros
    for i, col in enumerate(colunas_para_exibir_filtros):
        
        # Cria um expansor para cada filtro
        with st.expander(f"{col.replace('_', ' ').title()} ({df_proc[col].nunique()} opções)"):
            
            # Avisa se houver dados ausentes
            if col in ausentes_info:
                n_ausentes, total = ausentes_info[col]
                st.warning(f"⚠️ {n_ausentes} valores ausentes ({n_ausentes/total:.1%}) detectados. Valores NaN/vazios foram convertidos para 'N/A' e são filtráveis.")

            # Filtro Categórico / Texto
            if pd.api.types.is_categorical_dtype(df_proc[col]) or df_proc[col].dtype == 'object':
                opcoes_ordenadas = sorted(df_proc[col].unique().tolist(), key=lambda x: str(x))
                selecao = st.multiselect(f"Selecione valores para {col}:", opcoes_ordenadas, key=f"filter_{col}")
                if selecao:
                    filtros_aplicados[col] = df_proc[col].isin(selecao)

            # Filtro Numérico (Slider)
            elif pd.api.types.is_numeric_dtype(df_proc[col]):
                min_val = df_proc[col].min()
                max_val = df_proc[col].max()
                selecao = st.slider(f"Intervalo de {col}:", min_val, max_val, (min_val, max_val), key=f"filter_{col}")
                filtros_aplicados[col] = (df_proc[col] >= selecao[0]) & (df_proc[col] <= selecao[1])
                
            # Filtro de Data
            elif pd.api.types.is_datetime64_any_dtype(df_proc[col]):
                min_date = df_proc[col].min().to_pydatetime().date()
                max_date = df_proc[col].max().to_pydatetime().date()
                selecao = st.date_input(f"Intervalo de {col}:", [min_date, max_date], key=f"filter_{col}")
                if len(selecao) == 2:
                    start_date = pd.to_datetime(min(selecao))
                    end_date = pd.to_datetime(max(selecao))
                    filtros_aplicados[col] = (df_proc[col] >= start_date) & (df_proc[col] <= end_date)
                    
    
    # APLICAR TODOS OS FILTROS
    if filtros_aplicados:
        filtro_final = pd.Series(True, index=df_proc.index)
        for condicao in filtros_aplicados.values():
            filtro_final = filtro_final & condicao
        
        df_filtrado = df_proc[filtro_final]
        st.success(f"Filtro aplicado! {len(df_filtrado)} de {len(df_proc)} registros selecionados.")
    else:
        df_filtrado = df_proc.copy()

    # --- VISUALIZAÇÃO DO DATAFRAME FILTRADO ---
    st.subheader("Visualização dos Dados (Filtrados)")
    st.dataframe(df_filtrado)
