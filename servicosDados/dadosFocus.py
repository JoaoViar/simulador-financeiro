import requests
import pandas as pd

def puxar_dados_da_api_anual():
    print("Conectando à API externa para buscar dados anuais...")
    
    linkAPIanual = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais?$top=10&$filter=Indicador%20eq%20'Selic'&$orderby=Data%20desc&$format=json&$select=Indicador,Data,DataReferencia,Mediana,numeroRespondentes,baseCalculo"

    requisicaoAPIanual = requests.get(linkAPIanual)
    dicionarioRequisicaoAnual = requisicaoAPIanual.json()

    #Transformação do dicionario em DataFrame
    tabelaExpectativasFocusAnual = pd.DataFrame(dicionarioRequisicaoAnual["value"])

    #Pegando a base de calculo com maior numero de participantes
    tabelaExpectativasFocusAnual = tabelaExpectativasFocusAnual[tabelaExpectativasFocusAnual['baseCalculo'] == 0]

    #Tratamento do modelo de apresentacao da data para dd/mm/ano
    tabelaExpectativasFocusAnual['Data'] = pd.to_datetime(tabelaExpectativasFocusAnual['Data'])
    tabelaExpectativasFocusAnual['Data'] = tabelaExpectativasFocusAnual['Data'].dt.strftime('%d/%m/%Y')

    return tabelaExpectativasFocusAnual

def puxar_dados_da_api_reuniao(tabelaExpectativasFocusAnual):
    print("Conectando à API externa para buscar dados por reuniao...")
    
        ## Requisiçõ da API e transformação do json em dicionario
    linkAPIreunioes = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoSelic?$top=32&$orderby=Data%20desc&$format=json&$select=Indicador,Data,Reuniao,Media,Mediana,baseCalculo"

    requisicaoAPIreunioes = requests.get(linkAPIreunioes)
    dicionarioRequisicaoReunioes = requisicaoAPIreunioes.json()

    # Calendario Fixo de Reuniões por mes
    calendario_fixo_reunioes = {'1': 1, '2': 3,'3': 4,'4': 6,'5': 7,'6': 9,'7': 10,'8': 12}

    #Transformação do dicionario em DataFrame
    tabelaExpectativasFocusReunioes = pd.DataFrame(dicionarioRequisicaoReunioes["value"])

    #Pegando a base de calculo com maior numero de participantes
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes[tabelaExpectativasFocusReunioes['baseCalculo'] == 0]

    #Tratamento do modelo de apresentacao da data para dd/mm/ano
    tabelaExpectativasFocusReunioes['Data'] = pd.to_datetime(tabelaExpectativasFocusReunioes['Data'])
    tabelaExpectativasFocusReunioes['Data'] = tabelaExpectativasFocusReunioes['Data'].dt.strftime('%d/%m/%Y')

    #Criando a coluna ano reunião atraves do código da reunião com o ano
    tabelaExpectativasFocusReunioes['Ano Reunião'] = tabelaExpectativasFocusReunioes['Reuniao'].str.split('/').str[1].astype(int)
    tabelaExpectativasFocusReunioes['Ano Reunião'] = tabelaExpectativasFocusReunioes['Ano Reunião'].astype(int)

    #Pegando o número da reunião já que ela esta na mesma coluna que o ano
    tabelaExpectativasFocusReunioes['Número Reunião'] = tabelaExpectativasFocusReunioes['Reuniao'].str.split('/').str[0].str.replace('R', '', regex=False)

    #Criando a coluna mês reunião atraves do dicionario calendario_fixo_reunioes
    tabelaExpectativasFocusReunioes.loc[:, 'Mês Reunião'] = tabelaExpectativasFocusReunioes['Número Reunião'].astype(str).map(calendario_fixo_reunioes)

    #Remoendo colunas que não vamos utilizar
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.drop(['Indicador', 'Media', 'Reuniao', 'baseCalculo'], axis=1)

    #Cria uma coluna para adicionarmos os meses faltantes na respectiva tabela com as taxas dos meses anteriores
    tabelaExpectativasFocusReunioes['Data_Filtro'] = pd.to_datetime(
        tabelaExpectativasFocusReunioes['Ano Reunião'].astype(str) + '-' + 
        tabelaExpectativasFocusReunioes['Mês Reunião'].astype(int).astype(str) + '-01'
    )

    #Remover duplicatas caso haja mais de uma previsão para o mesmo mês/ano de reunião
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.drop_duplicates(subset=['Data_Filtro']).copy()

    #Definir a nova data como o índice da tabela
    tabelaExpectativasFocusReunioes.set_index('Data_Filtro', inplace=True)

    #Ordenar pelo índice para garantir a ordem correta
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.sort_index()

    #Ele vai pegar automaticamente desde a menor data até a maior data da sua tabela
    todos_os_meses = pd.date_range(start=tabelaExpectativasFocusReunioes.index.min(), end=tabelaExpectativasFocusReunioes.index.max(), freq='MS')

    #Reindexar a tabela: o pandas vai criar as linhas para os meses que estão faltando
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.reindex(todos_os_meses, method='ffill')

    #Trazer a data do índice de volta para uma coluna formatada e organizar
    tabelaExpectativasFocusReunioes.index.name = 'Data Referência'
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.reset_index()
    tabelaExpectativasFocusReunioes['Mês Reunião'] = tabelaExpectativasFocusReunioes['Data Referência'].dt.month
    tabelaExpectativasFocusReunioes['Ano Reunião'] = tabelaExpectativasFocusReunioes['Data Referência'].dt.year

    #Remoendo colunas que não vamos utilizar
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.drop(['Data Referência', 'Data'], axis=1)
        
        # Identificar onde a tabela mensal termina
    # Pegamos as informações da última linha real disponível na tabela de curto prazo
    ultima_linha_real = tabelaExpectativasFocusReunioes.dropna(subset=['Mediana']).iloc[-1]

    ultimo_ano_real = int(ultima_linha_real['Ano Reunião'])
    ultima_reuniao_real = int(ultima_linha_real['Número Reunião'])
    ultimo_valor_real = float(ultima_linha_real['Mediana'])

    novas_linhas_projetadas = []

    # Preencher o restante do ano atual
    reunioes_que_faltam = [r for r in calendario_fixo_reunioes.keys() if int(r) > ultima_reuniao_real]
    num_passos = len(reunioes_que_faltam)

    if num_passos > 0:
        tabelaExpectativasFocusAnual['DataReferencia'] = tabelaExpectativasFocusAnual['DataReferencia'].astype(int)
        
        filtro_ano = tabelaExpectativasFocusAnual[tabelaExpectativasFocusAnual['DataReferencia'] == int(ultimo_ano_real)]
        
        if not filtro_ano.empty:
            valor_fechamento_meta = float(filtro_ano['Mediana'].values[0])
            print(f"-> Ano {ultimo_ano_real} encontrado! Meta de fechamento: {valor_fechamento_meta}")
        else:
            print(f"-> AVISO: Ano {ultimo_ano_real} não foi encontrado na tabela anual! Usando valor atual.")
            valor_fechamento_meta = ultimo_valor_real

        variacao_passo = (valor_fechamento_meta - ultimo_valor_real) / num_passos
        
        valor_acumulado = ultimo_valor_real
        for i, r in enumerate(reunioes_que_faltam):
            # Para garantir que a última reunião seja cravada exatamente no valor da meta (evitando erros de arredondamento do Python)
            if i == num_passos - 1:
                valor_acumulado = valor_fechamento_meta
            else:
                valor_acumulado += variacao_passo
                
            novas_linhas_projetadas.append({
                'Mediana': round(valor_acumulado, 3),
                'Ano Reunião': int(ultimo_ano_real),
                'Número Reunião': r,
                'Mês Reunião': calendario_fixo_reunioes[r]
            })

    # Projetar os anos cheios seguintes
    # Seleciona apenas os anos da tabela Focus que são MAIORES do que o ano onde a tabela mensal parou
    anos_futuros_totais = sorted([ano for ano in tabelaExpectativasFocusAnual['DataReferencia'].unique() if int(ano) > ultimo_ano_real])

    for ano in anos_futuros_totais:
        # Pega o valor de fechamento (meta) para o ano cheio
        valor_final_meta = float(tabelaExpectativasFocusAnual[tabelaExpectativasFocusAnual['DataReferencia'] == ano]['Mediana'].values[0])
        
        # O valor inicial do ano será o último valor que calculamos no passo anterior
        valor_inicial_ano = novas_linhas_projetadas[-1]['Mediana'] if novas_linhas_projetadas else ultimo_valor_real
        
        # Como o ano está vazio, dividimos a transição pelas 8 reuniões do ano inteiro
        total_reunioes = len(calendario_fixo_reunioes)
        variacao_passo = (valor_final_meta - valor_inicial_ano) / total_reunioes
        
        valor_acumulado = valor_inicial_ano
        for r in sorted(calendario_fixo_reunioes.keys()):
            valor_acumulado += variacao_passo
            novas_linhas_projetadas.append({
                'Mediana': round(valor_acumulado, 3),
                'Ano Reunião': ano,
                'Número Reunião': r,
                'Mês Reunião': calendario_fixo_reunioes[r]
            })

    # Combinar tudo em uma tabela única
    dfTemporario = pd.DataFrame(novas_linhas_projetadas)
    tabelaExpectativasFocusReunioes = pd.concat([tabelaExpectativasFocusReunioes, dfTemporario], ignore_index=True)

    #Cria uma coluna para adicionarmos os meses faltantes na respectiva tabela com as taxas dos meses anteriores
    tabelaExpectativasFocusReunioes['Data_Filtro'] = pd.to_datetime(
        tabelaExpectativasFocusReunioes['Ano Reunião'].astype(str) + '-' + 
        tabelaExpectativasFocusReunioes['Mês Reunião'].astype(int).astype(str) + '-01'
    )

    #Remover duplicatas caso haja mais de uma previsão para o mesmo mês/ano de reunião
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.drop_duplicates(subset=['Data_Filtro']).copy()

    #Definir a nova data como o índice da tabela
    tabelaExpectativasFocusReunioes.set_index('Data_Filtro', inplace=True)

    #Ordenar pelo índice para garantir a ordem correta
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.sort_index()

    #Ele vai pegar automaticamente desde a menor data até a maior data da sua tabela
    todos_os_meses = pd.date_range(start=tabelaExpectativasFocusReunioes.index.min(), end=tabelaExpectativasFocusReunioes.index.max(), freq='MS')

    #Reindexar a tabela: o pandas vai criar as linhas para os meses que estão faltando
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.reindex(todos_os_meses, method='ffill')

    #Trazer a data do índice de volta para uma coluna formatada e organizar
    tabelaExpectativasFocusReunioes.index.name = 'Data Referência'
    tabelaExpectativasFocusReunioes = tabelaExpectativasFocusReunioes.reset_index()
    tabelaExpectativasFocusReunioes['Mês Reunião'] = tabelaExpectativasFocusReunioes['Data Referência'].dt.month
    tabelaExpectativasFocusReunioes['Ano Reunião'] = tabelaExpectativasFocusReunioes['Data Referência'].dt.year
    return tabelaExpectativasFocusReunioes, calendario_fixo_reunioes