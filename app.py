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


# Funções principais corrigidas
def cadastrar_os():
    st.header("📝 Cadastrar Nova Ordem de Serviço")

    with st.form("cadastro_os_form", clear_on_submit=True):
        descricao = st.text_area("Descrição da atividade*", placeholder="Descreva detalhadamente o serviço necessário")
        solicitante = st.text_input("Solicitante*", placeholder="Nome da pessoa que solicitou")
        local = st.text_input("Local*", placeholder="Local onde o serviço será realizado")

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
                st.success("✅ Ordem de serviço cadastrada com sucesso!")
                st.balloons()
                st.session_state.cadastro_realizado = True

    if st.session_state.get('cadastro_realizado', False):
        if st.button("↻ Cadastrar outra OS"):
            st.session_state.cadastro_realizado = False
            st.rerun()


def atualizar_os():
    st.header("🔄 Atualizar Ordem de Serviço")

    df = carregar_csv()
    df_nao_concluidas = df[df['Status'] != 'Concluído']

    if df_nao_concluidas.empty:
        st.warning("Nenhuma ordem de serviço pendente encontrada.")
        return

    os_id = st.selectbox("Selecione a OS para atualizar", df_nao_concluidas["ID"].values)

    if os_id:
        os_data = df[df["ID"] == os_id].iloc[0]

        with st.form("atualizar_os_form"):
            st.subheader(f"OS #{os_id}")
            st.write(f"**Descrição:** {os_data['Descrição']}")
            st.write(f"**Solicitante:** {os_data['Solicitante']}")
            st.write(f"**Local:** {os_data['Local']}")
            st.write(f"**Data de abertura:** {os_data['Data']}")

            col1, col2 = st.columns(2)

            with col1:
                status = st.selectbox(
                    "Status*",
                    list(STATUS_OPCOES.values()),
                    index=list(STATUS_OPCOES.values()).index(os_data['Status'])
                )

                tipo = st.selectbox(
                    "Tipo de manutenção*",
                    list(TIPOS_MANUTENCAO.values()),
                    index=list(TIPOS_MANUTENCAO.values()).index(os_data['Tipo']) if os_data[
                                                                                        'Tipo'] in TIPOS_MANUTENCAO.values() else 0
                )

            with col2:
                executantes = carregar_executantes()

                if status in ["Em execução", "Concluído"]:
                    if not executantes:
                        st.warning("Nenhum executante cadastrado!")
                        executante = ""
                    else:
                        # Corrigido o erro de verificação de executante
                        current_exec = os_data['Executante'] if pd.notna(os_data['Executante']) else ""
                        executante = st.selectbox(
                            "Executante*",
                            [""] + executantes,
                            index=executantes.index(current_exec) + 1 if current_exec in executantes else 0
                        )
                else:
                    executante = ""

                if status == "Concluído":
                    data_conclusao = st.text_input(
                        "Data de conclusão* (DD/MM/AAAA ou DDMMAAAA)",
                        value=os_data['Data Conclusão'] if pd.notna(os_data['Data Conclusão']) else ""
                    )
                else:
                    data_conclusao = ""

            submitted = st.form_submit_button("Atualizar OS")

            if submitted:
                if status in ["Em execução", "Concluído"] and not executante:
                    st.error("Selecione um executante para este status!")
                elif status == "Concluído" and not data_conclusao:
                    st.error("Informe a data de conclusão!")
                else:
                    df.loc[df["ID"] == os_id, ["Status", "Tipo", "Executante", "Data Conclusão"]] = [
                        status, tipo, str(executante), str(data_conclusao) if status == "Concluído" else ""
                    ]
                    df.to_csv(FILENAME, index=False)
                    st.success("✅ Ordem de serviço atualizada com sucesso!")
                    st.balloons()
                    st.session_state.atualizacao_realizada = True

        if st.session_state.get('atualizacao_realizada', False):
            st.session_state.atualizacao_realizada = False
            st.rerun()


# Outras funções (listar_os, buscar_os, dashboard, gerenciar_executantes) permanecem iguais
# ... (código anterior das outras funções)

def main():
    st.title("🔧 Sistema de Gestão de Ordens de Serviço")
    st.markdown("---")

    inicializar_arquivos()

    menu = st.sidebar.selectbox(
        "Menu Principal",
        ["🏠 Início", "📝 Cadastrar OS", "📋 Listar OS", "🔍 Buscar OS", "🔄 Atualizar OS", "📊 Dashboard",
         "👷 Gerenciar Executantes"]
    )

    if menu == "🏠 Início":
        st.subheader("Bem-vindo ao Sistema de Ordens de Serviço")
        st.write("""
        Este sistema permite gerenciar ordens de serviço de manutenção de forma eficiente.
        """)

    elif menu == "📝 Cadastrar OS":
        cadastrar_os()
    elif menu == "📋 Listar OS":
        listar_os()
    elif menu == "🔍 Buscar OS":
        buscar_os()
    elif menu == "🔄 Atualizar OS":
        atualizar_os()
    elif menu == "📊 Dashboard":
        dashboard()
    elif menu == "👷 Gerenciar Executantes":
        gerenciar_executantes()

    st.sidebar.markdown("---")
    st.sidebar.info("Sistema desenvolvido por Robson Vilela")


if __name__ == "__main__":
    main()