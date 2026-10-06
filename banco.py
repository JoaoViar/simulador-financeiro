import sqlite3
import pandas as pd
import unicodedata

DB_NAME = "dados_simulador.db"


def normalizar_nome_coluna(coluna) -> str:
    """Normaliza nomes de colunas removendo acentos, caracteres estranhos e espaços."""
    texto = str(coluna) if coluna is not None else ""
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto.strip().lower().replace(' ', '_')


def inicializar_banco():
    """Cria as tabelas necessárias no SQLite se não existirem[cite: 2]."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabela para os dados da Focus
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tb_focus (
            data_referencia TIMESTAMP,
            mediana REAL,
            ano INTEGER,
            numero_reuniao INTEGER,
            mes INTEGER,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ano, mes)
        )
    ''')

    # Tabela para os Juros Futuros
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tb_juros_futuros (
            ano INTEGER,
            mes INTEGER,
            contrato TEXT,
            taxa_futura REAL,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ano, mes)
        )
    ''')

    # Tabela Consolidada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tb_simulacao_unida (
            data_referencia TEXT,
            mediana REAL,
            ano INTEGER,
            numero_reuniao INTEGER,
            mes INTEGER,
            taxa_futura REAL,
            juros_futuro REAL,
            dias_uteis INTEGER,
            data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ano, mes)
        )
    ''')

    conn.commit()
    conn.close()
    print("💾 Banco de dados SQLite verificado/inicializado com sucesso!")


def salvar_focus_no_banco(df_focus):
    """Insere ou atualiza os dados do Focus[cite: 2]."""
    if df_focus.empty:
        return

    df_focus.columns = [normalizar_nome_coluna(c) for c in df_focus.columns]
    conn = sqlite3.connect(DB_NAME)
    df_focus.to_sql('tb_focus', conn, if_exists='replace', index=False)
    conn.close()
    processar_tabela_consolidada()


def salvar_futuros_no_banco(df_futuro):
    """Insere ou atualiza os dados de Juros Futuros[cite: 2]."""
    if df_futuro.empty:
        return

    df_futuro.columns = [normalizar_nome_coluna(c) for c in df_futuro.columns]
    conn = sqlite3.connect(DB_NAME)
    df_futuro.to_sql('tb_juros_futuros', conn, if_exists='replace', index=False)
    conn.close()
    processar_tabela_consolidada()


def processar_tabela_consolidada():
    """Cruza tb_focus e tb_juros_futuros, faz interpolação linear sem NaNs e grava a tb_simulacao_unida[cite: 2]."""
    conn = sqlite3.connect(DB_NAME)

    try:
        df_focus = pd.read_sql("SELECT * FROM tb_focus", conn)
        df_futuro = pd.read_sql("SELECT * FROM tb_juros_futuros", conn)

        if df_focus.empty or df_futuro.empty:
            print("⚠️ Uma das tabelas ainda está vazia no banco. Aguardando dados...")
            return

        # Normaliza colunas carregadas do banco
        df_focus.columns = [normalizar_nome_coluna(c) for c in df_focus.columns]
        df_futuro.columns = [normalizar_nome_coluna(c) for c in df_futuro.columns]

        # Mapeamentos de nomes de colunas
        df_focus.rename(columns={'ano_reuniao': 'ano', 'mes_reuniao': 'mes'}, inplace=True)
        df_futuro.rename(columns={'taxafutura': 'taxa_futura'}, inplace=True)

        # Garante tipos inteiros nas chaves
        df_focus['ano'] = pd.to_numeric(df_focus['ano'], errors='coerce').fillna(0).astype(int)
        df_focus['mes'] = pd.to_numeric(df_focus['mes'], errors='coerce').fillna(0).astype(int)
        df_futuro['ano'] = pd.to_numeric(df_futuro['ano'], errors='coerce').fillna(0).astype(int)
        df_futuro['mes'] = pd.to_numeric(df_futuro['mes'], errors='coerce').fillna(0).astype(int)

        # Merge usando Focus como base temporal contínua
        df_unido = pd.merge(
            df_focus,
            df_futuro[['ano', 'mes', 'taxa_futura']],
            on=['ano', 'mes'],
            how='left'
        )

        # Ordena cronologicamente para a interpolação funcionar na sequência exata
        df_unido = df_unido.sort_values(by=['ano', 'mes']).reset_index(drop=True)

        # Elimina taxas negativas ou zeradas incorretas da raspagem
        if 'taxa_futura' in df_unido.columns:
            df_unido.loc[df_unido['taxa_futura'] <= 0, 'taxa_futura'] = None

        # Interpolação Linear nas taxas (preenche a progressão entre os valores presentes)
        if 'taxa_futura' in df_unido.columns:
            df_unido['taxa_futura'] = df_unido['taxa_futura'].interpolate(method='linear')
            if 'mediana' in df_unido.columns:
                df_unido['taxa_futura'] = df_unido['taxa_futura'].fillna(df_unido['mediana'])
            df_unido['taxa_futura'] = df_unido['taxa_futura'].ffill().bfill()

        # Consolida a coluna 'juros_futuro' idêntica e sem valores nulos
        df_unido['juros_futuro'] = df_unido['taxa_futura']

        # Remove linhas incompletas sem data de referência
        if 'data_referencia' in df_unido.columns:
            df_unido = df_unido.dropna(subset=['data_referencia'])

        # Salva a tabela limpa no SQLite
        df_unido.to_sql('tb_simulacao_unida', conn, if_exists='replace', index=False)
        print("✅ Tabela 'tb_simulacao_unida' limpa, interpolada e consolidada com sucesso!")

    except Exception as e:
        print(f"❌ Erro ao consolidar tabela: {e}")
    finally:
        conn.close()


def carregar_tabela_simulacao():
    """Função ultra-rápida usada pelo Flask (< 0.01s)[cite: 2]."""
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql("SELECT * FROM tb_simulacao_unida", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df