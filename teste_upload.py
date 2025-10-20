import pandas as pd

# Altere para o nome do seu arquivo real
CAMINHO_ARQUIVO = "RUBRICAS.csv"  # ou "RUBRICAS.xlsx"

try:
    if CAMINHO_ARQUIVO.endswith('.csv'):
        try:
            df = pd.read_csv(CAMINHO_ARQUIVO, sep=';', decimal=',', encoding='utf-8')
        except Exception as e:
            print("Erro com sep=';' e decimal=',' :", e)
            df = pd.read_csv(CAMINHO_ARQUIVO, sep=',', decimal='.', encoding='utf-8')
    elif CAMINHO_ARQUIVO.endswith('.xlsx'):
        df = pd.read_excel(CAMINHO_ARQUIVO)
    else:
        print("Tipo de arquivo não suportado.")
        df = pd.DataFrame()

    print("Colunas:", df.columns.tolist())
    print("Primeiras linhas:")
    print(df.head())

except Exception as e:
    print("Erro ao ler arquivo:", e)
