import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import shutil
import time
import glob

# Configurações da página
st.set_page_config(
    page_title="Sistema de Ordens de Serviço",
    page_icon="🔧",
    layout="wide"
)

# Constantes
FILENAME = "ordens_servico.csv"
BACKUP_DIR = "backups"
EXECUTANTES_FILE = "executantes.txt"
MAX_BACKUPS = 10

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
    os.makedirs(BACKUP_DIR, exist_ok=True)

def carregar_executantes():
    if os.path.exists(EXECUTANTES_FILE):
        with open(EXECUTANTES_FILE, 'r') as f:
            return [linha.strip() for linha in f.readlines() if linha.strip()]
    return []

def salvar_executantes(executantes):
    with open(EXECUTANTES_FILE, 'w') as f:
        for nome in executantes:
            f.write(f"{nome}\n")

def fazer_backup():
    if os.path.exists(FILENAME) and os.path.getsize(FILENAME) > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = os.path.join(BACKUP_DIR, f"ordens_servico_{timestamp}.csv")
        shutil.copy(FILENAME, backup_name)
        limpar_backups_antigos(MAX_BACKUPS)
        return backup_name
    return None

def limpar_backups_antigos(max_backups):
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "ordens_servico_*.csv")))
    while len(backups) > max_backups:
        os.remove(backups[0])
        backups.pop(0)

def carregar_ultimo_backup():
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "ordens_servico_*.csv")))
    if backups:
        return backups[-1]
    return None

def carregar_csv():
    # Tenta carregar o arquivo principal
    if os.path.exists(FILENAME) and os.path.getsize(FILENAME) > 0:
        try:
            df = pd.read_csv(FILENAME)
            df["Executante"] = df["Executante"].astype(str)
            df["Data Conclusão"] = df["Data Conclusão"].astype(str)
            return df
        except:
            pass
    
    # Se falhar, tenta carregar do backup
    backup = carregar_ultimo_backup()
    if backup:
        try:
            df = pd.read_csv(backup)
            df.to_csv(FILENAME, index=False)  # Restaura o arquivo principal
            return df
        except:
            pass
    
    return pd.DataFrame(columns=["ID", "Descrição", "Data", "Solicitante", "Local", 
                               "Tipo", "Status", "Executante", "Data Conclusão"])

def formatar_data(data):
    try:
        if len(data) == 8 and data.isdigit():
            return datetime.strptime(data, "%d%m%Y").strftime("%d/%m/%Y")
        return datetime.strptime(data, "%d/%m/%Y").strftime("%d/%m/%Y")
    except ValueError:
        st.error("Data inválida! Use o formato DD/MM/AAAA.")
        return None

# Funções principais (mantidas as mesmas, exceto pela adição de backup após operações críticas)
def pagina_inicial():
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
    - 💾 **Backup automático** dos dados
    """)

    # Mostra informações de backup
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "ordens_servico_*.csv")), reverse=True)
    if backups:
        with st.expander("📁 Backups disponíveis"):
            st.write(f"Último backup: {os.path.basename(backups[0])}")
            st.write(f"Total de backups: {len(backups)}")

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
                fazer_backup()
                st.success("Ordem cadastrada com sucesso! Backup automático realizado.")
                time.sleep(1)
                st.rerun()

# [...] (As outras funções principais permanecem iguais, exceto por adicionar fazer_backup() após operações de escrita)

def main():
    # Inicializa estados da sessão
    if 'cadastro_realizado' not in st.session_state:
        st.session_state.cadastro_realizado = False
    if 'atualizacao_realizada' not in st.session_state:
        st.session_state.atualizacao_realizada = False

    # Menu principal com opção de backup
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
            "💾 Gerenciar Backups"
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
    elif opcao == "💾 Gerenciar Backups":
        gerenciar_backups()

    # Rodapé
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Sistema de Ordens de Serviço**")
    st.sidebar.markdown("Versão 2.1 com Backup")
    st.sidebar.markdown("Desenvolvido por Robson Vilela")

def gerenciar_backups():
    st.header("💾 Gerenciamento de Backups")
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "ordens_servico_*.csv")), reverse=True)
    
    if not backups:
        st.warning("Nenhum backup disponível")
        return
    
    st.write(f"Total de backups: {len(backups)}")
    st.write(f"Último backup: {os.path.basename(backups[0])}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Criar Backup Agora"):
            backup_path = fazer_backup()
            if backup_path:
                st.success(f"Backup criado: {os.path.basename(backup_path)}")
            else:
                st.error("Falha ao criar backup")
    
    with col2:
        if st.button("🧹 Limpar Backups Antigos"):
            limpar_backups_antigos(MAX_BACKUPS)
            st.success(f"Mantidos apenas os {MAX_BACKUPS} backups mais recentes")
    
    st.markdown("---")
    st.subheader("Restaurar Backup")
    
    backup_selecionado = st.selectbox(
        "Selecione um backup para restaurar",
        [os.path.basename(b) for b in backups]
    )
    
    if st.button("🔙 Restaurar Backup Selecionado"):
        backup_fullpath = os.path.join(BACKUP_DIR, backup_selecionado)
        try:
            shutil.copy(backup_fullpath, FILENAME)
            st.success(f"Dados restaurados do backup: {backup_selecionado}")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao restaurar: {str(e)}")

if __name__ == "__main__":
    # Inicializa sistema de arquivos
    inicializar_arquivos()
    
    # Verifica se precisa restaurar backup
    if not os.path.exists(FILENAME) or os.path.getsize(FILENAME) == 0:
        backup = carregar_ultimo_backup()
        if backup:
            shutil.copy(backup, FILENAME)
    
    # Cria backup inicial
    fazer_backup()
    
    # Inicia aplicação
    main()
