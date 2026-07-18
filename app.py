import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, timedelta
import json

# --- CONFIGURAÇÃO E CONEXÃO ---
# Carrega as credenciais do "Secrets" do Streamlit (explicarei abaixo)
def get_sheets():
    creds_dict = st.secrets["gcp_service_account"]
    creds = gspread.service_account_from_dict(creds_dict)
    sheet = creds.open_by_key("SEU_ID_DA_PLANILHA").worksheet("Escala")
    return sheet

st.set_page_config(page_title="Leitores Peregrinos", layout="centered")
st.title("Leitores Peregrinos")

# --- LÓGICA DO SISTEMA ---
sheet = get_sheets()
data = sheet.get_all_records()

for idx, row in enumerate(data):
    # Exibição simples e clara
    with st.expander(f"{row['Data']} - {row['Horario']} ({row['Comentarista'] or 'Vago'})"):
        # Regras de Negócio (ex: Cancelamento 36h)
        col1, col2 = st.columns(2)
        
        # Botão Servir
        if row['Comentarista'] == "":
            if col1.button("Servir", key=f"s_{idx}"):
                sheet.update_cell(idx + 2, 5, "NOME_DO_USUARIO") # Altera coluna 5
                st.rerun()
        
        # Botão Cancelar
        else:
            if col2.button("X Cancelar", key=f"c_{idx}"):
                # Lógica das 36h
                data_evento = datetime.strptime(row['Data'], '%d/%m/%Y')
                if (data_evento - datetime.now()) < timedelta(hours=36):
                    st.error("Não permitido: requer 36h de antecedência.")
                else:
                    sheet.update_cell(idx + 2, 5, "")
                    st.rerun()