import streamlit as st
import gspread
import base64
import json
import re
from datetime import datetime, date, timedelta
from google.oauth2 import service_account
from fpdf import FPDF

# Configuração da página otimizada para dispositivos móveis
st.set_page_config(page_title="Leitores Peregrinos", layout="centered")

# --- CONEXÃO SEGURA COM O GOOGLE SHEETS ---
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

def obter_lista_leitores(sh):
    try:
        ws_leitores = sh.worksheet("Nomes dos Leitores")
        dados = ws_leitores.get_all_values()
        leitores = []
        for row in dados[1:]:
            if len(row) > 0 and row[0].strip():
                leitores.append(row[0].strip())
        return sorted(leitores)
    except:
        return []

# --- GERENCIAMENTO DE ESTADO DA SESSÃO ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_profile = ""
    st.session_state.user_id = ""

if "pagina" not in st.session_state:
    st.session_state.pagina = "home"

# --- CABEÇALHO E IDENTIDADE VISUAL ---
st.markdown("<h1 style='text-align: center; font-size: 22px;'>Leitores Peregrinos</h1>", unsafe_allow_html=True)

col_l, col_img = st.columns([1, 2])
with col_l:
    st.image("https://i.ibb.co/HLqFZgZK/logo-igreja.jpg", width=70)
with col_img:
    st.image("https://i.ibb.co/hJswKtgV/IMG20260522140332.jpg", width=150)

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

# --- BARRA DO USUÁRIO LOGADO ---
col_info, col_logout = st.columns([3, 1])
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
        st.session_state.pagina = "home"
        st.rerun()

st.markdown("---")

# --- MENU DE NAVEGAÇÃO PRINCIPAL ---
menu_col1, menu_col2 = st.columns(2)
with menu_col1:
    if st.button("Escala Geral", use_container_width=True):
        st.session_state.pagina = "escala_geral"
        st.rerun()
    if st.button("Minha Escala", use_container_width=True):
        st.session_state.pagina = "minha_escala"
        st.rerun()
    if st.button("Coletar Intenções", use_container_width=True):
        st.markdown(
            '<meta http-equiv="refresh" content="0;url=https://docs.google.com/forms/d/e/1FAIpQLScgX8RkpDYhb-rMwb8_ZR6dJhp-tKUyowmRGrSK-tbsXveqCw/viewform?usp=sharing&ouid=103182596084814948709">',
            unsafe_allow_html=True
        )
        st.markdown("[Clique aqui se a página não abrir automaticamente](https://docs.google.com/forms/d/e/1FAIpQLScgX8RkpDYhb-rMwb8_ZR6dJhp-tKUyowmRGrSK-tbsXveqCw/viewform?usp=sharing&ouid=103182596084814948709)")

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

# --- CONEXÃO E CARREGAMENTO DA PLANILHA DE ESCALA ---
sh = get_connection()
try:
    ws_escala = sh.worksheet("Escala")
    escala_data = ws_escala.get_all_records()
except:
    escala_data = []

is_adm = (st.session_state.user_profile == "3")
lista_todos_leitores = obter_lista_leitores(sh) if is_adm else []

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
    
    usuario_atual = st.session_state.user_name

    # Gerenciador de estado para o painel de alteração do ADM
    if f"alterando_com_{idx}" not in st.session_state:
        st.session_state[f"alterando_com_{idx}"] = False
    if f"alterando_l1_{idx}" not in st.session_state:
        st.session_state[f"alterando_l1_{idx}"] = False
    if f"alterando_l2_{idx}" not in st.session_state:
        st.session_state[f"alterando_l2_{idx}"] = False

    # 1. COMENTARISTA
    if mostrar_com_l2:
        val_com = comentarista if comentarista else "Vago"
        c_col1, c_col2 = st.columns([3, 1])
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
                    ws_escala.update_cell(idx + 2, 4, val_salvar)
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
                        ws_escala.update_cell(idx + 2, 4, usuario_atual)
                        st.success("Escalado como Comentarista!")
                        st.rerun()
            else:
                if comentarista.upper() == usuario_atual.upper():
                    if c_col2.button("Cancelar", key=f"c_com_{idx}"):
                        if processar_tentativa_cancelamento(sh, usuario_atual, dia):
                            ws_escala.update_cell(idx + 2, 4, "")
                            st.success("Cancelado com sucesso!")
                            st.rerun()

    # 2. 1ª LEITURA
    val_l1 = leitura1 if leitura1 else "Vago"
    l1_col1, l1_col2 = st.columns([3, 1])
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
                ws_escala.update_cell(idx + 2, 5, val_salvar)
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
                    ws_escala.update_cell(idx + 2, 5, usuario_atual)
                    st.success("Escalado na 1ª Leitura!")
                    st.rerun()
        else:
            if leitura1.upper() == usuario_atual.upper():
                if l1_col2.button("Cancelar", key=f"c_l1_{idx}"):
                    if processar_tentativa_cancelamento(sh, usuario_atual, dia):
                        ws_escala.update_cell(idx + 2, 5, "")
                        st.success("Cancelado com sucesso!")
                        st.rerun()

    # 3. 2ª LEITURA
    if mostrar_com_l2:
        val_l2 = leitura2 if leitura2 else "Vago"
        l2_col1, l2_col2 = st.columns([3, 1])
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
                    ws_escala.update_cell(idx + 2, 6, val_salvar)
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
                        ws_escala.update_cell(idx + 2, 6, usuario_atual)
                        st.success("Escalado na 2ª Leitura!")
                        st.rerun()
            else:
                if leitura2.upper() == usuario_atual.upper():
                    if l2_col2.button("Cancelar", key=f"c_l2_{idx}"):
                        if processar_tentativa_cancelamento(sh, usuario_atual, dia):
                            ws_escala.update_cell(idx + 2, 6, "")
                            st.success("Cancelado com sucesso!")
                            st.rerun()

    st.markdown("---")

# --- ROTEAMENTO DAS PÁGINAS DO APLICATIVO ---

if st.session_state.pagina == "home":
    st.info("Selecione uma opção no menu acima para começar.")

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

elif st.session_state.pagina == "coletar":
    pass

elif st.session_state.pagina == "exibir_escala":
    st.subheader("Exibir Escala (PDF)")
    st.write("Gerando PDF com o mesmo layout da Escala Geral:")
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(190, 10, 'Escala Geral do Mes', 0, 1, 'C')
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(190, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    for row in escala_data:
        dia = str(row.get('DIA', ''))
        horario = str(row.get('HORARIO', ''))
        solenidade = str(row.get('SOLENIDADE', 'NÃO')).strip().upper()
        comentarista = str(row.get('COMENTARISTA', '')).strip() or 'Vago'
        l1 = str(row.get('LEITURA1', '')).strip() or 'Vago'
        l2 = str(row.get('LEITURA2', '')).strip() or 'Vago'
        
        mostrar_com_l2 = deve_exibir_comentarista_e_leitura2(row)
        
        # Cabeçalho do evento idêntico ao visual da tela
        linha_data = f"{dia} - {horario}" + (" (Solenidade)" if solenidade == 'SIM' else "")
        pdf.set_font("Arial", 'B', 10)
        pdf.multi_cell(190, 6, linha_data.encode('latin-1', 'replace').decode('latin-1'))
        
        pdf.set_font("Arial", '', 10)
        if mostrar_com_l2:
            pdf.multi_cell(190, 6, f"COMENTARISTA: {comentarista}".encode('latin-1', 'replace').decode('latin-1'))
        pdf.multi_cell(190, 6, f"1a LEITURA: {l1}".encode('latin-1', 'replace').decode('latin-1'))
        if mostrar_com_l2:
            pdf.multi_cell(190, 6, f"2a LEITURA: {l2}".encode('latin-1', 'replace').decode('latin-1'))
        
        pdf.ln(4)
    
    pdf_bytes = bytes(pdf.output())
    
    st.download_button(
        label="📥 Baixar Escala em PDF",
        data=pdf_bytes,
        file_name="escala_leitores.pdf",
        mime="application/pdf",
        use_container_width=True
    )

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
    st.markdown("Selecione abaixo a **Data e o Horário da Missa** para mesclar e exibir o relatório consolidado:")
    
    try:
        ws_resp = sh.worksheet("Respostas ao Formulário 2")
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
                    st.markdown("*Dica: Use Ctrl+P no seu navegador para imprimir este relatório consolidado.*")
    except Exception as e:
        st.error(f"Erro ao acessar a aba de respostas: {e}")