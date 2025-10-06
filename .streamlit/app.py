import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import datetime
import os
import json
import time
from fpdf import FPDF
import base64

# --- Configuração inicial ---
st.set_page_config(page_title="CVT App", layout="centered", page_icon="⚙️")

# --- Constantes e configurações ---
SHEET_NAME = "CVT_DB"
CVT_SHEET = "CVT"
REQ_SHEET = "REQUISICOES"
USERS_SHEET = "USERS"
CLIENTES_SHEET = "CLIENTES"
PECAS_SHEET = "PECAS"

# Arquivos CSV fallback
CVT_CSV = "cvt_local.csv"
REQ_CSV = "requisicoes_local.csv"
USERS_CSV = "users_local.csv"
CLIENTES_CSV = "clientes_local.csv"
PECAS_CSV = "pecas_local.csv"

# Colunas das planilhas
CVT_COLUMNS = [
    "created_at", "tecnico", "cliente", "endereco", "servico_realizado", 
    "obs", "pecas_requeridas", "elevador", "status_cvt", "numero_cvt"
]

REQ_COLUMNS = [
    "created_at", "tecnico", "numero_cvt", "ordem_id", "peca_codigo", 
    "peca_descricao", "quantidade", "status", "prioridade", "observacoes"
]

CLIENTES_COLUMNS = [
    "codigo", "nome", "endereco", "telefone", "email", "responsavel", "ativo"
]

PECAS_COLUMNS = [
    "codigo", "descricao", "categoria", "campos_especificos", "ativo"
]

# --- FUNÇÃO PARA GERAR PDF ---
def gerar_pdf_cvt(dados_cvt, pecas=None):
    """Gera um PDF da CVT com todas as informações"""
    
    pdf = FPDF()
    pdf.add_page()
    
    # Configurações
    pdf.set_font("Arial", size=12)
    
    # Cabeçalho
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="COMPROVANTE DE VISITA TÉCNICA", ln=1, align='C')
    pdf.ln(10)
    
    # Informações da CVT
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="INFORMAÇÕES DA VISITA", ln=1)
    pdf.set_font("Arial", size=11)
    
    # Dados básicos
    pdf.cell(100, 8, txt=f"Número CVT: {dados_cvt['numero_cvt']}", ln=1)
    
    # Formata data
    if 'created_at' in dados_cvt:
        try:
            data_obj = pd.to_datetime(dados_cvt['created_at'])
            data_formatada = data_obj.strftime("%d/%m/%Y %H:%M")
            pdf.cell(100, 8, txt=f"Data/Hora: {data_formatada}", ln=1)
        except:
            pdf.cell(100, 8, txt=f"Data/Hora: {dados_cvt['created_at']}", ln=1)
    
    pdf.cell(100, 8, txt=f"Técnico: {dados_cvt['tecnico']}", ln=1)
    pdf.cell(100, 8, txt=f"Cliente: {dados_cvt['cliente']}", ln=1)
    pdf.cell(100, 8, txt=f"Endereço: {dados_cvt['endereco']}", ln=1)
    pdf.cell(100, 8, txt=f"Elevador: {dados_cvt.get('elevador', 'Não informado')}", ln=1)
    pdf.ln(5)
    
    # Serviço Realizado
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="SERVIÇO REALIZADO / DIAGNÓSTICO", ln=1)
    pdf.set_font("Arial", size=11)
    
    # Quebra o texto do serviço em múltiplas linhas
    servico = dados_cvt['servico_realizado']
    pdf.multi_cell(0, 8, txt=servico)
    pdf.ln(5)
    
    # Observações (se houver)
    if dados_cvt.get('obs'):
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="OBSERVAÇÕES ADICIONAIS", ln=1)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, txt=dados_cvt['obs'])
        pdf.ln(5)
    
    # Seção de Peças (se houver)
    if pecas and len(pecas) > 0:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="PEÇAS SOLICITADAS", ln=1)
        pdf.set_font("Arial", size=10)
        
        # Cabeçalho da tabela
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(30, 8, "Código", 1, 0, 'C', True)
        pdf.cell(80, 8, "Descrição", 1, 0, 'C', True)
        pdf.cell(20, 8, "Qtd", 1, 0, 'C', True)
        pdf.cell(30, 8, "Prioridade", 1, 0, 'C', True)
        pdf.cell(30, 8, "Observações", 1, 1, 'C', True)
        
        # Dados das peças
        pdf.set_font("Arial", size=9)
        for peca in pecas:
            # Quebra linha se a descrição for muito longa
            descricao = peca['peca_descricao']
            if len(descricao) > 50:
                descricao = descricao[:47] + "..."
            
            pdf.cell(30, 8, peca['peca_codigo'], 1)
            pdf.cell(80, 8, descricao, 1)
            pdf.cell(20, 8, str(peca['quantidade']), 1, 0, 'C')
            pdf.cell(30, 8, peca['prioridade'], 1, 0, 'C')
            
            # Trunca observações muito longas
            obs = peca.get('observacoes', '')
            if len(obs) > 20:
                obs = obs[:17] + "..."
            pdf.cell(30, 8, obs, 1, 1)
        
        pdf.ln(5)
    
    # Rodapé
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, txt="Documento gerado automaticamente pelo Sistema CVT", ln=1, align='C')
    
    return pdf

def criar_botao_download_pdf(pdf, nome_arquivo):
    """Cria um botão de download para o PDF"""
    pdf_output = pdf.output(dest='S').encode('latin-1')
    b64_pdf = base64.b64encode(pdf_output).decode()
    
    href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{nome_arquivo}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px; font-weight: bold;">📄 Baixar PDF da CVT</a>'
    st.markdown(href, unsafe_allow_html=True)

# --- Inicialização do Google Sheets ---
def init_gsheets():
    """
    Configura conexão com Google Sheets
    """
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        
        creds_json = None
        if "gcp_service_account" in st.secrets:
            try:
                creds_json = st.secrets["gcp_service_account"]
                sa_info = json.loads(creds_json)
            except Exception as e:
                st.error(f"Erro nas credenciais: {str(e)}")
                return None
        elif os.path.exists("service_account.json"):
            with open("service_account.json", "r", encoding="utf-8") as f:
                sa_info = json.load(f)
        else:
            st.warning("Usando CSV local - configure as credenciais do Google Sheets")
            return None

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, scope)
        client = gspread.authorize(creds)
        return client
        
    except ImportError:
        st.warning("Bibliotecas Google não instaladas. Usando CSV local.")
        return None
    except Exception as e:
        st.error(f"Erro na inicialização: {str(e)}")
        return None

# --- Gerenciamento de planilhas ---
@st.cache_resource
def get_client_and_worksheets():
    client = init_gsheets()
    if not client:
        return None
        
    try:
        # Tenta abrir a planilha existente
        spreadsheet = client.open(SHEET_NAME)
    except Exception:
        # Cria nova planilha se não existir
        try:
            spreadsheet = client.create(SHEET_NAME)
            time.sleep(2)
        except Exception as e:
            st.error(f"Erro ao criar planilha: {str(e)}")
            return None

    # Garante que as worksheets existem
    def ensure_worksheet(name):
        try:
            return spreadsheet.worksheet(name)
        except Exception:
            try:
                return spreadsheet.add_worksheet(title=name, rows=1000, cols=20)
            except Exception:
                return None

    worksheets = {
        "client": client,
        "spreadsheet": spreadsheet,
        "cvt": ensure_worksheet(CVT_SHEET),
        "req": ensure_worksheet(REQ_SHEET),
        "users": ensure_worksheet(USERS_SHEET),
        "clientes": ensure_worksheet(CLIENTES_SHEET),
        "pecas": ensure_worksheet(PECAS_SHEET),
    }
    
    return worksheets

# --- Operações com dados ---
def append_to_sheet(worksheet, row):
    """Adiciona linha ao Google Sheets"""
    try:
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Sheets: {str(e)}")
        return False

def read_from_sheet(worksheet):
    """Lê dados do Google Sheets"""
    try:
        records = worksheet.get_all_records()
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Erro ao ler do Sheets: {str(e)}")
        return pd.DataFrame()

# --- Funções para Clientes ---
def load_clientes():
    """Carrega lista de clientes do Google Sheets"""
    client_info = get_client_and_worksheets()
    
    if client_info and client_info["clientes"]:
        try:
            df = read_from_sheet(client_info["clientes"])
            if not df.empty and 'ativo' in df.columns:
                df = df[df['ativo'].str.upper() == 'SIM']
            return df
        except Exception as e:
            st.error(f"Erro ao carregar clientes: {str(e)}")
    
    # Fallback para CSV
    if os.path.exists(CLIENTES_CSV):
        df = pd.read_csv(CLIENTES_CSV)
        if 'ativo' in df.columns:
            df = df[df['ativo'].str.upper() == 'SIM']
        return df
    
    return pd.DataFrame()

def get_cliente_by_nome(nome):
    """Busca cliente pelo nome"""
    clientes_df = load_clientes()
    if not clientes_df.empty and 'nome' in clientes_df.columns:
        cliente = clientes_df[clientes_df['nome'] == nome]
        if not cliente.empty:
            return cliente.iloc[0]
    return None

# --- Funções para Peças ---
def load_pecas():
    """Carrega lista de peças do Google Sheets"""
    client_info = get_client_and_worksheets()
    
    if client_info and client_info["pecas"]:
        try:
            df = read_from_sheet(client_info["pecas"])
            if not df.empty and 'ativo' in df.columns:
                df = df[df['ativo'].str.upper() == 'SIM']
            return df
        except Exception as e:
            st.error(f"Erro ao carregar peças: {str(e)}")
    
    # Fallback para CSV
    if os.path.exists(PECAS_CSV):
        df = pd.read_csv(PECAS_CSV)
        if 'ativo' in df.columns:
            df = df[df['ativo'].str.upper() == 'SIM']
        return df
    
    return pd.DataFrame()

def get_peca_by_codigo(codigo):
    """Busca peça pelo código"""
    pecas_df = load_pecas()
    if not pecas_df.empty:
        peca = pecas_df[pecas_df['codigo'] == codigo]
        if not peca.empty:
            return peca.iloc[0]
    return None

def get_campos_por_peca(codigo_peca):
    """Retorna os campos específicos para uma peça"""
    pecas_df = load_pecas()
    if not pecas_df.empty and 'campos_especificos' in pecas_df.columns:
        peca = pecas_df[pecas_df['codigo'] == codigo_peca]
        if not peca.empty:
            campos_str = peca.iloc[0]['campos_especificos']
            if pd.notna(campos_str) and campos_str != '':
                return [campo.strip() for campo in campos_str.split(',')]
    return []

def render_campos_dinamicos(campos):
    """Renderiza campos dinâmicos baseado na lista"""
    valores = {}
    
    if not campos:
        return valores
    
    st.subheader(" Informações Específicas da Peça")
    
    for campo in campos:
        if campo == 'pavimento':
            valores['pavimento'] = st.selectbox(
                "Pavimento/Cabine",
                ["Térreo", "1º Andar", "2º Andar", "3º Andar", "4º Andar", "5° Andar", "6° Andar", "Cabine", "Todos"]
            )
        elif campo == 'marca':
            valores['marca'] = st.text_input("Marca")
        elif campo == 'modelo':
            valores['modelo'] = st.text_input("Modelo")
        elif campo == 'quantidade':
            valores['quantidade'] = st.number_input("Quantidade", min_value=1, value=1)
        elif campo == 'tipo':
            valores['tipo'] = st.selectbox(
                "Tipo",
                ["Simples", "Duplo", "Com LED", "Emergência", "Tátil", "Comum"]
            )
        elif campo == 'voltagem':
            valores['voltagem'] = st.selectbox(
                "Voltagem",
                ["110V", "220V", "24V", "12V", "380V"]
            )
        elif campo == 'cor':
            valores['cor'] = st.selectbox(
                "Cor",
                ["Branco", "Preto", "Cinza", "Vermelho", "Azul", "Verde", "Personalizado"]
            )
        elif campo == 'potencia':
            valores['potencia'] = st.selectbox(
                "Potência",
                ["1/4 HP", "1/2 HP", "3/4 HP", "1 HP", "1.5 HP", "2 HP", "3 HP", "5 HP"]
            )
        elif campo == 'tensao':
            valores['tensao'] = st.selectbox(
                "Tensão",
                ["110V", "220V", "380V", "440V", "Bivolt"]
            )
        elif campo == 'rotacao':
            valores['rotacao'] = st.selectbox(
                "Rotação",
                ["1200 RPM", "1800 RPM", "3600 RPM", "Variável"]
            )
        elif campo == 'polegadas':
            valores['polegadas'] = st.selectbox(
                "Polegadas",
                ["7''", "10''", "15''", "17''", "19''", "21''", "24''"]
            )
        elif campo == 'resolucao':
            valores['resolucao'] = st.selectbox(
                "Resolução",
                ["640x480", "800x600", "1024x768", "1280x1024", "1920x1080"]
            )
        elif campo == 'material':
            valores['material'] = st.selectbox(
                "Material",
                ["Aço", "Alumínio", "Plástico", "Bronze", "Latão", "Inox"]
            )
        elif campo == 'diametro':
            valores['diametro'] = st.text_input("Diâmetro (mm)")
        elif campo == 'comprimento':
            valores['comprimento'] = st.text_input("Comprimento (mm)")
        else:
            # Campo genérico para qualquer outro
            valores[campo] = st.text_input(f"{campo.replace('_', ' ').title()}")
    
    return valores

# --- Funções para CVT ---
def append_cvt(data):
    """Salva CVT no Google Sheets ou CSV"""
    client_info = get_client_and_worksheets()
    
    # Gera número único para CVT
    numero_cvt = f"CVT-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    row = [
        datetime.datetime.now().isoformat(),
        data["tecnico"],
        data["cliente"],
        data["endereco"],
        data.get("elevador", ""),
        data["servico_realizado"],
        data["obs"],
        data["pecas_requeridas"],
        "SALVO",
        numero_cvt
    ]
    
    if client_info and client_info["cvt"]:
        success = append_to_sheet(client_info["cvt"], row)
        if success:
            st.success(f"CVT {numero_cvt} salva com sucesso no Google Sheets!")
            return numero_cvt
    else:
        # Fallback para CSV
        df = pd.DataFrame([row], columns=CVT_COLUMNS)
        if os.path.exists(CVT_CSV):
            existing_df = pd.read_csv(CVT_CSV)
            df = pd.concat([existing_df, df], ignore_index=True)
        df.to_csv(CVT_CSV, index=False)
        st.success(f"CVT {numero_cvt} salva localmente!")
        return numero_cvt
    
    return None



def read_all_cvt():
    """Lê todas as CVTs"""
    client_info = get_client_and_worksheets()
    
    if client_info and client_info["cvt"]:
        return read_from_sheet(client_info["cvt"])
    else:
        if os.path.exists(CVT_CSV):
            return pd.read_csv(CVT_CSV)
        return pd.DataFrame(columns=CVT_COLUMNS)

# --- Funções para Requisições ---
def append_requisicao(data):
    """Salva requisição de peças"""
    client_info = get_client_and_worksheets()
    
    row = [
        datetime.datetime.now().isoformat(),
        data["tecnico"],
        data["numero_cvt"],
        data.get("ordem_id", ""),
        data["peca_codigo"],
        data["peca_descricao"],
        data["quantidade"],
        "PENDENTE",
        data.get("prioridade", "NORMAL"),
        data.get("observacoes", "")
    ]
    
    if client_info and client_info["req"]:
        success = append_to_sheet(client_info["req"], row)
        if success:
            st.success("Requisição salva com sucesso no Google Sheets!")
    else:
        df = pd.DataFrame([row], columns=REQ_COLUMNS)
        if os.path.exists(REQ_CSV):
            existing_df = pd.read_csv(REQ_CSV)
            df = pd.concat([existing_df, df], ignore_index=True)
        df.to_csv(REQ_CSV, index=False)
        st.success("Requisição salva localmente!")

def read_all_requisicoes():
    """Lê todas as requisições"""
    client_info = get_client_and_worksheets()
    
    if client_info and client_info["req"]:
        return read_from_sheet(client_info["req"])
    else:
        if os.path.exists(REQ_CSV):
            return pd.read_csv(REQ_CSV)
        return pd.DataFrame(columns=REQ_COLUMNS)

# --- Sistema de Autenticação ---
def load_users():
    """Carrega usuários do Google Sheets ou CSV"""
    client_info = get_client_and_worksheets()
    
    if client_info and client_info["users"]:
        users_df = read_from_sheet(client_info["users"])
        if not users_df.empty:
            return users_df.to_dict('records')
    
    # Fallback para CSV
    if os.path.exists(USERS_CSV):
        return pd.read_csv(USERS_CSV).to_dict('records')
    
    # Usuários padrão
    return [
        {"username": "tecnico1", "password": "123", "role": "TECNICO", "nome": "João Silva"},
        {"username": "tecnico2", "password": "123", "role": "TECNICO", "nome": "Maria Santos"},
        {"username": "supervisor", "password": "admin", "role": "SUPERVISOR", "nome": "Carlos Oliveira"}
    ]

def login_form():
    """Formulário de login"""
    st.markdown("## 🔐 Login - Sistema CVT")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            users = load_users()
            user_match = next(
                (u for u in users if u["username"] == username and str(u["password"]) == str(password)),
                None
            )
            
            if user_match:
                st.session_state.update({
                    "authenticated": True,
                    "username": username,
                    "role": user_match["role"],
                    "user_nome": user_match.get("nome", username)
                })
                st.success(f"Bem-vindo, {st.session_state['user_nome']}!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

def logout():
    """Realiza logout"""
    for key in ["authenticated", "username", "role", "user_nome"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# --- Componente para Adicionar Peças ---
def seccion_pecas_cvt():
    """Seção de peças que aparece quando clica em 'Pedir peças'"""
    st.markdown("---")
    st.subheader("⚙️ Pedido de Peças")
    
    # Carrega lista de peças
    pecas_df = load_pecas()
    
    # Inicializa listas e estados
    if 'pecas_adicionadas' not in st.session_state:
        st.session_state.pecas_adicionadas = []
    if 'peca_em_edicao' not in st.session_state:
        st.session_state.peca_em_edicao = None
    if 'peca_temp_campos' not in st.session_state:
        st.session_state.peca_temp_campos = {}
    
    # ---------- FORM 1: Selecionar peça e abrir campos ----------
    with st.form("form_select_peca"):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if not pecas_df.empty:
                peca_options = pecas_df[['codigo', 'descricao', 'categoria']].apply(
                    lambda x: f"{x['codigo']} - {x['descricao']} ({x['categoria']})", axis=1
                ).tolist()
                
                peca_selecionada = st.selectbox(
                    "Selecionar Peça", 
                    options=[""] + peca_options,
                    key="select_peca_cvt"
                )
                
                codigo_peca = ""
                descricao_peca = ""
                peca_info = None
                if peca_selecionada:
                    codigo_peca = peca_selecionada.split(" - ")[0]
                    peca_info = get_peca_by_codigo(codigo_peca)
                    if peca_info is not None:
                        st.text_input("Código", value=peca_info['codigo'], disabled=True)
                        st.text_input("Descrição", value=peca_info['descricao'], disabled=True)
                        st.text_input("Categoria", value=peca_info.get('categoria', 'N/A'), disabled=True)
            else:
                st.info("Nenhuma peça cadastrada")
                codigo_peca = st.text_input("Código da Peça", placeholder="Código interno")
                descricao_peca = st.text_input("Descrição da Peça", placeholder="Descrição detalhada")
        
        with col2:
            prioridade_temp = st.selectbox("Prioridade", ["NORMAL", "URGENTE"], key="prio_peca_select")
            observacoes_temp = st.text_area("Observações", placeholder="Observações específicas...", key="obs_peca_select")
        
        abrir_campos = st.form_submit_button("➕ Abrir Campos para Detalhes")
        
        if abrir_campos:
            # Valida e abre o modo de edição (não salva ainda)
            if not pecas_df.empty and peca_selecionada:
                if peca_info is not None:
                    st.session_state.peca_em_edicao = {
                        "codigo": peca_info['codigo'],
                        "descricao": peca_info['descricao']
                    }
                else:
                    st.error("Peça selecionada não encontrada.")
                    st.session_state.peca_em_edicao = None
            else:
                if codigo_peca and descricao_peca:
                    st.session_state.peca_em_edicao = {
                        "codigo": codigo_peca,
                        "descricao": descricao_peca
                    }
                else:
                    st.error("Preencha código e descrição da peça para abrir os campos.")
                    st.session_state.peca_em_edicao = None
            
            # Salva temporariamente prioridade e observações
            st.session_state.peca_temp_campos = {
                "prioridade": prioridade_temp,
                "observacoes": observacoes_temp
            }
            st.rerun()
    
    # ---------- FORM 2: editar os detalhes e salvar ----------
    if st.session_state.peca_em_edicao:
        peca_edit = st.session_state.peca_em_edicao
        st.markdown("---")
        st.subheader(f"✍️ Detalhes da Peça: {peca_edit['descricao']}")
        
        codigo_edit = peca_edit['codigo']
        campos_especificos = get_campos_por_peca(codigo_edit) if not pecas_df.empty else []
        
        with st.form("form_editar_peca"):
            # Campos dinâmicos (se houver)
            valores_campos = render_campos_dinamicos(campos_especificos)
            
            # Agora sim: quantidade só aqui
            quantidade = st.number_input("Quantidade", min_value=1, value=1, key="qtd_peca_edit")
            prioridade = st.selectbox(
                "Prioridade",
                ["NORMAL", "URGENTE"],
                index=["NORMAL", "URGENTE"].index(st.session_state.peca_temp_campos.get('prioridade', 'NORMAL')),
                key="prio_peca_edit"
            )
            observacoes_peca = st.text_area(
                "Observações",
                value=st.session_state.peca_temp_campos.get('observacoes', ''),
                key="obs_peca_edit"
            )
            
            col_salvar, col_cancel = st.columns([1,1])
            with col_salvar:
                salvar_peca = st.form_submit_button("💾 Salvar Peça")
            with col_cancel:
                cancelar = st.form_submit_button("↩️ Cancelar")
            
            if salvar_peca:
                dados_extras = ""
                if valores_campos:
                    dados_extras = " | ".join([f"{k}: {v}" for k, v in valores_campos.items()])
                
                peca_data = {
                    "codigo": codigo_edit,
                    "descricao": peca_edit['descricao'],
                    "dados_extras": dados_extras,
                    "quantidade": int(quantidade),
                    "prioridade": prioridade,
                    "observacoes": observacoes_peca
                }
                
                st.session_state.pecas_adicionadas.append(peca_data)
                st.success(f"Peça {peca_edit['descricao']} adicionada à lista!")
                
                st.session_state.peca_em_edicao = None
                st.session_state.peca_temp_campos = {}
                st.rerun()
            
            if cancelar:
                st.session_state.peca_em_edicao = None
                st.session_state.peca_temp_campos = {}
                st.rerun()
    
    # ---------- Lista final de peças ----------
    if st.session_state.pecas_adicionadas:
        st.markdown("---")
        st.subheader(" Peças na Lista")
        
        for i, peca in enumerate(st.session_state.pecas_adicionadas):
            col_peca1, col_peca2, col_peca3 = st.columns([3, 1, 1])
            with col_peca1:
                descricao_completa = f"{peca['descricao']} [{peca['dados_extras']}]" if peca['dados_extras'] else peca['descricao']
                st.write(f"**{peca['codigo']}** - {descricao_completa}")
                st.caption(f"Qtd: {peca['quantidade']} | Prioridade: {peca['prioridade']} | Obs: {peca['observacoes']}")
            with col_peca2:
                if st.button("✏️", key=f"edit_{i}"):
                    st.session_state.peca_em_edicao = {"codigo": peca['codigo'], "descricao": peca['descricao']}
                    st.session_state.peca_temp_campos = {
                        "prioridade": peca['prioridade'],
                        "observacoes": peca['observacoes']
                    }
                    st.rerun()
            with col_peca3:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.pecas_adicionadas.pop(i)
                    st.rerun()


# --- Componentes da Interface ---
def cvt_form():
    """Formulário para preenchimento de CVT - Peças aparecem só quando solicitado"""
    st.header(" Comprovante de Visita Técnica")
    
    # Carrega lista de clientes
    clientes_df = load_clientes()
    
    with st.form("cvt_form", clear_on_submit=False):
        st.subheader("Dados da Visita")
        
        # Seleção de cliente
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if not clientes_df.empty and 'nome' in clientes_df.columns:
                cliente_options = clientes_df['nome'].tolist()
                cliente_selecionado = st.selectbox(
                    "Cliente *", 
                    options=[""] + cliente_options,
                    help="Selecione o cliente da lista"
                )
                
                # Busca endereço automaticamente quando cliente é selecionado
                endereco_cliente = ""
                cliente_info = None
                if cliente_selecionado:
                    cliente_info = get_cliente_by_nome(cliente_selecionado)
                    if cliente_info is not None and 'endereco' in cliente_info:
                        endereco_cliente = cliente_info['endereco']
            else:
                st.info("Nenhum cliente cadastrado na base de dados")
                cliente_selecionado = st.text_input("Cliente *", placeholder="Nome do cliente")
                endereco_cliente = st.text_input("Endereço *", placeholder="Endereço completo")
        
        with col2:
            # Mostra informações do cliente selecionado
            if cliente_selecionado and cliente_info is not None:
                st.markdown("**Informações do Cliente:**")
                if 'telefone' in cliente_info:
                    st.text(f"📞 {cliente_info.get('telefone', 'N/A')}")
                if 'responsavel' in cliente_info:
                    st.text(f"👤 {cliente_info.get('responsavel', 'N/A')}")
        
        # Endereço (preenchido automaticamente ou manual)
        endereco = st.text_input("Endereço *", value=endereco_cliente, 
                               placeholder="Endereço completo da visita")
        #Elevador
        elevador = st.selectbox(
            "Elevador*",
            ["", "Principal", "Secundário", "Ambos"],
            help="Selecione em qual elevador o serviço foi realizado"
        )
        
        servico_realizado = st.text_area("Serviço Realizado/Diagnóstico *", 
                                       placeholder="Descreva detalhadamente o serviço executado...",
                                       height=100)
        observacoes = st.text_area("Observações Adicionais", 
                                 placeholder="Observações, recomendações, etc...",
                                 height=80)
        
        # BOTÃO PARA PEDIR PEÇAS - aparece no final do formulário principal
        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            pedir_pecas = st.form_submit_button("⚙️ Pedir Peças")
        with col_btn2:
            salvar_sem_pecas = st.form_submit_button("✅ Salvar CVT sem Peças")
        
        if pedir_pecas:
            if not all([cliente_selecionado, endereco, elevador, servico_realizado]):
                st.error("Preencha todos os campos obrigatórios da CVT (*) antes de pedir peças")
            else:
                st.session_state.mostrar_pecas = True
                st.session_state.dados_cvt_temp = {
                    "cliente": cliente_selecionado,
                    "endereco": endereco,
                    "elevador": elevador,
                    "servico_realizado": servico_realizado,
                    "obs": observacoes
                }
                st.rerun()
        
        if salvar_sem_pecas:
            if not all([cliente_selecionado, endereco, elevador, servico_realizado]):
                st.error("Preencha todos os campos obrigatórios (*)")
            else:
                cvt_data = {
                    "tecnico": st.session_state["user_nome"],
                    "cliente": cliente_selecionado,
                    "endereco": endereco,
                    "elevador": elevador,
                    "servico_realizado": servico_realizado,
                    "obs": observacoes,
                    "pecas_requeridas": ""
                }
                numero_cvt = append_cvt(cvt_data)
                if numero_cvt:
                    st.success(f"CVT {numero_cvt} salva sem peças!")
                    st.session_state.cvt_salva = True
                    st.session_state.numero_cvt_salva = numero_cvt
                    st.rerun()

    # SEÇÃO DE PEÇAS - SÓ APARECE QUANDO CLICAR EM "PEDIR PEÇAS"
    if st.session_state.get('mostrar_pecas', False):
        # Mostra os dados da CVT resumidos
        st.markdown("---")
        st.subheader(" Resumo da CVT")
        dados_temp = st.session_state.dados_cvt_temp
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write(f"**Cliente:** {dados_temp['cliente']}")
            st.write(f"**Endereço:** {dados_temp['endereco']}")
            st.write(f"**Elevador:** {dados_temp['elevador']}")
        with col_res2:
            st.write(f"**Serviço:** {dados_temp['servico_realizado'][:100]}...")
            if dados_temp['obs']:
                st.write(f"**Obs:** {dados_temp['obs'][:100]}...")
        
        # Chama a seção de peças
        seccion_pecas_cvt()
        
        # Botão para SALVAR CVT COM PEÇAS
        st.markdown("---")
        col_save1, col_save2, col_save3 = st.columns([1, 1, 1])
        with col_save1:
            if st.button("✅ Salvar CVT com Peças", type="primary"):
                if not st.session_state.pecas_adicionadas:
                    st.error("Adicione pelo menos uma peça antes de salvar")
                else:
                    # Salva a CVT
                    cvt_data = {
                        "tecnico": st.session_state["user_nome"],
                        "cliente": dados_temp['cliente'],
                        "endereco": dados_temp['endereco'],
                        "elevador": dados_temp['elevador'],
                        "servico_realizado": dados_temp['servico_realizado'],
                        "obs": dados_temp['obs'],
                        "pecas_requeridas": ", ".join([f"{p['codigo']} ({p['quantidade']})" for p in st.session_state.pecas_adicionadas])
                    }
                    numero_cvt = append_cvt(cvt_data)
                    
                    if numero_cvt:
                        # Salva cada peça como requisição
                        for peca in st.session_state.pecas_adicionadas:
                            descricao_completa = f"{peca['descricao']} [{peca['dados_extras']}]" if peca['dados_extras'] else peca['descricao']
                            req_data = {
                                "tecnico": st.session_state["user_nome"],
                                "numero_cvt": numero_cvt,
                                "peca_codigo": peca['codigo'],
                                "peca_descricao": descricao_completa,
                                "quantidade": peca['quantidade'],
                                "prioridade": peca['prioridade'],
                                "observacoes": peca['observacoes']
                            }
                            append_requisicao(req_data)
                        
                        st.success(f"CVT {numero_cvt} salva com {len(st.session_state.pecas_adicionadas)} peça(s)!")
                        
                        # Limpa o session state
                        st.session_state.mostrar_pecas = False
                        st.session_state.pecas_adicionadas = []
                        st.session_state.dados_cvt_temp = None
                        st.session_state.cvt_salva = True
                        st.session_state.numero_cvt_salva = numero_cvt
                        st.rerun()
        
        with col_save2:
            if st.button("↩️ Voltar para Editar CVT"):
                st.session_state.mostrar_pecas = False
                st.rerun()
        
        with col_save3:
            if st.button("🗑️ Cancelar CVT"):
                st.session_state.mostrar_pecas = False
                st.session_state.pecas_adicionadas = []
                st.session_state.dados_cvt_temp = None
                st.rerun()

    # Se a CVT foi salva, mostra opções pós-salvamento
    if st.session_state.get('cvt_salva', False):
        numero_cvt = st.session_state.get('numero_cvt_salva')
        st.success(f"CVT {numero_cvt} processada com sucesso!")

        # --- BOTÃO PARA BAIXAR PDF ---
    st.markdown("---")
    st.subheader("📄 Gerar PDF da CVT")

    if not cvt_salva.empty:
        dados_cvt = cvt_salva.iloc[0].to_dict()
        
        # Busca as peças relacionadas a esta CVT
        req_df = read_all_requisicoes()
        pecas_cvt = req_df[req_df['numero_cvt'] == numero_cvt]
        pecas_lista = pecas_cvt.to_dict('records') if not pecas_cvt.empty else None
        
        # Gera o PDF
        pdf = gerar_pdf_cvt(dados_cvt, pecas_lista)
        
        # Botão de download
        nome_arquivo = f"CVT_{numero_cvt}.pdf"
        criar_botao_download_pdf(pdf, nome_arquivo)
        
        col_pos1, col_pos2 = st.columns(2)
        with col_pos1:
            if st.button(" Nova CVT"):
                # Limpa tudo
                for key in ['cvt_salva', 'numero_cvt_salva', 'mostrar_pecas', 'pecas_adicionadas', 'dados_cvt_temp']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        with col_pos2:
            if st.button(" Ver Minhas CVTs"):
                st.session_state.mostrar_minhas_cvts = True
        
        if st.session_state.get('mostrar_minhas_cvts', False):
            st.subheader(" Minhas CVTs Recentes")
            cvt_df = read_all_cvt()
            user_cvts = cvt_df[cvt_df["tecnico"] == st.session_state["user_nome"]]
            
        if not user_cvts.empty:
        display_cols = ["numero_cvt", "cliente", "endereco", "elevador", "created_at", "status_cvt"]
        display_df = user_cvts[display_cols].copy()
        display_df["created_at"] = pd.to_datetime(display_df["created_at"]).dt.strftime("%d/%m/%Y %H:%M")
        # Mostra a tabela
        st.dataframe(display_df.sort_values("created_at", ascending=False).head(10), use_container_width=True)
        
        # Adiciona opção de baixar PDF para cada CVT
        st.subheader("📄 Baixar PDF de CVTs Anteriores")
        
        cvts_para_download = display_df.head(5)  # Mostra apenas as 5 mais recentes
        
        for _, cvt_row in cvts_para_download.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{cvt_row['numero_cvt']}** - {cvt_row['cliente']} ({cvt_row['created_at']})")
            with col2:
                if st.button(f"📄 PDF", key=f"pdf_{cvt_row['numero_cvt']}"):
                    # Busca dados completos
                    cvt_completa = cvt_df[cvt_df['numero_cvt'] == cvt_row['numero_cvt']].iloc[0].to_dict()
                    
                    # Busca peças
                    req_df = read_all_requisicoes()
                    pecas_cvt = req_df[req_df['numero_cvt'] == cvt_row['numero_cvt']]
                    pecas_lista = pecas_cvt.to_dict('records') if not pecas_cvt.empty else None
                    
                    # Gera e faz download do PDF
                    pdf = gerar_pdf_cvt(cvt_completa, pecas_lista)
                    pdf_output = pdf.output(dest='S').encode('latin-1')
                    
                    st.download_button(
                        label="Baixar PDF",
                        data=pdf_output,
                        file_name=f"CVT_{cvt_row['numero_cvt']}.pdf",
                        mime="application/pdf",
                        key=f"download_{cvt_row['numero_cvt']}"
                    )
            else:
                st.info("Nenhuma CVT encontrada.")

def minhas_requisicoes():
    """Mostra requisições do técnico logado"""
    st.header("Minhas Requisições")
    
    df = read_all_requisicoes()
    if df.empty:
        st.info("Nenhuma requisição encontrada.")
        return
    
    user_reqs = df[df["tecnico"] == st.session_state["user_nome"]]
    
    if user_reqs.empty:
        st.info("Você não possui requisições registradas.")
        return
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Filtrar por status", 
                                   ["Todos"] + sorted(user_reqs["status"].unique()))
    with col2:
        prioridade_filter = st.selectbox("Filtrar por prioridade",
                                       ["Todas"] + sorted(user_reqs["prioridade"].unique()))
    
    # Aplicar filtros
    filtered_reqs = user_reqs.copy()
    if status_filter != "Todos":
        filtered_reqs = filtered_reqs[filtered_reqs["status"] == status_filter]
    if prioridade_filter != "Todas":
        filtered_reqs = filtered_reqs[filtered_reqs["prioridade"] == prioridade_filter]
    
    # Mostrar resultados
    st.write(f"**Total de requisições:** {len(filtered_reqs)}")
    
    # Formatação da tabela
    display_cols = ["created_at", "numero_cvt", "peca_descricao", "quantidade", "status", "prioridade"]
    display_df = filtered_reqs[display_cols].copy()
    display_df["created_at"] = pd.to_datetime(display_df["created_at"]).dt.strftime("%d/%m/%Y %H:%M")
    
    st.dataframe(display_df.sort_values("created_at", ascending=False), use_container_width=True)

def supervisor_panel():
    """Painel exclusivo para supervisores"""
    if st.session_state["role"] != "SUPERVISOR":
        st.error("⛔ Acesso restrito a supervisores")
        return
    
    st.header("Painel de Gerenciamento")
    
    tab1, tab2, tab3 = st.tabs([
        "📦 Todas as Requisições", 
        "📊 Estatísticas", 
        "👥 CVTs"
    ])
    
    with tab1:
        st.subheader("Gestão de Requisições")
        
        df = read_all_requisicoes()
        if df.empty:
            st.info("Nenhuma requisição encontrada.")
            return
        
        # Filtros para supervisor
        col1, col2, col3 = st.columns(3)
        with col1:
            tecnico_filter = st.selectbox("Técnico", ["Todos"] + sorted(df["tecnico"].unique()))
        with col2:
            status_filter = st.selectbox("Status", ["Todos"] + sorted(df["status"].unique()))
        with col3:
            prioridade_filter = st.selectbox("Prioridade", ["Todas"] + sorted(df["prioridade"].unique()))
        
        # Aplicar filtros
        filtered_df = df.copy()
        if tecnico_filter != "Todos":
            filtered_df = filtered_df[filtered_df["tecnico"] == tecnico_filter]
        if status_filter != "Todos":
            filtered_df = filtered_df[filtered_df["status"] == status_filter]
        if prioridade_filter != "Todas":
            filtered_df = filtered_df[filtered_df["prioridade"] == prioridade_filter]
        
        st.write(f"**Requisições encontradas:** {len(filtered_df)}")
        
        # Exibir tabela
        st.dataframe(filtered_df.sort_values("created_at", ascending=False), use_container_width=True)
    
    with tab2:
        st.subheader("Estatísticas e Relatórios")
        
        df = read_all_requisicoes()
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total = len(df)
                pendentes = len(df[df["status"] == "PENDENTE"])
                st.metric("Total Requisições", total)
                st.metric("Pendentes", pendentes)
            
            with col2:
                tecnicos = df["tecnico"].nunique()
                st.metric("Técnicos Ativos", tecnicos)
            
            with col3:
                urgentes = len(df[df["prioridade"] == "URGENTE"])
                st.metric("Urgentes", urgentes)
            
            # Gráfico simples de status
            st.bar_chart(df["status"].value_counts())
        else:
            st.info("Nenhuma requisição encontrada para estatísticas.")
    
    with tab3:
        st.subheader("CVTs dos Técnicos")
        
        cvt_df = read_all_cvt()
        if not cvt_df.empty:
            st.dataframe(cvt_df.sort_values("created_at", ascending=False), use_container_width=True)
        else:
            st.info("Nenhuma CVT encontrada.")

# --- Interface Principal ---
def main_interface():
    """Interface principal do aplicativo"""
    
    # Header com informações do usuário
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=80)
        else:
            st.markdown("### ⚙️")
    with col2:
        st.title("Sistema CVT")
        st.caption(f"Logado como: {st.session_state['user_nome']} ({st.session_state['role']})")
    with col3:
        if st.button("Sair", use_container_width=True):
            logout()
    
    # Menu de navegação - REMOVIDA A ABA "REQUISIÇÃO"
    if st.session_state["role"] == "SUPERVISOR":
        menu_options = [" Nova CVT", " Minhas Req", "Gerenciamento"]
        menu_icons = ["file-earmark-text", "clipboard", "person-badge"]
        default_index = 0
    else:
        menu_options = [" Nova CVT", " Minhas Req"]
        menu_icons = ["file-earmark-text", "clipboard"]
        default_index = 0
    
    with st.container():
        selected = option_menu(
            menu_title=None,
            options=menu_options,
            icons=menu_icons,
            default_index=default_index,
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "#f0f2f6"},
                "icon": {"color": "orange", "font-size": "18px"}, 
                "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#2E86AB"},
            }
        )
    
    # Conteúdo baseado na seleção
    if selected == " Nova CVT":
        cvt_form()
    elif selected == " Minhas Req":
        minhas_requisicoes()
    elif selected == "Gerenciamento":
        supervisor_panel()

# --- App Principal ---
def main():
    """Função principal do aplicativo"""
    
    # Inicialização da sessão
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "cvt_salva" not in st.session_state:
        st.session_state.cvt_salva = False
    if "mostrar_pecas" not in st.session_state:
        st.session_state.mostrar_pecas = False
    if "pecas_adicionadas" not in st.session_state:
        st.session_state.pecas_adicionadas = []
    if "dados_cvt_temp" not in st.session_state:
        st.session_state.dados_cvt_temp = None
    if "mostrar_minhas_cvts" not in st.session_state:
        st.session_state.mostrar_minhas_cvts = False
    
    # Verifica autenticação
    if not st.session_state.authenticated:
        login_form()
        
        # Footer informativo
        
    else:
        main_interface()

if __name__ == "__main__":
    main()
