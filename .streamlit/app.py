from pathlib import Path
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import datetime
import os
import json
import time
from fpdf import FPDF
import base64

# ----------------------
# CONFIGURAÇÕES GERAIS
# ----------------------
st.set_page_config(page_title="CVT App", layout="centered", page_icon="⚙️")

SHEET_NAME = "CVT_DB"
CVT_SHEET = "CVT"
REQ_SHEET = "REQUISICOES"
USERS_SHEET = "USERS"
CLIENTES_SHEET = "CLIENTES"
PECAS_SHEET = "PECAS"

# CSVs de fallback (mesmos nomes esperados)
CVT_CSV = "cvt_local.csv"
REQ_CSV = "requisicoes_local.csv"
USERS_CSV = "users_local.csv"
CLIENTES_CSV = "clientes_local.csv"
PECAS_CSV = "pecas_local.csv"

# Colunas esperadas (ordem usada ao salvar)
CVT_COLUMNS = [
    "created_at", "tecnico", "cliente", "endereco", "servico_realizado",
    "obs", "pecas_requeridas", "elevador", "status_cvt", "numero_cvt"
]

REQ_COLUMNS = [
    "created_at", "tecnico", "numero_cvt", "ordem_id", "peca_codigo",
    "peca_descricao", "quantidade", "status", "prioridade", "observacoes"
]

# ----------------------
# GOOGLE SHEETS INIT
# ----------------------
@st.cache_resource
def init_gsheets_client():
    """
    Inicializa o cliente gspread usando st.secrets['gcp_service_account'] ou arquivo service_account.json.
    Retorna o client gspread ou None.
    """
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
    except Exception as e:
        # gspread não instalado
        st.warning("gspread / oauth2client não encontrados. Instale com: pip install gspread oauth2client")
        return None

    sa_info = None
    # Prioriza st.secrets
    if "gcp_service_account" in st.secrets:
        try:
            sa_info = json.loads(st.secrets["gcp_service_account"])
        except Exception as e:
            st.error("Erro ao ler st.secrets['gcp_service_account']: " + str(e))
            return None
    elif os.path.exists("service_account.json"):
        try:
            with open("service_account.json", "r", encoding="utf-8") as f:
                sa_info = json.load(f)
        except Exception as e:
            st.error("Erro ao ler service_account.json: " + str(e))
            return None
    else:
        # Sem credenciais; usar fallback CSV
        return None

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error("Erro ao autorizar Google Sheets: " + str(e))
        return None


@st.cache_resource
def get_spreadsheet_and_worksheets():
    """
    Retorna dicionário com client, spreadsheet e worksheets (ou None se não for possível).
    Caches o resultado para reduzir chamadas.
    """
    client = init_gsheets_client()
    if not client:
        return {"client": None, "spreadsheet": None, "worksheets": {}}

    try:
        spreadsheet = client.open(SHEET_NAME)
    except Exception as e:
        # Tenta abrir por URL ou avisa
        try:
            spreadsheet = client.open(SHEET_NAME)
        except Exception as e2:
            st.error(f"Não foi possível abrir a planilha '{SHEET_NAME}': {e2}")
            return {"client": client, "spreadsheet": None, "worksheets": {}}

    def safe_get_ws(ss, name):
        try:
            return ss.worksheet(name)
        except Exception:
            return None

    worksheets = {
        "cvt": safe_get_ws(spreadsheet, CVT_SHEET),
        "req": safe_get_ws(spreadsheet, REQ_SHEET),
        "users": safe_get_ws(spreadsheet, USERS_SHEET),
        "clientes": safe_get_ws(spreadsheet, CLIENTES_SHEET),
        "pecas": safe_get_ws(spreadsheet, PECAS_SHEET)
    }

    return {"client": client, "spreadsheet": spreadsheet, "worksheets": worksheets}


def using_gsheets():
    info = get_spreadsheet_and_worksheets()
    return info["client"] is not None and info["spreadsheet"] is not None

# ----------------------
# LEITURA E GRAVAÇÃO (Sheets / CSV fallback)
# ----------------------
@st.cache_data(ttl=60)
def read_sheet(sheet_key):
    """
    sheet_key: uma das chaves 'cvt', 'req', 'users', 'clientes', 'pecas'
    Retorna DataFrame (pode ser vazio).
    """
    info = get_spreadsheet_and_worksheets()
    ws = info["worksheets"].get(sheet_key) if info and info.get("worksheets") else None

    # Mapeia chaves pras constantes de nome e CSV
    mapping = {
        "cvt": (CVT_SHEET, CVT_CSV),
        "req": (REQ_SHEET, REQ_CSV),
        "users": (USERS_SHEET, USERS_CSV),
        "clientes": (CLIENTES_SHEET, CLIENTES_CSV),
        "pecas": (PECAS_SHEET, PECAS_CSV)
    }

    sheet_name, csv_path = mapping.get(sheet_key, (None, None))

    if ws is not None:
        try:
            records = ws.get_all_records()
            df = pd.DataFrame(records)
            return df
        except Exception as e:
            st.warning(f"Erro ao obter registros da worksheet '{sheet_name}': {e}")

    # Fallback CSV
    if csv_path and os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            return df
        except Exception as e:
            st.warning(f"Erro ao ler CSV de fallback '{csv_path}': {e}")

    # Retorna DataFrame vazio
    return pd.DataFrame()


def append_to_sheet(sheet_key, row_dict_or_list):
    """
    Adiciona uma linha no sheet ou no CSV fallback.
    row_dict_or_list: pode ser lista (ordem) ou dict (col->val).
    """
    info = get_spreadsheet_and_worksheets()
    ws = info["worksheets"].get(sheet_key) if info and info.get("worksheets") else None

    mapping = {
        "cvt": (CVT_SHEET, CVT_CSV, CVT_COLUMNS),
        "req": (REQ_SHEET, REQ_CSV, REQ_COLUMNS)
    }

    if sheet_key not in mapping:
        st.error("Chave de planilha inválida para append.")
        return False

    sheet_name, csv_path, columns = mapping[sheet_key]

    # Converter dict em lista na ordem correta
    if isinstance(row_dict_or_list, dict):
        row = [row_dict_or_list.get(col, "") for col in columns]
    else:
        row = row_dict_or_list

    if ws is not None:
        try:
            # Usar input option para manter formatos
            ws.append_row(row, value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            st.warning(f"Erro ao salvar na worksheet '{sheet_name}': {e}")

    # Fallback CSV
    try:
        if os.path.exists(csv_path):
            existing = pd.read_csv(csv_path)
            new_row_df = pd.DataFrame([row], columns=columns)
            combined = pd.concat([existing, new_row_df], ignore_index=True)
        else:
            new_row_df = pd.DataFrame([row], columns=columns)
            combined = new_row_df
        combined.to_csv(csv_path, index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no CSV de fallback '{csv_path}': {e}")
        return False

# ----------------------
# UTILIDADES (tempo, pdf)
# ----------------------
def get_brasilia_time():
    return datetime.datetime.utcnow() - datetime.timedelta(hours=3)


def gerar_pdf_cvt(dados_cvt, pecas=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "COMPROVANTE DE VISITA TÉCNICA", ln=1, align="C")
    pdf.ln(6)

    pdf.set_font("Arial", "", 11)
    # Ordenar exibição para ficar legível
    campos_ordem = ["numero_cvt", "created_at", "tecnico", "cliente", "endereco", "elevador", "servico_realizado", "obs", "pecas_requeridas"]
    for campo in campos_ordem:
        if campo in dados_cvt and pd.notna(dados_cvt.get(campo, "")):
            valor = dados_cvt.get(campo, "")
            # formata data caso seja ISO
            if campo == "created_at":
                try:
                    valor = pd.to_datetime(valor).strftime("%d/%m/%Y %H:%M")
                except:
                    valor = str(valor)
            pdf.multi_cell(0, 8, f"{campo}: {valor}")
            pdf.ln(0)

    if pecas and len(pecas) > 0:
        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "PEÇAS SOLICITADAS", ln=1)
        pdf.set_font("Arial", "", 10)
        for p in pecas:
            desc = p.get("peca_descricao", p.get("descricao", ""))
            qtd = p.get("quantidade", "")
            pdf.multi_cell(0, 7, f"- {desc} (Qtd: {qtd})")

    pdf.ln(6)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 6, "Documento gerado pelo sistema CVT", ln=1, align="C")
    return pdf


def criar_botao_download_pdf_streamlit(pdf, nome_arquivo):
    try:
        pdf_bytes = pdf.output(dest="S").encode("latin-1")
        st.download_button(
            label=f"📥 Baixar PDF ({nome_arquivo})",
            data=pdf_bytes,
            file_name=nome_arquivo,
            mime="application/pdf"
        )
    except Exception as e:
        st.error("Erro ao preparar PDF para download: " + str(e))


# ----------------------
# FUNÇÕES DE DOMÍNIO (clientes, peças, cvt, req)
# ----------------------
def load_clientes_active():
    df = read_sheet("clientes")
    if df.empty:
        return pd.DataFrame()
    # Normalizar colunas
    df.columns = [c.lower() for c in df.columns]
    if "ativo" in df.columns:
        # considerar entradas com 'SIM' ou True
        ativos = df[df["ativo"].astype(str).str.upper().isin(["SIM", "TRUE", "1"])]
        return ativos
    return df


def load_pecas_active():
    df = read_sheet("pecas")
    if df.empty:
        return pd.DataFrame()
    df.columns = [c.lower() for c in df.columns]
    if "ativo" in df.columns:
        return df[df["ativo"].astype(str).str.upper().isin(["SIM", "TRUE", "1"])]
    return df


def get_cliente_by_nome(nome):
    df = load_clientes_active()
    if df.empty or "nome" not in df.columns:
        return None
    found = df[df["nome"] == nome]
    if not found.empty:
        return found.iloc[0].to_dict()
    return None


def get_peca_by_codigo(codigo):
    df = load_pecas_active()
    if df.empty or "codigo" not in df.columns:
        return None
    found = df[df["codigo"] == codigo]
    if not found.empty:
        return found.iloc[0].to_dict()
    return None


def append_cvt(data):
    """
    data: dict com chaves: tecnico, cliente, endereco, servico_realizado, obs, pecas_requeridas, elevador
    """
    ts = get_brasilia_time()
    numero_cvt = f"CVT-{ts.strftime('%Y%m%d-%H%M%S')}"
    row = {
        "created_at": ts.isoformat(),
        "tecnico": data.get("tecnico", ""),
        "cliente": data.get("cliente", ""),
        "endereco": data.get("endereco", ""),
        "servico_realizado": data.get("servico_realizado", ""),
        "obs": data.get("obs", ""),
        "pecas_requeridas": data.get("pecas_requeridas", ""),
        "elevador": data.get("elevador", ""),
        "status_cvt": data.get("status_cvt", "SALVO"),
        "numero_cvt": numero_cvt
    }
    success = append_to_sheet("cvt", row)
    return numero_cvt if success else None


def append_requisicao(data):
    """
    data: dict com chaves: tecnico, numero_cvt, peca_codigo, peca_descricao, quantidade, prioridade, observacoes
    """
    ts = get_brasilia_time()
    row = {
        "created_at": ts.isoformat(),
        "tecnico": data.get("tecnico", ""),
        "numero_cvt": data.get("numero_cvt", ""),
        "ordem_id": data.get("ordem_id", ""),
        "peca_codigo": data.get("peca_codigo", ""),
        "peca_descricao": data.get("peca_descricao", ""),
        "quantidade": data.get("quantidade", 1),
        "status": data.get("status", "PENDENTE"),
        "prioridade": data.get("prioridade", "NORMAL"),
        "observacoes": data.get("observacoes", "")
    }
    return append_to_sheet("req", row)


def read_all_cvt_df():
    df = read_sheet("cvt")
    # garantir colunas mínimas
    if df.empty:
        return pd.DataFrame(columns=CVT_COLUMNS)
    # Normalizar nomes de colunas para facilitar acesso
    df.columns = [c if isinstance(c, str) else c for c in df.columns]
    # Se faltar column, preencher
    for col in CVT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df


def read_all_reqs_df():
    df = read_sheet("req")
    if df.empty:
        return pd.DataFrame(columns=REQ_COLUMNS)
    for col in REQ_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df

# ----------------------
# INTERFACE: Login (simples) e Sessão
# ----------------------
def load_users_list():
    df = read_sheet("users")
    if df.empty:
        # fallback hardcoded
        return [
            {"username": "tecnico1", "password": "123", "role": "TECNICO", "nome": "João Silva"},
            {"username": "supervisor", "password": "admin", "role": "SUPERVISOR", "nome": "Carlos Oliveira"}
        ]
    # normalizar
    users = []
    for _, row in df.iterrows():
        users.append({
            "username": str(row.get("username", row.get("user", ""))).strip(),
            "password": str(row.get("password", "")).strip(),
            "role": str(row.get("role", "TECNICO")).strip(),
            "nome": str(row.get("nome", "")).strip() or str(row.get("user", "")).strip()
        })
    return users


def login_form():
    st.markdown("## 🔐 Login")
    with st.form("login"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            users = load_users_list()
            match = next((u for u in users if u["username"] == username and str(u["password"]) == str(password)), None)
            if match:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = match.get("role", "TECNICO")
                st.session_state.user_nome = match.get("nome", username)
                st.success(f"Bem-vindo, {st.session_state.user_nome}!")
                st.session_state._rerun_flag = True
                 if st.session_state.get("_rerun_flag", False):
                 st.session_state._rerun_flag = False
                 st.experimental_rerun()

            else:
                st.error("Usuário ou senha inválidos.")


def logout():
    keys = ["authenticated", "username", "role", "user_nome"]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]
    st.experimental_rerun()

# ----------------------
# INTERFACE: Seção de Peças (resumida e funcional)
# ----------------------
def seccion_pecas_cvt():
    st.markdown("---")
    st.subheader("⚙️ Pedido de Peças")

    pecas_df = load_pecas_active()
    if 'pecas_adicionadas' not in st.session_state:
        st.session_state.pecas_adicionadas = []

    with st.form("select_peca"):
        col1, col2 = st.columns([2,1])
        with col1:
            if not pecas_df.empty and "codigo" in pecas_df.columns:
                options = pecas_df.apply(lambda r: f'{r["codigo"]} - {r.get("descricao","")}', axis=1).tolist()
                selected = st.selectbox("Selecionar peça", options=[""] + options, key="select_peca_box")
            else:
                selected = st.text_input("Código da peça (manual)", key="select_peca_box_manual")
        with col2:
            qtd = st.number_input("Quantidade", min_value=1, value=1, key="qtd_peca")
            prioridade = st.selectbox("Prioridade", ["NORMAL","URGENTE"], key="prio_peca")
        observ = st.text_area("Observações da peça", key="obs_peca", height=60)

        submit = st.form_submit_button("Adicionar peça")
        if submit:
            if isinstance(selected, str) and "-" in selected:
                codigo = selected.split(" - ")[0].strip()
                pinfo = get_peca_by_codigo(codigo) or {}
                descricao = pinfo.get("descricao", selected)
            else:
                codigo = selected.strip()
                descricao = selected.strip()
            if not codigo:
                st.error("Informe o código/descrição da peça.")
            else:
                st.session_state.pecas_adicionadas.append({
                    "codigo": codigo,
                    "descricao": descricao,
                    "quantidade": int(qtd),
                    "prioridade": prioridade,
                    "observacoes": observ
                })
                st.success(f"Peça {descricao} adicionada.")

    # Lista de peças adicionadas
    if st.session_state.pecas_adicionadas:
        st.markdown("**Peças adicionadas:**")
        for i, p in enumerate(st.session_state.pecas_adicionadas):
            cols = st.columns([4,1,1])
            cols[0].write(f"**{p['codigo']}** - {p['descricao']} (Qtd: {p['quantidade']})")
            if cols[1].button("✏️", key=f"edit_{i}"):
                st.info("Use remover e readicionar para editar (simplificado).")
            if cols[2].button("🗑️", key=f"del_{i}"):
                st.session_state.pecas_adicionadas.pop(i)
                st.session_state._rerun_flag = True

            if st.session_state.get("_rerun_flag", False):
               st.session_state._rerun_flag = False
               st.experimental_rerun()


# ----------------------
# INTERFACE: Formulário de CVT (simplificado)
# ----------------------
def cvt_form():
    st.header("Comprovante de Visita Técnica (CVT)")
    clientes_df = load_clientes_active()

    with st.form("cvt_main"):
        col1, col2 = st.columns([2,1])
        with col1:
            if not clientes_df.empty and "nome" in clientes_df.columns:
                cliente_opts = clientes_df["nome"].tolist()
                cliente = st.selectbox("Cliente", options=[""] + cliente_opts, key="cvt_cliente")
                endereco_auto = ""
                if cliente:
                    cinfo = get_cliente_by_nome(cliente)
                    endereco_auto = cinfo.get("endereco","") if cinfo else ""
            else:
                cliente = st.text_input("Cliente", key="cvt_cliente_manual")
                endereco_auto = ""
        with col2:
            elevador = st.selectbox("Elevador", ["","Principal","Secundário","Ambos"], key="cvt_elevador")

        endereco = st.text_input("Endereço", value=endereco_auto, key="cvt_endereco")
        servico = st.text_area("Serviço realizado / diagnóstico", key="cvt_servico", height=120)
        obs = st.text_area("Observações adicionais", key="cvt_obs", height=80)

        colbtn1, colbtn2 = st.columns([1,1])
        with colbtn1:
            pedir_pecas = st.form_submit_button("⚙️ Pedir Peças")
        with colbtn2:
            salvar = st.form_submit_button("✅ Salvar CVT sem peças")

        if pedir_pecas:
            if not cliente or cliente == "":
                st.error("Selecione ou informe um cliente antes de pedir peças.")
            else:
                # guarda temporariamente
                st.session_state.cvt_temp = {
                    "cliente": cliente,
                    "endereco": endereco,
                    "elevador": elevador,
                    "servico_realizado": servico,
                    "obs": obs,
                    "tecnico": st.session_state.get("user_nome", "Desconhecido")
                }
                st.session_state.mostrar_pecas = True
                st.session_state._rerun_flag = True
            if st.session_state.get("_rerun_flag", False):
             st.session_state._rerun_flag = False
              st.experimental_rerun()


        if salvar:
            if not cliente:
                st.error("Preencha o cliente.")
            else:
                dados = {
                    "tecnico": st.session_state.get("user_nome","Desconhecido"),
                    "cliente": cliente,
                    "endereco": endereco,
                    "elevador": elevador,
                    "servico_realizado": servico,
                    "obs": obs,
                    "pecas_requeridas": ""
                }
                nro = append_cvt(dados)
                if nro:
                    st.success(f"CVT {nro} salva com sucesso!")
                    st.session_state.cvt_salva = True
                    st.session_state.numero_cvt_salva = nro
                    st.session_state._rerun_flag = True


    # Seção de peças (após pedir peças)
    if st.session_state.get("mostrar_pecas", False):
        st.markdown("---")
        st.subheader("Resumo da CVT")
        dados_temp = st.session_state.get("cvt_temp", {})
        st.write(f"**Cliente:** {dados_temp.get('cliente','')}")
        st.write(f"**Endereço:** {dados_temp.get('endereco','')}")
        st.write(f"**Elevador:** {dados_temp.get('elevador','')}")
        st.write(f"**Serviço:** {str(dados_temp.get('servico_realizado',''))[:120]}...")

        seccion_pecas_cvt()

        st.markdown("---")
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            if st.button("✅ Salvar CVT com Peças"):
                if not st.session_state.pecas_adicionadas:
                    st.error("Adicione ao menos uma peça.")
                else:
                    dados = {
                        "tecnico": st.session_state.get("user_nome","Desconhecido"),
                        "cliente": dados_temp.get("cliente",""),
                        "endereco": dados_temp.get("endereco",""),
                        "elevador": dados_temp.get("elevador",""),
                        "servico_realizado": dados_temp.get("servico_realizado",""),
                        "obs": dados_temp.get("obs",""),
                        "pecas_requeridas": ", ".join([f'{p["codigo"]}({p["quantidade"]})' for p in st.session_state.pecas_adicionadas])
                    }
                    nro = append_cvt(dados)
                    if nro:
                        # salvar requisições
                        for p in st.session_state.pecas_adicionadas:
                            req = {
                                "tecnico": st.session_state.get("user_nome","Desconhecido"),
                                "numero_cvt": nro,
                                "peca_codigo": p.get("codigo",""),
                                "peca_descricao": p.get("descricao",""),
                                "quantidade": p.get("quantidade",1),
                                "prioridade": p.get("prioridade","NORMAL"),
                                "observacoes": p.get("observacoes","")
                            }
                            append_requisicao(req)
                        st.success(f"CVT {nro} salva com {len(st.session_state.pecas_adicionadas)} peça(s).")
                        # limpa estado
                        st.session_state.pecas_adicionadas = []
                        st.session_state.mostrar_pecas = False
                        st.session_state.cvt_temp = {}
                        st.session_state.cvt_salva = True
                        st.session_state.numero_cvt_salva = nro
                        st.experimental_rerun()
        with col2:
            if st.button("↩️ Voltar"):
                st.session_state.mostrar_pecas = False
                st.experimental_rerun()
        with col3:
            if st.button("🗑️ Cancelar"):
                st.session_state.mostrar_pecas = False
                st.session_state.pecas_adicionadas = []
                st.experimental_rerun()

    # Pós-salvamento: gerar pdf / ver minhas CVTs
    if st.session_state.get("cvt_salva", False):
        st.success(f"CVT {st.session_state.get('numero_cvt_salva')} salva.")
        st.markdown("---")
        pref = st.columns(2)
        with pref[0]:
            if st.button("📄 Gerar PDF da última CVT"):
                cvt_df = read_all_cvt_df()
                sel = st.session_state.get("numero_cvt_salva")
                if sel and sel in cvt_df["numero_cvt"].values:
                    row = cvt_df[cvt_df["numero_cvt"] == sel].iloc[0].to_dict()
                    req_df = read_all_reqs_df()
                    pecas = req_df[req_df["numero_cvt"] == sel].to_dict("records") if not req_df.empty else None
                    pdf = gerar_pdf_cvt(row, pecas)
                    criar_botao_download_pdf_streamlit(pdf, f"CVT_{sel}.pdf")
        with pref[1]:
            if st.button("📋 Ver Minhas CVTs"):
                st.session_state.mostrar_minhas_cvts = True
                st.experimental_rerun()

    if st.session_state.get("mostrar_minhas_cvts", False):
        st.subheader("Minhas CVTs Recentes")
        cvt_df = read_all_cvt_df()
        user = st.session_state.get("user_nome", "")
        my = cvt_df[cvt_df["tecnico"] == user] if not cvt_df.empty else pd.DataFrame()
        if my.empty:
            st.info("Nenhuma CVT encontrada para você.")
        else:
            display_cols = ["numero_cvt", "cliente", "endereco", "elevador", "created_at", "status_cvt"]
            cols = [c for c in display_cols if c in my.columns]
            df_show = my[cols].copy()
            try:
                df_show["created_at"] = pd.to_datetime(df_show["created_at"]).dt.strftime("%d/%m/%Y %H:%M")
            except:
                pass
            st.dataframe(df_show.sort_values("created_at", ascending=False).head(20), use_container_width=True)
        if st.button("↩️ Voltar - Nova CVT"):
            st.session_state.mostrar_minhas_cvts = False
            st.experimental_rerun()

# ----------------------
# INTERFACE: Minhas Requisições
# ----------------------
def minhas_requisicoes():
    st.header("Minhas Requisições")
    df = read_all_reqs_df()
    if df.empty:
        st.info("Nenhuma requisição encontrada.")
        return
    user = st.session_state.get("user_nome", "")
    my = df[df["tecnico"] == user]
    if my.empty:
        st.info("Você não possui requisições.")
        return
    try:
        my["created_at"] = pd.to_datetime(my["created_at"]).dt.strftime("%d/%m/%Y %H:%M")
    except:
        pass
    st.dataframe(my.sort_values("created_at", ascending=False), use_container_width=True)

# ----------------------
# INTERFACE: Supervisor / Gerenciamento
# ----------------------
def supervisor_panel():
    st.header("Painel de Gerenciamento (Supervisor)")

    # Visualização se estamos usando Google Sheets
    st.write("**Fonte de dados:**", "Google Sheets" if using_gsheets() else "CSV local (fallback)")
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 Todas as Requisições",
        "📊 Estatísticas",
        "👥 CVTs",
        "📄 Gerar PDFs",
        "🔍 DEBUG CVTs"
    ])

    with tab1:
        st.subheader("Gestão de Requisições")
        df = read_all_reqs_df()
        if df.empty:
            st.info("Nenhuma requisição encontrada.")
        else:
            st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True)

    with tab2:
        st.subheader("Estatísticas Rápidas")
        df = read_all_reqs_df()
        if df.empty:
            st.info("Sem dados para estatísticas.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Requisições", len(df))
            with col2:
                st.metric("Técnicos", df["tecnico"].nunique())
            with col3:
                st.metric("Urgentes", len(df[df["prioridade"] == "URGENTE"]))
            try:
                st.bar_chart(df["status"].value_counts())
            except:
                pass

    with tab3:
        st.subheader("CVTs dos Técnicos")
        cvt_df = read_all_cvt_df()
        if cvt_df.empty:
            st.info("Nenhuma CVT encontrada no sistema.")
        else:
            # debug opcional
            if st.checkbox("🔍 Modo Debug - Mostrar estrutura"):
                st.write("Colunas:", list(cvt_df.columns))
                st.write("Total linhas:", len(cvt_df))
                st.write(cvt_df.head())

            # Filtros
            col1, col2 = st.columns([2,2])
            with col1:
                techs = ["Todos"] + sorted(cvt_df["tecnico"].dropna().unique().tolist())
                sel_tech = st.selectbox("Filtrar por técnico", options=techs, index=0)
            with col2:
                statuses = ["Todos"] + sorted(cvt_df["status_cvt"].dropna().unique().tolist()) if "status_cvt" in cvt_df.columns else ["Todos"]
                sel_status = st.selectbox("Filtrar por status", options=statuses, index=0)

            filtered = cvt_df.copy()
            if sel_tech != "Todos":
                filtered = filtered[filtered["tecnico"] == sel_tech]
            if sel_status != "Todos" and "status_cvt" in filtered.columns:
                filtered = filtered[filtered["status_cvt"] == sel_status]

            if filtered.empty:
                st.info("Nenhuma CVT encontrada com os filtros aplicados.")
            else:
                display_cols = [c for c in ["numero_cvt","tecnico","cliente","created_at","status_cvt"] if c in filtered.columns]
                df_display = filtered[display_cols].copy()
                try:
                    df_display["created_at"] = pd.to_datetime(df_display["created_at"]).dt.strftime("%d/%m/%Y %H:%M")
                except:
                    pass
                st.dataframe(df_display.sort_values("created_at", ascending=False), use_container_width=True)

    with tab4:
        st.subheader("Gerar PDF de CVT")
        cvt_df = read_all_cvt_df()
        if cvt_df.empty:
            st.info("Sem CVTs para gerar PDF.")
        else:
            opts = cvt_df["numero_cvt"].tolist()
            sel = st.selectbox("Selecionar CVT", options=[""]+opts, key="select_cvt_pdf_supervisor")
            if sel:
                row = cvt_df[cvt_df["numero_cvt"]==sel].iloc[0].to_dict()
                req_df = read_all_reqs_df()
                pecas = req_df[req_df["numero_cvt"]==sel].to_dict("records") if not req_df.empty else None
                pdf = gerar_pdf_cvt(row, pecas)
                criar_botao_download_pdf_streamlit(pdf, f"CVT_{sel}.pdf")

    with tab5:
        st.subheader("DEBUG - Leitura completa de CVTs")
        cvt_df = read_all_cvt_df()
        st.write("Usando Google Sheets:", using_gsheets())
        st.write("Total de CVTs:", len(cvt_df))
        if not cvt_df.empty:
            st.write("Colunas detectadas:", list(cvt_df.columns))
            st.dataframe(cvt_df.head(10))
        if st.button("🔄 Forçar recarregar caches"):
            try:
                # limpar caches - força reexecução das funções de cache
                st.cache_data.clear()
                st.cache_resource.clear()
            except Exception:
                pass
            st.experimental_rerun()

# ----------------------
# INTERFACE PRINCIPAL / MENU
# ----------------------
def main_interface():
    col1, col2, col3 = st.columns([1,3,1])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=80)
        else:
            st.markdown("### ⚙️")
    with col2:
        st.title("Sistema CVT")
        st.caption(f"Logado como: {st.session_state.get('user_nome','-')} ({st.session_state.get('role','-')})")
    with col3:
        if st.button("Sair"):
            logout()

    # Menu
    if st.session_state.get("role","TECNICO") == "SUPERVISOR":
        menu = [" Nova CVT", " Minhas Req", "Gerenciamento"]
        icons = ["file-text","clipboard","people"]
    else:
        menu = [" Nova CVT", " Minhas Req"]
        icons = ["file-text","clipboard"]

    selected = option_menu(None, menu, icons=icons, orientation="horizontal", default_index=0)

    if selected == " Nova CVT":
        cvt_form()
    elif selected == " Minhas Req":
        minhas_requisicoes()
    elif selected == "Gerenciamento":
        supervisor_panel()

# ----------------------
# INICIALIZAÇÃO DO APP
# ----------------------
def main():
    # estado default
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "mostrar_pecas" not in st.session_state:
        st.session_state.mostrar_pecas = False
    if "pecas_adicionadas" not in st.session_state:
        st.session_state.pecas_adicionadas = []
    if "cvt_salva" not in st.session_state:
        st.session_state.cvt_salva = False
    if "mostrar_minhas_cvts" not in st.session_state:
        st.session_state.mostrar_minhas_cvts = False

    if not st.session_state.authenticated:
        login_form()
        st.markdown("---")
        st.markdown("<small style='color:gray'>Sistema CVT - Versão refeita. Configure 'service_account.json' ou st.secrets['gcp_service_account'] para Google Sheets.</small>", unsafe_allow_html=True)
    else:
        main_interface()


if __name__ == "__main__":
    main()

