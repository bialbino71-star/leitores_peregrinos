import streamlit as st
import gspread
import base64
import json
from datetime import datetime, date

# Configuração da página
st.set_page_config(page_title="Leitores Peregrinos", layout="wide")

# Função de Conexão com o Google Sheets
def get_connection():
    encoded_json = st.secrets["gcp_service_account"]["base64_json"]
    decoded_json = json.loads(base64.b64decode(encoded_json).decode('utf-8'))
    creds = gspread.service_account_from_dict(decoded_json)
    return creds.open_by_key("1RnwgFBWytspiM5eh5i0pgW2HXNRrwLXU4dYGXviDHlU")

# Função auxiliar para verificar se o usuário já tem alguma função no mesmo dia
def usuario_ja_escalado_no_dia(escala, data_alvo, nome_usuario):
    for r in escala:
        if str(r.get('DIA', '')).strip() == str(data_alvo).strip():
            if (r.get('COMENTARISTA') == nome_usuario or 
                r.get('LEITURA1') == nome_usuario or 
                r.get('LEITURA2') == nome_usuario):
                return True
    return False

# Inicialização do Session State para Login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_profile = ""
    st.session_state.user_id = ""

# --- CABEÇALHO VISUAL ---
st.markdown("<h1 style='text-align: center;'>Leitores Peregrinos</h1>", unsafe_allow_html=True)

# Logo e Imagem centralizados
col_l, col_img, col_r = st.columns([1, 2, 1])
with col_l:
    st.image("https://i.ibb.co/HLqFZgZK/logo-igreja.jpg", width=100)
with col_img:
    st.image("https://i.ibb.co/hJswKtgV/IMG20260522140332.jpg", use_container_width=True)

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
                
                # Validação: Nome na coluna 0, ID na coluna 1
                usuario_encontrado = False
                for idx, row in enumerate(leitores_data[1:], start=2):
                    if len(row) > 4 and row[0].strip().upper() == input_nome.strip().upper() and row[1].strip() == input_senha.strip():
                        st.session_state.logged_in = True
                        st.session_state.user_name = row[0].strip()
                        st.session_state.user_id = row[1].strip()
                        # Perfil na coluna de índice 4
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

# --- BARRA DE USUÁRIO LOGADO ---
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
        st.rerun()

st.markdown("---")

# --- MENU PRINCIPAL (Baseado no Layout) ---
menu_col1, menu_col2 = st.columns(2)

with menu_col1:
    btn_escala_geral = st.button("Escala Geral", use_container_width=True)
    btn_minha_escala = st.button("Minha Escala", use_container_width=True)
    btn_coletar = st.button("Coletar Intenções", use_container_width=True)

with menu_col2:
    btn_exibir_escala = st.button("Exibir Escala (PDF)", use_container_width=True)
    btn_aguardando = st.button("Aguardando Leitores", use_container_width=True)
    btn_ver_intencoes = st.button("Ver Intenções", use_container_width=True)

st.markdown("---")

# Lógica das Ações do Menu
sh = get_connection()
try:
    ws_escala = sh.worksheet("Escala")
    escala_data = ws_escala.get_all_records()
except:
    escala_data = []

is_adm = (st.session_state.user_profile == "3")

# 1. ESCALA GERAL
if btn_escala_geral or not (btn_minha_escala or btn_coletar or btn_exibir_escala or btn_aguardando or btn_ver_intencoes):
    st.subheader("Escala Geral do Mês")
    
    for idx, row in enumerate(escala_data):
        dia = row.get('DIA', '')
        horario = row.get('HORARIO', '')
        solenidade = str(row.get('SOLENIDADE', '')).upper()
        comentarista = row.get('COMENTARISTA', '')
        leitura1 = row.get('LEITURA1', '')
        leitura2 = row.get('LEITURA2', '')
        
        display_str = f"Data: {dia} | Horário: {horario} | Solenidade: {solenidade} | Comentarista: {comentarista or 'Vago'} | 1ª Leitura: {leitura1 or 'Vago'} | 2ª Leitura: {leitura2 or 'Vago'}"
        
        with st.expander(display_str):
            # Botões de ação baseados nas regras
            c1, c2, c3 = st.columns(3)
            
            # Regra para Comentarista
            if not comentarista:
                if c1.button("Servir Comentarista", key=f"srv_com_{idx}"):
                    if st.session_state.user_profile == "1" and not is_adm:
                        st.error("Você não possui o perfil “Comentarista”")
                    elif not is_adm and usuario_ja_escalado_no_dia(escala_data, dia, st.session_state.user_name):
                        st.error("Você já possui uma função agendada neste dia.")
                    else:
                        ws_escala.update_cell(idx + 2, 4, st.session_state.user_name)
                        st.success("Escalado com sucesso como Comentarista!")
                        st.rerun()
            else:
                if comentarista == st.session_state.user_name or is_adm:
                    if c1.button("Cancelar Comentarista", key=f"can_com_{idx}"):
                        ws_escala.update_cell(idx + 2, 4, "")
                        st.success("Cancelado com sucesso!")
                        st.rerun()

            # Regra para 1ª Leitura (LEITURA1)
            if not leitura1:
                if c2.button("Servir 1ª Leitura", key=f"srv_l1_{idx}"):
                    if not is_adm and usuario_ja_escalado_no_dia(escala_data, dia, st.session_state.user_name):
                        st.error("Você já possui uma função agendada neste dia.")
                    else:
                        ws_escala.update_cell(idx + 2, 5, st.session_state.user_name)
                        st.success("Escalado na 1ª Leitura!")
                        st.rerun()
            else:
                if leitura1 == st.session_state.user_name or is_adm:
                    if c2.button("Cancelar 1ª Leitura", key=f"can_l1_{idx}"):
                        ws_escala.update_cell(idx + 2, 5, "")
                        st.success("Cancelado com sucesso!")
                        st.rerun()

            # Regra para 2ª Leitura (LEITURA2)
            if not leitura2:
                if c3.button("Servir 2ª Leitura", key=f"srv_l2_{idx}"):
                    if not is_adm and usuario_ja_escalado_no_dia(escala_data, dia, st.session_state.user_name):
                        st.error("Você já possui uma função agendada neste dia.")
                    else:
                        ws_escala.update_cell(idx + 2, 6, st.session_state.user_name)
                        st.success("Escalado na 2ª Leitura!")
                        st.rerun()
            else:
                if leitura2 == st.session_state.user_name or is_adm:
                    if c3.button("Cancelar 2ª Leitura", key=f"can_l2_{idx}"):
                        ws_escala.update_cell(idx + 2, 6, "")
                        st.success("Cancelado com sucesso!")
                        st.rerun()

# 2. MINHA ESCALA
elif btn_minha_escala:
    st.subheader("Minha Escala")
    st.info(f"Exibindo eventos agendados para: {st.session_state.user_name}")
    
    encontrou_meu = False
    for idx, row in enumerate(escala_data):
        if (row.get('COMENTARISTA') == st.session_state.user_name or 
            row.get('LEITURA1') == st.session_state.user_name or 
            row.get('LEITURA2') == st.session_state.user_name):
            
            encontrou_meu = True
            st.write(f"📅 **{row.get('DIA')}** às **{row.get('HORARIO')}** | Solenidade: {row.get('SOLENIDADE')}")

    if not encontrou_meu:
        st.write("You don't have active schedules.") # fallback or pt translation
        st.write("Você não possui escalas ativas no momento.")

# 3. COLETAR INTENÇÕES
elif btn_coletar:
    st.subheader("Coleta de Intenções")
    st.markdown("Clique no link abaixo para abrir o formulário oficial de coleta de intenções da missa:")
    st.markdown("[Abrir Formulário de Intenções no Google Forms](https://docs.google.com/forms/d/e/1FAIpQLScgX8RkpDYhb-rMwb8_ZR6dJhp-tKUyowmRGrSK-tbsXveqCw/viewform?usp=sharing&ouid=103182596084814948709)", unsafe_allow_html=True)

# 4. EXIBIR ESCALA
elif btn_exibir_escala:
    st.subheader("Exibir Escala (Impressão / PDF)")
    st.write("Geração da visualização para impressão da Escala Geral:")
    st.dataframe(escala_data, use_container_width=True)
    st.markdown("*Dica: Use Ctrl+P no seu navegador para imprimir esta visualização em PDF.*")

# 5. AGUARDANDO LEITORES
elif btn_aguardando:
    st.subheader("Eventos com Vagas Pendentes")
    encontrou_vaga = False
    for idx, row in enumerate(escala_data):
        if not row.get('COMENTARISTA') or not row.get('LEITURA1') or not row.get('LEITURA2'):
            encontrou_vaga = True
            st.warning(f"Data: {row.get('DIA')} - {row.get('HORARIO')} | Comentarista: {row.get('COMENTARISTA') or 'Vago'} | 1ª Leitura: {row.get('LEITURA1') or 'Vago'} | 2ª Leitura: {row.get('LEITURA2') or 'Vago'}")
    
    if not encontrou_vaga:
        st.success("Parabéns! Não há vagas pendentes no momento.")

# 6. VER INTENÇÕES
elif btn_ver_intencoes:
    st.subheader("Relatório de Intenções Coletadas")
    st.write("Aqui serão mesclados os relatórios gerados pelo AutoCrat no Google Drive para o mesmo dia e horário.")
    st.info("Módulo em preparação para integração direta com a API do Google Drive.")