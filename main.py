from flask import Flask, render_template, request
import pandas as pd
from servicosDados.dadosFocus import puxar_dados_da_api_anual, puxar_dados_da_api_reuniao
from calculos.calculos import realizar_calculo_financeiro
from banco import inicializar_banco, carregar_tabela_simulacao
from atualizar import atualizar_tudo
import sqlite3

inicializar_banco()
try:
    atualizar_tudo()
except Exception as e:
    print(f"Aviso na atualização inicial: {e}")
app = Flask(__name__)

# Garante que as tabelas existam ao subir a aplicação
inicializar_banco()


def carregar_dados_mercado():
    """Lê as tabelas brutas do Focus e Juros Futuros diretamente do banco SQLite."""
    conn = sqlite3.connect('dados_simulador.db')

    try:
        df_focus = pd.read_sql("SELECT * FROM tb_focus", conn)
    except Exception:
        df_focus = pd.DataFrame()

    try:
        df_juros = pd.read_sql("SELECT * FROM tb_juros_futuros", conn)
    except Exception:
        df_juros = pd.DataFrame()

    conn.close()
    return df_focus, df_juros


def formatar_nome_coluna(col_name):
    """Converte 'data_referencia' para 'Data Referência' e trata acentuações."""
    mapeamento_customizado = {
        'data_referencia': 'Data Referência',
        'data_cotacao': 'Data Cotação',
        'taxa_esperada': 'Taxa Esperada (%)',
        'taxa_fechamento': 'Taxa Fechamento (%)',
        'data_vencimento': 'Data Vencimento',
        'vencimento': 'Vencimento',
        'codigo': 'Código'
    }

    col_clean = col_name.lower().strip()
    if col_clean in mapeamento_customizado:
        return mapeamento_customizado[col_clean]

    # Regra geral: substitui '_' por espaço e coloca em Title Case
    return col_name.replace('_', ' ').title()


@app.route('/dados')
def pagina_dados():
    df_focus, df_juros = carregar_dados_mercado()

    chart_focus = {'labels': [], 'data': []}
    chart_juros = {'labels': [], 'data': []}

    # ==========================================
    # 1. TRATAMENTO DA TABELA BOLETIM FOCUS
    # ==========================================
    if not df_focus.empty:
        # Identifica colunas para o gráfico
        col_data_f = [c for c in df_focus.columns if 'data' in c.lower() or 'dt' in c.lower() or 'reuni' in c.lower()]
        col_taxa_f = [c for c in df_focus.columns if
                      'taxa' in c.lower() or 'selic' in c.lower() or 'esperada' in c.lower() or 'valor' in c.lower()]

        col_lbl_f = col_data_f[0] if col_data_f else df_focus.columns[0]
        col_val_f = col_taxa_f[0] if col_taxa_f else (
            df_focus.columns[1] if len(df_focus.columns) > 1 else df_focus.columns[0])

        try:
            # Formata rótulos do Eixo X para DD/MM/AAAA sem horários
            labels_f = pd.to_datetime(df_focus[col_lbl_f], errors='coerce').dt.strftime('%d/%m/%Y')
            chart_focus['labels'] = labels_f.fillna(df_focus[col_lbl_f].astype(str).str.split(' ').str[0]).tolist()

            # Converte valores numéricos para float (aceita vírgula ou ponto)
            vals_f = df_focus[col_val_f].astype(str).str.replace(',', '.').str.extract(r'(\d+\.?\d*)')[0]
            chart_focus['data'] = pd.to_numeric(vals_f, errors='coerce').fillna(0).tolist()
        except Exception as e:
            print(f"Erro ao processar gráfico Focus: {e}")

        # Tabela para exibição HTML
        df_focus_exibicao = df_focus.copy()

        # Remove coluna redundante de reunião
        colunas_para_remover = [col for col in df_focus_exibicao.columns if 'reuni' in col.lower()]
        df_focus_exibicao = df_focus_exibicao.drop(
            columns=[c for c in colunas_para_remover if c in df_focus_exibicao.columns])

        # Formata datas da tabela
        for col in df_focus_exibicao.columns:
            if 'data' in col.lower() or 'dt' in col.lower():
                df_focus_exibicao[col] = pd.to_datetime(df_focus_exibicao[col], errors='coerce').dt.strftime('%d/%m/%Y')

        # Formata títulos das colunas
        df_focus_exibicao.columns = [formatar_nome_coluna(c) for c in df_focus_exibicao.columns]
    else:
        df_focus_exibicao = df_focus

    # ==========================================
    # 2. TRATAMENTO DA TABELA JUROS FUTUROS
    # ==========================================
    if not df_juros.empty:
        col_data_j = [c for c in df_juros.columns if
                      'venc' in c.lower() or 'codigo' in c.lower() or 'data' in c.lower()]
        col_taxa_j = [c for c in df_juros.columns if
                      'taxa' in c.lower() or 'fechamento' in c.lower() or 'valor' in c.lower()]

        col_lbl_j = col_data_j[0] if col_data_j else df_juros.columns[0]
        col_val_j = col_taxa_j[0] if col_taxa_j else (
            df_juros.columns[1] if len(df_juros.columns) > 1 else df_juros.columns[0])

        try:
            # Formata rótulos do Eixo X sem horários
            labels_j = pd.to_datetime(df_juros[col_lbl_j], errors='coerce').dt.strftime('%d/%m/%Y')
            chart_juros['labels'] = labels_j.fillna(df_juros[col_lbl_j].astype(str).str.split(' ').str[0]).tolist()

            # Converte valores numéricos para float
            vals_j = df_juros[col_val_j].astype(str).str.replace(',', '.').str.extract(r'(\d+\.?\d*)')[0]
            chart_juros['data'] = pd.to_numeric(vals_j, errors='coerce').fillna(0).tolist()
        except Exception as e:
            print(f"Erro ao processar gráfico Juros: {e}")

        # Tabela para exibição HTML
        df_juros_exibicao = df_juros.copy()

        for col in df_juros_exibicao.columns:
            if 'data' in col.lower() or 'dt' in col.lower():
                df_juros_exibicao[col] = pd.to_datetime(df_juros_exibicao[col], errors='coerce').dt.strftime('%d/%m/%Y')

        df_juros_exibicao.columns = [formatar_nome_coluna(c) for c in df_juros_exibicao.columns]
    else:
        df_juros_exibicao = df_juros

    # ==========================================
    # 3. RENDERIZAÇÃO DAS TABELAS EM HTML
    # ==========================================
    classes_tabela = 'table table-sm table-striped table-hover align-middle text-center mb-0'

    focus_html = df_focus_exibicao.to_html(
        classes=classes_tabela,
        index=False,
        float_format=lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    ) if not df_focus_exibicao.empty else "<p class='text-muted p-3 text-center'>Nenhum dado do Boletim Focus encontrado.</p>"

    juros_html = df_juros_exibicao.to_html(
        classes=classes_tabela,
        index=False,
        float_format=lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    ) if not df_juros_exibicao.empty else "<p class='text-muted p-3 text-center'>Nenhum dado de Juros Futuros encontrado.</p>"

    return render_template(
        'dados.html',
        tabela_focus=focus_html,
        tabela_juros=juros_html,
        chart_focus=chart_focus,
        chart_juros=chart_juros
    )

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