import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import datetime
import os
import json
import time
from fpdf import FPDF
import base64

# ===============================
# CONFIGURAÇÕES GERAIS
# ===============================
st.set_page_config(page_title="CVT App", layout="centered", page_icon="⚙️")
SHEET_NAME = "CVT_DB"

# Nomes das planilhas
CVT_SHEET = "CVT"
REQ_SHEET = "REQUISICOES"
USERS_SHEET = "USERS"
CLIENTES_SHEET = "CLIENTES"
PECAS_SHEET = "PECAS"

# Cache global de dados
@st.cache_resource
def init_gsheets():
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        if "gcp_service_account" in st.secrets:
            sa_info = json.loads(st.secrets["gcp_service_account"])
        elif os.path.exists("service_account.json"):
            with open("service_account.json", "r", encoding="utf-8") as f:
                sa_info = json.load(f)
        else:
            st.warning("⚠️ Credenciais não encontradas. Usando CSV local.")
            return None

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Erro ao inicializar Google Sheets: {e}")
        return None


def get_worksheet(sheet_name):
    # Obtém worksheet do Google Sheets ou None
    client = init_gsheets()
    if not client:
        return None

    try:
        spreadsheet = client.open(SHEET_NAME)
        return spreadsheet.worksheet(sheet_name)
    except Exception as e:
        st.error(f"Erro ao acessar planilha '{sheet_name}': {e}")
        return None


# ===============================
# FUNÇÕES DE DADOS
# ===============================
@st.cache_data(ttl=120)
def read_sheet(sheet_name):
    ws = get_worksheet(sheet_name)
    if not ws:
        return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Erro ao ler dados da planilha {sheet_name}: {e}")
        return pd.DataFrame()


def append_row(sheet_name, row):
    ws = get_worksheet(sheet_name)
    if not ws:
        st.error("Erro ao acessar Google Sheets.")
        return False
    try:
        ws.append_row(row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha {sheet_name}: {e}")
        return False


# ===============================
# FUNÇÕES DE TEMPO E PDF
# ===============================
def get_brasilia_time():
    return datetime.datetime.utcnow() - datetime.timedelta(hours=3)


def gerar_pdf_cvt(dados_cvt, pecas=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "COMPROVANTE DE VISITA TÉCNICA", ln=1, align="C")
    pdf.set_font("Arial", size=11)
    pdf.ln(8)

    for campo, valor in dados_cvt.items():
        pdf.cell(200, 8, f"{campo}: {valor}", ln=1)

    if pecas and len(pecas) > 0:
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, "PEÇAS SOLICITADAS", ln=1)
        pdf.set_font("Arial", size=10)
        for p in pecas:
            pdf.cell(200, 8, f"- {p.get('peca_descricao', '')} ({p.get('quantidade', '')})", ln=1)

    pdf.ln(10)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 10, "Documento gerado automaticamente.", ln=1, align="C")
    return pdf


def criar_botao_download_pdf(pdf, nome):
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{nome}" style="background:#4CAF50;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;">📄 Baixar PDF</a>'
    st.markdown(href, unsafe_allow_html=True)


# ===============================
# INTERFACES
# ===============================
def supervisor_panel():
    st.header("Painel de Gerenciamento")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Requisições",
        "📊 Estatísticas",
        "👥 CVTs",
        "📄 PDFs"
    ])

    with tab1:
        req_df = read_sheet(REQ_SHEET)
        if req_df.empty:
            st.info("Nenhuma requisição encontrada.")
        else:
            st.dataframe(req_df)

    with tab2:
        req_df = read_sheet(REQ_SHEET)
        if not req_df.empty:
            st.metric("Total de requisições", len(req_df))
            st.bar_chart(req_df["prioridade"].value_counts())
        else:
            st.info("Sem dados para estatísticas.")

    with tab3:
        cvt_df = read_sheet(CVT_SHEET)
        if cvt_df.empty:
            st.warning("Nenhuma CVT encontrada.")
        else:
            if "status_cvt" not in cvt_df.columns:
                cvt_df["status_cvt"] = "SALVO"
            st.dataframe(cvt_df)

    with tab4:
        cvt_df = read_sheet(CVT_SHEET)
        if cvt_df.empty:
            st.info("Sem CVTs para PDF.")
            return
        numero_cvt = st.selectbox("Selecione uma CVT:", cvt_df["numero_cvt"].tolist())
        if numero_cvt:
            cvt_info = cvt_df[cvt_df["numero_cvt"] == numero_cvt].iloc[0].to_dict()
            req_df = read_sheet(REQ_SHEET)
            pecas = req_df[req_df["numero_cvt"] == numero_cvt].to_dict("records") if not req_df.empty else None
            pdf = gerar_pdf_cvt(cvt_info, pecas)
            criar_botao_download_pdf(pdf, f"CVT_{numero_cvt}.pdf")


def main():
    st.title("⚙️ Sistema CVT Simplificado")
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = True
        st.session_state.role = "SUPERVISOR"
        st.session_state.user_nome = "Supervisor"

    supervisor_panel()


if __name__ == "__main__":
    main()
