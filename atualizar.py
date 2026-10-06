from servicosDados.dadosFuturo import puxar_dados_juros_futuro
from servicosDados.dadosFocus import puxar_dados_da_api_anual, puxar_dados_da_api_reuniao
from banco import inicializar_banco, salvar_focus_no_banco, salvar_futuros_no_banco

def atualizar_tudo():
    print("Iniciando a atualização dos dados...")

    inicializar_banco()
    
    # Atualiza Focus
    try:
        print("Buscando dados do Boletim Focus")
        anual = puxar_dados_da_api_anual()
        focus, _ = puxar_dados_da_api_reuniao(anual)
        if not focus.empty:
            salvar_focus_no_banco(focus)
            print("Focus atualizado no banco!")
    except Exception as e:
        print(f"Erro na atualização da Focus: {e}")

    # Atualiza Juros Futuros
    try:
        print("Executando raspagem do InfoMoney")
        futuro = puxar_dados_juros_futuro()
        if not futuro.empty:
            salvar_futuros_no_banco(futuro)
            print("Juros Futuros atualizados no banco!")
    except Exception as e:
        print(f"Erro na raspagem dos Futuros: {e}")

    print("Atualização concluída!")

if __name__ == '__main__':
    atualizar_tudo()