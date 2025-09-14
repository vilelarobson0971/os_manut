import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import os
import shutil
import time
import glob
import base64
import json

def carregar_imagem(caminho_arquivo):
    with open(caminho_arquivo, "rb") as f:
        dados = f.read()
        encoded = base64.b64encode(dados).decode()
    return f"data:image/png;base64,{encoded}"

# Configurações da página
st.set_page_config(
    page_title="Gestão de Ordens de Serviço",
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
EXECUTANTES_PREDEFINIDOS = ["Guilherme", "Ismael"]

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

def converter_arquivo_antigo(df):
    """Converte o formato antigo (com 'Executante') para o novo (com 'Executante1' e 'Executante2')"""
    if 'Executante' in df.columns and 'Executante1' not in df.columns:
        df['Executante1'] = df['Executante']
        df['Executante2'] = ""
        df['Observações'] = ""  # Adiciona coluna de observações se não existir
        df.drop('Executante', axis=1, inplace=True)
    if 'Observações' not in df.columns:  # Garante que a coluna existe
        df['Observações'] = ""
    return df

def inicializar_arquivos():
    """Garante que todos os arquivos necessários existam e estejam válidos"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    carregar_config()
    
    usar_github = GITHUB_AVAILABLE and GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN
    
    if not os.path.exists(LOCAL_FILENAME) or os.path.getsize(LOCAL_FILENAME) == 0:
        if usar_github:
            baixar_do_github()
        else:
            df = pd.DataFrame(columns=["ID", "Descrição", "Data", "Hora Abertura", "Solicitante", "Local", 
                                     "Tipo", "Status", "Data Conclusão", "Hora Conclusão", "Executante1", "Executante2", "Urgente", "Observações"])
            df.to_csv(LOCAL_FILENAME, index=False)

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
        file_content = contents.decoded_content.decode('utf-8')
        
        with open(LOCAL_FILENAME, 'w', encoding='utf-8') as f:
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
        
        with open(LOCAL_FILENAME, 'r', encoding='utf-8') as f:
            content = f.read()
        
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
        if not os.path.exists(LOCAL_FILENAME):
            inicializar_arquivos()
            
        df = pd.read_csv(LOCAL_FILENAME)
        df = converter_arquivo_antigo(df)
        
        colunas_necessarias = ["ID", "Descrição", "Data", "Hora Abertura", "Solicitante", "Local", 
                             "Tipo", "Status", "Data Conclusão", "Hora Conclusão", "Executante1", "Executante2", "Urgente", "Observações"]
        
        for coluna in colunas_necessarias:
            if coluna not in df.columns:
                df[coluna] = ""
        
        df["Executante1"] = df["Executante1"].astype(str)
        df["Executante2"] = df["Executante2"].astype(str)
        df["Data Conclusão"] = df["Data Conclusão"].astype(str)
        df["Hora Conclusão"] = df["Hora Conclusão"].astype(str)
        df["Urgente"] = df["Urgente"].astype(str)
        df["Observações"] = df["Observações"].astype(str)
        
        return df
    except Exception as e:
        st.error(f"Erro ao ler arquivo local: {str(e)}")
        backup = carregar_ultimo_backup()
        if backup:
            try:
                df = pd.read_csv(backup)
                df = converter_arquivo_antigo(df)
                df.to_csv(LOCAL_FILENAME, index=False)
                return df
            except Exception as e:
                st.error(f"Erro ao carregar backup: {str(e)}")
        
        return pd.DataFrame(columns=["ID", "Descrição", "Data", "Hora Abertura", "Solicitante", "Local", 
                                   "Tipo", "Status", "Data Conclusão", "Hora Conclusão", "Executante1", "Executante2", "Urgente", "Observações"])

def salvar_csv(df):
    """Salva o DataFrame no arquivo CSV local e faz backup"""
    try:
        colunas_necessarias = ["ID", "Descrição", "Data", "Hora Abertura", "Solicitante", "Local", 
                             "Tipo", "Status", "Data Conclusão", "Hora Conclusão", "Executante1", "Executante2", "Urgente", "Observações"]
        
        for coluna in colunas_necessarias:
            if coluna not in df.columns:
                df[coluna] = ""
        
        df["Executante1"] = df["Executante1"].astype(str)
        df["Executante2"] = df["Executante2"].astype(str)
        df["Data Conclusão"] = df["Data Conclusão"].astype(str)
        df["Hora Conclusão"] = df["Hora Conclusão"].astype(str)
        df["Urgente"] = df["Urgente"].astype(str)
        df["Observações"] = df["Observações"].astype(str)
        
        df.to_csv(LOCAL_FILENAME, index=False, encoding='utf-8')
        fazer_backup()
        
        if GITHUB_AVAILABLE and GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN:
            enviar_para_github()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados: {str(e)}")
        return False

def pagina_inicial():
    # Carrega a imagem
    logo = carregar_imagem("logo.png")
    
    col1, col2 = st.columns([1, 15])
    with col1:
        # Substitui o emoji pela imagem
        st.markdown(f'<div style="margin-top: 10px;"><img src="{logo}" width="60"></div>', 
                   unsafe_allow_html=True)
    with col2:
        st.markdown("<h1 style='font-size: 2.5em;'>GESTÃO DE ORDENS DE SERVIÇO DE MANUTENÇÃO</h1>", 
                   unsafe_allow_html=True)

    st.markdown("<p style='text-align: center; font-size: 2.0em;'>AKR BRANDS</p>", 
               unsafe_allow_html=True)
    st.markdown("---")

    df = carregar_csv()
    if not df.empty:
        # Mostrar apenas OS com status "Pendente"
        novas_os = df[df["Status"] == "Pendente"]
        if not novas_os.empty:
            # Pegar as últimas 3 OS (ou menos se não houver 3)
            ultimas_os = novas_os.tail(3).iloc[::-1]  # Inverte para mostrar a mais recente primeiro
            
            # Container para as notificações
            with st.container():
                # Botão para limpar notificações
                if st.button("🗑️ Limpar Notificações", key="limpar_notificacoes"):
                    st.session_state.notificacoes_limpas = True
                    st.rerun()
                
                st.markdown("<style>div[data-testid='stVerticalBlock'] > div:has(>.stAlert) {margin-bottom: -1rem;}</style>", unsafe_allow_html=True)
                
                if not st.session_state.get('notificacoes_limpas', False):
                    for _, os_data in ultimas_os.iterrows():
                        if os_data.get("Urgente", "") == "Sim":
                            st.error(f"🚨 ORDEM DE SERVIÇO URGENTE: ID {os_data['ID']} - {os_data['Descrição']}")
                        else:
                            st.warning(f"⚠️ NOVA ORDEM DE SERVIÇO ABERTA: ID {os_data['ID']} - {os_data['Descrição']}")
                else:
                    st.info("Notificações limpas")
                    if st.button("Mostrar Notificações"):
                        st.session_state.notificacoes_limpas = False
                        st.rerun()
            st.markdown("---")

    st.markdown("""
    ### Bem-vindo ao Sistema de Gestão de Ordens de Serviço
    **Funcionalidades disponíveis:**
    - 📝 **Cadastro** de novas ordens de serviço
    - 🔍 **Busca** avançada por diversos critérios
    - 📊 **Dashboard** com análises gráficas
    - 🔐 **Supervisão** (área restrita)
    """)

    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "ordens_servico_*.csv")), reverse=True)
    if backups:
        with st.expander("📁 Backups disponíveis"):
            st.write(f"Último backup: {os.path.basename(backups[0])}")
            st.write(f"Total de backups: {len(backups)}")

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
        urgente = st.checkbox("Urgente")

        submitted = st.form_submit_button("Cadastrar OS")
        if submitted:
            if not descricao or not solicitante or not local:
                st.error("Preencha todos os campos obrigatórios (*)")
            else:
                df = carregar_csv()
                novo_id = int(df["ID"].max()) + 1 if not df.empty and not pd.isna(df["ID"].max()) else 1
                data_hora_utc = datetime.utcnow()
                data_hora_local = data_hora_utc - timedelta(hours=3)
                data_abertura = data_hora_local.strftime("%d/%m/%Y")
                hora_abertura = data_hora_local.strftime("%H:%M")
                
                nova_os = pd.DataFrame([{
                    "ID": novo_id,
                    "Descrição": descricao,
                    "Data": data_abertura,
                    "Hora Abertura": hora_abertura,
                    "Solicitante": solicitante,
                    "Local": local,
                    "Tipo": "",
                    "Status": "Pendente",
                    "Data Conclusão": "",
                    "Hora Conclusão": "",
                    "Executante1": "",
                    "Executante2": "",
                    "Urgente": "Sim" if urgente else "Não",
                    "Observações": ""
                }])

                df = pd.concat([df, nova_os], ignore_index=True)
                if salvar_csv(df):
                    st.success("Ordem cadastrada com sucesso! Backup automático realizado.")
                    time.sleep(1)
                    st.rerun()

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
                              ["Status", "ID", "Solicitante", "Local", "Tipo", "Executante1", "Executante2", "Observações"])
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
continue ate a ultima linha
text
    st.warning("Nenhuma OS encontrada com os critérios informados.")
def dashboard():
st.header("📊 Dashboard Analítico")
df = carregar_csv()

text
if df.empty:
    st.warning("Nenhuma OS cadastrada para análise.")
    return

tab1, tab2, tab3 = st.tabs(["🔧 Tipos", "👥 Executantes", "📈 Status"])

with tab1:
    st.subheader("Distribuição por Tipo de Manutenção")
    tipo_counts = df["Tipo"].value_counts()
    
    if not tipo_counts.empty:
        fig, ax = plt.subplots(figsize=(3, 2))
        
        wedges, texts, autotexts = ax.pie(
            tipo_counts.values,
            labels=None,
            autopct='%1.1f%%',
            startangle=90,
            wedgeprops=dict(width=0.4),
            textprops={'fontsize': 4, 'color': 'black'}
        )
        
        centre_circle = plt.Circle((0,0), 0.70, fc='white')
        ax.add_artist(centre_circle)
        
        ax.legend(
            wedges,
            tipo_counts.index,
            title="Tipos",
            loc="lower right",
            bbox_to_anchor=(1.5, 0),
            prop={'size': 4},
            title_fontsize='6'
        )
        
        ax.set_title("Distribuição por Tipo", fontsize=10)
        st.pyplot(fig, bbox_inches='tight')
    else:
        st.warning("Nenhum dado de tipo disponível")

with tab2:
    st.subheader("OS por Executantes")
    
    # Adicionando filtro por período
    col1, col2 = st.columns(2)
    with col1:
        periodo = st.selectbox("Período", ["Todos", "Por Mês/Ano"])
    
    df_filtrado = df.copy()
    
    if periodo == "Por Mês/Ano":
        with col2:
            # Converter a coluna Data Conclusão para datetime
            df_filtrado['Data Conclusão'] = pd.to_datetime(df_filtrado['Data Conclusão'], dayfirst=True, errors='coerce')
            
            # Filtrar apenas OS concluídas
            df_filtrado = df_filtrado[df_filtrado['Status'] == 'Concluído']
            
            # Criar listas de meses e anos disponíveis
            meses = list(range(1, 13))
            anos = list(range(2024, 2031))  # De 2024 até 2030
            
            mes_selecionado = st.selectbox("Mês", meses, format_func=lambda x: f"{x:02d}")
            ano_selecionado = st.selectbox("Ano", anos)
            
            # Filtrar os dados pela data de conclusão
            df_filtrado = df_filtrado[
                (df_filtrado['Data Conclusão'].dt.month == mes_selecionado) & 
                (df_filtrado['Data Conclusão'].dt.year == ano_selecionado)
            ]
    else:
        # Filtrar apenas OS concluídas quando selecionado "Todos"
        df_filtrado = df_filtrado[df_filtrado['Status'] == 'Concluído']
    
    # Concatenar executantes e filtrar valores inválidos
    executantes = pd.concat([df_filtrado["Executante1"], df_filtrado["Executante2"]])
    executantes = executantes[~executantes.isin(['', 'nan'])]
    
    if not executantes.empty:
        executante_counts = executantes.value_counts()
        
        fig, ax = plt.subplots(figsize=(3, 2))
        
        wedges, texts, autotexts = ax.pie(
            executante_counts.values,
            labels=None,
            autopct='%1.1f%%',
            startangle=90,
            wedgeprops=dict(width=0.4),
            textprops={'fontsize': 4, 'color': 'black'}
        )
        
        centre_circle = plt.Circle((0,0), 0.70, fc='white')
        ax.add_artist(centre_circle)
        
        ax.legend(
            wedges,
            executante_counts.index,
            title="Executantes",
            loc="lower right",
            bbox_to_anchor=(1.5, 0),
            prop={'size': 4},
            title_fontsize='6'
        )
        
        ax.set_title("OS por Executantes", fontsize=10)
        st.pyplot(fig, bbox_inches='tight')
    else:
        st.warning("Nenhuma OS concluída encontrada para o período selecionado")

with tab3:
    st.subheader("Distribuição por Status")
    status_counts = df["Status"].value_counts()
    
    if not status_counts.empty:
        fig, ax = plt.subplots(figsize=(3, 2))
        
        bars = ax.bar(
            status_counts.index,
            status_counts.values,
            color=sns.color_palette("pastel")
        )
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height}',
                    ha='center', va='bottom',
                    fontsize=4)
        
        ax.set_title("Distribuição por Status", fontsize=10)
        plt.xticks(rotation=45, fontsize=6)
        st.pyplot(fig, bbox_inches='tight')
    else:
        st.warning("Nenhum dado de status disponível")
def pagina_supervisao():
st.header("🔐 Área de Supervisão")

text
if not st.session_state.get('autenticado', False):
    senha = st.text_input("Digite a senha de supervisão:", type="password")
    if senha == SENHA_SUPERVISAO:
        st.session_state.autenticado = True
        st.rerun()
    elif senha:
        st.error("Senha incorreta!")
    return

st.success("Acesso autorizado à área de supervisão")

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

text
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

        executante1_atual = str(os_data["Executante1"]) if pd.notna(os_data["Executante1"]) else ""
        try:
            index_executante1 = EXECUTANTES_PREDEFINIDOS.index(executante1_atual)
        except ValueError:
            index_executante1 = 0

        executante1 = st.selectbox(
            "Executante Principal*",
            EXECUTANTES_PREDEFINIDOS,
            index=index_executante1
        )

    with col2:
        executante2_atual = str(os_data["Executante2"]) if pd.notna(os_data["Executante2"]) else ""
        try:
            index_executante2 = EXECUTANTES_PREDEFINIDOS.index(executante2_atual) + 1
        except ValueError:
            index_executante2 = 0

        executante2 = st.selectbox(
            "Executante Secundário (opcional)",
            [""] + EXECUTANTES_PREDEFINIDOS,
            index=index_executante2
        )

        if novo_status == "Concluído":
            data_hora_utc = datetime.utcnow()
            data_hora_local = data_hora_utc - timedelta(hours=3)
            data_atual = data_hora_local.strftime("%d/%m/%Y")
            hora_atual = data_hora_local.strftime("%H:%M")
            
            data_conclusao = data_atual
            hora_conclusao = hora_atual
            
            st.text_input(
                "Data de conclusão",
                value=data_atual,
                disabled=True
            )
            st.text_input(
                "Hora de conclusão",
                value=hora_atual,
                disabled=True
            )
        else:
            data_conclusao = ""
            hora_conclusao = ""

    observacoes = st.text_area("Observações", value=os_data.get("Observações", ""))

    submitted = st.form_submit_button("Atualizar OS")

    if submitted:
        if novo_status in ["Em execução", "Concluído"] and not executante1:
            st.error("Selecione pelo menos um executante principal para este status!")
        else:
            df.loc[df["ID"] == os_id, "Status"] = novo_status
            df.loc[df["ID"] == os_id, "Executante1"] = executante1
            df.loc[df["ID"] == os_id, "Executante2"] = executante2 if executante2 != "" else ""
            df.loc[df["ID"] == os_id, "Tipo"] = tipo
            df.loc[df["ID"] == os_id, "Observações"] = observacoes
            
            if novo_status == "Concluído":
                df.loc[df["ID"] == os_id, "Data Conclusão"] = data_conclusao
                df.loc[df["ID"] == os_id, "Hora Conclusão"] = hora_conclusao
            else:
                df.loc[df["ID"] == os_id, "Data Conclusão"] = ""
                df.loc[df["ID"] == os_id, "Hora Conclusão"] = ""
            
            if salvar_csv(df):
                st.success("OS atualizada com sucesso! Backup automático realizado.")
                time.sleep(1)
                st.rerun()
def gerenciar_backups():
st.header("💾 Gerenciamento de Backups")
backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "ordens_servico_*.csv")), reverse=True)

text
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

text
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
                g = Github(token)
                g.get_repo(repo).get_contents(filepath)
                
                config = {
                    'github_repo': repo,
                    'github_filepath': filepath,
                    'github_token': token
                }
                
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(config, f)
                
                GITHUB_REPO = repo
                GITHUB_FILEPATH = filepath
                GITHUB_TOKEN = token
                
                st.success("Configurações salvas e validadas com sucesso!")
                
                if baixar_do_github():
                    st.success("Dados sincronizados do GitHub!")
                else:
                    st.warning("Configurações salvas, mas não foi possível sincronizar com o GitHub")
                    
            except Exception as e:
                st.error(f"Credenciais inválidas ou sem permissão: {str(e)}")
        else:
            st.error("Preencha todos os campos para ativar a sincronização com GitHub")
def main():
if 'notificacoes_limpas' not in st.session_state:
st.session_state.notificacoes_limpas = False

text
inicializar_arquivos()

# Adiciona o JavaScript para recarregar a página a cada 10 minutos (600000 milissegundos)
st.markdown("""
<script>
function checkReload() {
    // Verifica se estamos na página principal (não na área de supervisão)
    if (!window.location.href.includes('Supervis%C3%A3o')) {
        setTimeout(function() {
            window.location.reload();
        }, 600000); // 10 minutos = 600000 ms
    }
}
window.onload = checkReload;
</script>
""", unsafe_allow_html=True)

st.sidebar.title("Menu")
opcao = st.sidebar.selectbox(
    "Selecione",
    [
        "🏠 Página Inicial",
        "📝 Cadastrar OS",
        "🔍 Buscar OS",
        "📊 Dashboard",
        "🔐 Supervisão"
    ]
)

if opcao == "🏠 Página Inicial":
    pagina_inicial()
elif opcao == "📝 Cadastrar OS":
    cadastrar_os()
elif opcao == "🔍 Buscar OS":
    buscar_os()
elif opcao == "📊 Dashboard":
    dashboard()
elif opcao == "🔐 Supervisão":
    pagina_supervisao()

st.sidebar.markdown("---")
st.sidebar.markdown("**Sistema de Gestão de Ordens de Serviço**")
st.sidebar.markdown("Versão 2.5 com Múltiplos Executantes")
st.sidebar.markdown("Desenvolvedor Robson Vilela")
st.sidebar.markdown("Todos os Direitos Reservados")
st.sidebar.markdown("2025")
if name == "main":
main()

text
