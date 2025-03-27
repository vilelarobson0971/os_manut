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

# Constantes e inicialização de estado
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

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


# Funções auxiliares (mantidas as mesmas)
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


# Funções modificadas para resolver os problemas
def cadastrar_os():
    st.header("Cadastrar Nova Ordem de Serviço")

    with st.form("cadastro_os"):
        descricao = st.text_area("Descrição da atividade", key="descricao")
        solicitante = st.text_input("Nome do solicitante", key="solicitante")
        local = st.text_input("Local solicitante", key="local")

        submitted = st.form_submit_button("Cadastrar")

        if submitted:
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
            st.success("Ordem de serviço cadastrada com sucesso!")
            st.session_state.form_submitted = True
            st.experimental_rerun()

    if st.session_state.get('form_submitted', False):
        st.session_state.form_submitted = False
        st.experimental_rerun()


def atualizar_os():
    st.header("Atualizar Ordem de Serviço")

    df = carregar_csv()
    df_nao_concluidas = df[df['Status'] != 'Concluído']

    if df_nao_concluidas.empty:
        st.warning("Nenhuma ordem de serviço pendente encontrada.")
        return

    os_id = st.selectbox("Selecione a OS para atualizar", df_nao_concluidas["ID"].values, key="os_select")

    if os_id:
        os_data = df[df["ID"] == os_id].iloc[0]

        with st.form("atualizar_os"):
            st.write(f"**Descrição:** {os_data['Descrição']}")
            st.write(f"**Solicitante:** {os_data['Solicitante']}")
            st.write(f"**Local:** {os_data['Local']}")

            col1, col2 = st.columns(2)

            with col1:
                status = st.selectbox(
                    "Status",
                    list(STATUS_OPCOES.values()),
                    index=list(STATUS_OPCOES.values()).index(os_data['Status']),
                    key="status_select"
                )

                tipo = st.selectbox(
                    "Tipo de manutenção",
                    list(TIPOS_MANUTENCAO.values()),
                    index=list(TIPOS_MANUTENCAO.values()).index(os_data['Tipo']) if os_data[
                                                                                        'Tipo'] in TIPOS_MANUTENCAO.values() else 0,
                    key="tipo_select"
                )

            with col2:
                # Mostra o seletor de executante apenas se o status for "Em execução" ou "Concluído"
                if status in ["Em execução", "Concluído"]:
                    executantes = carregar_executantes()
                    if not executantes:
                        st.warning("Nenhum executante cadastrado. Cadastre executantes primeiro.")
                    else:
                        executante = st.selectbox(
                            "Selecione o executante",
                            [""] + executantes,
                            key="executante_select"
                        )
                else:
                    executante = ""

                # Mostra o campo de data de conclusão apenas se o status for "Concluído"
                if status == "Concluído":
                    data_conclusao = st.text_input(
                        "Data de conclusão (DD/MM/AAAA ou DDMMAAAA)",
                        value=os_data['Data Conclusão'] if pd.notna(os_data['Data Conclusão']) else "",
                        key="data_conclusao"
                    )
                else:
                    data_conclusao = ""

            submitted = st.form_submit_button("Atualizar")

            if submitted:
                if status in ["Em execução", "Concluído"] and not executante:
                    st.error("Selecione um executante para OS em execução ou concluída!")
                elif status == "Concluído" and not data_conclusao:
                    st.error("Informe a data de conclusão!")
                else:
                    df.loc[df["ID"] == os_id, ["Status", "Tipo", "Executante", "Data Conclusão"]] = [
                        status, tipo, str(executante), str(data_conclusao) if status == "Concluído" else ""
                    ]

                    fazer_backup()
                    df.to_csv(FILENAME, index=False)
                    st.success("Ordem de serviço atualizada com sucesso!")
                    st.session_state.form_submitted = True
                    st.experimental_rerun()

    if st.session_state.get('form_submitted', False):
        st.session_state.form_submitted = False
        st.experimental_rerun()


# As outras funções (listar_os, buscar_os, dashboard, gerenciar_executantes) permanecem as mesmas
# ... (mantenha o restante do código igual)

def main():
    st.title("🔧 Sistema de Ordens de Serviço")
    st.markdown("By Robson Vilela")

    inicializar_arquivos()

    menu = st.sidebar.selectbox("Menu", ["Cadastrar OS", "Listar OS", "Atualizar OS", "Buscar OS", "Dashboard",
                                         "Gerenciar Executantes"], key="menu_select")

    if menu == "Cadastrar OS":
        cadastrar_os()
    elif menu == "Listar OS":
        listar_os()
    elif menu == "Atualizar OS":
        atualizar_os()
    elif menu == "Buscar OS":
        buscar_os()
    elif menu == "Dashboard":
        dashboard()
    elif menu == "Gerenciar Executantes":
        gerenciar_executantes()


if __name__ == "__main__":
    main()