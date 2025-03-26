# app.py
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


# Interface Streamlit
def main():
    st.title("🔧 Sistema de Ordens de Serviço")
    st.markdown("By Robson Vilela")

    inicializar_arquivos()

    menu = st.sidebar.selectbox("Menu", ["Cadastrar OS", "Listar OS", "Atualizar OS", "Buscar OS", "Dashboard",
                                         "Gerenciar Executantes"])

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


def cadastrar_os():
    st.header("Cadastrar Nova Ordem de Serviço")

    with st.form("cadastro_os"):
        descricao = st.text_area("Descrição da atividade")
        solicitante = st.text_input("Nome do solicitante")
        local = st.text_input("Local solicitante")

        if st.form_submit_button("Cadastrar"):
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


def listar_os():
    st.header("Listagem de Ordens de Serviço")

    df = carregar_csv()
    if df.empty:
        st.warning("Nenhuma ordem de serviço encontrada.")
    else:
        st.dataframe(df, use_container_width=True)


def buscar_os():
    st.header("Buscar Ordens de Serviço")

    df = carregar_csv()
    if df.empty:
        st.warning("Nenhuma ordem de serviço encontrada.")
        return

    col1, col2 = st.columns(2)

    with col1:
        opcao = st.radio("Critério de busca", ["ID", "Data", "Solicitante", "Local", "Status", "Executante"])

    with col2:
        if opcao == "ID":
            filtro = st.number_input("Digite o ID", min_value=1, step=1)
            resultado = df[df["ID"] == filtro]
        elif opcao == "Data":
            filtro = st.text_input("Digite a data (DD/MM/AAAA ou DDMMAAAA)")
            filtro = formatar_data(filtro)
            if filtro:
                resultado = df[df["Data"] == filtro]
        else:
            filtro = st.text_input(f"Digite o {opcao.lower()}")
            coluna = opcao
            resultado = df[df[coluna].str.contains(filtro, case=False, na=False)]

    if 'resultado' in locals() and not resultado.empty:
        st.dataframe(resultado, use_container_width=True)
    else:
        st.warning("Nenhuma OS encontrada com esse critério.")


def selecionar_executante():
    executantes = carregar_executantes()
    if not executantes:
        st.warning("Nenhum executante cadastrado. Cadastre executantes primeiro.")
        return ""

    return st.selectbox("Selecione o executante", [""] + executantes)


def atualizar_os():
    st.header("Atualizar Ordem de Serviço")

    df = carregar_csv()
    df_nao_concluidas = df[df['Status'] != 'Concluído']

    if df_nao_concluidas.empty:
        st.warning("Nenhuma ordem de serviço pendente encontrada.")
        return

    os_id = st.selectbox("Selecione a OS para atualizar", df_nao_concluidas["ID"].values)

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
                    index=list(STATUS_OPCOES.values()).index(os_data['Status'])
                )

                tipo = st.selectbox(
                    "Tipo de manutenção",
                    list(TIPOS_MANUTENCAO.values()),
                    index=list(TIPOS_MANUTENCAO.values()).index(os_data['Tipo']) if os_data[
                                                                                        'Tipo'] in TIPOS_MANUTENCAO.values() else 0
                )

            with col2:
                executante = selecionar_executante() if status in ["Em execução", "Concluído"] else ""

                data_conclusao = ""
                if status == "Concluído":
                    data_input = st.text_input("Data de conclusão (DD/MM/AAAA ou DDMMAAAA)",
                                               value=os_data['Data Conclusão'])
                    data_conclusao = formatar_data(data_input) if data_input else ""

            if st.form_submit_button("Atualizar"):
                df.loc[df["ID"] == os_id, ["Status", "Tipo", "Executante", "Data Conclusão"]] = [
                    status, tipo, str(executante), str(data_conclusao)
                ]

                fazer_backup()
                df.to_csv(FILENAME, index=False)
                st.success("Ordem de serviço atualizada com sucesso!")


def dashboard():
    st.header("Dashboard de Ordens de Serviço")

    df = carregar_csv()
    if df.empty:
        st.warning("Nenhuma ordem de serviço encontrada para gerar gráficos.")
        return

    sns.set(style="whitegrid")

    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return '{p:.1f}%\n({v:d})'.format(p=pct, v=val)

        return my_autopct

    tab1, tab2, tab3 = st.tabs(["Por Tipo", "Por Status", "Por Executante"])

    with tab1:
        st.subheader("O.S. Concluídas por Tipo de Manutenção")
        df_concluidas = df[df['Status'] == 'Concluído']
        if not df_concluidas.empty:
            tipo_counts = df_concluidas['Tipo'].value_counts()
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(tipo_counts, labels=tipo_counts.index, autopct=make_autopct(tipo_counts),
                   colors=sns.color_palette('Set2'))
            st.pyplot(fig)
        else:
            st.warning("Nenhuma OS concluída encontrada.")

    with tab2:
        st.subheader("Distribuição de O.S. por Status")
        status_counts = df['Status'].value_counts()
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.pie(status_counts, labels=status_counts.index, autopct=make_autopct(status_counts),
               colors=sns.color_palette('Set1'))
        st.pyplot(fig)

    with tab3:
        st.subheader("Distribuição de O.S. por Executante")
        executante_counts = df[df['Executante'] != '']['Executante'].value_counts()
        if not executante_counts.empty:
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(executante_counts, labels=executante_counts.index, autopct=make_autopct(executante_counts),
                   colors=sns.color_palette('Set2'))
            st.pyplot(fig)
        else:
            st.warning("Nenhuma OS com executante atribuído encontrada.")


def gerenciar_executantes():
    st.header("Gerenciamento de Executantes")

    executantes = carregar_executantes()

    tab1, tab2 = st.tabs(["Adicionar", "Remover/Listar"])

    with tab1:
        with st.form("adicionar_executante"):
            novo_nome = st.text_input("Nome do novo executante")
            if st.form_submit_button("Adicionar"):
                if novo_nome:
                    if novo_nome in executantes:
                        st.error("Este executante já está cadastrado!")
                    else:
                        executantes.append(novo_nome)
                        salvar_executantes(executantes)
                        st.success("Executante adicionado com sucesso!")
                else:
                    st.error("Nome inválido!")

    with tab2:
        if not executantes:
            st.warning("Nenhum executante cadastrado.")
        else:
            st.write("Executantes cadastrados:")
            for i, nome in enumerate(executantes, 1):
                st.write(f"{i}. {nome}")

            with st.form("remover_executante"):
                num = st.number_input("Número do executante a remover", min_value=1, max_value=len(executantes), step=1)
                if st.form_submit_button("Remover"):
                    removido = executantes.pop(num - 1)
                    salvar_executantes(executantes)
                    st.success(f"Executante '{removido}' removido com sucesso!")


if __name__ == "__main__":
    main()