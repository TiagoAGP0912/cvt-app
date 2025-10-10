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

# Colunas das planilhas - VERIFICAR ORDEM CORRETA
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
    pdf.cell(100, 8, txt=f"Número CVT: {dados_cvt.get('numero_cvt', 'N/A')}", ln=1)
    
    # Formata data
    if 'created_at' in dados_cvt:
        try:
            data_obj = pd.to_datetime(dados_cvt['created_at'])
            data_formatada = data_obj.strftime("%d/%m/%Y %H:%M")
            pdf.cell(100, 8, txt=f"Data/Hora: {data_formatada}", ln=1)
        except:
            pdf.cell(100, 8, txt=f"Data/Hora: {dados_cvt.get('created_at', 'N/A')}", ln=1)
    
    pdf.cell(100, 8, txt=f"Técnico: {dados_cvt.get('tecnico', 'N/A')}", ln=1)
    pdf.cell(100, 8, txt=f"Cliente: {dados_cvt.get('cliente', 'N/A')}", ln=1)
    pdf.cell(100, 8, txt=f"Endereço: {dados_cvt.get('endereco', 'N/A')}", ln=1)
    pdf.cell(100, 8, txt=f"Elevador: {dados_cvt.get('elevador', 'Não informado')}", ln=1)
    pdf.ln(5)
    
    # Serviço Realizado
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="SERVIÇO REALIZADO / DIAGNÓSTICO", ln=1)
    pdf.set_font("Arial", size=11)
    
    # Quebra o texto do serviço em múltiplas linhas
    servico = dados_cvt.get('servico_realizado', 'Não informado')
    pdf.multi_cell(0, 8, txt=str(servico))
    pdf.ln(5)
    
    # Observações (se houver)
    if dados_cvt.get('obs'):
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="OBSERVAÇÕES ADICIONAIS", ln=1)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, txt=str(dados_cvt.get('obs', '')))
        pdf.ln(5)
    
    # 🔹 Seção de Peças (se houver) - CORREÇÃO AQUI
    if pecas and isinstance(pecas, (list, tuple)) and len(pecas) > 0:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="PEÇAS SOLICITADAS", ln=1)
        pdf.set_font("Arial", size=9)
        
        # Cabeçalho da tabela
        pdf.set_fill_color(200, 200, 200)
        col_widths = [25, 70, 15, 25, 65]
        headers = ["Código", "Descrição", "Qtd", "Prioridade", "Observações"]
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, 1, 0, 'C', True)
        pdf.ln()

        # Linhas da tabela - CORREÇÃO: SÓ ENTRA NO LOOP SE HOUVER PEÇAS
        for peca in pecas:
            linha_altura = 8
            campos = [
                str(peca.get('peca_codigo', '')),
                str(peca.get('peca_descricao', '')),
                str(peca.get('quantidade', '')),
                str(peca.get('prioridade', '')),
                str(peca.get('observacoes', ''))
            ]

            # Calcula altura máxima da linha (quantas linhas cada campo vai precisar)
            alturas = []
            for i, texto in enumerate(campos):
                n_linhas = len(pdf.multi_cell(col_widths[i], linha_altura, texto, border=0, align='L', split_only=True))
                alturas.append(n_linhas * linha_altura)
            linha_max_altura = max(alturas)

            # Posição inicial da linha
            y_inicial = pdf.get_y()
            x_inicial = pdf.get_x()

            # Escreve cada célula com altura igual
            for i, texto in enumerate(campos):
                x_atual = x_inicial + sum(col_widths[:i])
                pdf.set_xy(x_atual, y_inicial)
                pdf.multi_cell(col_widths[i], linha_altura, texto, border=1, align='L', max_line_height=linha_altura)
                
                # Se a célula tiver menos linhas, completa a borda até a altura máxima
                y_final = y_inicial + linha_max_altura
                pdf.set_xy(x_atual + col_widths[i], y_inicial)

            # Move o cursor pra próxima linha
            pdf.set_y(y_inicial + linha_max_altura)
        pdf.ln(5)
    else:
        # Se não há peças, mostra uma mensagem
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="PEÇAS SOLICITADAS", ln=1)
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 8, txt="Nenhuma peça solicitada nesta CVT", ln=1)
        pdf.ln(5)

    # Rodapé
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, txt="Documento somente para teste", ln=1, align='C')
    
    return pdf

def criar_botao_download_pdf(pdf, nome_arquivo):
    """Cria um botão de download para o PDF"""
    try:
        # Método correto para obter o conteúdo do PDF
        pdf_output = pdf.output(dest='S')
        
        # Se já é uma string, apenas encode
        if isinstance(pdf_output, str):
            pdf_bytes = pdf_output.encode('latin-1')
        else:
            # Se for bytes, use diretamente
            pdf_bytes = pdf_output
            
        b64_pdf = base64.b64encode(pdf_bytes).decode()
        
        href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{nome_arquivo}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px; font-weight: bold;">📄 Baixar PDF da CVT</a>'
        st.markdown(href, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {str(e)}")
        # Fallback: criar um botão de download alternativo
        try:
            # Salva em um arquivo temporário e lê os bytes
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                pdf.output(tmp.name)
                tmp.flush()
                with open(tmp.name, 'rb') as f:
                    pdf_bytes = f.read()
                
                b64_pdf = base64.b64encode(pdf_bytes).decode()
                href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{nome_arquivo}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px; font-weight: bold;">📄 Baixar PDF da CVT</a>'
                st.markdown(href, unsafe_allow_html=True)
                
            # Limpa o arquivo temporário
            os.unlink(tmp.name)
            
        except Exception as e2:
            st.error(f"Erro ao criar PDF alternativo: {str(e2)}")

def debug_cvt_salvar(data, numero_cvt):
    """Função para debug do salvamento da CVT"""
    st.write("### 🔧 DEBUG - Dados da CVT sendo salvos:")
    st.write(f"**Número CVT:** {numero_cvt}")
    st.write(f"**Técnico:** {data['tecnico']}")
    st.write(f"**Cliente:** {data['cliente']}")
    st.write(f"**Endereço:** {data['endereco']}")
    st.write(f"**Serviço:** {data['servico_realizado'][:50]}...")
    st.write(f"**Peças requeridas:** {data['pecas_requeridas']}")
    
    # Verifica onde está salvando
    client_info = get_client_and_worksheets()
    if client_info and client_info["cvt"]:
        st.write("**Local:** Google Sheets")
    else:
        st.write("**Local:** CSV Local")

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
        st.write(f"📖 Lendo dados da worksheet: {worksheet.title}")
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        
        # DEBUG
        st.write(f"📊 Registros brutos do Sheets: {len(records)}")
        if records:
            st.write(f"📋 Primeiro registro: {records[0]}")
        
        return df
    except Exception as e:
        st.error(f"❌ Erro ao ler do Sheets: {str(e)}")
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

# --- Usa o tempo de Brasília ---
def get_brasilia_time():
    """Retorna o horário atual no fuso horário de Brasília (UTC-3)"""
    utc_now = datetime.datetime.utcnow()
    brasilia_offset = datetime.timedelta(hours=-3)
    return utc_now + brasilia_offset
    
# --- Funções para CVT ---
def append_cvt(data):
    """Salva CVT no Google Sheets ou CSV"""
    client_info = get_client_and_worksheets()
    
    # Usar horário de Brasília
    data_hora_brasilia = get_brasilia_time()
    
    # Gera número único para CVT com horário correto
    numero_cvt = f"CVT-{data_hora_brasilia.strftime('%Y%m%d-%H%M%S')}"
    
    # CORREÇÃO CRÍTICA: Ordem das colunas deve corresponder EXATAMENTE à CVT_COLUMNS
    row = [
        data_hora_brasilia.isoformat(),  # created_at
        data["tecnico"],                 # tecnico
        data["cliente"],                 # cliente
        data["endereco"],                # endereco
        data["servico_realizado"],       # servico_realizado
        data["obs"],                     # obs
        data["pecas_requeridas"],        # pecas_requeridas
        data.get("elevador", ""),        # elevador
        "SALVO",                         # status_cvt
        numero_cvt                       # numero_cvt
    ]
    
    # DEBUG - Mostrar o que está sendo salvo
    st.write("### 🔍 DEBUG - Dados sendo salvos:")
    st.write(f"**Ordem das colunas:** {CVT_COLUMNS}")
    st.write(f"**Dados na linha:** {row}")
    
    if client_info and client_info["cvt"]:
        success = append_to_sheet(client_info["cvt"], row)
        if success:
            st.success(f"CVT {numero_cvt} salva com sucesso no Google Sheets!")
            return numero_cvt
        else:
            st.error("Falha ao salvar no Google Sheets!")
            return None
    else:
        # Fallback para CSV
        df = pd.DataFrame([row], columns=CVT_COLUMNS)
        if os.path.exists(CVT_CSV):
            try:
                existing_df = pd.read_csv(CVT_CSV)
                df = pd.concat([existing_df, df], ignore_index=True)
            except Exception as e:
                st.warning(f"Erro ao ler CSV existente, criando novo: {e}")
        
        try:
            df.to_csv(CVT_CSV, index=False)
            st.success(f"CVT {numero_cvt} salva localmente no CSV!")
            return numero_cvt
        except Exception as e:
            st.error(f"Erro ao salvar CSV: {e}")
            return None

def read_all_cvt():
    """Lê todas as CVTs"""
    client_info = get_client_and_worksheets()
    
    if client_info and client_info["cvt"]:
        try:
            st.write("🔍 Lendo CVTs do Google Sheets...")
            df = read_from_sheet(client_info["cvt"])
            
            # DEBUG: Mostrar informações sobre o DataFrame
            st.write(f"📊 CVTs encontradas no Sheets: {len(df)}")
            if not df.empty:
                st.write(f"📋 Colunas: {list(df.columns)}")
                st.write(f"👥 Técnicos únicos: {df['tecnico'].unique() if 'tecnico' in df.columns else 'Coluna tecnico não encontrada'}")
                st.write(f"🔢 Amostra de dados:")
                st.dataframe(df.head(3))
            else:
                st.warning("⚠️ DataFrame vazio retornado do Google Sheets")
            
            return df
        except Exception as e:
            st.error(f"❌ Erro ao ler do Google Sheets: {str(e)}")
            # Fallback para CSV
            if os.path.exists(CVT_CSV):
                st.info("📁 Usando fallback para CSV...")
                return pd.read_csv(CVT_CSV)
            return pd.DataFrame(columns=CVT_COLUMNS)
    else:
        # Fallback para CSV
        if os.path.exists(CVT_CSV):
            st.write("🔍 Lendo CVTs do CSV local...")
            df = pd.read_csv(CVT_CSV)
            st.write(f"📊 CVTs encontradas no CSV: {len(df)}")
            if not df.empty:
                st.write(f"📋 Colunas: {list(df.columns)}")
            return df
        st.info("📁 Nenhum arquivo CSV local encontrado")
        return pd.DataFrame(columns=CVT_COLUMNS)


# --- Funções para Requisições ---
def append_requisicao(data):
    """Salva requisição de peças"""
    client_info = get_client_and_worksheets()
    
    # CORREÇÃO: Usar horário de Brasília também para requisições
    data_hora_brasilia = get_brasilia_time()
    
    row = [
        data_hora_brasilia.isoformat(),  # created_at
        data["tecnico"],                 # tecnico
        data["numero_cvt"],              # numero_cvt
        data.get("ordem_id", ""),        # ordem_id
        data["peca_codigo"],             # peca_codigo
        data["peca_descricao"],          # peca_descricao
        data["quantidade"],              # quantidade
        "PENDENTE",                      # status
        data.get("prioridade", "NORMAL"),# prioridade
        data.get("observacoes", "")      # observacoes
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

        # Busca os dados da CVT salva
        cvt_df = read_all_cvt()
        cvt_salva_df = cvt_df[cvt_df['numero_cvt'] == numero_cvt]
        
        if not cvt_salva_df.empty:
            dados_cvt = cvt_salva_df.iloc[0].to_dict()
            
            # CORREÇÃO: Verificar se a coluna existe antes de filtrar
            req_df = read_all_requisicoes()
            
            # Verifica se a coluna 'numero_cvt' existe no DataFrame de requisições
            if not req_df.empty and 'numero_cvt' in req_df.columns:
                pecas_cvt = req_df[req_df['numero_cvt'] == numero_cvt]
                pecas_lista = pecas_cvt.to_dict('records') if not pecas_cvt.empty else None
            else:
                # Se não existe a coluna ou o DataFrame está vazio, não há peças
                pecas_lista = None
            
            # Gera o PDF
            pdf = gerar_pdf_cvt(dados_cvt, pecas_lista)
            
            # Botão de download
            nome_arquivo = f"CVT_{numero_cvt}.pdf"
            criar_botao_download_pdf(pdf, nome_arquivo)
            
            col_pos1, col_pos2 = st.columns(2)
            with col_pos1:
                if st.button("➕ Nova CVT"):
                    # Limpa tudo
                    for key in ['cvt_salva', 'numero_cvt_salva', 'mostrar_pecas', 'pecas_adicionadas', 'dados_cvt_temp']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            with col_pos2:
                if st.button("📋 Ver Minhas CVTs"):
                    st.session_state.mostrar_minhas_cvts = True
                    st.rerun()

    # Seção para visualizar CVTs anteriores - FORA DO BLOCO ANTERIOR
    if st.session_state.get('mostrar_minhas_cvts', False):
        st.subheader("📋 Minhas CVTs Recentes")
        cvt_df = read_all_cvt()
        user_cvts = cvt_df[cvt_df["tecnico"] == st.session_state["user_nome"]]
        
        if not user_cvts.empty:
            display_cols = ["numero_cvt", "cliente", "endereco", "elevador", "created_at", "status_cvt"]
            display_df = user_cvts[display_cols].copy()
            
            # Converte a data para formato legível
            try:
                display_df["created_at"] = pd.to_datetime(display_df["created_at"]).dt.strftime("%d/%m/%Y %H:%M")
            except:
                display_df["created_at"] = display_df["created_at"].astype(str)
            
            # Mostra a tabela
            st.dataframe(display_df.sort_values("created_at", ascending=False).head(10), use_container_width=True)
            
            # Adiciona opção de baixar PDF para cada CVT
            st.subheader("📄 Baixar PDF de CVTs Anteriores")
            
            # Seleção de CVT para download
            cvts_options = display_df['numero_cvt'].tolist()
            if cvts_options:
                cvt_selecionada = st.selectbox(
                    "Selecione uma CVT para gerar PDF:",
                    options=cvts_options,
                    key="select_cvt_pdf"
                )
                
                if cvt_selecionada:
                    # Busca dados completos da CVT selecionada
                    cvt_completa_df = cvt_df[cvt_df['numero_cvt'] == cvt_selecionada]
                    
                    if not cvt_completa_df.empty:
                        cvt_completa = cvt_completa_df.iloc[0].to_dict()
                        
                        # Busca peças
                        req_df = read_all_requisicoes()
                        if not req_df.empty and 'numero_cvt' in req_df.columns:
                            pecas_cvt = req_df[req_df['numero_cvt'] == cvt_selecionada]
                            pecas_lista = pecas_cvt.to_dict('records') if not pecas_cvt.empty else None
                        else:
                            pecas_lista = None
                        
                        # Gera o PDF
                        pdf = gerar_pdf_cvt(cvt_completa, pecas_lista)
                        pdf_output = pdf.output(dest='S').encode('latin-1')
                        
                        # Botão de download
                        st.download_button(
                            label=f"📥 Baixar PDF da CVT {cvt_selecionada}",
                            data=pdf_output,
                            file_name=f"CVT_{cvt_selecionada}.pdf",
                            mime="application/pdf",
                            key=f"download_{cvt_selecionada}",
                            use_container_width=True
                        )
                    else:
                        st.error("CVT não encontrada nos dados completos.")
            else:
                st.info("Nenhuma CVT disponível para download.")
        else:
            st.info("Nenhuma CVT encontrada.")
        
        # Botão para voltar
        if st.button("↩️ Voltar para Nova CVT"):
            st.session_state.mostrar_minhas_cvts = False
            st.rerun()

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
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 Todas as Requisições", 
        "📊 Estatísticas", 
        "👥 CVTs",
        "📄 Gerar PDFs",
        "🔍 DEBUG CVTs"
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
    
    # DEBUG EXTENDIDO
    st.write("### 🔍 DEBUG - Status da Leitura")
    st.write(f"**Total de CVTs carregadas:** {len(cvt_df)}")
    
    if not cvt_df.empty:
        st.write("**📋 Estrutura do DataFrame:**")
        st.write(f"- Colunas: {list(cvt_df.columns)}")
        st.write(f"- Shape: {cvt_df.shape}")
        st.write(f"- Técnicos únicos: {cvt_df['tecnico'].unique()}")
        st.write(f"- Status únicos: {cvt_df['status_cvt'].unique() if 'status_cvt' in cvt_df.columns else 'Coluna status_cvt não encontrada'}")
        
        st.write("**📊 Primeiras 3 linhas:**")
        st.dataframe(cvt_df.head(3))
        
        # Filtros para CVTs
        col1, col2 = st.columns(2)
        with col1:
            tecnico_cvt_filter = st.selectbox(
                "Filtrar por Técnico", 
                ["Todos"] + sorted(cvt_df["tecnico"].unique()),
                key="tecnico_cvt_filter"
            )
        with col2:
            status_cvt_filter = st.selectbox(
                "Filtrar por Status",
                ["Todos"] + sorted(cvt_df["status_cvt"].unique()) if 'status_cvt' in cvt_df.columns else ["Todos"],
                key="status_cvt_filter"
            )
        
        # Aplicar filtros
        filtered_cvts = cvt_df.copy()
        if tecnico_cvt_filter != "Todos":
            filtered_cvts = filtered_cvts[filtered_cvts["tecnico"] == tecnico_cvt_filter]
        if status_cvt_filter != "Todos" and 'status_cvt' in filtered_cvts.columns:
            filtered_cvts = filtered_cvts[filtered_cvts["status_cvt"] == status_cvt_filter]
        
        st.write(f"**CVTs encontradas após filtro:** {len(filtered_cvts)}")
        
        # Formatar datas para exibição
        display_cvts = filtered_cvts.copy()
        if 'created_at' in display_cvts.columns:
            try:
                display_cvts["created_at"] = pd.to_datetime(display_cvts["created_at"]).dt.strftime("%d/%m/%Y %H:%M")
            except:
                display_cvts["created_at"] = display_cvts["created_at"].astype(str)
        
        # Mostrar tabela com colunas selecionadas
        cols_disponiveis = []
        for col in ["numero_cvt", "tecnico", "cliente", "created_at", "status_cvt"]:
            if col in display_cvts.columns:
                cols_disponiveis.append(col)
        
        if cols_disponiveis:
            st.dataframe(display_cvts[cols_disponiveis].sort_values("created_at" if "created_at" in cols_disponiveis else "numero_cvt", ascending=False), 
                        use_container_width=True)
        else:
            st.error("❌ Nenhuma coluna de exibição disponível")
    else:
        st.info("ℹ️ Nenhuma CVT encontrada no sistema.")
    
    with tab4:
        st.subheader("📄 Gerar PDF de CVTs")
        
        cvt_df = read_all_cvt()
        if not cvt_df.empty:
            # Filtros para busca de CVTs
            col1, col2 = st.columns(2)
            with col1:
                tecnico_pdf_filter = st.selectbox(
                    "Filtrar por Técnico", 
                    ["Todos"] + sorted(cvt_df["tecnico"].unique()),
                    key="tecnico_pdf_filter"
                )
            with col2:
                # Campo de busca por número da CVT
                numero_cvt_busca = st.text_input("Buscar por Número da CVT", placeholder="Ex: CVT-20251006-232324")
            
            # Aplicar filtros
            cvts_filtradas = cvt_df.copy()
            if tecnico_pdf_filter != "Todos":
                cvts_filtradas = cvts_filtradas[cvts_filtradas["tecnico"] == tecnico_pdf_filter]
            if numero_cvt_busca:
                cvts_filtradas = cvts_filtradas[cvts_filtradas["numero_cvt"].str.contains(numero_cvt_busca, case=False, na=False)]
            
            if not cvts_filtradas.empty:
                # Seleção da CVT para gerar PDF
                st.subheader("Selecionar CVT para Gerar PDF")
                
                # Criar opções para selectbox
                cvts_options = cvts_filtradas.apply(
                    lambda x: f"{x['numero_cvt']} - {x['cliente']} ({x['tecnico']}) - {x['created_at']}", 
                    axis=1
                ).tolist()
                
                cvt_selecionada_str = st.selectbox(
                    "Selecione uma CVT:",
                    options=cvts_options,
                    key="select_cvt_supervisor"
                )
                
                if cvt_selecionada_str:
                    # Extrair o número da CVT da string selecionada
                    numero_cvt_selecionada = cvt_selecionada_str.split(" - ")[0]
                    
                    # Buscar dados completos da CVT selecionada
                    cvt_completa_df = cvt_df[cvt_df['numero_cvt'] == numero_cvt_selecionada]
                    
                    if not cvt_completa_df.empty:
                        cvt_completa = cvt_completa_df.iloc[0].to_dict()
                        
                        # Buscar peças relacionadas
                        req_df = read_all_requisicoes()
                        if not req_df.empty and 'numero_cvt' in req_df.columns:
                            pecas_cvt = req_df[req_df['numero_cvt'] == numero_cvt_selecionada]
                            pecas_lista = pecas_cvt.to_dict('records') if not pecas_cvt.empty else None
                        else:
                            pecas_lista = None
                        
                        # Gerar preview dos dados
                        st.subheader("Pré-visualização dos Dados")
                        col_preview1, col_preview2 = st.columns(2)
                        with col_preview1:
                            st.write(f"**Número CVT:** {cvt_completa.get('numero_cvt', 'N/A')}")
                            st.write(f"**Técnico:** {cvt_completa.get('tecnico', 'N/A')}")
                            st.write(f"**Cliente:** {cvt_completa.get('cliente', 'N/A')}")
                            st.write(f"**Data:** {cvt_completa.get('created_at', 'N/A')}")
                        with col_preview2:
                            st.write(f"**Endereço:** {cvt_completa.get('endereco', 'N/A')}")
                            st.write(f"**Elevador:** {cvt_completa.get('elevador', 'N/A')}")
                            st.write(f"**Status:** {cvt_completa.get('status_cvt', 'N/A')}")
                            st.write(f"**Peças:** {len(pecas_lista) if pecas_lista else 0}")
                        
                        # Botão para gerar e baixar PDF
                        st.markdown("---")
                        st.subheader("Gerar PDF")
                        
                        # Gerar o PDF
                        pdf = gerar_pdf_cvt(cvt_completa, pecas_lista)
                        
                        # Botão de download
                        nome_arquivo = f"CVT_{numero_cvt_selecionada}.pdf"
                        criar_botao_download_pdf(pdf, nome_arquivo)
                        
                    else:
                        st.error("CVT selecionada não encontrada nos dados completos.")
                else:
                    st.info("Selecione uma CVT da lista para gerar o PDF.")
            
            else:
                st.info("Nenhuma CVT encontrada com os filtros aplicados.")
                
            # Mostrar estatísticas rápidas
            st.markdown("---")
            st.subheader("📊 Estatísticas das CVTs")
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Total de CVTs", len(cvt_df))
            with col_stat2:
                cvts_por_tecnico = cvt_df["tecnico"].nunique()
                st.metric("Técnicos com CVTs", cvts_por_tecnico)
            with col_stat3:
                cvts_com_pecas = len(cvt_df[cvt_df["pecas_requeridas"] != ""])
                st.metric("CVTs com Peças", cvts_com_pecas)
                
        else:
            st.info("Nenhuma CVT encontrada no sistema.")
    
    with tab5:
        st.subheader("🔍 DEBUG - Todas as CVTs")
        cvt_df = read_all_cvt()
        
        st.write(f"**Total de CVTs no sistema:** {len(cvt_df)}")
        
        if not cvt_df.empty:
            st.write("**Colunas disponíveis:**", list(cvt_df.columns))
            st.write("**Primeiras 5 CVTs:**")
            st.dataframe(cvt_df.head())
            
            # Mostrar estatísticas por técnico
            st.write("**CVTs por Técnico:**")
            tech_stats = cvt_df['tecnico'].value_counts()
            st.write(tech_stats)
        else:
            st.info("Nenhuma CVT encontrada para debug.")

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
    
    # Menu de navegação
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
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: gray;'>
            <small>Sistema CVT - Desenvolvido para gestão de visitas técnicas</small>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        main_interface()

if __name__ == "__main__":
    main()
