from flask import Flask, render_template, request
import pandas as pd
from servicosDados.dadosFocus import puxar_dados_da_api_anual, puxar_dados_da_api_reuniao
from calculos.calculos import realizar_calculo_financeiro
from banco import inicializar_banco, carregar_tabela_simulacao
from atualizar import atualizar_tudo

inicializar_banco()
try:
    atualizar_tudo()
except Exception as e:
    print(f"Aviso na atualização inicial: {e}")
app = Flask(__name__)

# Garante que as tabelas existam ao subir a aplicação
inicializar_banco()

# Formatar Moeda
@app.template_filter('moeda_br')
def moeda_br(valor):
    try:
        val = float(valor)
        return f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "0,00"


@app.route('/')
def index():
    tabela_completa = carregar_tabela_simulacao()
    qntTabela = len(tabela_completa) if not tabela_completa.empty else 0
    return render_template('index.html', max_parcelas=qntTabela)


@app.route('/calcular', methods=['POST'])
def calcular():
    print("🖱️ [Botão Pressionado] O usuário clicou em Simular!")

    tabela_completa = carregar_tabela_simulacao()
    qntTabela = len(tabela_completa)

    if tabela_completa.empty:
        return render_template('index.html', max_parcelas=0,
                               erro="Dados indisponíveis. Execute o script 'atualizar.py'.")

    valor_vista = request.form.get('valor_vista', type=float, default=0.0)
    parcelas = request.form.get('parcelas', type=int, default=1)

    modo_prazo = request.form.get('modo_prazo', default='parcela')
    valor_parcela_input = request.form.get('valor_parcela', type=float, default=0.0)
    valor_total_prazo_input = request.form.get('valor_total_prazo', type=float, default=0.0)

    # Lógica para definir o valor por parcela
    if modo_prazo == 'total' and parcelas > 0:
        valor_parcela = valor_total_prazo_input / parcelas
    else:
        valor_parcela = valor_parcela_input

    # Busca calendário fixo para a rotina de cálculo
    anual_temp = puxar_dados_da_api_anual()
    _, calendario_fixo_reunioes = puxar_dados_da_api_reuniao(anual_temp)

    tabela_para_calculo = tabela_completa.copy()

    resultado = realizar_calculo_financeiro(
        qnt_parcela=parcelas,
        valor_parcela=valor_parcela,
        valor_vista=valor_vista,
        tabela_completa=tabela_para_calculo,
        calendario_fixo_reunioes=calendario_fixo_reunioes
    )

    # Renderização da Tabela HTML com números em padrão Br
    tabela_html = resultado.to_html(
        classes='table table-sm table-striped table-hover align-middle text-center mb-0',
        index=False,
        float_format=lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    )

    linha_vista = [valor_vista] + [0.0] * (len(resultado) - 1)

    # Cálculo da Sobra/Custo
    saldo_final_prazo = resultado['Saldo Pós-Parcela (R$)'].iloc[
        -1] if 'Saldo Pós-Parcela (R$)' in resultado.columns else 0.0
    se_vale_prazo = saldo_final_prazo > 0
    diferenca_sobra = abs(saldo_final_prazo)

    dados_grafico = {
        'labels': resultado['Período'].tolist(),
        'saldo_pos': resultado['Saldo Pós-Parcela (R$)'].tolist(),
        'desembolso_vista': linha_vista
    }

    return render_template(
        'index.html',
        tabela=tabela_html,
        dados_grafico=dados_grafico,
        max_parcelas=qntTabela,
        valor_vista=valor_vista,
        valor_parcela=valor_parcela,
        valor_total_prazo=valor_total_prazo_input,
        parcelas=parcelas,
        modo_prazo=modo_prazo,
        se_vale_prazo=se_vale_prazo,
        saldo_final_prazo=saldo_final_prazo,
        diferenca_sobra=diferenca_sobra
    )


if __name__ == '__main__':
    app.run(debug=True)