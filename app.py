import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import shutil
import time
import glob
import requests
from github import Github
import base64
import json

# Configurações da página
st.set_page_config(
    page_title="Sistema de Ordens de Serviço",
    page_icon="🔧",
    layout="wide"
)

# Constantes
LOCAL_FILENAME = "ordens_servico.csv"
BACKUP_DIR = "backups"
EXECUTANTES_FILE = "executantes.txt"
MAX_BACKUPS = 10
SENHA_SUPERVISAO = "king@2025"
CONFIG_FILE = "config.json"

# Variáveis globais para configuração do GitHub
GITHUB_REPO = None
GITHUB_FILEPATH = None
GITHUB_TOKEN = None

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
def carregar_config():
    """Carrega as configurações do GitHub do arquivo config.json"""
    global GITHUB_REPO, GITHUB_FILEPATH, GITHUB_TOKEN
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                GITHUB_REPO = config.get('github_repo')
                GITHUB_FILEPATH = config.get('github_filepath')
                GITHUB_TOKEN = config.get('github_token')
    except Exception as e:
        st.error(f"Erro ao carregar configurações: {str(e)}")

def inicializar_arquivos():
    """Garante que todos os arquivos necessários existam e estejam válidos"""
    # Criar diretório de backups se não existir
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Carregar configurações do GitHub
    carregar_config()
    
    # Verificar se temos configuração do GitHub
    usar_github = GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN
    
    # Inicializar arquivo de ordens de serviço
    if not os.path.exists(LOCAL_FILENAME) or os.path.getsize(LOCAL_FILENAME) == 0:
        if usar_github:
            baixar_do_github()
        else:
            pd.DataFrame(columns=["ID", "Descrição", "Data", "Solicitante", "Local", 
                                "Tipo", "Status", "Executante", "Data Conclusão"]).to_csv(LOCAL_FILENAME, index=False)
    
    # Inicializar arquivo de executantes
    if not os.path.exists(EXECUTANTES_FILE):
        with open(EXECUTANTES_FILE, 'w') as f:
            f.write("")

def baixar_do_github():
    """Baixa o arquivo do GitHub se estiver mais atualizado"""
    global GITHUB_REPO, GITHUB_FILEPATH, GITHUB_TOKEN
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        contents = repo.get_contents(GITHUB_FILEPATH)
        
        # Decodificar conteúdo
        file_content = contents.decoded_content.decode('utf-8')
        
        # Salvar localmente
        with open(LOCAL_FILENAME, 'w') as f:
            f.write(file_content)
            
        return True
    except Exception as e:
        st.error(f"Erro ao baixar do GitHub: {str(e)}")
        return False

def enviar_para_github():
    """Envia o arquivo local para o GitHub"""
    global GITHUB_REPO, GITHUB_FILEPATH, GITHUB_TOKEN
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        
        with open(LOCAL_FILENAME, 'r') as f:
            content = f.read()
        
        # Verifica se o arquivo já existe no GitHub
        try:
            contents = repo.get_contents(GITHUB_FILEPATH)
            repo.update_file(contents.path, "Atualização automática do sistema de OS", content, contents.sha)
        except:
            repo.create_file(GITHUB_FILEPATH, "Criação inicial do arquivo de OS", content)
            
        return True
    except Exception as e:
        st.error(f"Erro ao enviar para GitHub: {str(e)}")
        return False

# ... (mantenha as outras funções auxiliares como carregar_executantes, salvar_executantes, etc.)

def pagina_supervisao():
    st.header("🔐 Área de Supervisão")
    
    # Verifica se o usuário já está autenticado
    if not st.session_state.get('autenticado', False):
        senha = st.text_input("Digite a senha de supervisão:", type="password")
        if senha == SENHA_SUPERVISAO:
            st.session_state.autenticado = True
            st.rerun()
        elif senha:  # Só mostra erro se o usuário tentou digitar algo
            st.error("Senha incorreta!")
        return
    
    # Se chegou aqui, está autenticado
    st.success("Acesso autorizado à área de supervisão")
    
    # Menu interno da supervisão
    opcao_supervisao = st.selectbox(
        "Selecione a função de supervisão:",
        [
            "🔄 Atualizar OS",
            "👷 Gerenciar Executantes",
            "💾 Gerenciar Backups",
            "⚙️ Configurar GitHub"
        ]
    )
    
    if opcao_supervisao == "🔄 Atualizar OS":
        atualizar_os()
    elif opcao_supervisao == "👷 Gerenciar Executantes":
        gerenciar_executantes()
    elif opcao_supervisao == "💾 Gerenciar Backups":
        gerenciar_backups()
    elif opcao_supervisao == "⚙️ Configurar GitHub":
        configurar_github()

def configurar_github():
    st.header("⚙️ Configuração do GitHub")
    global GITHUB_REPO, GITHUB_FILEPATH, GITHUB_TOKEN
    
    with st.form("github_config_form"):
        repo = st.text_input("Repositório GitHub (user/repo)", value=GITHUB_REPO or "")
        filepath = st.text_input("Caminho do arquivo no repositório", value=GITHUB_FILEPATH or "")
        token = st.text_input("Token de acesso GitHub", type="password", value=GITHUB_TOKEN or "")
        
        submitted = st.form_submit_button("Salvar Configurações")
        
        if submitted:
            if repo and filepath and token:
                try:
                    config = {
                        'github_repo': repo,
                        'github_filepath': filepath,
                        'github_token': token
                    }
                    
                    with open(CONFIG_FILE, 'w') as f:
                        json.dump(config, f)
                    
                    # Atualiza variáveis globais
                    GITHUB_REPO = repo
                    GITHUB_FILEPATH = filepath
                    GITHUB_TOKEN = token
                    
                    st.success("Configurações salvas com sucesso!")
                    
                    # Tenta sincronizar imediatamente
                    if baixar_do_github():
                        st.success("Dados sincronizados do GitHub!")
                    else:
                        st.warning("Configurações salvas, mas não foi possível sincronizar com o GitHub")
                        
                except Exception as e:
                    st.error(f"Erro ao salvar configurações: {str(e)}")
            else:
                st.error("Preencha todos os campos para ativar a sincronização com GitHub")

# ... (mantenha as outras funções principais como cadastrar_os, listar_os, etc.)

def main():
    # Inicializa arquivos e verifica consistência
    inicializar_arquivos()
    
    # Menu principal
    st.sidebar.title("Menu")
    opcao = st.sidebar.selectbox(
        "Selecione",
        [
            "🏠 Página Inicial",
            "📝 Cadastrar OS",
            "📋 Listar OS",
            "🔍 Buscar OS",
            "📊 Dashboard",
            "🔐 Supervisão"
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
    elif opcao == "📊 Dashboard":
        dashboard()
    elif opcao == "🔐 Supervisão":
        pagina_supervisao()

    # Rodapé
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Sistema de Ordens de Serviço**")
    st.sidebar.markdown("Versão 2.2 com Sincronização GitHub")
    st.sidebar.markdown("Desenvolvido por Robson Vilela")

if __name__ == "__main__":
    main()
