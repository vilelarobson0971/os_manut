import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import shutil
from PIL import Image

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

                if st.button("Cadastrar outra OS"):
                    st.rerun()


def listar_os():
    st.header("📋 Listagem de Ordens de Serviço")

    df = carregar_csv()
    if df.empty:
        st.warning("Nenhuma ordem de serviço cadastrada.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Opções de filtro
        with st.expander("Filtrar OS"):
            col1, col2 = st.columns(2)
            with col1:
                filtrar_status = st.selectbox("Status", ["Todos"] + list(STATUS_OPCOES.values()))
            with col2:
                filtrar_tipo = st.selectbox("Tipo de manutenção", ["Todos"] + list(TIPOS_MANUTENCAO.values()))

            if filtrar_status != "Todos":
                df = df[df["Status"] == filtrar_status]
            if filtrar_tipo != "Todos":
                df = df[df["Tipo"] == filtrar_tipo]

            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("Nenhuma OS encontrada com esses filtros.")


def buscar_os():
    st.header("🔍 Buscar Ordens de Serviço")

    df = carregar_csv()
    if df.empty:
        st.warning("Nenhuma ordem de serviço cadastrada.")
        return

    col1, col2 = st.columns(2)

    with col1:
        criterio = st.radio("Buscar por:", ["ID", "Solicitante", "Local", "Status", "Tipo", "Executante"])

    with col2:
        if criterio == "ID":
            busca = st.number_input("Digite o ID", min_value=1, step=1)
            resultado = df[df["ID"] == busca]
        elif criterio == "Solicitante":
            busca = st.text_input("Digite o nome do solicitante")
            resultado = df[df["Solicitante"].str.contains(busca, case=False, na=False)]
        elif criterio == "Local":
            busca = st.text_input("Digite o local")
            resultado = df[df["Local"].str.contains(busca, case=False, na=False)]
        elif criterio == "Status":
            busca = st.selectbox("Selecione o status", list(STATUS_OPCOES.values()))
            resultado = df[df["Status"] == busca]
        elif criterio == "Tipo":
            busca = st.selectbox("Selecione o tipo", list(TIPOS_MANUTENCAO.values()))
            resultado = df[df["Tipo"] == busca]
        elif criterio == "Executante":
            busca = st.text_input("Digite o nome do executante")
            resultado = df[df["Executante"].str.contains(busca, case=False, na=False)]

    if not resultado.empty:
        st.dataframe(resultado, use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhuma OS encontrada com esse critério.")


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
                        executante = st.selectbox(
                            "Executante*",
                            [""] + executantes,
                            index=executantes.index(os_data['Executante']) + 1 if os_data[
                                                                                      'Executante'] in executantes else 0
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


def dashboard():
    st.header("📊 Dashboard de Ordens de Serviço")

    df = carregar_csv()
    if df.empty:
        st.warning("Nenhuma ordem de serviço encontrada para gerar gráficos.")
        return

    sns.set(style="whitegrid")
    plt.style.use('seaborn')

    tab1, tab2, tab3 = st.tabs(["📈 Por Status", "🔧 Por Tipo", "👷 Por Executante"])

    with tab1:
        st.subheader("Distribuição por Status")
        status_counts = df['Status'].value_counts()

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%',
               colors=sns.color_palette('Set2'), startangle=90)
        ax.axis('equal')
        st.pyplot(fig)

        st.dataframe(status_counts, use_container_width=True)

    with tab2:
        st.subheader("Distribuição por Tipo de Manutenção")
        tipo_counts = df['Tipo'].value_counts()

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(x=tipo_counts.values, y=tipo_counts.index, palette='Set3')
        plt.xlabel('Quantidade')
        plt.ylabel('Tipo de Manutenção')
        st.pyplot(fig)

        st.dataframe(tipo_counts, use_container_width=True)

    with tab3:
        st.subheader("Distribuição por Executante")
        executante_counts = df[df['Executante'] != '']['Executante'].value_counts()

        if not executante_counts.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(x=executante_counts.values, y=executante_counts.index, palette='Set1')
            plt.xlabel('Quantidade de OS')
            plt.ylabel('Executante')
            st.pyplot(fig)

            st.dataframe(executante_counts, use_container_width=True)
        else:
            st.warning("Nenhuma OS com executante atribuído encontrada.")


def gerenciar_executantes():
    st.header("👷‍♂️ Gerenciamento de Executantes")

    executantes = carregar_executantes()

    tab1, tab2 = st.tabs(["➕ Adicionar Executante", "🗑️ Remover Executante"])

    with tab1:
        with st.form("adicionar_executante_form", clear_on_submit=True):
            novo_nome = st.text_input("Nome do novo executante", placeholder="Digite o nome completo")

            if st.form_submit_button("Adicionar Executante"):
                if not novo_nome:
                    st.error("Digite um nome válido!")
                elif novo_nome in executantes:
                    st.warning("Este executante já está cadastrado!")
                else:
                    executantes.append(novo_nome)
                    salvar_executantes(executantes)
                    st.success(f"✅ Executante '{novo_nome}' adicionado com sucesso!")
                    st.rerun()

    with tab2:
        if not executantes:
            st.warning("Nenhum executante cadastrado.")
        else:
            st.write("Executantes cadastrados:")
            for i, nome in enumerate(executantes, 1):
                st.write(f"{i}. {nome}")

            with st.form("remover_executante_form"):
                executante_remover = st.selectbox(
                    "Selecione o executante para remover",
                    executantes
                )

                if st.form_submit_button("Remover Executante"):
                    executantes.remove(executante_remover)
                    salvar_executantes(executantes)
                    st.success(f"✅ Executante '{executante_remover}' removido com sucesso!")
                    st.rerun()


# Menu principal
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

        **Funcionalidades disponíveis:**
        - Cadastro de novas ordens de serviço
        - Listagem e filtragem de OS
        - Atualização de status e informações
        - Dashboard com análises gráficas
        - Gerenciamento de executantes
        """)

        st.image("https://via.placeholder.com/800x300?text=Sistema+de+Ordens+de+Serviço", use_column_width=True)

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
    st.sidebar.warning("Versão 1.0 - 2023")


if __name__ == "__main__":
    main()