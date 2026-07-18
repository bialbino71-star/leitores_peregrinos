import streamlit as st
import gspread
import base64
import json

# Função atualizada para ler Base64 do Secrets
def get_sheets():
    # Pega o texto codificado que está no Secrets
    encoded_json = st.secrets["gcp_service_account"]["base64_json"]
    
    # Decodifica de Base64 para JSON normal e carrega
    decoded_json = json.loads(base64.b64decode(encoded_json).decode('utf-8'))
    
    # Conecta com a planilha
    creds = gspread.service_account_from_dict(decoded_json)
    
    # Substitua o ID abaixo pelo ID da sua planilha (o código longo na URL)
    return creds.open_by_key("1RnwgFBWytspiM5eh5i0pgW2HXNRrwLXU4dYGXviDHlU").worksheet("Escala")

# --- Interface ---
st.set_page_config(page_title="Leitores Peregrinos", layout="centered")
st.title("Leitores Peregrinos")

# Conectando
sheet = get_sheets()
data = sheet.get_all_records()
st.write(data[0])

# Exibição
for idx, row in enumerate(data):
    with st.expander(f"{row['Data']} - {row['Horario']} ({row['Comentarista'] or 'Vago'})"):
        col1, col2 = st.columns(2)
        
        # Botão Servir
        if row['Comentarista'] == "":
            if col1.button("Servir", key=f"s_{idx}"):
                sheet.update_cell(idx + 2, 5, "NOME_DO_USUARIO")
                st.rerun()
        # Botão Cancelar
        else:
            if col2.button("X - Cancelar", key=f"c_{idx}"):
                sheet.update_cell(idx + 2, 5, "")
                st.rerun()