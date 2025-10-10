import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import datetime
import os
import json
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

# ----------------------
# GOOGLE SHEETS INIT
# ----------------------
@st.cache_resource
def init_gsheets_client():
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
    except Exception:
        st.warning("⚠️ Instale gspread e oauth2client para integração com Google Sheets.")
        return None

    sa_info = None
    if "gcp_service_account" in st.secrets:
        sa_info = json.loads(st.secrets["gcp_service_account"])
    elif os.path.exists("service_account.json"):
        with open("service_account.json", "r", encoding="utf-8") as f:
            sa_info = json.load(f)
    else:
        return None

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, scope)
    client = gspread.authorize(creds)
    return client


@st.cache_data(ttl=60)
def read_sheet(sheet_name):
    client = init_gsheets_client()
    if not client:
        return pd.DataFrame()
    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Erro ao ler planilha '{sheet_name}': {e}")
        return pd.DataFrame()


def append_row(sheet_name, row):
    client = init_gsheets_client()
    if not client:
        return False
    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.warning(f"Erro ao gravar na planilha '{sheet_name}': {e}")
        return False


# ----------------------
# FUNÇÕES AUXILIARES
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
    for campo, valor in dados_cvt.items():
        pdf.multi_cell(0, 8, f"{campo}: {valor}")
        pdf.ln(0)

    if pecas and len(pecas) > 0:
        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "PEÇAS SOLICITADAS", ln=1)
        pdf.set_font("Arial", "", 10)
        for p in pecas:
            pdf.multi_cell(0, 7, f"- {p.get('peca_descricao', '')} (Qtd: {p.get('quantidade', '')})")

    pdf.ln(6)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 6, "Documento gerado automaticamente.", ln=1, align="C")
    return pdf


def criar_botao_download_pdf(pdf, nome):
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    st.download_button("📥 Baixar PDF", pdf_bytes, file_name=nome, mime="application/pdf")


# ----------------------
# INTERFACE PRINCIPAL
# ----------------------
def cvt_form():
    st.header("Comprovante de Visita Técnica (CVT)")

    with st.form("cvt_form"):
        cliente = st.text_input("Cliente")
        endereco = st.text_input("Endereço")
        elevador = st.text_input("Elevador")
        servico = st.text_area("Serviço realizado / diagnóstico")
        obs = st.text_area("Observações")
        salvar = st.form_submit_button("Salvar CVT")

        if salvar:
            dados = {
                "created_at": get_brasilia_time().isoformat(),
                "cliente": cliente,
                "endereco": endereco,
                "elevador": elevador,
                "servico_realizado": servico,
                "obs": obs,
                "status_cvt": "SALVO",
                "numero_cvt": f"CVT-{int(time.time())}"
            }
            row = list(dados.values())
            if append_row(CVT_SHEET, row):
                st.success(f"CVT salva com sucesso: {dados['numero_cvt']}")
                st.session_state._rerun_flag = True

    # Rerun seguro (fora do formulário)
    if st.session_state.get("_rerun_flag", False):
        st.session_state._rerun_flag = False
        st.experimental_rerun()


def supervisor_panel():
    st.header("Painel de Gerenciamento")
    tab1, tab2, tab3, tab4 = st.tabs(["📦 Requisições", "📊 Estatísticas", "👥 CVTs", "📄 PDFs"])

    with tab1:
        df = read_sheet(REQ_SHEET)
        if df.empty:
            st.info("Nenhuma requisição encontrada.")
        else:
            st.dataframe(df)

    with tab2:
        df = read_sheet(REQ_SHEET)
        if not df.empty and "prioridade" in df.columns:
            st.bar_chart(df["prioridade"].value_counts())
        else:
            st.info("Sem dados suficientes para gerar gráfico.")

    with tab3:
        cvt_df = read_sheet(CVT_SHEET)
        if cvt_df.empty:
            st.info("Nenhuma CVT encontrada.")
        else:
            st.dataframe(cvt_df)

    with tab4:
        cvt_df = read_sheet(CVT_SHEET)
        if not cvt_df.empty:
            numero = st.selectbox("Selecione uma CVT:", cvt_df["numero_cvt"].tolist())
            if numero:
                dados = cvt_df[cvt_df["numero_cvt"] == numero].iloc[0].to_dict()
                pdf = gerar_pdf_cvt(dados)
                criar_botao_download_pdf(pdf, f"CVT_{numero}.pdf")


def main_interface():
    menu = option_menu(None, ["Nova CVT", "Gerenciamento"], icons=["file-text", "gear"], orientation="horizontal")
    if menu == "Nova CVT":
        cvt_form()
    else:
        supervisor_panel()


def main():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = True
        st.session_state.role = "SUPERVISOR"

    main_interface()


if __name__ == "__main__":
    main()
