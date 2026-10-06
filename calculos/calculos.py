import pandas as pd
from datetime import date
import calendar
from bizdays import Calendar

def unir_tabelas(tabela_futuro, tabela_api):
    print("Unindo tabelas da Focus e Juros Futuros (B3)...")

    colunas_futuro = {col.lower(): col for col in tabela_futuro.columns} if tabela_futuro is not None else {}
    col_taxa = colunas_futuro.get('taxa futura', colunas_futuro.get('taxa_futura', 'Taxa Futura'))

    if tabela_futuro is None or tabela_futuro.empty or col_taxa not in tabela_futuro.columns:
        print("Tabela de futuros vazia. Usando Mediana Focus como fallback.")
        tabela_api['Juros Futuro'] = tabela_api['Mediana'].values if 'Mediana' in tabela_api else tabela_api['mediana'].values
        tabela_api['Mês Futuro'] = tabela_api['Mês Reunião'].values if 'Mês Reunião' in tabela_api else tabela_api['mes'].values
        return len(tabela_api), tabela_api

    df_api = tabela_api.copy()
    df_futuro = tabela_futuro.copy()

    col_ano_api = 'Ano Reunião' if 'Ano Reunião' in df_api.columns else ('ano' if 'ano' in df_api.columns else 'Ano')
    col_mes_api = 'Mês Reunião' if 'Mês Reunião' in df_api.columns else ('mes' if 'mes' in df_api.columns else 'Mês')
    
    col_ano_fut = 'Ano' if 'Ano' in df_futuro.columns else 'ano'
    col_mes_fut = 'Mês' if 'Mês' in df_futuro.columns else 'mes'

    df_api['Ano_Temp'] = df_api[col_ano_api].astype(int)
    df_api['Mês_Temp'] = df_api[col_mes_api].astype(int)

    df_futuro['Ano_Temp'] = df_futuro[col_ano_fut].astype(int)
    df_futuro['Mês_Temp'] = df_futuro[col_mes_fut].astype(int)

    tabela_unida = pd.merge(
        df_api,
        df_futuro[['Ano_Temp', 'Mês_Temp', col_taxa]],
        on=['Ano_Temp', 'Mês_Temp'],
        how='left'
    )

    col_mediana = 'Mediana' if 'Mediana' in tabela_unida.columns else 'mediana'
    tabela_unida[col_taxa] = tabela_unida[col_taxa].ffill().bfill()
    tabela_unida[col_taxa] = tabela_unida[col_taxa].fillna(tabela_unida[col_mediana])

    tabela_api['Juros Futuro'] = tabela_unida[col_taxa].values
    tabela_api['Mês Futuro'] = tabela_api[col_mes_api].values

    qnt_parcelas = len(tabela_api)
    return qnt_parcelas, tabela_api


def realizar_calculo_financeiro(qnt_parcela, valor_parcela, valor_vista, tabela_completa, calendario_fixo_reunioes):
    qntParcela = int(qnt_parcela)
    # Copia a tabela recebida no parâmetro
    tabelaCompleta = tabela_completa.copy()
    saldo = valor_vista
    tabelaCompleta = tabelaCompleta.head(qntParcela)

    resultados = []
    resultadoArredondado = []

    tabelaCompleta = tabelaCompleta.loc[:, ~tabelaCompleta.columns.duplicated()].copy()

    mapa_colunas = {
        'numero_reuniao': 'Número Reunião',
        'numero reunião': 'Número Reunião',
        'ano_reuniao': 'Ano Reunião',
        'ano reunião': 'Ano Reunião',
        'ano': 'Ano Reunião',
        'mes_reuniao': 'Mês Reunião',
        'mês reunião': 'Mês Reunião',
        'mes': 'Mês Reunião',
        'mediana': 'Mediana',
        'juros_futuro': 'Juros Futuro',
        'juros futuro': 'Juros Futuro',
        'taxa_futura': 'Juros Futuro'
    }

    novas_colunas = {}
    for col in tabelaCompleta.columns:
        col_clean = str(col).lower().strip()
        if col_clean in mapa_colunas:
            novas_colunas[col] = mapa_colunas[col_clean]

    tabelaCompleta.rename(columns=novas_colunas, inplace=True)
    tabelaCompleta = tabelaCompleta.loc[:, ~tabelaCompleta.columns.duplicated()].copy()

    if 'Número Reunião' not in tabelaCompleta.columns:
        tabelaCompleta['Número Reunião'] = range(1, len(tabelaCompleta) + 1)

    tabelaCompleta['Número Reunião'] = pd.to_numeric(tabelaCompleta['Número Reunião'], errors='coerce').astype('Int64')

    mudou_reuniao = (tabelaCompleta['Número Reunião'] != tabelaCompleta['Número Reunião'].shift()) | (tabelaCompleta['Ano Reunião'] != tabelaCompleta['Ano Reunião'].shift())
    tabelaCompleta['Número Reunião Contínuo'] = mudou_reuniao.cumsum()

    n = tabelaCompleta['Número Reunião Contínuo'].iloc[-1] + 1

    for col_nome in ['Mediana', 'Juros Futuro']:
        serie_val = tabelaCompleta[col_nome]
        if isinstance(serie_val, pd.DataFrame):
            serie_val = serie_val.iloc[:, 0]
        
        serie_limpa = serie_val.astype(str).str.strip().str.replace(',', '.', regex=False)
        tabelaCompleta[col_nome] = pd.to_numeric(serie_limpa, errors='coerce')

    # Loop para o cálculo ponderado da taxa entre Focus e DI
    for i in range(len(tabelaCompleta)):
        if i == 0:
            num_reuniao = tabelaCompleta['Número Reunião Contínuo'].iloc[i]
            mediana = tabelaCompleta['Mediana'].iloc[i]
            juros_futuro = tabelaCompleta['Juros Futuro'].iloc[i]
            
            calculo = (((n - num_reuniao) / n) * mediana) + ((num_reuniao / n) * juros_futuro)
            resultados.append(calculo)
        else:
            reuniao_atual = tabelaCompleta['Número Reunião Contínuo'].iloc[i]
            reuniao_anterior = tabelaCompleta['Número Reunião Contínuo'].iloc[i - 1]
            
            if reuniao_atual == reuniao_anterior:
                resultados.append(resultados[-1])
            else:
                num_reuniao = tabelaCompleta['Número Reunião Contínuo'].iloc[i]
                mediana = tabelaCompleta['Mediana'].iloc[i]
                juros_futuro = tabelaCompleta['Juros Futuro'].iloc[i]
                
                calculo = (((n - num_reuniao) / n) * mediana) + ((num_reuniao / n) * juros_futuro)
                resultados.append(calculo)

    tabelaCompleta['Resultado Calculo'] = resultados

    for i in range(len(resultados)):
        numArredondado = round(resultados[i] / 0.25) * 0.25
        resultadoArredondado.append(numArredondado)

    tabelaCompleta['Resultado Calculo Arredondado'] = resultadoArredondado
    tabelaCompleta = tabelaCompleta.sort_index()

    cal = Calendar.load("ANBIMA")
    meses_com_copom = list(calendario_fixo_reunioes.values()) if calendario_fixo_reunioes else [1, 3, 5, 6, 8, 9, 11, 12]

    hoje = date.today()
    taxa_anterior = float(tabelaCompleta.iloc[0]['Resultado Calculo Arredondado'])
    historico_final = []

    for idx, (index_original, linha) in enumerate(tabelaCompleta.iterrows()):
        taxa_atual = float(linha['Resultado Calculo Arredondado'])
        fator_periodo = 1.0

        if idx == 0:
            ano = hoje.year
            mes = hoje.month
            _, ultimo_dia_mes = calendar.monthrange(ano, mes)
            data_fim_mes = date(ano, mes, ultimo_dia_mes)

            if hoje >= data_fim_mes:
                dias_uteis = 1
            else:
                dias_uteis = max(1, cal.bizdays(hoje, data_fim_mes))

            fator_unico = (1 + (taxa_atual / 100)) ** (1 / 252)
            fator_periodo = fator_unico ** dias_uteis
            saldo_final_mes = saldo * fator_periodo

        else:
            ano = int(linha['Ano Reunião'])
            mes = int(linha['Mês Reunião'])
            _, ultimo_dia_mes = calendar.monthrange(ano, mes)
            
            dias_uteis_totais = cal.bizdays(f"{ano}-{mes:02d}-01", f"{ano}-{mes:02d}-{ultimo_dia_mes:02d}")
            
            if mes in meses_com_copom:
                dias_fatia1 = dias_uteis_totais // 2
                dias_fatia2 = dias_uteis_totais - dias_fatia1
                
                fator_antigo = (1 + (taxa_anterior / 100)) ** (1 / 252)
                fator_novo = (1 + (taxa_atual / 100)) ** (1 / 252)
                
                fator_periodo = (fator_antigo ** dias_fatia1) * (fator_novo ** dias_fatia2)
                saldo_final_mes = saldo * fator_periodo
            
            else:
                fator_unico = (1 + (taxa_atual / 100)) ** (1 / 252)
                fator_periodo = fator_unico ** dias_uteis_totais
                saldo_final_mes = saldo * fator_periodo

        rendimento_pct = (fator_periodo - 1) * 100
        juros_ganhos = saldo_final_mes - saldo
        saldo_apos_pagamento = saldo_final_mes - valor_parcela
        
        ano_exibicao = int(linha['Ano Reunião'])
        mes_exibicao = int(linha['Mês Reunião'])

        historico_final.append({
            'Nº Parcela': idx + 1,
            'Período': f"{mes_exibicao:02d}/{ano_exibicao}",
            'Taxa Anual (% a.a.)': f"{taxa_atual:.2f}%", 
            'Rendimento Mês (%)': f"{rendimento_pct:.2f}%",
            'Saldo Inicial (R$)': round(saldo, 2),
            'Rendimento Juros (R$)': round(juros_ganhos, 2),
            'Saldo Final com Juros (R$)': round(saldo_final_mes, 2),
            'Parcela Paga (R$)': valor_parcela,
            'Saldo Pós-Parcela (R$)': round(saldo_apos_pagamento, 2)
        })
        
        saldo = saldo_apos_pagamento
        taxa_anterior = taxa_atual

    return pd.DataFrame(historico_final)