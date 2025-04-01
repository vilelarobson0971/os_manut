import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import shutil
import time
import glob
import base64
import json

# Configurações da página
st.set_page_config(
    page_title="Sistema de Ordens de Serviço",
    page_icon="🔧",
    layout="wide"
)

# Tenta importar o PyGithub com fallback
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    st.warning("Funcionalidade do GitHub não disponível (PyGithub não instalado)")

# Constantes
LOCAL_FILENAME = "ordens_servico.csv"
BACKUP_DIR = "backups"
MAX_BACKUPS = 10
SENHA_SUPERVISAO = "king@2025"
CONFIG_FILE = "config.json"

# Executantes pré-definidos
EXECUTANTES_PREDEFINIDOS = ["Robson", "Guilherme", "Paulinho"]

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
    
    # Verificar se temos configuração do GitHub e se o módulo está disponível
    usar_github = GITHUB_AVAILABLE and GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN
    
    # Inicializar arquivo de ordens de serviço
    if not os.path.exists(LOCAL_FILENAME) or os.path.getsize(LOCAL_FILENAME) == 0:
        if usar_github:
            baixar_do_github()
        else:
            pd.DataFrame(columns=["ID", "Descrição", "Data", "Solicitante", "Local", 
                                "Tipo", "Status", "Executante", "Data Conclusão"]).to_csv(LOCAL_FILENAME, index=False)

def baixar_do_github():
    """Baixa o arquivo do GitHub se estiver mais atualizado"""
    if not GITHUB_AVAILABLE:
        st.error("Funcionalidade do GitHub não está disponível")
        return False
    
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
    if not GITHUB_AVAILABLE:
        st.error("Funcionalidade do GitHub não disponível")
        return False
    
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
        # Garante que os campos importantes são strings
        df["Executante"] = df["Executante"].astype(str)
        df["Data Conclusão"] = df["Data Conclusão"].astype(str)
        
        df.to_csv(LOCAL_FILENAME, index=False)
        fazer_backup()
        
        # Se configurado, envia para o GitHub
        if GITHUB_AVAILABLE and GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN:
            enviar_para_github()
            
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados: {str(e)}")
        return False

# Funções de página
def pagina_inicial():
    col1, col2 = st.columns([1, 15])
    with col1:
        st.markdown('<div style="font-size: 2.5em; margin-top: 10px;">🔧</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("<h1 style='font-size: 2.5em;'>SISTEMA DE GESTÃO DE ORDENS DE SERVIÇO</h1>", unsafe_allow_html=True)

    st.markdown("<p style='text-align: center; font-size: 1.2em;'>King & Joe</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Verifica se há novas OS pendentes para notificação
    df = carregar_csv()
    if not df.empty:
        novas_os = df[df["Status"] == "Pendente"]
        if not novas_os.empty:
            ultima_os = novas_os.iloc[-1]
            # Usamos o ID da última OS como chave para a notificação
            notificacao_key = f"notificacao_vista_{ultima_os['ID']}"
            
            if not st.session_state.get(notificacao_key, False):
                with st.container():
                    st.warning(f"⚠️ NOVA ORDEM DE SERVIÇO ABERTA: ID {ultima_os['ID']} - {ultima_os['Descrição']}")
                    if st.button("✅ Confirmar recebimento da notificação"):
                        st.session_state[notificacao_key] = True
                        st.experimental_rerun()
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
    if GITHUB_AVAILABLE and GITHUB_REPO:
        st.info("✅ Sincronização com GitHub ativa")
    elif GITHUB_AVAILABLE:
        st.warning("⚠️ Sincronização com GitHub não configurada")
    else:
        st.warning("⚠️ Funcionalidade GitHub não disponível (PyGithub não instalado)")

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
                if salvar_csv(df):
                    st.success("Ordem cadastrada com sucesso! Backup automático realizado.")
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
                              ["Status", "ID", "Solicitante", "Local", "Tipo", "Executante"])
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

def dashboard():
    st.header("📊 Dashboard Analítico")
    df = carregar_csv()

    if df.empty:
        st.warning("Nenhuma OS cadastrada para análise.")
        return

    tab1, tab2, tab3 = st.tabs(["🔧 Tipos", "👥 Executantes", "📈 Status"])

    with tab1:
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
            
            ax.set_xlabel('')
            ax.set_xticks([])
            
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

    with tab2:
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
            
            ax.set_xlabel('')
            ax.set_xticks([])
            
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

    with tab3:
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
            
            ax.set_xlabel('')
            ax.set_xticks([])
            
            for bar in bars.patches:
                width = bar.get_width()
                ax.text(width - 0.3 * width,
                        bar.get_y() + bar.get_height()/2,
                        f'{int(width)}',
                        va='center',
                        ha='right',
                        color='red',
                        fontsize=8)
            
            plt.ylabel("Status", fontsize=9)
            ax.set_yticklabels(ax.get_yticklabels(), fontsize=8)
            ax.set_title("Distribuição por Status", fontsize=10)
            st.pyplot(fig)
        else:
            st.warning("Nenhum dado de status disponível")

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
            "💾 Gerenciar Backups",
            "⚙️ Configurar GitHub"
        ]
    )
    
    if opcao_supervisao == "🔄 Atualizar OS":
        atualizar_os()
    elif opcao_supervisao == "💾 Gerenciar Backups":
        gerenciar_backups()
    elif opcao_supervisao == "⚙️ Configurar GitHub":
        configurar_github()

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
        st.write(f"**Local:** {os_data['Local']}")

        col1, col2 = st.columns(2)
        with col1:
            # Campo para selecionar o tipo de serviço
            tipo_atual = str(os_data["Tipo"]) if pd.notna(os_data["Tipo"]) else ""
            tipo = st.selectbox(
                "Tipo de Serviço",
                [""] + list(TIPOS_MANUTENCAO.values()),
                index=0 if tipo_atual == "" else list(TIPOS_MANUTENCAO.values()).index(tipo_atual)
            )

            novo_status = st.selectbox(
                "Status*",
                list(STATUS_OPCOES.values()),
                index=list(STATUS_OPCOES.values()).index(os_data["Status"])
            )

            # Verifica se o executante atual está na lista de pré-definidos
            executante_atual = str(os_data["Executante"]) if pd.notna(os_data["Executante"]) else ""
            try:
                index_executante = EXECUTANTES_PREDEFINIDOS.index(executante_atual)
            except ValueError:
                index_executante = 0

            executante = st.selectbox(
                "Executante*",
                EXECUTANTES_PREDEFINIDOS,
                index=index_executante
            )

        with col2:
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
                # Atualiza todos os campos relevantes
                df.loc[df["ID"] == os_id, "Status"] = novo_status
                df.loc[df["ID"] == os_id, "Executante"] = executante
                df.loc[df["ID"] == os_id, "Tipo"] = tipo
                
                if novo_status == "Concluído":
                    df.loc[df["ID"] == os_id, "Data Conclusão"] = data_conclusao
                
                if salvar_csv(df):
                    st.success("OS atualizada com sucesso! Backup automático realizado.")
                    time.sleep(1)
                    st.rerun()

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
                time.sleep(1)
                st.rerun()
            else:
                st.error("Falha ao criar backup")
    
    with col2:
        if st.button("🧹 Limpar Backups Antigos"):
            limpar_backups_antigos(MAX_BACKUPS)
            st.success(f"Mantidos apenas os {MAX_BACKUPS} backups mais recentes")
            time.sleep(1)
            st.rerun()
    
    st.markdown("---")
    st.subheader("Restaurar Backup")
    
    backup_selecionado = st.selectbox(
        "Selecione um backup para restaurar",
        [os.path.basename(b) for b in backups]
    )
    
    if st.button("🔙 Restaurar Backup Selecionado"):
        backup_fullpath = os.path.join(BACKUP_DIR, backup_selecionado)
        try:
            shutil.copy(backup_fullpath, LOCAL_FILENAME)
            st.success(f"Dados restaurados do backup: {backup_selecionado}")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao restaurar: {str(e)}")

def configurar_github():
    st.header("⚙️ Configuração do GitHub")
    global GITHUB_REPO, GITHUB_FILEPATH, GITHUB_TOKEN
    
    if not GITHUB_AVAILABLE:
        st.error("""Funcionalidade do GitHub não está disponível. 
                Para ativar, instale o pacote PyGithub com: 
                `pip install PyGithub`""")
        return
    
    with st.form("github_config_form"):
        repo = st.text_input("Repositório GitHub (user/repo)", value=GITHUB_REPO or "vilelarobson0971/os_manut")
        filepath = st.text_input("Caminho do arquivo no repositório", value=GITHUB_FILEPATH or "ordens_servico.csv")
        token = st.text_input("Token de acesso GitHub", type="password", value=GITHUB_TOKEN or "")
        
        submitted = st.form_submit_button("Salvar Configurações")
        
        if submitted:
            if repo and filepath and token:
                try:
                    # Testa as credenciais antes de salvar
                    g = Github(token)
                    g.get_repo(repo).get_contents(filepath)
                    
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
                    
                    st.success("Configurações salvas e validadas com sucesso!")
                    
                    # Tenta sincronizar imediatamente
                    if baixar_do_github():
                        st.success("Dados sincronizados do GitHub!")
                    else:
                        st.warning("Configurações salvas, mas não foi possível sincronizar com o GitHub")
                        
                except Exception as e:
                    st.error(f"Credenciais inválidas ou sem permissão: {str(e)}")
            else:
                st.error("Preencha todos os campos para ativar a sincronização com GitHub")

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
    st.sidebar.markdown("Versão 2.4 com Validação de Credenciais")
    st.sidebar.markdown("Desenvolvido por Robson Vilela")

if __name__ == "__main__":
    main()
