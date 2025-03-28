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

# Configurações do GitHub (serão carregadas do arquivo config.json)
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

def carregar_executantes():
    """Carrega a lista de executantes do arquivo"""
    if os.path.exists(EXECUTANTES_FILE):
        try:
            with open(EXECUTANTES_FILE, 'r') as f:
                return [linha.strip() for linha in f.readlines() if linha.strip()]
        except:
            return []
    return []

def salvar_executantes(executantes):
    """Salva a lista de executantes no arquivo"""
    with open(EXECUTANTES_FILE, 'w') as f:
        for nome in executantes:
            f.write(f"{nome}\n")

def fazer_backup():
    """Cria um backup dos dados atuais"""
    if os.path.exists(LOCAL_FILENAME) and os.path.getsize(LOCAL_FILENAME) > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = os.path.join(BACKUP_DIR, f"ordens_servico_{timestamp}.csv")
        shutil.copy(LOCAL_FILENAME, backup_name)
        limpar_backups_antigos(MAX_BACKUPS)
        return backup_name
    return None

def limpar_backups_antigos(max_backups):
    """Remove backups antigos mantendo apenas os mais recentes"""
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "ordens_servico_*.csv")))
    while len(backups) > max_backups:
        try:
            os.remove(backups[0])
            backups.pop(0)
        except:
            continue

def carregar_ultimo_backup():
    """Retorna o caminho do backup mais recente"""
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "ordens_servico_*.csv")))
    if backups:
        return backups[-1]
    return None

def carregar_csv():
    """Carrega os dados do CSV local"""
    try:
        df = pd.read_csv(LOCAL_FILENAME)
        # Garante que as colunas importantes são strings
        df["Executante"] = df["Executante"].astype(str)
        df["Data Conclusão"] = df["Data Conclusão"].astype(str)
        return df
    except Exception as e:
        st.error(f"Erro ao ler arquivo local: {str(e)}")
        # Tenta carregar do backup
        backup = carregar_ultimo_backup()
        if backup:
            try:
                df = pd.read_csv(backup)
                df.to_csv(LOCAL_FILENAME, index=False)  # Restaura o arquivo principal
                return df
            except:
                pass
        
        return pd.DataFrame(columns=["ID", "Descrição", "Data", "Solicitante", "Local", 
                                   "Tipo", "Status", "Executante", "Data Conclusão"])

def salvar_csv(df):
    """Salva o DataFrame no arquivo CSV local e faz backup"""
    try:
        df.to_csv(LOCAL_FILENAME, index=False)
        fazer_backup()
        
        # Se configurado, envia para o GitHub
        if GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN:
            enviar_para_github()
            
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados: {str(e)}")
        return False

# Funções principais (páginas) - Mantidas as mesmas do código anterior
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
    - 📊 **Dashboard** com análises gráficas
    - 🔐 **Supervisão** (área restrita)
    """)

    # Mostra informações de backup
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "ordens_servico_*.csv")), reverse=True)
    if backups:
        with st.expander("📁 Backups disponíveis"):
            st.write(f"Último backup: {os.path.basename(backups[0])}")
            st.write(f"Total de backups: {len(backups)}")

    # Mostra status de sincronização com GitHub
    if GITHUB_REPO:
        st.info("✅ Sincronização com GitHub ativa")
    else:
        st.warning("⚠️ Sincronização com GitHub não configurada")

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
                    global GITHUB_REPO, GITHUB_FILEPATH, GITHUB_TOKEN
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

# As demais funções (cadastrar_os, listar_os, buscar_os, dashboard, etc.) 
# permanecem exatamente como no código anterior, apenas usando LOCAL_FILENAME 
# em vez de FILENAME para os arquivos locais

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
