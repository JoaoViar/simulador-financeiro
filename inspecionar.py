import sqlite3
import pandas as pd

conn = sqlite3.connect("dados_simulador.db")

print("\n--- 🔍 CONTEÚDO DA TABELA tb_simulacao_unida ---")
df_unida = pd.read_sql("SELECT * FROM tb_simulacao_unida", conn)
print(df_unida.to_string())  # Exibe todas as linhas e colunas

print("\n--- ⚠️ LINHAS COM VALORES NULOS (NaN) ---")
nulos = df_unida[df_unida.isna().any(axis=1)]
if not nulos.empty:
    print(nulos)
else:
    print("Nenhum valor nulo encontrado!")

print(f"\nTotal de linhas disponíveis na tabela: {len(df_unida)}")
conn.close()