import pandas as pd
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def puxar_dados_juros_futuro():
    print("Buscando dados de juros futuros via raspagem no InfoMoney (Playwright)...")

    url = "https://www.infomoney.com.br/ferramentas/juros-futuros-di/"
    lista_contratos = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

            # Navega até a página
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Espera o elemento existir na árvore DOM (mesmo que com classe hidden)
            page.wait_for_selector("#contratos_di_futuro", state="attached", timeout=20000)
            
            # Aguarda 3 segundos extras para garantir que o JS do InfoMoney preencheu as linhas <tr>
            page.wait_for_timeout(3000)

            html = page.content()
            browser.close()

        site = BeautifulSoup(html, 'html.parser')
        
        # Busca a tabela específica pelo ID capturado no Playwright
        tabela_element = site.find('table', id='contratos_di_futuro')
        if not tabela_element:
            tabela_element = site.find('table')

        linhas = tabela_element.find_all('tr') if tabela_element else []

        for linha in linhas:
            celulas = linha.find_all('td')
            if len(celulas) >= 3:
                codigo = celulas[0].text.strip().upper()
                
                if "DI1" in codigo:
                    taxa_encontrada = None
                    
                    # Varre as colunas procurando o valor numérico com vírgula/ponto %
                    for col in celulas[1:]:
                        texto_col = col.text.strip()
                        if (',' in texto_col or '.' in texto_col) and '/' not in texto_col:
                            taxa_encontrada = texto_col
                            break

                    if not taxa_encontrada and len(celulas) >= 3:
                        taxa_encontrada = celulas[2].text.strip()

                    if taxa_encontrada:
                        clean_taxa = re.sub(r'[^\d,. -]', '', taxa_encontrada).strip().replace(',', '.')

                        if clean_taxa and clean_taxa != '-':
                            lista_contratos.append({"Contrato": codigo, "Taxa Futura": clean_taxa})

        tabelaJurosFuturo = pd.DataFrame(lista_contratos)

        if tabelaJurosFuturo.empty:
            print("⚠️ AVISO: Nenhuma linha 'DI1' foi encontrada dentro de #contratos_di_futuro.")
            return pd.DataFrame(columns=['Ano', 'Mês', 'Taxa Futura'])

        tabelaJurosFuturo['Taxa Futura'] = pd.to_numeric(tabelaJurosFuturo['Taxa Futura'], errors='coerce')
        
        # Descarta linhas nulas ou datas inteiras
        tabelaJurosFuturo = tabelaJurosFuturo[tabelaJurosFuturo['Taxa Futura'] < 100]
        tabelaJurosFuturo = tabelaJurosFuturo.dropna(subset=['Taxa Futura'])
        tabelaJurosFuturo = tabelaJurosFuturo.drop_duplicates(subset=['Contrato']).reset_index(drop=True)

        tabelaJurosFuturo['Código Mês'] = tabelaJurosFuturo['Contrato'].str.split('DI1').str[1]
        tabelaJurosFuturo['Ano'] = tabelaJurosFuturo['Código Mês'].str.replace(r'\D+', '', regex=True)
        tabelaJurosFuturo['Código Mês'] = tabelaJurosFuturo['Código Mês'].str.replace(r'\d+', '', regex=True)

        tabelaJurosFuturo['Ano'] = tabelaJurosFuturo['Ano'].astype(int) + 2000

        tabelaMeses = {'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6, 'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12}
        tabelaJurosFuturo['Mês Vencimento'] = tabelaJurosFuturo['Código Mês'].map(tabelaMeses)

        # Regra M+1
        tabelaJurosFuturo['Mês'] = tabelaJurosFuturo['Mês Vencimento'] - 1
        tabelaJurosFuturo.loc[tabelaJurosFuturo['Mês'] == 0, 'Ano'] -= 1
        tabelaJurosFuturo.loc[tabelaJurosFuturo['Mês'] == 0, 'Mês'] = 12

        tabelaJurosFuturo = tabelaJurosFuturo.sort_values(by=['Ano', 'Mês']).reset_index(drop=True)

        print("\n--- DADOS RASPADOS COM SUCESSO DO INFOMONEY ---")
        print(tabelaJurosFuturo[['Ano', 'Mês', 'Taxa Futura']].head(10).to_string())
        print("------------------------------------------------\n")

        return tabelaJurosFuturo[['Ano', 'Mês', 'Taxa Futura']]

    except Exception as e:
        print(f"Erro ao raspar InfoMoney via Playwright: {e}")
        return pd.DataFrame(columns=['Ano', 'Mês', 'Taxa Futura'])