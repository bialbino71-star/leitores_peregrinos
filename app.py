import streamlit as st
import streamlit.components.v1 as components
import gspread
import base64
import json
import re
from datetime import datetime, date, timedelta
from google.oauth2 import service_account
from fpdf import FPDF

# Configuração da página - Centralizado e responsivo
st.set_page_config(
    page_title="Leitores Peregrinos", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- GERENCIAMENTO DE ESTADO DA SESSÃO ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_profile = ""
    st.session_state.user_id = ""

if "pagina" not in st.session_state:
    st.session_state.pagina = "home"

# --- FUNÇÕES DE TRANSIÇÃO DE TELA (NATIVAS E RÁPIDAS) ---
def navegar_para(nome_pagina):
    st.session_state.pagina = nome_pagina

def efetuar_logout():
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_profile = ""
    st.session_state.user_id = ""
    st.session_state.pagina = "home"

# --- FOLHA DE ESTILO GLOBAL (SEM PARAMETROS DE URL OU LINKS FALSOS) ---
st.markdown("""
    <style>
    /* Forçar a largura ideal da página */
    .block-container {
        max-width: 700px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }
    
    /* Fundo Geral da Página (Marfim Quente) */
    .stApp {
        background-color: #FEFAE0 !important;
    }
    
    /* Ocultar elementos nativos do Streamlit */
    #MainMenu, footer, header {visibility: hidden !important;}
    
    /* Contêiner do Cabeçalho Superior Oficial */
    .cartao-superior-oficial {
        width: 100%;
        margin-bottom: 25px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .imagem-layout-completo {
        width: 100% !important;
        height: auto !important;
        display: block;
        border-radius: 16px;
    }
    
    /* BARRA DE STATUS TERRACOTA UNIFICADA */
    .barra-status-alinhada {
        background-color: #EAB99F !important;
        border-radius: 20px !important;
        padding: 14px 20px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        height: 56px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.05);
        width: 100%;
        box-sizing: border-box;
    }
    
    .texto-logado-interno {
        color: #3D2612 !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        font-family: sans-serif;
    }

    /* POSICIONADOR DO BOTÃO SAIR NATIVO CHAVEADO (ao lado da barra, mesma altura) */
    .st-key-sair_wrapper {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        height: 56px !important;
        margin-bottom: 15px !important;
    }

    .st-key-sair_wrapper button {
        background: #1C120C !important;
        color: #FFFFFF !important;
        border: 1px solid #3D2612 !important;
        border-radius: 25px !important;
        padding: 4px 24px !important;
        font-size: 15px !important;
        font-weight: bold !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.25) !important;
        height: 36px !important;
        width: auto !important;
    }
    
    .st-key-sair_wrapper button:hover {
        background: #2D1E15 !important;
    }
    
    /* ESTILIZAÇÃO DO PAINEL DO MENU (CINZA-GRAFITE) - AGORA EM COLUNA ÚNICA */
    .st-key-menu_grid {
        background-color: #4F5666 !important;
        border-radius: 16px !important;
        padding: 24px 16px !important;
        margin-bottom: 25px !important;
        box-shadow: inset 0 2px 6px rgba(0,0,0,0.2), 0 4px 10px rgba(0,0,0,0.1) !important;
    }
    
    /* RESOLUÇÃO VISUAL DOS BOTÕES INTERNOS (AZUL PETRÓLEO + DUPLO CONTORNO CHANFRADO BRONZE) */
    .st-key-menu_grid button,
    .st-key-menu_grid div.stLinkButton a {
        background: #0D1B2A !important;
        border: 3.5px solid #8C6D4F !important;
        outline: 1.5px solid #423224 !important;
        border-radius: 24px !important;
        padding: 12px 10px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        text-align: center !important;
        width: 100% !important;
        display: block !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.35), inset 0 1px 2px rgba(255,255,255,0.1) !important;
        font-family: sans-serif;
        text-decoration: none !important;
        box-sizing: border-box !important;
        height: auto !important;
        white-space: normal !important;
        line-height: 1.2 !important;
    }

    /* Cor do texto DENTRO do botão (o Streamlit envolve o rótulo do botão num stMarkdownContainer,
       então precisamos de mais especificidade do que a regra de texto de conteúdo abaixo) */
    .stApp.stApp .st-key-menu_grid button,
    .stApp.stApp .st-key-menu_grid button p,
    .stApp.stApp .st-key-menu_grid button div,
    .stApp.stApp .st-key-menu_grid button span,
    .stApp.stApp .st-key-menu_grid div.stLinkButton a,
    .stApp.stApp .st-key-menu_grid div.stLinkButton a p,
    .stApp.stApp .st-key-menu_grid div.stLinkButton a div,
    .stApp.stApp .st-key-menu_grid div.stLinkButton a span {
        color: #FFFFFF !important;
    }
    
    .st-key-menu_grid button:hover,
    .st-key-menu_grid div.stLinkButton a:hover {
        background: #15273C !important;
        border-color: #A38465 !important;
    }

    /* TÍTULO "Identificação do Leitor" (mesma paleta/estilo do cabeçalho oficial) */
    .titulo-identificacao {
        color: #5C3A21 !important;
        font-family: Georgia, 'Times New Roman', serif !important;
        font-weight: 700 !important;
        font-size: 26px !important;
        text-align: center;
        margin-bottom: 10px;
    }

    /* LABELS E TÍTULOS PADRÃO DO APP: sempre em tom escuro, mesmo se o celular estiver em modo escuro */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp label {
        color: #3D2612 !important;
    }

    /* TEXTO DE CONTEÚDO (descrições dos eventos em Escala Geral, Minha Escala, Aguardando Leitores etc.)
       Mira apenas o texto dentro de blocos de markdown/write - nunca o texto interno de botões. */
    .stApp div[data-testid="stMarkdownContainer"] p,
    .stApp div[data-testid="stMarkdownContainer"] li,
    .stApp div[data-testid="stMarkdownContainer"] {
        color: #3D2612 !important;
    }

    /* CAIXAS DE TEXTO (login e demais formulários): fundo branco, texto preto */
    .stTextInput input, .stTextArea textarea {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }

    /* BOTÕES PADRÃO DO APP (Entrar, Voltar ao Menu, Alterar, Salvar, Servir, Cancelar etc.) 
       Estes não têm key específico, então aplicamos um estilo legível (fundo escuro + texto dourado) */
    div[data-testid="stButton"] button,
    div[data-testid="stFormSubmitButton"] button {
        background-color: #0D1B2A !important;
        border: 1px solid #3D2612 !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
    }
    .stApp.stApp div[data-testid="stButton"] button,
    .stApp.stApp div[data-testid="stButton"] button p,
    .stApp.stApp div[data-testid="stButton"] button div,
    .stApp.stApp div[data-testid="stButton"] button span,
    .stApp.stApp div[data-testid="stFormSubmitButton"] button,
    .stApp.stApp div[data-testid="stFormSubmitButton"] button p,
    .stApp.stApp div[data-testid="stFormSubmitButton"] button div,
    .stApp.stApp div[data-testid="stFormSubmitButton"] button span {
        color: #FFFFFF !important;
    }
    div[data-testid="stButton"] button:hover,
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #15273C !important;
    }

    /* O botão Sair e os botões do menu têm estilo próprio mais específico, então continuam intactos abaixo */
    .stApp.stApp .st-key-sair_wrapper button,
    .stApp.stApp .st-key-sair_wrapper button p,
    .stApp.stApp .st-key-sair_wrapper button div,
    .stApp.stApp .st-key-sair_wrapper button span {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO SEGURA COM O GOOGLE SHEETS ---
@st.cache_resource
def get_credentials():
    encoded_json = st.secrets["gcp_service_account"]["base64_json"]
    decoded_json = json.loads(base64.b64decode(encoded_json).decode('utf-8'))
    return service_account.Credentials.from_service_account_info(
        decoded_json,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

def get_connection():
    creds = get_credentials()
    client = gspread.authorize(creds)
    return client.open_by_key("1RnwgFBWytspiM5eh5i0pgW2HXNRrwLXU4dYGXviDHlU")

@st.cache_data(ttl=30)
def carregar_dados_escala():
    try:
        sh = get_connection()
        ws_escala = sh.worksheet("Escala")
        return ws_escala.get_all_records()
    except Exception as e:
        st.error(f"Erro ao conectar com a base de dados: {e}")
        return []

def obter_lista_leitores():
    try:
        sh = get_connection()
        ws_leitores = sh.worksheet("Nomes dos Leitores")
        dados = ws_leitores.get_all_values()
        leitores = []
        for row in dados[1:]:
            if len(row) > 0 and row[0].strip():
                leitores.append(row[0].strip())
        return sorted(leitores)
    except:
        return []

@st.cache_data(ttl=30)
def obter_roteiros():
    try:
        sh = get_connection()
        ws_roteiros = sh.worksheet("Roteiros")
        dados = ws_roteiros.get_all_records()
        roteiros = {}
        for r in dados:
            data_str = str(r.get('DIA', '')).strip()
            link = str(r.get('LINK', '')).strip()
            if data_str and link:
                roteiros[data_str] = link
        return roteiros
    except Exception:
        return {}

def salvar_roteiro(sh, data_str, link):
    ws_roteiros = sh.worksheet("Roteiros")
    dados = ws_roteiros.get_all_values()
    for idx, row in enumerate(dados[1:], start=2):
        if len(row) > 0 and row[0].strip() == data_str:
            ws_roteiros.update_cell(idx, 2, link)
            return
    ws_roteiros.append_row([data_str, link])

# --- FUNÇÕES DE VALIDAÇÃO E REGRAS DE NEGÓCIO ---
def usuario_ja_escalado_no_dia(escala, data_alvo, nome_usuario):
    for r in escala:
        if str(r.get('DIA', '')).strip() == str(data_alvo).strip():
            if (str(r.get('COMENTARISTA', '')).strip().upper() == nome_usuario.strip().upper() or 
                str(r.get('LEITURA1', '')).strip().upper() == nome_usuario.strip().upper() or 
                str(r.get('LEITURA2', '')).strip().upper() == nome_usuario.strip().upper()):
                return True
    return False

def contar_servicos_no_mes(escala, nome_usuario):
    count = 0
    for r in escala:
        if str(r.get('COMENTARISTA', '')).strip().upper() == nome_usuario.strip().upper():
            count += 1
        if str(r.get('LEITURA1', '')).strip().upper() == nome_usuario.strip().upper():
            count += 1
        if str(r.get('LEITURA2', '')).strip().upper() == nome_usuario.strip().upper():
            count += 1
    return count

def extrair_data_evento(dia_str):
    match = re.search(r'(\d{2}/\d{2}/\d{4})', str(dia_str))
    if match:
        try:
            return datetime.strptime(match.group(1), "%d/%m/%Y").date()
        except:
            pass
    return None

def processar_tentativa_cancelamento(sh, nome_usuario, dia_evento):
    data_evento = extrair_data_evento(dia_evento)
    if data_evento:
        hoje = date.today()
        vespera = data_evento - timedelta(days=1)
        if hoje >= vespera:
            st.error("Contate o coordenador para a sua substituição")
            try:
                ws_leitores = sh.worksheet("Nomes dos Leitores")
                leitores_rows = ws_leitores.get_all_values()
                for r_idx, l_row in enumerate(leitores_rows[1:], start=2):
                    if len(l_row) > 0 and l_row[0].strip().upper() == nome_usuario.strip().upper():
                        faltas_atual = l_row[2].strip() if len(l_row) > 2 and l_row[2].strip().isdigit() else "0"
                        novo_faltas = int(faltas_atual) + 1
                        ws_leitores.update_cell(r_idx, 3, str(novo_faltas))
                        break
            except Exception:
                pass
            return False
    return True

def eh_fim_de_semana(dia_str):
    d = dia_str.lower()
    return "sábado" in d or "sabado" in d or "domingo" in d

def deve_exibir_comentarista_e_leitura2(row):
    dia = str(row.get('DIA', ''))
    solenidade = str(row.get('SOLENIDADE', 'NÃO')).strip().upper()
    return eh_fim_de_semana(dia) or solenidade == 'SIM'

def data_valida_para_roteiro(data_roteiro, escala):
    if data_roteiro.weekday() in (5, 6):
        return True
    for r in escala:
        dia_evento = extrair_data_evento(str(r.get('DIA', '')))
        solenidade = str(r.get('SOLENIDADE', 'NÃO')).strip().upper()
        if dia_evento == data_roteiro and solenidade == 'SIM':
            return True
    return False


# --- RENDERIZAÇÃO DO CABEÇALHO OFICIAL IMUTÁVEL ---
st.markdown("""
    <div class="cartao-superior-oficial">
        <img class="imagem-layout-completo" src="https://i.ibb.co/j92LZnZJ/novo-logo-oficial.png" />
    </div>
""", unsafe_allow_html=True)


# --- TELA DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown('<div class="titulo-identificacao">Identificação do Leitor</div>', unsafe_allow_html=True)
    with st.form("login_form"):
        input_nome = st.text_input("Nome cadastrado:")
        input_senha = st.text_input("ID (Senha):", type="password")
        submit_login = st.form_submit_button("Entrar")
        
        if submit_login:
            try:
                sh = get_connection()
                ws_leitores = sh.worksheet("Nomes dos Leitores")
                leitores_data = ws_leitores.get_all_values()
                
                usuario_encontrado = False
                for idx, row in enumerate(leitores_data[1:], start=2):
                    if len(row) > 4 and row[0].strip().upper() == input_nome.strip().upper() and row[1].strip() == input_senha.strip():
                        st.session_state.logged_in = True
                        st.session_state.user_name = row[0].strip()
                        st.session_state.user_id = row[1].strip()
                        st.session_state.user_profile = row[4].strip()
                        usuario_encontrado = True
                        break
                
                if usuario_encontrado:
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Nome ou ID inválidos. Verifique seus dados.")
            except Exception as e:
                st.error(f"Erro ao conectar com a base de dados: {e}")
    st.stop()


# --- ÁREA LOGADA INTERNA ---
perfil_texto = "LEITOR"
if st.session_state.user_profile == "2":
    perfil_texto = "LEITOR & COMENTARISTA"
elif st.session_state.user_profile == "3":
    perfil_texto = "ADM"

# 1. Barra Terracota + Botão Sair, lado a lado na mesma linha
status_col1, status_col2 = st.columns([4, 1])

with status_col1:
    st.markdown(f"""
        <div class="barra-status-alinhada">
            <div class="texto-logado-interno">Servo(a): {st.session_state.user_name} ({perfil_texto})</div>
        </div>
    """, unsafe_allow_html=True)

with status_col2:
    with st.container(key="sair_wrapper"):
        st.button("Sair", key="btn_logout_definitivo", on_click=efetuar_logout)

# 3. Menu de Botões Nativo, em coluna única (container com key="menu_grid" gera a classe .st-key-menu_grid usada no CSS acima)
with st.container(key="menu_grid"):
    st.button("Escala Geral", key="menu_geral", on_click=navegar_para, args=("escala_geral",), use_container_width=True)
    st.button("Minha Escala", key="menu_minha", on_click=navegar_para, args=("minha_escala",), use_container_width=True)
    st.button("Exibir Escala (PDF)", key="menu_pdf", on_click=navegar_para, args=("exibir_escala",), use_container_width=True)
    st.button("Aguardando Leitores", key="menu_vagas", on_click=navegar_para, args=("aguardando",), use_container_width=True)
    st.link_button("Coletar Intenções", "https://docs.google.com/forms/d/e/1FAIpQLScgX8RkpDYhb-rMwb8_ZR6dJhp-tKUyowmRGrSK-tbsXveqCw/viewform?usp=sharing", use_container_width=True)
    st.button("Ver Intenções", key="menu_intencoes", on_click=navegar_para, args=("ver_intencoes",), use_container_width=True)
    st.link_button("Liturgia Diária", "https://liturgia.cancaonova.com/pb/", use_container_width=True)
    if st.session_state.user_profile == "3":
        st.button("Roteiro", key="menu_roteiro", on_click=navegar_para, args=("cadastrar_roteiro",), use_container_width=True)


# Carregamento seguro dos dados da escala para os blocos abaixo
escala_data = carregar_dados_escala()
roteiros_data = obter_roteiros()
is_adm = (st.session_state.user_profile == "3")
lista_todos_leitores = obter_lista_leitores() if is_adm else []


# --- FUNÇÃO CENTRAL DE RENDERIZAÇÃO DOS EVENTOS ---
def renderizar_evento(idx, row, modo_aguardando=False):
    dia = str(row.get('DIA', ''))
    horario = str(row.get('HORARIO', ''))
    solenidade = str(row.get('SOLENIDADE', 'NÃO')).strip().upper()
    
    comentarista = str(row.get('COMENTARISTA', '')).strip()
    leitura1 = str(row.get('LEITURA1', '')).strip()
    leitura2 = str(row.get('LEITURA2', '')).strip()
    
    mostrar_com_l2 = deve_exibir_comentarista_e_leitura2(row)
    
    tem_vago = (not leitura1) or (mostrar_com_l2 and (not comentarista or not leitura2))
    if modo_aguardando and not tem_vago:
        return

    header_text = f"📅 **{dia}** — ⏰ **{horario}**"
    if solenidade == 'SIM':
        header_text += " ✨ *(Solenidade)*"
    st.markdown(header_text)

    data_evento = extrair_data_evento(dia)
    if data_evento:
        data_evento_fmt = data_evento.strftime("%d/%m/%Y")
        if data_evento_fmt in roteiros_data:
            st.markdown(f"📄 [Roteiro desta missa]({roteiros_data[data_evento_fmt]})")
    
    usuario_atual = st.session_state.user_name

    if f"alterando_com_{idx}" not in st.session_state:
        st.session_state[f"alterando_com_{idx}"] = False
    if f"alterando_l1_{idx}" not in st.session_state:
        st.session_state[f"alterando_l1_{idx}"] = False
    if f"alterando_l2_{idx}" not in st.session_state:
        st.session_state[f"alterando_l2_{idx}"] = False

    # 1. COMENTARISTA
    if mostrar_com_l2:
        val_com = comentarista if comentarista else "Vago"
        c_col1, c_col2 = st.columns([3, 1.5])
        c_col1.write(f"**COMENTARISTA:** {val_com}")
        
        if is_adm:
            if not st.session_state[f"alterando_com_{idx}"]:
                if c_col2.button("Alterar", key=f"btn_alt_com_{idx}"):
                    st.session_state[f"alterando_com_{idx}"] = True
                    st.rerun()
            else:
                novo_nome_com = c_col2.selectbox("Novo Leitor:", ["(Vago)"] + lista_todos_leitores, key=f"sel_com_{idx}")
                if c_col2.button("Salvar", key=f"save_com_{idx}"):
                    val_salvar = "" if novo_nome_com == "(Vago)" else novo_nome_com
                    sh_conn = get_connection()
                    ws_live = sh_conn.worksheet("Escala")
                    ws_live.update_cell(idx + 2, 4, val_salvar)
                    st.cache_data.clear()
                    st.session_state[f"alterando_com_{idx}"] = False
                    st.success("Alterado com sucesso!")
                    st.rerun()
        else:
            if not comentarista:
                if c_col2.button("Servir", key=f"s_com_{idx}"):
                    if st.session_state.user_profile == "1":
                        st.error("Você não possui o perfil “Comentarista”")
                    elif contar_servicos_no_mes(escala_data, usuario_atual) >= 3:
                        st.error("Você já serviu três vezes nesse mês")
                    elif usuario_ja_escalado_no_dia(escala_data, dia, usuario_atual):
                        st.error("Você já possui uma função agendada neste dia.")
                    else:
                        sh_conn = get_connection()
                        ws_live = sh_conn.worksheet("Escala")
                        ws_live.update_cell(idx + 2, 4, usuario_atual)
                        st.cache_data.clear()
                        st.success("Escalado como Comentarista!")
                        st.rerun()
            else:
                if comentarista.upper() == usuario_atual.upper():
                    if c_col2.button("Cancelar", key=f"c_com_{idx}"):
                        sh_conn = get_connection()
                        if processar_tentativa_cancelamento(sh_conn, usuario_atual, dia):
                            ws_live = sh_conn.worksheet("Escala")
                            ws_live.update_cell(idx + 2, 4, "")
                            st.cache_data.clear()
                            st.success("Cancelado com sucesso!")
                            st.rerun()

    # 2. 1ª LEITURA
    val_l1 = leitura1 if leitura1 else "Vago"
    l1_col1, l1_col2 = st.columns([3, 1.5])
    l1_col1.write(f"**1ª LEITURA:** {val_l1}")

    if is_adm:
        if not st.session_state[f"alterando_l1_{idx}"]:
            if l1_col2.button("Alterar", key=f"btn_alt_l1_{idx}"):
                st.session_state[f"alterando_l1_{idx}"] = True
                st.rerun()
        else:
            novo_nome_l1 = l1_col2.selectbox("Novo Leitor:", ["(Vago)"] + lista_todos_leitores, key=f"sel_l1_{idx}")
            if l1_col2.button("Salvar", key=f"save_l1_{idx}"):
                val_salvar = "" if novo_nome_l1 == "(Vago)" else novo_nome_l1
                sh_conn = get_connection()
                ws_live = sh_conn.worksheet("Escala")
                ws_live.update_cell(idx + 2, 5, val_salvar)
                st.cache_data.clear()
                st.session_state[f"alterando_l1_{idx}"] = False
                st.success("Alterado com sucesso!")
                st.rerun()
    else:
        if not leitura1:
            if l1_col2.button("Servir", key=f"s_l1_{idx}"):
                if contar_servicos_no_mes(escala_data, usuario_atual) >= 3:
                    st.error("Você já serviu três vezes nesse mês")
                elif usuario_ja_escalado_no_dia(escala_data, dia, usuario_atual):
                    st.error("Você já possui uma função agendada neste dia.")
                else:
                    sh_conn = get_connection()
                    ws_live = sh_conn.worksheet("Escala")
                    ws_live.update_cell(idx + 2, 5, usuario_atual)
                    st.cache_data.clear()
                    st.success("Escalado na 1ª Leitura!")
                    st.rerun()
        else:
            if leitura1.upper() == usuario_atual.upper():
                if l1_col2.button("Cancelar", key=f"c_l1_{idx}"):
                    sh_conn = get_connection()
                    if processar_tentativa_cancelamento(sh_conn, usuario_atual, dia):
                        ws_live = sh_conn.worksheet("Escala")
                        ws_live.update_cell(idx + 2, 5, "")
                        st.cache_data.clear()
                        st.success("Cancelado com sucesso!")
                        st.rerun()

    # 3. 2ª LEITURA
    if mostrar_com_l2:
        val_l2 = leitura2 if leitura2 else "Vago"
        l2_col1, l2_col2 = st.columns([3, 1.5])
        l2_col1.write(f"**2ª LEITURA:** {val_l2}")

        if is_adm:
            if not st.session_state[f"alterando_l2_{idx}"]:
                if l2_col2.button("Alterar", key=f"btn_alt_l2_{idx}"):
                    st.session_state[f"alterando_l2_{idx}"] = True
                    st.rerun()
            else:
                novo_nome_l2 = l2_col2.selectbox("Novo Leitor:", ["(Vago)"] + lista_todos_leitores, key=f"sel_l2_{idx}")
                if l2_col2.button("Salvar", key=f"save_l2_{idx}"):
                    val_salvar = "" if novo_nome_l2 == "(Vago)" else novo_nome_l2
                    sh_conn = get_connection()
                    ws_live = sh_conn.worksheet("Escala")
                    ws_live.update_cell(idx + 2, 6, val_salvar)
                    st.cache_data.clear()
                    st.session_state[f"alterando_l2_{idx}"] = False
                    st.success("Alterado com sucesso!")
                    st.rerun()
        else:
            if not leitura2:
                if l2_col2.button("Servir", key=f"s_l2_{idx}"):
                    if contar_servicos_no_mes(escala_data, usuario_atual) >= 3:
                        st.error("Você já serviu três vezes nesse mês")
                    elif usuario_ja_escalado_no_dia(escala_data, dia, usuario_atual):
                        st.error("Você já possui uma função agendada neste dia.")
                    else:
                        sh_conn = get_connection()
                        ws_live = sh_conn.worksheet("Escala")
                        ws_live.update_cell(idx + 2, 6, usuario_atual)
                        st.cache_data.clear()
                        st.success("Escalado na 2ª Leitura!")
                        st.rerun()
            else:
                if leitura2.upper() == usuario_atual.upper():
                    if l2_col2.button("Cancelar", key=f"c_l2_{idx}"):
                        sh_conn = get_connection()
                        if processar_tentativa_cancelamento(sh_conn, usuario_atual, dia):
                            ws_live = sh_conn.worksheet("Escala")
                            ws_live.update_cell(idx + 2, 6, "")
                            st.cache_data.clear()
                            st.success("Cancelado com sucesso!")
                            st.rerun()

    st.markdown("---")

# --- ROTEAMENTO E CONTEÚDOS ---
if st.session_state.pagina != "home":
    st.button("⬅️ Voltar ao Menu Principal", key="btn_voltar_menu", on_click=navegar_para, args=("home",))
    st.markdown('<div id="ancora-conteudo"></div>', unsafe_allow_html=True)

    # Rola automaticamente até o início do conteúdo desta tela
    components.html("""
        <script>
            console.log("[SCROLL-DEBUG] script de conteúdo iniciado");
            setTimeout(function() {
                try {
                    var doc = window.parent.document;
                    console.log("[SCROLL-DEBUG] acesso a window.parent.document OK");
                    var el = doc.getElementById("ancora-conteudo");
                    console.log("[SCROLL-DEBUG] ancora-conteudo encontrada?", el);
                    if (!el) { console.log("[SCROLL-DEBUG] âncora não encontrada, abortando"); return; }
                    var contentEl = el;
                    var scrollable = null;
                    while (contentEl && contentEl !== doc.body) {
                        var style = doc.defaultView.getComputedStyle(contentEl);
                        if ((style.overflowY === "auto" || style.overflowY === "scroll") && contentEl.scrollHeight > contentEl.clientHeight) {
                            scrollable = contentEl;
                            break;
                        }
                        contentEl = contentEl.parentElement;
                    }
                    console.log("[SCROLL-DEBUG] contêiner rolável encontrado?", scrollable);
                    if (scrollable) {
                        var elRect = el.getBoundingClientRect();
                        var scrollableRect = scrollable.getBoundingClientRect();
                        var alvo = scrollable.scrollTop + (elRect.top - scrollableRect.top);
                        scrollable.scrollTop = alvo;
                        console.log("[SCROLL-DEBUG] scrollTop aplicado:", scrollable.scrollTop, "alvo calculado:", alvo);
                    } else {
                        el.scrollIntoView({behavior: "auto", block: "start"});
                        console.log("[SCROLL-DEBUG] fallback scrollIntoView aplicado");
                    }
                } catch (e) {
                    console.log("[SCROLL-DEBUG] ERRO:", e);
                }
            }, 80);
        </script>
    """, height=0)
else:
    # De volta ao menu principal: rola instantaneamente para o topo da página
    components.html("""
        <script>
            setTimeout(function() {
                try {
                    var doc = window.parent.document;
                    var candidatos = doc.querySelectorAll('section, div, main');
                    candidatos.forEach(function(el) {
                        var style = doc.defaultView.getComputedStyle(el);
                        if ((style.overflowY === "auto" || style.overflowY === "scroll") && el.scrollHeight > el.clientHeight) {
                            el.scrollTop = 0;
                        }
                    });
                    doc.documentElement.scrollTop = 0;
                    doc.body.scrollTop = 0;
                    window.parent.scrollTo(0, 0);
                } catch (e) {
                    console.log("Erro ao rolar para o topo:", e);
                }
            }, 80);
        </script>
    """, height=0)

if st.session_state.pagina == "home":
    st.markdown('<div style="background-color: #A9ACB4; color: #10141A; border-radius: 8px; padding: 16px; text-align: center; font-size: 16px; font-weight: 600; margin-top: 5px; font-family: sans-serif;">Selecione uma opção no menu acima para começar.</div>', unsafe_allow_html=True)

elif st.session_state.pagina == "cadastrar_roteiro":
    st.subheader("Cadastrar Roteiro")
    if st.session_state.user_profile != "3":
        st.error("Apenas o ADM pode acessar esta tela.")
    else:
        st.write("Selecione a data da missa (sábado, domingo, ou dia marcado como Solenidade na Escala) e informe o link do arquivo de roteiro.")
        data_roteiro = st.date_input("Data da missa:", format="DD/MM/YYYY")
        link_roteiro = st.text_input("Link do arquivo de roteiro:")

        if st.button("Salvar Roteiro"):
            if not data_valida_para_roteiro(data_roteiro, escala_data):
                st.error("A data deve ser um sábado, domingo, ou um dia marcado como Solenidade na Escala Geral.")
            elif not link_roteiro.strip():
                st.error("Informe o link do arquivo de roteiro.")
            else:
                sh_conn = get_connection()
                data_str = data_roteiro.strftime("%d/%m/%Y")
                salvar_roteiro(sh_conn, data_str, link_roteiro.strip())
                st.cache_data.clear()
                st.success(f"Roteiro salvo para {data_str}!")
                st.rerun()

        st.markdown("---")
        st.write("**Roteiros já cadastrados:**")
        if not roteiros_data:
            st.info("Nenhum roteiro cadastrado ainda.")
        else:
            for data_str, link in sorted(roteiros_data.items()):
                st.markdown(f"- **{data_str}**: [{link}]({link})")

elif st.session_state.pagina == "escala_geral":
    st.subheader("Escala Geral do Mês")
    for idx, row in enumerate(escala_data):
        renderizar_evento(idx, row, modo_aguardando=False)

elif st.session_state.pagina == "minha_escala":
    st.subheader("Minha Escala")
    st.info(f"Exibindo eventos agendados para: {st.session_state.user_name}")
    
    encontrou = False
    for idx, row in enumerate(escala_data):
        c = str(row.get('COMENTARISTA', '')).strip().upper()
        l1 = str(row.get('LEITURA1', '')).strip().upper()
        l2 = str(row.get('LEITURA2', '')).strip().upper()
        u = st.session_state.user_name.upper()
        
        if c == u or l1 == u or l2 == u:
            encontrou = True
            renderizar_evento(idx, row, modo_aguardando=False)
            
    if not encontrou:
        st.write("Você não possui escalas ativas no momento.")

elif st.session_state.pagina == "exibir_escala":
    st.subheader("Exibir Escala (PDF)")
    st.write("Gerando PDF estruturado:")
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(190, 10, 'Escala Geral do Mes', 0, 1, 'C')
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(190, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    
    for row in escala_data:
        dia = str(row.get('DIA', ''))
        horario = str(row.get('HORARIO', ''))
        solenidade = str(row.get('SOLENIDADE', 'NÃO')).strip().upper()
        comentarista = str(row.get('COMENTARISTA', '')).strip() or 'Vago'
        l1 = str(row.get('LEITURA1', '')).strip() or 'Vago'
        l2 = str(row.get('LEITURA2', '')).strip() or 'Vago'
        
        mostrar_com_l2 = deve_exibir_comentarista_e_leitura2(row)
        
        texto_cabecalho = f"Data: {dia} - Horario: {horario}"
        if solenidade == 'SIM':
            texto_cabecalho += " (Solenidade)"
            
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(190, 7, texto_cabecalho.encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L')
        
        pdf.set_font("Arial", '', 10)
        if mostrar_com_l2:
            pdf.cell(190, 6, f"  - COMENTARISTA: {comentarista}".encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L')
        pdf.cell(190, 6, f"  - 1a LEITURA: {l1}".encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L')
        if mostrar_com_l2:
            pdf.cell(190, 6, f"  - 2a LEITURA: {l2}".encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L')
        
        pdf.ln(4)
    
    pdf_bytes = bytes(pdf.output())

    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    st.markdown(f"""
        <a href="data:application/pdf;base64,{b64_pdf}" target="_blank" rel="noopener noreferrer"
           style="display:block; text-align:center; background:#0D1B2A; color:#E0E2E5; border:3.5px solid #8C6D4F;
                  border-radius:24px; padding:12px 6px; font-size:18px; font-weight:700; text-decoration:none;
                  margin-top:10px; font-family:sans-serif;">
            📄 Abrir Escala em PDF no Navegador
        </a>
    """, unsafe_allow_html=True)

elif st.session_state.pagina == "aguardando":
    st.subheader("Aguardando Leitores (Vagas Pendentes)")
    encontrou_vaga = False
    for idx, row in enumerate(escala_data):
        mostrar_com_l2 = deve_exibir_comentarista_e_leitura2(row)
        c = str(row.get('COMENTARISTA', '')).strip()
        l1 = str(row.get('LEITURA1', '')).strip()
        l2 = str(row.get('LEITURA2', '')).strip()
        
        if (not l1) or (mostrar_com_l2 and (not c or not l2)):
            encontrou_vaga = True
            renderizar_evento(idx, row, modo_aguardando=True)
            
    if not encontrou_vaga:
        st.success("Parabéns! Não há vagas pendentes no momento.")

elif st.session_state.pagina == "ver_intencoes":
    st.subheader("Relatório de Intenções Coletadas")
    st.markdown("Selecione abaixo a **Data e o Horário da Missa**:")
    
    try:
        sh_conn = get_connection()
        ws_resp = sh_conn.worksheet("Respostas ao Formulário 2")
        respostas_data = ws_resp.get_all_records()
        
        opcoes_missas = []
        for r in respostas_data:
            d_val = str(r.get('Data', r.get('DATA', ''))).strip()
            h_val = str(r.get('Horário da Missa', r.get('Horario da Missa', r.get('HORARIO', '')))).strip()
            if d_val and h_val:
                item = f"{d_val} - {h_val}"
                if item not in opcoes_missas:
                    opcoes_missas.append(item)
                    
        if not opcoes_missas:
            st.info("Nenhuma intenção encontrada na planilha.")
        else:
            missa_selecionada = st.selectbox("Selecione a Missa (Ticket):", opcoes_missas)
            
            if st.button("Gerar Relatório Consolidado"):
                partes = missa_selecionada.split(" - ")
                f_data = partes[0].strip()
                f_horario = partes[1].strip()
                
                conteudo_mesclado = ""
                encontrou = False
                
                for r in respostas_data:
                    data_resp = str(r.get('Data', r.get('DATA', ''))).strip()
                    horario_resp = str(r.get('Horário da Missa', r.get('Horario da Missa', r.get('HORARIO', '')))).strip()
                    
                    if data_resp == f_data and horario_resp == f_horario:
                        encontrou = True
                        conteudo_mesclado += f"\n--- Resposta de: {r.get('Carimbo de data/hora', 'Anônimo')} ---\n"
                        for k, v in r.items():
                            conteudo_mesclado += f"{k}: {v}\n"
                        conteudo_mesclado += "\n" + "-"*40 + "\n"
                        
                if not encontrou:
                    st.info("Nenhum registro encontrado para a missa selecionada.")
                else:
                    st.success("Relatórios mesclados com sucesso!")
                    st.text_area("Relatório Consolidado", conteudo_mesclado, height=300)
    except Exception as e:
        st.error(f"Erro ao acessar a aba de respostas: {e}")
