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
        df = pd.read_csv(FILENAME)
        # Conversão explícita para string
        df["Executante"] = df["Executante"].astype(str)
        df["Data Conclusão"] = df["Data Conclusão"].astype(str)
        return df
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
    # Layout com colunas para o ícone e título
    col1, col2 = st.columns([1, 15])
    with col1:
        st.markdown('<div style="font-size: 2.5em; margin-top: 10px;">🔧</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("<h1 style='font-size: 2.5em;'>SISTEMA DE GESTÃO DE ORDENS DE SERVIÇO</h1>", unsafe_allow_html=True)

    st.markdown("<p style='text-align: center; font-size: 1.2em;'>By Robson Vilela</p>", unsafe_allow_html=True)
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
                # Correção para lidar com DataFrame vazio ou IDs NaN
                novo_id = int(df["ID"].max()) + 1 if not df.empty and not pd.isna(df["ID"].max()) else 1
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
                time.sleep(1)
                st.rerun()


def listar_os():
    st.header("📋 Listagem Completa de OS")
    df = carregar_csv()

    if df.empty:
        st.warning("Nenhuma ordem de serviço cadastrada ainda.")
    else:
        with st.expander("Filtrar OS"):
            col1, col2 = st.columns(2)
            with col1:
                filtro_status = st.selectbox("Status", ["Todos"] + list(STATUS_OPCOES.values()))
            with col2:
                filtro_tipo = st.selectbox("Tipo de Manutenção", ["Todos"] + list(TIPOS_MANUTENCAO.values()))

        if filtro_status != "Todos":
            df = df[df["Status"] == filtro_status]
        if filtro_tipo != "Todos":
            df = df[df["Tipo"] == filtro_tipo]

        st.dataframe(df, use_container_width=True)


def buscar_os():
    st.header("🔍 Busca Avançada")
    df = carregar_csv()

    if df.empty:
        st.warning("Nenhuma OS cadastrada para busca.")
        return

    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            criterio = st.radio("Critério de busca:",
                              ["ID", "Solicitante", "Local", "Status", "Tipo", "Executante"])
        with col2:
            if criterio == "ID":
                busca = st.number_input("Digite o ID da OS", min_value=1)
                resultado = df[df["ID"] == busca]
            elif criterio == "Status":
                busca = st.selectbox("Selecione o status", list(STATUS_OPCOES.values()))
                resultado = df[df["Status"] == busca]
            elif criterio == "Tipo":
                busca = st.selectbox("Selecione o tipo", list(TIPOS_MANUTENCAO.values()))
                resultado = df[df["Tipo"] == busca]
            else:
                busca = st.text_input(f"Digite o {criterio.lower()}")
                resultado = df[df[criterio].astype(str).str.contains(busca, case=False)]

    if not resultado.empty:
        st.success(f"Encontradas {len(resultado)} OS:")
        st.dataframe(resultado, use_container_width=True)
    else:
        st.warning("Nenhuma OS encontrada com os critérios informados.")


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

            executantes = carregar_executantes()
            executante_atual = str(os_data["Executante"]) if pd.notna(os_data["Executante"]) else ""
            index_executante = (executantes.index(executante_atual) + 1
                              if executante_atual in executantes else 0)

            executante = st.selectbox(
                "Executante",
                [""] + executantes,
                index=index_executante
            )

        with col2:
            # Preenche automaticamente com a data atual quando o status não é Pendente
            if novo_status != "Pendente":
                data_atual = datetime.now().strftime("%d/%m/%Y")
                data_conclusao = st.text_input(
                    "Data de atualização",
                    value=data_atual if pd.isna(os_data['Data Conclusão']) or os_data['Status'] == "Pendente" else str(
                        os_data['Data Conclusão']),
                    disabled=novo_status != "Concluído"
                )
            else:
                data_conclusao = st.text_input(
                    "Data de conclusão (DD/MM/AAAA ou DDMMAAAA)",
                    value=str(os_data['Data Conclusão']) if pd.notna(os_data['Data Conclusão']) else "",
                    disabled=True
                )

        submitted = st.form_submit_button("Atualizar OS")

        if submitted:
            if novo_status in ["Em execução", "Concluído"] and not executante:
                st.error("Selecione um executante para este status!")
            elif novo_status == "Concluído" and not data_conclusao:
                st.error("Informe a data de conclusão!")
            else:
                df.loc[df["ID"] == os_id, ["Status", "Executante"]] = [novo_status, executante]
                if novo_status == "Concluído":
                    df.loc[df["ID"] == os_id, "Data Conclusão"] = data_conclusao
                df.to_csv(FILENAME, index=False)
                st.success("OS atualizada com sucesso!")
                time.sleep(1)
                st.rerun()


def dashboard():
    st.header("📊 Dashboard Analítico")
    df = carregar_csv()

    if df.empty:
        st.warning("Nenhuma OS cadastrada para análise.")
        return

    tab1, tab2, tab3 = st.tabs(["📈 Status", "🔧 Tipos", "👥 Executantes"])

    with tab1:
        st.subheader("Distribuição por Status")
        status_counts = df["Status"].value_counts()
        
        if not status_counts.empty:
            fig, ax = plt.subplots(figsize=(4, 2))
            bars = sns.barplot(
                x=status_counts.values,
                y=status_counts.index,
                palette="viridis",
                ax=ax
            )
            
            # Remover eixo X e seus rótulos
            ax.set_xlabel('')
            ax.set_xticks([])
            
            # Adicionar valores dentro das barras
            for bar in bars.patches:
                width = bar.get_width()
                ax.text(width - 0.3 * width,  # Posição X (ajuste conforme necessário)
                        bar.get_y() + bar.get_height()/2,  # Posição Y (centro da barra)
                        f'{int(width)}',  # Valor formatado
                        va='center',  # Alinhamento vertical
                        ha='right',   # Alinhamento horizontal
                        color='yellow',
                        fontsize=8)
            
            plt.ylabel("Status", fontsize=9)
            ax.set_yticklabels(ax.get_yticklabels(), fontsize=8)
            ax.set_title("Distribuição por Status", fontsize=10)
            st.pyplot(fig)
        else:
            st.warning("Nenhum dado de status disponível")

    with tab2:
        st.subheader("Distribuição por Tipo de Manutenção")
        tipo_counts = df["Tipo"].value_counts()
        
        if not tipo_counts.empty:
            fig, ax = plt.subplots(figsize=(4, 2))
            bars = sns.barplot(
                x=tipo_counts.values,
                y=tipo_counts.index,
                palette="viridis",
                ax=ax
            )
            
            # Remover eixo X e seus rótulos
            ax.set_xlabel('')
            ax.set_xticks([])
            
            # Adicionar valores dentro das barras
            for bar in bars.patches:
                width = bar.get_width()
                ax.text(width - 0.3 * width,
                        bar.get_y() + bar.get_height()/2,
                        f'{int(width)}',
                        va='center',
                        ha='right',
                        color='yellow',
                        fontsize=8)
            
            plt.ylabel("Tipo", fontsize=9)
            ax.set_yticklabels(ax.get_yticklabels(), fontsize=8)
            ax.set_title("Distribuição por Tipo de Manutenção", fontsize=10)
            st.pyplot(fig)
        else:
            st.warning("Nenhum dado de tipo disponível")

    with tab3:
        st.subheader("OS por Executante")
        executante_counts = df[df["Executante"] != ""]["Executante"].value_counts()
        
        if not executante_counts.empty:
            fig, ax = plt.subplots(figsize=(4, 2))
            bars = sns.barplot(
                x=executante_counts.values,
                y=executante_counts.index,
                palette="rocket",
                ax=ax
            )
            
            # Remover eixo X e seus rótulos
            ax.set_xlabel('')
            ax.set_xticks([])
            
            # Adicionar valores dentro das barras
            for bar in bars.patches:
                width = bar.get_width()
                ax.text(width - 0.3 * width,
                        bar.get_y() + bar.get_height()/2,
                        f'{int(width)}',
                        va='center',
                        ha='right',
                        color='yellow',
                        fontsize=8)
            
            plt.ylabel("Executante", fontsize=9)
            ax.set_yticklabels(ax.get_yticklabels(), fontsize=8)
            ax.set_title("OS por Executante", fontsize=10)
            st.pyplot(fig)
        else:
            st.warning("Nenhuma OS atribuída a executantes")


def gerenciar_executantes():
    st.header("👷 Gerenciar Executantes")
    executantes = carregar_executantes()

    tab1, tab2 = st.tabs(["Adicionar", "Remover"])

    with tab1:
        with st.form("add_executante_form"):
            novo = st.text_input("Nome do novo executante*")
            submitted_add = st.form_submit_button("Adicionar")

            if submitted_add:
                if not novo:
                    st.error("Digite um nome válido!")
                elif novo in executantes:
                    st.warning("Este executante já está cadastrado!")
                else:
                    executantes.append(novo)
                    salvar_executantes(executantes)
                    st.success(f"Executante '{novo}' adicionado com sucesso!")
                    time.sleep(1)
                    st.rerun()

    with tab2:
        if not executantes:
            st.warning("Nenhum executante cadastrado")
        else:
            with st.form("rem_executante_form"):
                selecionado = st.selectbox("Selecione o executante para remover", executantes)
                submitted_rem = st.form_submit_button("Remover")

                if submitted_rem:
                    executantes.remove(selecionado)
                    salvar_executantes(executantes)
                    st.success(f"Executante '{selecionado}' removido com sucesso!")
                    time.sleep(1)
                    st.rerun()


def main():
    # Inicializa estados da sessão
    if 'cadastro_realizado' not in st.session_state:
        st.session_state.cadastro_realizado = False
    if 'atualizacao_realizada' not in st.session_state:
        st.session_state.atualizacao_realizada = False

    # Menu principal
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

    # Rodapé
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Sistema de Ordens de Serviço**")
    st.sidebar.markdown("Versão 2.0")
    st.sidebar.markdown("Desenvolvido por Robson Vilela")


if __name__ == "__main__":
    inicializar_arquivos()
    main()
