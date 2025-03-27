import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import shutil
import time

# Configurações da página
st.set_page_config(
    page_title="Sistema de Ordens de Serviço",
    page_icon="🔧",
    layout="wide"
)

# Constantes
DATA_DIR = "data"
FILENAME = os.path.join(DATA_DIR, "ordens_servico.csv")
BACKUP_FILE = os.path.join(DATA_DIR, "ordens_servico_backup.csv")
EXECUTANTES_FILE = os.path.join(DATA_DIR, "executantes.txt")

TIPOS_MANUTENCAO = {
    1: "Elétrica",
    2: "Mecânica",
    3: "Refrigeração",
    4: "Hidráulica",
    5: "Civil",
    6: "Instalação"
}

STATUS_OPCOES = {
    1: "Pendente",
    2: "Pausado",
    3: "Em execução",
    4: "Concluído"
}

# Funções auxiliares
def garantir_diretorio_dados():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def inicializar_arquivos():
    garantir_diretorio_dados()
    if not os.path.exists(FILENAME):
        pd.DataFrame(columns=["ID", "Descrição", "Data", "Solicitante", "Local",
                              "Tipo", "Status", "Executante", "Data Conclusão"]).to_csv(FILENAME, index=False)
    if not os.path.exists(EXECUTANTES_FILE):
        with open(EXECUTANTES_FILE, 'w') as f:
            f.write("")

def carregar_executantes():
    if os.path.exists(EXECUTANTES_FILE):
        with open(EXECUTANTES_FILE, 'r') as f:
            return [linha.strip() for linha in f.readlines() if linha.strip()]
    return []

def salvar_executantes(executantes):
    garantir_diretorio_dados()
    with open(EXECUTANTES_FILE, 'w') as f:
        for nome in executantes:
            f.write(f"{nome}\n")

def carregar_csv():
    if os.path.exists(FILENAME) and os.path.getsize(FILENAME) > 0:
        df = pd.read_csv(FILENAME)
        df["Executante"] = df["Executante"].astype(str).fillna("")
        df["Data Conclusão"] = df["Data Conclusão"].astype(str).fillna("")
        return df
    return pd.DataFrame(columns=["ID", "Descrição", "Data", "Solicitante", "Local",
                                 "Tipo", "Status", "Executante", "Data Conclusão"])

def salvar_csv(df):
    garantir_diretorio_dados()
    df.to_csv(FILENAME, index=False)

def fazer_backup():
    if os.path.exists(FILENAME) and os.path.getsize(FILENAME) > 0:
        shutil.copy(FILENAME, BACKUP_FILE)
        st.success(f"Backup criado com sucesso: {BACKUP_FILE}")

# Funções das páginas
def pagina_inicial():
    col1, col2 = st.columns([1, 15])
    with col1:
        st.markdown('<div style="font-size: 2.5em; margin-top: 10px;">🔧</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("<h1 style='font-size: 2.5em;'>SISTEMA DE GESTÃO DE ORDENS DE SERVIÇO</h1>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    ### Bem-vindo ao Sistema de Gestão de Ordens de Serviço
    **Funcionalidades disponíveis:**
    - 📝 **Cadastro** de novas ordens de serviço
    - 📋 **Listagem** completa de OS cadastradas
    - 🔍 **Busca** avançada por diversos critérios
    - 🔄 **Atualização** de status e informações
    - 📊 **Dashboard** com análises gráficas
    - 👷 **Gerenciamento** de executantes
    """)

def cadastrar_os():
    st.header("📝 Cadastrar Nova Ordem de Serviço")
    with st.form("cadastro_os_form", clear_on_submit=True):
        descricao = st.text_area("Descrição da atividade*")
        solicitante = st.text_input("Solicitante*")
        local = st.text_input("Local*")
        submitted = st.form_submit_button("Cadastrar OS")

        if submitted:
            if not descricao or not solicitante or not local:
                st.error("Preencha todos os campos obrigatórios (*)")
            else:
                df = carregar_csv()
                novo_id = (df["ID"].max() if not df.empty else 0) + 1
                nova_os = pd.DataFrame([{
                    "ID": novo_id,
                    "Descrição": descricao,
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Solicitante": solicitante,
                    "Local": local,
                    "Tipo": "",
                    "Status": "Pendente",
                    "Executante": "",
                    "Data Conclusão": ""
                }])
                df = pd.concat([df, nova_os], ignore_index=True)
                salvar_csv(df)
                st.success("Ordem cadastrada com sucesso!")
                time.sleep(1)
                st.rerun()

# Funções vazias para evitar erros de execução
def listar_os():
    st.header("📋 Listar Ordens de Serviço")
    st.write("Função ainda não implementada.")

def buscar_os():
    st.header("🔍 Buscar Ordem de Serviço")
    st.write("Função ainda não implementada.")

def atualizar_os():
    st.header("🔄 Atualizar Ordem de Serviço")
    st.write("Função ainda não implementada.")

def dashboard():
    st.header("📊 Dashboard")
    st.write("Função ainda não implementada.")

def gerenciar_executantes():
    st.header("👷 Gerenciar Executantes")
    st.write("Função ainda não implementada.")

# Função principal
def main():
    inicializar_arquivos()

    st.sidebar.title("Menu")
    opcao = st.sidebar.selectbox(
        "Selecione",
        [
            "🏠 Página Inicial",
            "📝 Cadastrar OS",
            "📋 Listar OS",
            "🔍 Buscar OS",
            "🔄 Atualizar OS",
            "📊 Dashboard",
            "👷 Gerenciar Executantes",
            "💾 Fazer Backup"
        ]
    )

    # Navegação
    if opcao == "🏠 Página Inicial":
        pagina_inicial()
    elif opcao == "📝 Cadastrar OS":
        cadastrar_os()
    elif opcao == "📋 Listar OS":
        listar_os()
    elif opcao == "🔍 Buscar OS":
        buscar_os()
    elif opcao == "🔄 Atualizar OS":
        atualizar_os()
    elif opcao == "📊 Dashboard":
        dashboard()
    elif opcao == "👷 Gerenciar Executantes":
        gerenciar_executantes()
    elif opcao == "💾 Fazer Backup":
        fazer_backup()

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Sistema de Ordens de Serviço**")
    st.sidebar.markdown("Versão 2.3")
    st.sidebar.markdown("Desenvolvido por Robson Vilela")

if __name__ == "__main__":
    main()
