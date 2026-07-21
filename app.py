import streamlit as st
import gspread
import base64
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuração da página
st.set_page_config(page_title="Leitores Peregrinos", layout="centered")

# --- CONEXÃO COM GOOGLE SHEETS E DRIVE ---
def get_credentials():
    encoded_json = st.secrets["gcp_service_account"]["base64_json"]
    decoded_json = json.loads(base64.b64decode(encoded_json).decode('utf-8'))
    return service_account.Credentials.from_service_account_info(
        decoded_json,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

def get_connection():
    creds = get_credentials()
    client = gspread.authorize(creds)
    return client.open_by_key("1RnwgFBWytspiM5eh5i0pgW2HXNRrwLXU4dYGXviDHlU")

def get_drive_service():
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)

# --- FUNÇÕES AUXILIARES DE REGRAS ---
def usuario_ja_escalado_no_dia(escala, data_alvo, nome_usuario):
    for r in escala:
        if str(r.get('DIA', '')).strip() == str(data_alvo).strip():
            if (str(r.get('COMENTARISTA', '')).strip() == nome_usuario or 
                str(r.get('LEITURA1', '')).strip() == nome_usuario or 
                str(r.get('LEITURA2', '')).strip() == nome_usuario):
                return True
    return False

def eh_fim_de_semana(dia_str):
    d = dia_str.lower()
    return "sábado" in d or "sabado" in d or "domingo" in d

def deve_exibir_comentarista_e_leitura2(row):
    dia = str(row.get('DIA', ''))
    solenidade = str(row.get('SOLENIDADE', 'NÃO')).strip().upper()
    return eh_fim_de_semana(dia) or solenidade == 'SIM'

# --- CONTROLE DE SESSÃO ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_profile = ""
    st.session_state.user_id = ""

if "pagina" not in st.session_state:
    st.session_state.pagina = "escala_geral"

# --- CABEÇALHO VISUAL (Ajuste de tamanho para smartphone) ---
st.markdown("<h1 style='text-align: center; font-size: 24px;'>Leitores Peregrinos</h1>", unsafe_allow_html=True)

col_l, col_img = st.columns([1, 2])
with col_l:
    st.image("https://i.ibb.co/HLqFZgZK/logo-igreja.jpg", width=80)
with col_img:
    st.image("https://i.ibb.co/hJswKtgV/IMG20260522140332.jpg", width=180)

st.markdown("---")

# --- TELA DE LOGIN ---
if not st.session_state.logged_in:
    st.subheader("Identificação do Leitor")
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

# --- BARRA DE USUÁRIO LOGADO (Sem resíduos de formatação) ---
col_info, col_logout = st.columns([4, 1])
with col_info:
    perfil_texto = "LEITOR"
    if st.session_state.user_profile == "2":
        perfil_texto = "LEITOR & COMENTARISTA"
    elif st.session_state.user_profile == "3":
        perfil_texto = "ADM"
    st.markdown(f"**Logado:** {st.session_state.user_name} ({perfil_texto})")

with col_logout:
    if st.button("Sair"):
        st.session_state.logged_in = False
        st.session_state.user_name = ""
        st.session_state.user_profile = ""
        st.session_state.user_id = ""
        st.session_state.pagina = "escala_geral"
        st.rerun()

st.markdown("---")

# --- MENU PRINCIPAL (Apenas os botões) ---
menu_col1, menu_col2 = st.columns(2)
with menu_col1:
    if st.button("Escala Geral", use_container_width=True):
        st.session_state.pagina = "escala_geral"
        st.rerun()
    if st.button("Minha Escala", use_container_width=True):
        st.session_state.pagina = "minha_escala"
        st.rerun()
    if st.button("Coletar Intenções", use_container_width=True):
        st.session_state.pagina = "coletar"
        st.rerun()

with menu_col2:
    if st.button("Exibir Escala (PDF)", use_container_width=True):
        st.session_state.pagina = "exibir_escala"
        st.rerun()
    if st.button("Aguardando Leitores", use_container_width=True):
        st.session_state.pagina = "aguardando"
        st.rerun()
    if st.button("Ver Intenções", use_container_width=True):
        st.session_state.pagina = "ver_intencoes"
        st.rerun()

st.markdown("---")

# Carregamento dos dados da planilha
sh = get_connection()
try:
    ws_escala = sh.worksheet("Escala")
    escala_data = ws_escala.get_all_records()
except:
    escala_data = []

is_adm = (st.session_state.user_profile == "3")

# Função para renderizar blocos de eventos com o layout solicitado
def renderizar_evento(idx, row, modo_aguardando=False):
    dia = str(row.get('DIA', ''))
    horario = str(row.get('HORARIO', ''))
    solenidade = str(row.get('SOLENIDADE', 'NÃO')).strip().upper()
    
    comentarista = str(row.get('COMENTARISTA', '')).strip()
    leitura1 = str(row.get('LEITURA1', '')).strip()
    leitura2 = str(row.get('LEITURA2', '')).strip()
    
    # Se modo aguardando, filtrar apenas se tiver pelo menos um Vago nas funções visíveis
    mostrar_com_l2 = deve_exibir_comentarista_e_leitura2(row)
    
    tem_vago = (not leitura1) or (mostrar_com_l2 and (not comentarista or not leitura2))
    if modo_aguardando and not tem_vago:
        return

    # Cabeçalho do Evento: <Dia> <Horário>
    header_text = f"📅 **{dia}** — ⏰ **{horario}**"
    if solenidade == 'SIM':
        header_text += " ✨ *(Solenidade)*"
    
    st.markdown(header_text)
    
    # 1. COMENTARISTA (Apenas se sábado, domingo ou Solenidade == 'SIM')
    if mostrar_com_l2:
        val_com = comentarista if comentarista else "Vago"
        c_col1, c_col2 = st.columns([3, 1])
        c_col1.write(f"**COMENTARISTA:** {val_com}")
        
        # Regra de ADM: Nem mesmo perfil 3 pode alterar/cancelar seus próprios eventos diretamente por bypass se for dono
        is_owner_com = (comentarista == st.session_state.user_name)
        pode_agir_adm = is_adm and not is_owner_com

        if not comentarista:
            if c_col2.button("Servir", key=f"s_com_{idx}"):
                if st.session_state.user_profile == "1" and not is_adm:
                    st.error("Você não possui o perfil “Comentarista”")
                elif not is_adm and usuario_ja_escalado_no_dia(escala_data, dia, st.session_state.user_name):
                    st.error("Você já possui uma função agendada neste dia.")
                else:
                    ws_escala.update_cell(idx + 2, 4, st.session_state.user_name)
                    st.success("Escalado como Comentarista!")
                    st.rerun()
        else:
            if comentarista == st.session_state.user_name or pode_agir_adm:
                if c_col2.button("Cancelar", key=f"c_com_{idx}"):
                    ws_escala.update_cell(idx + 2, 4, "")
                    st.success("Cancelado com sucesso!")
                    st.rerun()

    # 2. 1ª LEITURA (Exibida todos os dias)
    val_l1 = leitura1 if leitura1 else "Vago"
    l1_col1, l1_col2 = st.columns([3, 1])
    l1_col1.write(f"**1ª LEITURA:** {val_l1}")
    
    is_owner_l1 = (leitura1 == st.session_state.user_name)
    pode_agir_l1 = is_adm and not is_owner_l1

    if not leitura1:
        if l1_col2.button("Servir", key=f"s_l1_{idx}"):
            if not is_adm and usuario_ja_escalado_no_dia(escala_data, dia, st.session_state.user_name):
                st.error("Você já possui uma função agendada neste dia.")
            else:
                ws_escala.update_cell(idx + 2, 5, st.session_state.user_name)
                st.success("Escalado na 1ª Leitura!")
                st.rerun()
    else:
        if leitura1 == st.session_state.user_name or pode_agir_l1:
            if l1_col2.button("Cancelar", key=f"c_l1_{idx}"):
                ws_escala.update_cell(idx + 2, 5, "")
                st.success("Cancelado com sucesso!")
                st.rerun()

    # 3. 2ª LEITURA (Apenas se sábado, domingo ou Solenidade == 'SIM')
    if mostrar_com_l2:
        val_l2 = leitura2 if leitura2 else "Vago"
        l2_col1, l2_col2 = st.columns([3, 1])
        l2_col1.write(f"**2ª LEITURA:** {val_l2}")
        
        is_owner_l2 = (leitura2 == st.session_state.user_name)
        pode_agir_l2 = is_adm and not is_owner_l2

        if not leitura2:
            if l2_col2.button("Servir", key=f"s_l2_{idx}"):
                if not is_adm and usuario_ja_escalado_no_dia(escala_data, dia, st.session_state.user_name):
                    st.error("Você já possui uma função agendada neste dia.")
                else:
                    ws_escala.update_cell(idx + 2, 6, st.session_state.user_name)
                    st.success("Escalado na 2ª Leitura!")
                    st.rerun()
        else:
            if leitura2 == st.session_state.user_name or pode_agir_l2:
                if l2_col2.button("Cancelar", key=f"c_l2_{idx}"):
                    ws_escala.update_cell(idx + 2, 6, "")
                    st.success("Cancelado com sucesso!")
                    st.rerun()

    st.markdown("---")

# --- ROTEAMENTO DE PÁGINAS POR ESTADO ---

if st.session_state.pagina == "escala_geral":
    st.subheader("Escala Geral do Mês")
    for idx, row in enumerate(escala_data):
        renderizar_evento(idx, row, modo_aguardando=False)

elif st.session_state.pagina == "minha_escala":
    st.subheader("Minha Escala")
    st.info(f"Exibindo eventos agendados para: {st.session_state.user_name}")
    
    encontrou = False
    for idx, row in enumerate(escala_data):
        c = str(row.get('COMENTARISTA', '')).strip()
        l1 = str(row.get('LEITURA1', '')).strip()
        l2 = str(row.get('LEITURA2', '')).strip()
        
        if c == st.session_state.user_name or l1 == st.session_state.user_name or l2 == st.session_state.user_name:
            encontrou = True
            renderizar_evento(idx, row, modo_aguardando=False)
            
    if not encontrou:
        st.write("Você não possui escalas ativas no momento.")

elif st.session_state.pagina == "coletar":
    st.subheader("Coleta de Intenções")
    st.markdown("Clique no link abaixo para abrir o formulário oficial de coleta de intenções da missa:")
    st.markdown("[Abrir Formulário de Intenções no Google Forms](https://docs.google.com/forms/d/e/1FAIpQLScgX8RkpDYhb-rMwb8_ZR6dJhp-tKUyowmRGrSK-tbsXveqCw/viewform?usp=sharing&ouid=103182596084814948709)", unsafe_allow_html=True)

elif st.session_state.pagina == "exibir_escala":
    st.subheader("Exibir Escala (Impressão / PDF)")
    st.write("Visualização consolidada para impressão:")
    st.dataframe(escala_data, use_container_width=True)
    st.markdown("*Dica: Use Ctrl+P no seu navegador para imprimir.*")

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
    st.markdown("Selecione a data e o horário da missa para buscar, mesclar e exibir os relatórios do AutoCrat:")
    
    col_d, col_h = st.columns(2)
    with col_d:
        filtro_data = st.text_input("Data da Missa (ex: 01/07/2026):")
    with col_h:
        filtro_horario = st.text_input("Horário da Missa (ex: 19:00:00):")
        
    if st.button("Buscar e Mesclar Relatórios"):
        if not filtro_data or not filtro_horario:
            st.warning("Preencha a data e o horário para realizar a busca.")
        else:
            try:
                with st.spinner("Buscando relatórios no Google Drive..."):
                    drive_service = get_drive_service()
                    query_nome = f"intenções_{filtro_data}_{filtro_horario}"
                    
                    results = drive_service.files().list(
                        q=f"name contains '{query_nome}' and trashed = false",
                        pageSize=10,
                        fields="files(id, name, mimeType)"
                    ).execute()
                    
                    files = results.get('files', [])
                    
                    if not files:
                        st.info(f"Nenhum relatório encontrado para {filtro_data} às {filtro_horario}.")
                    else:
                        st.success(f"{len(files)} relatório(s) encontrado(s). Mesclando conteúdo...")
                        
                        conteudo_mesclado = ""
                        for file in files:
                            file_id = file['id']
                            file_name = file['name']
                            conteudo_mesclado += f"\n\n--- [ Relatório de: {file_name} ] ---\n\n"
                            
                            if file['mimeType'] == 'application/vnd.google-apps.document':
                                request = drive_service.files().export_media(fileId=file_id, mimeType='text/plain')
                                data_bytes = request.execute()
                                conteudo_mesclado += data_bytes.decode('utf-8', errors='ignore')
                            else:
                                request = drive_service.files().get_media(fileId=file_id)
                                data_bytes = request.execute()
                                conteudo_mesclado += data_bytes.decode('utf-8', errors='ignore')
                        
                        st.markdown("### Relatório Consolidado para Impressão:")
                        st.text_area("Conteúdo Mesclado", conteudo_mesclado, height=300)
                        st.markdown("*Dica: Use Ctrl+P no seu navegador para imprimir este relatório consolidado.*")
            except Exception as e:
                st.error(f"Erro ao acessar o Google Drive: {e}")