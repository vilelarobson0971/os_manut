import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import shutil

# Configurações da página
st.set_page_config(
    page_title="Sistema de Ordens de Serviço",
    page_icon="🔧",
    layout="wide"
)

# Constantes
FILENAME = "ordens_servico.csv"
BACKUP_FILE = "ordens_servico_backup.csv"
EXECUTANTES_FILE = "executantes.txt"

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
def inicializar_arquivos():
    if not os.path.exists(FILENAME):
        pd.DataFrame(columns=["ID", "Descrição", "Data", "Solicitante", "Local", "Tipo", "Status", "Executante",
                              "Data Conclusão"]).to_csv(FILENAME, index=False)
    if not os.path.exists(EXECUTANTES_FILE):
        with open(EXECUTANTES_FILE, 'w') as f:
            f.write("")


def carregar_executantes():
    if os.path.exists(EXECUTANTES_FILE):
        with open(EXECUTANTES_FILE, 'r') as f:
            return [linha.strip() for linha in f.readlines() if linha.strip()]
    return []


def salvar_executantes(executantes):
    with open(EXECUTANTES_FILE, 'w') as f:
        for nome in executantes:
            f.write(f"{nome}\n")


def carregar_csv():
    if os.path.exists(FILENAME) and os.path.getsize(FILENAME) > 0:
        return pd.read_csv(FILENAME, dtype={"Executante": "string", "Data Conclusão": "string"})
    return pd.DataFrame(
        columns=["ID", "Descrição", "Data", "Solicitante", "Local", "Tipo", "Status", "Executante", "Data Conclusão"])


def fazer_backup():
    if os.path.exists(FILENAME) and os.path.getsize(FILENAME) > 0:
        shutil.copy(FILENAME, BACKUP_FILE)
        st.success(f"Backup criado com sucesso: {BACKUP_FILE}")


def formatar_data(data):
    try:
        if len(data) == 8 and data.isdigit():
            return datetime.strptime(data, "%d%m%Y").strftime("%d/%m/%Y")
        return datetime.strptime(data, "%d/%m/%Y").strftime("%d/%m/%Y")
    except ValueError:
        st.error("Data inválida! Use o formato DD/MM/AAAA.")
        return None


# Funções principais
def pagina_inicial():
    st.markdown("<h1 style='text-align: center; font-size: 36px;'>SISTEMA DE GESTÃO DE ORDENS DE SERVIÇO</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>By Robson Vilela</p>", unsafe_allow_html=True)
    st.write("---")

    st.write("""
    **Funcionalidades disponíveis:**
    - Cadastro de novas ordens de serviço
    - Listagem completa de OS
    - Busca avançada
    - Atualização de status
    - Dashboard analítico
    - Gerenciamento de executantes
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
                novo_id = df["ID"].max() + 1 if not df.empty else 1
                data_formatada = datetime.now().strftime("%d/%m/%Y")

                nova_os = pd.DataFrame([{
                    "ID": novo_id,
                    "Descrição": descricao,
                    "Data": data_formatada,
                    "Solicitante": solicitante,
                    "Local": local,
                    "Tipo": "",
                    "Status": "Pendente",
                    "Executante": "",
                    "Data Conclusão": ""
                }])

                df = pd.concat([df, nova_os], ignore_index=True)
                df.to_csv(FILENAME, index=False)
                st.success("Ordem cadastrada com sucesso!")
                st.session_state.cadastro_realizado = True

    if st.session_state.get('cadastro_realizado', False):
        st.session_state.cadastro_realizado = False
        st.experimental_rerun()


def listar_os():
    st.header("📋 Listagem de Ordens de Serviço")
    df = carregar_csv()

    if df.empty:
        st.warning("Nenhuma OS cadastrada")
    else:
        st.dataframe(df, use_container_width=True)


def buscar_os():
    st.header("🔍 Buscar Ordens de Serviço")
    df = carregar_csv()

    if df.empty:
        st.warning("Nenhuma OS cadastrada")
        return

    col1, col2 = st.columns(2)

    with col1:
        criterio = st.radio("Critério:", ["ID", "Solicitante", "Local", "Status"])

    with col2:
        if criterio == "ID":
            busca = st.number_input("ID", min_value=1)
            resultado = df[df["ID"] == busca]
        elif criterio == "Solicitante":
            busca = st.text_input("Solicitante")
            resultado = df[df["Solicitante"].str.contains(busca, case=False)]
        elif criterio == "Local":
            busca = st.text_input("Local")
            resultado = df[df["Local"].str.contains(busca, case=False)]
        elif criterio == "Status":
            busca = st.selectbox("Status", list(STATUS_OPCOES.values()))
            resultado = df[df["Status"] == busca]

    if not resultado.empty:
        st.dataframe(resultado, use_container_width=True)
    else:
        st.warning("Nenhuma OS encontrada")


def atualizar_os():
    st.header("🔄 Atualizar Ordem de Serviço")
    df = carregar_csv()

    nao_concluidas = df[df["Status"] != "Concluído"]
    if nao_concluidas.empty:
        st.warning("Nenhuma OS pendente")
        return

    os_id = st.selectbox("Selecione a OS", nao_concluidas["ID"])
    os_data = df[df["ID"] == os_id].iloc[0]

    with st.form("atualizar_form"):
        st.write(f"**Descrição:** {os_data['Descrição']}")
        st.write(f"**Solicitante:** {os_data['Solicitante']}")

        col1, col2 = st.columns(2)
        with col1:
            novo_status = st.selectbox(
                "Status*",
                list(STATUS_OPCOES.values()),
                index=list(STATUS_OPCOES.values()).index(os_data["Status"])
            )

            # Campo de executante sempre visível
            executantes = carregar_executantes()
            executante = st.selectbox(
                "Executante",
                [""] + executantes,
                index=executantes.index(os_data["Executante"]) + 1 if os_data["Executante"] in executantes else 0
            )

        with col2:
            if novo_status == "Concluído":
                data_conclusao = st.text_input(
                    "Data de conclusão (DD/MM/AAAA ou DDMMAAAA)",
                    value=os_data['Data Conclusão'] if pd.notna(os_data['Data Conclusão']) else ""
                )
            else:
                data_conclusao = ""

        if st.form_submit_button("Atualizar"):
            df.loc[df["ID"] == os_id, "Status"] = novo_status
            df.loc[df["ID"] == os_id, "Executante"] = executante
            if novo_status == "Concluído":
                df.loc[df["ID"] == os_id, "Data Conclusão"] = data_conclusao
            df.to_csv(FILENAME, index=False)
            st.success("OS atualizada com sucesso!")
            st.session_state.atualizacao_realizada = True

    if st.session_state.get('atualizacao_realizada', False):
        st.session_state.atualizacao_realizada = False
        st.experimental_rerun()


def dashboard():
    st.header("📊 Dashboard Analítico")
    df = carregar_csv()

    if df.empty:
        st.warning("Nenhuma OS cadastrada")
        return

    tab1, tab2 = st.tabs(["Por Status", "Por Tipo"])

    with tab1:
        st.subheader("Distribuição por Status")
        fig, ax = plt.subplots()
        df["Status"].value_counts().plot.pie(autopct="%1.1f%%", ax=ax)
        st.pyplot(fig)

    with tab2:
        st.subheader("Distribuição por Tipo")
        fig, ax = plt.subplots()
        df["Tipo"].value_counts().plot.bar(ax=ax)
        st.pyplot(fig)


def gerenciar_executantes():
    st.header("👷 Gerenciar Executantes")
    executantes = carregar_executantes()

    tab1, tab2 = st.tabs(["Adicionar", "Remover"])

    with tab1:
        with st.form("add_executante"):
            novo = st.text_input("Nome do executante")
            if st.form_submit_button("Adicionar"):
                if novo and novo not in executantes:
                    executantes.append(novo)
                    salvar_executantes(executantes)
                    st.success("Executante adicionado")
                    st.experimental_rerun()

    with tab2:
        if executantes:
            with st.form("rem_executante"):
                selecionado = st.selectbox("Executante", executantes)
                if st.form_submit_button("Remover"):
                    executantes.remove(selecionado)
                    salvar_executantes(executantes)
                    st.success("Executante removido")
                    st.experimental_rerun()
        else:
            st.warning("Nenhum executante cadastrado")


# Menu principal
def main():
    if 'cadastro_realizado' not in st.session_state:
        st.session_state.cadastro_realizado = False
    if 'atualizacao_realizada' not in st.session_state:
        st.session_state.atualizacao_realizada = False

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
            "👷 Gerenciar Executantes"
        ]
    )

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


if __name__ == "__main__":
    inicializar_arquivos()
    main()