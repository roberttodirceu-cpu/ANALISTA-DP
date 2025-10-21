# ... (início do código, sem alterações) ...

# --- SIDEBAR (CONFIGURAÇÕES E UPLOAD) ---
with st.sidebar:
# ... (bloco de upload e gerenciamento de arquivos) ...
    
    # --- Lógica de Configuração de Colunas (COM CORREÇÃO PARA LEITURA BR) ---
    if st.session_state.show_reconfig_section:
        
        df_novo = pd.DataFrame()
        all_dataframes = []
        
        for file_name, file_bytes in st.session_state.uploaded_files_data.items():
            
            # CORREÇÃO 1: Inicializa df_temp como None em cada iteração
            df_temp = None 
            
            try:
                uploaded_file_stream = BytesIO(file_bytes)
                
                if file_name.endswith('.csv'):
                    
                    # TENTATIVA 1 (ROBUSTA BR): Separador ';', Decimal ',', Milhar '.', Latin-1
                    try:
                        uploaded_file_stream.seek(0)
                        df_temp = pd.read_csv(
                            uploaded_file_stream, 
                            sep=';', 
                            decimal=',', 
                            thousands='.',         # <--- CORREÇÃO: Essencial para valores como '1.100,00'
                            encoding='latin-1',    # <--- CORREÇÃO: Codificação comum para sistemas legados
                            skipinitialspace=True  # <--- CORREÇÃO: Ignora espaços após o delimitador
                        )
                    except Exception as e1:
                        # TENTATIVA 2 (PADRÃO US): Separador ',', Decimal '.', UTF-8
                        try:
                            uploaded_file_stream.seek(0)
                            df_temp = pd.read_csv(
                                uploaded_file_stream, 
                                sep=',', 
                                decimal='.', 
                                encoding='utf-8' 
                            )
                        except Exception as e2:
                             # Falha total
                            st.error(f"Falha total ao ler o arquivo {file_name} nas duas tentativas de formato CSV. Erro Tentativa 1 (BR): {e1} | Erro Tentativa 2 (US): {e2}")
                            df_temp = None
                        
                elif file_name.endswith('.xlsx'):
                    df_temp = pd.read_excel(uploaded_file_stream)
                
                # CORREÇÃO 2: Apenas adiciona se df_temp foi definido (não é None) e não está vazio
                if df_temp is not None and not df_temp.empty: 
                    all_dataframes.append(df_temp)
                    
            except Exception as e:
                # Captura erros gerais de I/O
                st.error(f"Erro inesperado ao processar o stream do arquivo {file_name}: {e}. O arquivo será ignorado.")
                pass 

        if all_dataframes:
            # Concatena todos os DataFrames que foram lidos com sucesso
            df_novo = pd.concat(all_dataframes, ignore_index=True)
        
        if df_novo.empty:
            # Exibe a mensagem de erro se nenhum arquivo pôde ser lido
            st.error("O conjunto de dados consolidado está vazio. Nenhum arquivo pôde ser lido com sucesso.")
            st.session_state.dados_atuais = pd.DataFrame() 
        else:
            # ... (restante da lógica de processamento e configuração de colunas) ...
            
# ... (restante do código, sem alterações) ...
