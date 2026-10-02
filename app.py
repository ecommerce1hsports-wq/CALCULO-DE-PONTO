import base64
import calendar
from datetime import datetime, timedelta
import json
import os
import requests
import streamlit as st

# Configuração da Página
st.set_page_config(
    page_title="HSports - Controle de Ponto", page_icon="⏱️", layout="wide"
)

# Configuração do GitHub
GITHUB_TOKEN = "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"
GITHUB_REPO = "ecommerce1hsports-wq/CALCULO-DE-PONTO"
CAMINHO_DB_JSON = "dados_ponto.json"


# Funções de Sincronização com o GitHub (JSON na Nuvem)
def carregar_dados_github():
  url = (
      f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CAMINHO_DB_JSON}"
  )
  headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
  response = requests.get(url, headers=headers)

  if response.status_code == 200:
    conteudo_base64 = response.json()["content"]
    conteudo_bytes = base64.b64decode(conteudo_base64)
    return json.loads(conteudo_bytes.decode("utf-8"))
  else:
    # Estrutura inicial se o arquivo ainda não existir no GitHub
    return {"funcionarios": [], "registros": {}}


def salvar_dados_github(dados):
  url = (
      f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CAMINHO_DB_JSON}"
  )
  headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

  # Obter o SHA atual do arquivo (necessário para atualizar no GitHub)
  resp_get = requests.get(url, headers=headers)
  sha = resp_get.json().get("sha") if resp_get.status_code == 200 else None

  conteudo_json = json.dumps(dados, indent=4, ensure_ascii=False)
  conteudo_base64 = base64.b64encode(conteudo_json.encode("utf-8")).decode(
      "utf-8"
  )

  payload = {
      "message": "Atualização automática de dados de ponto",
      "content": conteudo_base64,
  }
  if sha:
    payload["sha"] = sha

  requests.put(url, headers=headers, json=payload)


# Carrega os dados atuais da nuvem do GitHub para a memória
if "dados" not in st.session_state:
  st.session_state["dados"] = carregar_dados_github()


st.title("⏱️ HSports - Cartão de Ponto (Estilo Secullum)")
st.markdown(
    "**Jornada Padrão:** 07:45 às 12:00 | 13:15 às 17:48 (Carga diária:"
    " 08:48)"
)

# Menu lateral em formato de botões profissionais
st.sidebar.markdown("### 🎛️ Painel de Controle")
menu = st.sidebar.radio(
    "Navegação",
    ["Cartão de Ponto Mensal", "Lançamento Diário", "Gerenciar Funcionários"],
    label_visibility="collapsed",
)


# Função para formatar automaticamente o horário (ex: 755 ou 0755 -> 07:55)
def formatar_hora_digitada(texto):
  if not texto:
    return ""
  texto_limpo = "".join(filter(str.isdigit, str(texto)))
  if len(texto_limpo) == 3:
    texto_limpo = "0" + texto_limpo
  if len(texto_limpo) == 4:
    return f"{texto_limpo[:2]}:{texto_limpo[2:]}"
  return texto


# Função auxiliar para calcular o saldo de minutos considerando virada de noite
def calcular_saldo_dia(ent, sa_al, ret_al, sai):
  ent = formatar_hora_digitada(ent)
  sai = formatar_hora_digitada(sai)
  if not ent or not sai:
    return 0

  JORNADA_PADRAO_MINUTOS = 528  # 8h48m
  try:
    t_entrada = datetime.strptime(ent, "%H:%M")
    t_saida = datetime.strptime(sai, "%H:%M")

    minutos_totais = (t_saida - t_entrada).total_seconds() / 60
    if minutos_totais < 0:
      minutos_totais += 24 * 60

    if sa_al and ret_al:
      sa_al = formatar_hora_digitada(sa_al)
      ret_al = formatar_hora_digitada(ret_al)
      t_saida_almoco = datetime.strptime(sa_al, "%H:%M")
      t_retorno_almoco = datetime.strptime(ret_al, "%H:%M")
      minutos_almoco = (
          t_retorno_almoco - t_saida_almoco
      ).total_seconds() / 60
      if minutos_almoco < 0:
        minutos_almoco += 24 * 60
      minutos_totais -= minutos_almoco
    else:
      minutos_totais -= 75  # Intervalo padrão de almoço (12:00 até 13:15)

    return int(minutos_totais - JORNADA_PADRAO_MINUTOS)
  except:
    return 0


# Formatação do saldo diário: se < 60 min, mostra só minutos. Se >= 60 min, mostra horas.
def formatar_saldo_dia(minutos):
  if minutos is None:
    minutos = 0
  sinal = "-" if minutos < 0 else "+"
  minutos_abs = abs(minutos)

  if minutos_abs < 60:
    return f"{sinal}{minutos_abs} min"
  else:
    horas = minutos_abs // 60
    mins = minutos_abs % 60
    return f"{sinal}{horas:02d}:{mins:02d}"


# Formatação do acumulado do mês em horas
def formatar_horas(minutos):
  if minutos is None:
    minutos = 0
  sinal = "-" if minutos < 0 else "+"
  minutos_abs = abs(minutos)
  horas = minutos_abs // 60
  mins = minutos_abs % 60
  return f"{sinal}{horas:02d}:{mins:02d}"


# Função para gerar o HTML do relatório em PDF idêntico ao modelo
def gerar_html_pdf(func_nome, mes, ano, registros_mes):
  _, ultimo_dia = calendar.monthrange(ano, mes)

  html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 11px; color: #000; margin: 20px; }}
            .header {{ border: 1px solid #000; padding: 8px; margin-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 5px; }}
            th, td {{ border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 10px; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div style="float: right; font-weight: bold;">CARTÃO PONTO</div>
            <div><b>EMPRESA:</b> L&C PRESTADORA DE SERVIÇOS LTDA</div>
            <div><b>CNPJ:</b> 63.168.829/0001-18</div>
            <hr style="border: 0.5px solid #000; margin: 5px 0;">
            <div><b>NOME:</b> {func_nome}</div>
            <div><b>DEPARTAMENTO:</b> PRODUÇÃO &nbsp;&nbsp;&nbsp;&nbsp; <b>FUNÇÃO:</b> Auxiliar Produção</div>
            <div><b>PERÍODO:</b> 01/{mes:02d}/{ano} até {ultimo_dia:02d}/{mes:02d}/{ano}</div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>DATA</th>
                    <th>DIA</th>
                    <th>ENTRADA 1</th>
                    <th>SAÍDA 1</th>
                    <th>ENTRADA 2</th>
                    <th>SAÍDA 2</th>
                    <th>SALDO DIA</th>
                </tr>
            </thead>
            <tbody>
    """

  dias_sem_map = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
  total_minutos_mes = 0

  for dia in range(1, ultimo_dia + 1):
    data_str = f"{dia:02d}/{mes:02d}/{ano}"
    dt_obj = datetime(ano, mes, dia)
    d_sem = dias_sem_map[dt_obj.weekday()]

    reg = registros_mes.get(data_str, ("", "", "", "", 0))
    e1, s1, e2, s2, saldo = reg

    if dt_obj.weekday() >= 5 and not (e1 or s1 or e2 or s2):
      e1_fmt, s1_fmt, e2_fmt, s2_fmt = "FOLGA", "FOLGA", "FOLGA", "FOLGA"
      saldo_txt = "00:00"
    else:
      e1_fmt = formatar_hora_digitada(e1) if e1 else "-"
      s1_fmt = formatar_hora_digitada(s1) if s1 else "-"
      e2_fmt = formatar_hora_digitada(e2) if e2 else "-"
      s2_fmt = formatar_hora_digitada(s2) if s2 else "-"
      s_calc = calcular_saldo_dia(e1, s1, e2, s2)
      total_minutos_mes += s_calc
      saldo_txt = formatar_saldo_dia(s_calc)

    html += f"""
            <tr>
                <td><b>{data_str}</b></td>
                <td>{d_sem}</td>
                <td>{e1_fmt}</td>
                <td>{s1_fmt}</td>
                <td>{e2_fmt}</td>
                <td>{s2_fmt}</td>
                <td><b>{saldo_txt}</b></td>
            </tr>
        """

  saldo_total_txt = formatar_horas(total_minutos_mes)
  html += f"""
            </tbody>
        </table>
        <br>
        <div style="border: 1px solid #000; padding: 6px;">
            <b>TOTAIS DO PERÍODO:</b> Saldo Acumulado: <b>{saldo_total_txt} horas</b>
        </div>
    </body>
    </html>
    """
  return html


# ---------------------------------------------------------
# 1. CARTÃO DE PONTO MENSAL
# ---------------------------------------------------------
if menu == "Cartão de Ponto Mensal":
  st.header("Cartão de Ponto - Visualização e Edição Mensal")

  funcs = st.session_state["dados"]["funcionarios"]

  if not funcs:
    st.warning("Cadastre um funcionário primeiro na aba lateral.")
  else:
    func_dict = {f"{f['id']} - {f['nome']}": f for f in funcs}
    selecao = st.selectbox(
        "Selecione o Funcionário:", options=list(func_dict.keys())
    )
    f_dados = func_dict[selecao]
    func_id, func_nome = f_dados["id"], f_dados["nome"]

    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    anos_disponiveis = [2025, 2026, 2027, 2028]
    idx_ano = (
        anos_disponiveis.index(ano_atual)
        if ano_atual in anos_disponiveis
        else 1
    )

    col_m1, col_m2 = st.columns(2)
    with col_m1:
      ano_sel = st.selectbox(
          "Ano", anos_disponiveis, index=idx_ano
      )
    with col_m2:
      mes_sel = st.selectbox(
          "Mês",
          list(range(1, 13)),
          index=mes_atual - 1,
          format_func=lambda x: [
              "Janeiro",
              "Fevereiro",
              "Março",
              "Abril",
              "Maio",
              "Junho",
              "Julho",
              "Agosto",
              "Setembro",
              "Outubro",
              "Novembro",
              "Dezembro",
          ][x - 1],
      )

    _, ultimo_dia = calendar.monthrange(ano_sel, mes_sel)
    dias_semana_map = {
        0: "Seg",
        1: "Ter",
        2: "Qua",
        3: "Qui",
        4: "Sex",
        5: "Sáb",
        6: "Dom",
    }

    registros_todos = st.session_state["dados"]["registros"]
    registros_db = registros_todos.get(str(func_id), {})

    st.markdown("---")

    with st.form(f"form_cartao_{func_id}_{mes_sel}"):
      btn_salvar_topo = st.form_submit_button(
          "💾 SALVAR ALTERAÇÕES (TOPO)", use_container_width=True
      )

      st.markdown("### Espelho de Ponto Diário")

      cols_cab = st.columns([1, 1, 1.2, 1.2, 1.2, 1.2, 1.5])
      cols_cab[0].markdown("**Data**")
      cols_cab[1].markdown("**Dia**")
      cols_cab[2].markdown("**Entrada 1**")
      cols_cab[3].markdown("**Saída 1**")
      cols_cab[4].markdown("**Entrada 2**")
      cols_cab[5].markdown("**Saída 2**")
      cols_cab[6].markdown("**Saldo Dia**")

      novos_dados = []

      for dia in range(1, ultimo_dia + 1):
        data_str = f"{dia:02d}/{mes_sel:02d}/{ano_sel}"
        dt_obj = datetime(ano_sel, mes_sel, dia)
        d_sem = dias_semana_map[dt_obj.weekday()]

        r = registros_db.get(data_str, ["", "", "", "", 0])
        e1, s1, e2, s2 = r[0] or "", r[1] or "", r[2] or "", r[3] or ""

        c_linha = st.columns([1, 1, 1.2, 1.2, 1.2, 1.2, 1.5])
        c_linha[0].text(data_str)
        c_linha[1].text(d_sem)

        val_e1 = c_linha[2].text_input(
            f"e1_{dia}", value=e1, label_visibility="collapsed"
        )
        val_s1 = c_linha[3].text_input(
            f"s1_{dia}", value=s1, label_visibility="collapsed"
        )
        val_e2 = c_linha[4].text_input(
            f"e2_{dia}", value=e2, label_visibility="collapsed"
        )
        val_s2 = c_linha[5].text_input(
            f"s2_{dia}", value=s2, label_visibility="collapsed"
        )

        f_e1 = formatar_hora_digitada(val_e1)
        f_s1 = formatar_hora_digitada(val_s1)
        f_e2 = formatar_hora_digitada(val_e2)
        f_s2 = formatar_hora_digitada(val_s2)

        s_calc = calcular_saldo_dia(f_e1, f_s1, f_e2, f_s2)
        saldo_formatado = formatar_saldo_dia(s_calc)
        c_linha[6].text(saldo_formatado)

        novos_dados.append(
            (data_str, d_sem, f_e1, f_s1, f_e2, f_s2, s_calc)
        )

      btn_salvar_baixo = st.form_submit_button(
          "💾 SALVAR ALTERAÇÕES (FINAL)", use_container_width=True
      )

      if btn_salvar_topo or btn_salvar_baixo:
        if str(func_id) not in st.session_state["dados"]["registros"]:
          st.session_state["dados"]["registros"][str(func_id)] = {}

        for item in novos_dados:
          d_str, d_sem_str, v_e1, v_s1, v_e2, v_s2, v_sal = item
          st.session_state["dados"]["registros"][str(func_id)][d_str] = [
              v_e1,
              v_s1,
              v_e2,
              v_s2,
              v_sal,
          ]

        # Salva automaticamente no GitHub
        salvar_dados_github(st.session_state["dados"])
        st.success("Cartão de ponto salvo e sincronizado no GitHub com sucesso!")
        st.rerun()

    st.markdown("---")
    st.subheader("📥 Exportar Relatório Oficial")
    if st.button("Gerar Relatório em PDF (Estilo Secullum)"):
      html_conteudo = gerar_html_pdf(
          func_nome, mes_sel, ano_sel, registros_db
      )
      st.download_button(
          label="Clique aqui para baixar o arquivo HTML do Relatório (Pronto para Imprimir/Salvar em PDF)",
          data=html_conteudo,
          file_name=f"cartao_ponto_{func_nome.replace(' ', '_')}_{mes_sel:02d}_{ano_sel}.html",
          mime="text/html",
      )

# ---------------------------------------------------------
# 2. LANÇAMENTO DIÁRIO
# ---------------------------------------------------------
elif menu == "Lançamento Diário":
  st.header("Marcação Rápida de Ponto do Dia")

  funcs = st.session_state["dados"]["funcionarios"]

  if not funcs:
    st.warning("Nenhum funcionário cadastrado.")
  else:
    func_dict = {f"{f['id']} - {f['nome']}": f["id"] for f in funcs}
    selecao = st.selectbox(
        "Selecione o Funcionário:", options=list(func_dict.keys())
    )
    func_id = func_dict[selecao]

    data_hoje = datetime.now().strftime("%d/%m/%Y")
    data_input = st.text_input("Data do Registro (DD/MM/AAAA)", value=data_hoje)

    registros_db = st.session_state["dados"]["registros"].get(
        str(func_id), {}
    )
    reg_atual = registros_db.get(data_input, None)

    e1_t = reg_atual[0] if reg_atual and reg_atual[0] else "07:45"
    s1_t = reg_atual[1] if reg_atual and reg_atual[1] else "12:00"
    e2_t = reg_atual[2] if reg_atual and reg_atual[2] else "13:15"
    s2_t = reg_atual[3] if reg_atual and reg_atual[3] else "17:48"

    with st.form("form_diario_unico"):
      c1, c2, c3, c4 = st.columns(4)
      with c1:
        ent1 = st.text_input("Entrada 1 (ex: 0755)", value=e1_t)
      with c2:
        sai1 = st.text_input("Saída Almoço (ex: 1200)", value=s1_t)
      with c3:
        ent2 = st.text_input("Retorno Almoço (ex: 1315)", value=e2_t)
      with c4:
        sai2 = st.text_input("Saída Final (ex: 1748)", value=s2_t)

      btn_gravar = st.form_submit_button("Salvar Registro do Dia")

      if btn_gravar:
        f_ent1 = formatar_hora_digitada(ent1)
        f_sai1 = formatar_hora_digitada(sai1)
        f_ent2 = formatar_hora_digitada(ent2)
        f_sai2 = formatar_hora_digitada(sai2)

        saldo_m = calcular_saldo_dia(f_ent1, f_sai1, f_ent2, f_sai2)

        if str(func_id) not in st.session_state["dados"]["registros"]:
          st.session_state["dados"]["registros"][str(func_id)] = {}

        st.session_state["dados"]["registros"][str(func_id)][data_input] = [
            f_ent1,
            f_sai1,
            f_ent2,
            f_sai2,
            saldo_m,
        ]

        # Salva automaticamente no GitHub
        salvar_dados_github(st.session_state["dados"])

        st.success(
            f"Ponto do dia {data_input} salvo e sincronizado no GitHub! Saldo:"
            f" {formatar_saldo_dia(saldo_m)}"
        )
        st.rerun()

# ---------------------------------------------------------
# 3. GERENCIAR FUNCIONÁRIOS
# ---------------------------------------------------------
elif menu == "Gerenciar Funcionários":
  st.header("Gerenciamento de Funcionários")

  st.subheader("➕ Cadastrar Novo Funcionário")
  with st.form("form_cad"):
    nome_novo = st.text_input("Nome Completo do Funcionário")
    submit = st.form_submit_button("Cadastrar Funcionário")

    if submit:
      if nome_novo.strip() == "":
        st.error("O nome não pode estar vazio.")
      else:
        funcs = st.session_state["dados"]["funcionarios"]
        novo_id = max([f["id"] for f in funcs], default=0) + 1
        funcs.append({"id": novo_id, "nome": nome_novo.strip()})

        # Salva automaticamente no GitHub
        salvar_dados_github(st.session_state["dados"])

        st.success(
            f"Funcionário {nome_novo} cadastrado e sincronizado no GitHub!"
        )
        st.rerun()

  st.markdown("---")
  st.subheader("✏️ Editar Nome de Funcionário Existente")

  todos_funcs = st.session_state["dados"]["funcionarios"]

  if not todos_funcs:
    st.info("Nenhum funcionário cadastrado para editar.")
  else:
    func_edit_dict = {f"{f['id']} - {f['nome']}": f for f in todos_funcs}
    selecao_edit = st.selectbox(
        "Selecione o Funcionário para Editar:",
        options=list(func_edit_dict.keys()),
    )
    f_atual = func_edit_dict[selecao_edit]
    f_id_edit, f_nome_atual = f_atual["id"], f_atual["nome"]

    with st.form("form_edicao_func"):
      novo_nome_input = st.text_input(
          "Alterar Nome Completo", value=f_nome_atual
      )
      btn_salvar_nome = st.form_submit_button("Salvar Alteração do Nome")

      if btn_salvar_nome:
        if novo_nome_input.strip() == "":
          st.error("O nome não pode ficar vazio.")
        else:
          for f in st.session_state["dados"]["funcionarios"]:
            if f["id"] == f_id_edit:
              f["nome"] = novo_nome_input.strip()

          # Salva automaticamente no GitHub
          salvar_dados_github(st.session_state["dados"])

          st.success("Nome atualizado e sincronizado no GitHub com sucesso!")
          st.rerun()