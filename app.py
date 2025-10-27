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
import hashlib
from typing import Optional, Tuple, Dict
from functools import lru_cache

# ==================== CONFIGURAÇÕES ====================
class Config:
    """Classe para centralizar todas as configurações do sistema"""
    LOCAL_FILENAME = "ordens_servico.csv"
    BACKUP_DIR = "backups"
    MAX_BACKUPS = 10
    CONFIG_FILE = "config.json"
    LOGO_FILE = "logo.png"
    
    # Configurações de senha (usar hash em produção)
    SENHA_HASH = hashlib.sha256("king@2025".encode()).hexdigest()
    
    # Executantes
    EXECUTANTES_PREDEFINIDOS = ["Guilherme", "Ismael"]
    
    # Tipos de manutenção
    TIPOS_MANUTENCAO = {
        1: "Elétrica",
        2: "Mecânica",
        3: "Refrigeração",
        4: "Hidráulica",
        5: "Civil",
        6: "Instalação"
    }
    
    # Status
    STATUS_OPCOES = {
        1: "Pendente",
        2: "Pausado",
        3: "Em execução",
        4: "Concluído"
    }
    
    # Colunas necessárias
    COLUNAS_NECESSARIAS = [
        "ID", "Descrição", "Data", "Hora Abertura", "Solicitante", 
        "Local", "Tipo", "Status", "Data Conclusão", "Hora Conclusão", 
        "Executante1", "Executante2", "Urgente", "Observações"
    ]

# ==================== UTILIDADES ====================
class Utils:
    """Classe com funções utilitárias"""
    
    @staticmethod
    def carregar_imagem(caminho_arquivo: str) -> str:
        """Carrega imagem e retorna em base64"""
        try:
            if os.path.exists(caminho_arquivo):
                with open(caminho_arquivo, "rb") as f:
                    dados = f.read()
                    encoded = base64.b64encode(dados).decode()
                return f"data:image/png;base64,{encoded}"
        except Exception as e:
            st.warning(f"Erro ao carregar imagem: {str(e)}")
        return ""
    
    @staticmethod
    def obter_data_hora_local() -> Tuple[str, str]:
        """Retorna data e hora local no formato brasileiro"""
        data_hora_utc = datetime.utcnow()
        data_hora_local = data_hora_utc - timedelta(hours=3)
        return (
            data_hora_local.strftime("%d/%m/%Y"),
            data_hora_local.strftime("%H:%M")
        )
    
    @staticmethod
    def validar_senha(senha: str) -> bool:
        """Valida senha usando hash"""
        return hashlib.sha256(senha.encode()).hexdigest() == Config.SENHA_HASH

# ==================== GITHUB MANAGER ====================
class GitHubManager:
    """Gerencia operações com GitHub"""
    
    def __init__(self):
        self.repo = None
        self.filepath = None
        self.token = None
        self.available = False
        self._inicializar()
    
    def _inicializar(self):
        """Inicializa configurações do GitHub"""
        try:
            from github import Github
            self.available = True
            self._carregar_config()
        except ImportError:
            self.available = False
            st.warning("PyGithub não instalado. Sincronização GitHub desabilitada.")
    
    def _carregar_config(self):
        """Carrega configurações do arquivo JSON"""
        try:
            if os.path.exists(Config.CONFIG_FILE):
                with open(Config.CONFIG_FILE) as f:
                    config = json.load(f)
                    self.repo = config.get('github_repo')
                    self.filepath = config.get('github_filepath')
                    self.token = config.get('github_token')
        except Exception as e:
            st.error(f"Erro ao carregar configurações GitHub: {str(e)}")
    
    def salvar_config(self, repo: str, filepath: str, token: str) -> bool:
        """Salva configurações do GitHub"""
        try:
            config = {
                'github_repo': repo,
                'github_filepath': filepath,
                'github_token': token
            }
            with open(Config.CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            
            self.repo = repo
            self.filepath = filepath
            self.token = token
            return True
        except Exception as e:
            st.error(f"Erro ao salvar configurações: {str(e)}")
            return False
    
    def baixar(self) -> bool:
        """Baixa arquivo do GitHub"""
        if not self.available or not all([self.repo, self.filepath, self.token]):
            return False
        
        try:
            from github import Github
            g = Github(self.token)
            repo = g.get_repo(self.repo)
            contents = repo.get_contents(self.filepath)
            file_content = contents.decoded_content.decode('utf-8')
            
            with open(Config.LOCAL_FILENAME, 'w', encoding='utf-8') as f:
                f.write(file_content)
            return True
        except Exception as e:
            st.error(f"Erro ao baixar do GitHub: {str(e)}")
            return False
    
    def enviar(self) -> bool:
        """Envia arquivo para o GitHub"""
        if not self.available or not all([self.repo, self.filepath, self.token]):
            return False
        
        try:
            from github import Github
            g = Github(self.token)
            repo = g.get_repo(self.repo)
            
            with open(Config.LOCAL_FILENAME, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                contents = repo.get_contents(self.filepath)
                repo.update_file(
                    contents.path, 
                    "Atualização automática do sistema de OS", 
                    content, 
                    contents.sha
                )
            except:
                repo.create_file(
                    self.filepath, 
                    "Criação inicial do arquivo de OS", 
                    content
                )
            return True
        except Exception as e:
            st.error(f"Erro ao enviar para GitHub: {str(e)}")
            return False

# ==================== DATA MANAGER ====================
class DataManager:
    """Gerencia operações com dados (CSV e backups)"""
    
    def __init__(self, github_manager: GitHubManager):
        self.github = github_manager
        self._inicializar_arquivos()
    
    def _inicializar_arquivos(self):
        """Garante que arquivos necessários existam"""
        os.makedirs(Config.BACKUP_DIR, exist_ok=True)
        
        if not os.path.exists(Config.LOCAL_FILENAME) or \
           os.path.getsize(Config.LOCAL_FILENAME) == 0:
            if not self.github.baixar():
                self._criar_csv_vazio()
    
    def _criar_csv_vazio(self):
        """Cria CSV vazio com estrutura correta"""
        df = pd.DataFrame(columns=Config.COLUNAS_NECESSARIAS)
        df.to_csv(Config.LOCAL_FILENAME, index=False, encoding='utf-8')
    
    @staticmethod
    def _converter_tipos(df: pd.DataFrame) -> pd.DataFrame:
        """Converte tipos de dados das colunas"""
        colunas_str = ["Executante1", "Executante2", "Data Conclusão", 
                       "Hora Conclusão", "Urgente", "Observações"]
        for col in colunas_str:
            if col in df.columns:
                df[col] = df[col].astype(str)
        return df
    
    @staticmethod
    def _garantir_colunas(df: pd.DataFrame) -> pd.DataFrame:
        """Garante que todas as colunas necessárias existam"""
        for coluna in Config.COLUNAS_NECESSARIAS:
            if coluna not in df.columns:
                df[coluna] = ""
        return df
    
    def carregar(self) -> pd.DataFrame:
        """Carrega dados do CSV"""
        try:
            if not os.path.exists(Config.LOCAL_FILENAME):
                self._inicializar_arquivos()
            
            df = pd.read_csv(Config.LOCAL_FILENAME)
            df = self._garantir_colunas(df)
            df = self._converter_tipos(df)
            return df
            
        except Exception as e:
            st.error(f"Erro ao carregar dados: {str(e)}")
            return self._restaurar_do_backup()
    
    def _restaurar_do_backup(self) -> pd.DataFrame:
        """Tenta restaurar dados do backup mais recente"""
        backup = self._obter_ultimo_backup()
        if backup:
            try:
                df = pd.read_csv(backup)
                df = self._garantir_colunas(df)
                df = self._converter_tipos(df)
                df.to_csv(Config.LOCAL_FILENAME, index=False, encoding='utf-8')
                st.warning("Dados restaurados do backup")
                return df
            except Exception as e:
                st.error(f"Erro ao restaurar backup: {str(e)}")
        
        return pd.DataFrame(columns=Config.COLUNAS_NECESSARIAS)
    
    def salvar(self, df: pd.DataFrame) -> bool:
        """Salva DataFrame no CSV"""
        try:
            df = self._garantir_colunas(df)
            df = self._converter_tipos(df)
            df.to_csv(Config.LOCAL_FILENAME, index=False, encoding='utf-8')
            
            self._fazer_backup()
            
            if self.github.available:
                self.github.enviar()
            
            return True
        except Exception as e:
            st.error(f"Erro ao salvar dados: {str(e)}")
            return False
    
    def _fazer_backup(self):
        """Cria backup dos dados atuais"""
        if os.path.exists(Config.LOCAL_FILENAME) and \
           os.path.getsize(Config.LOCAL_FILENAME) > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = os.path.join(
                Config.BACKUP_DIR, 
                f"ordens_servico_{timestamp}.csv"
            )
            shutil.copy(Config.LOCAL_FILENAME, backup_name)
            self._limpar_backups_antigos()
    
    def _limpar_backups_antigos(self):
        """Remove backups antigos"""
        backups = sorted(glob.glob(
            os.path.join(Config.BACKUP_DIR, "ordens_servico_*.csv")
        ))
        while len(backups) > Config.MAX_BACKUPS:
            try:
                os.remove(backups[0])
                backups.pop(0)
            except:
                continue
    
    def _obter_ultimo_backup(self) -> Optional[str]:
        """Retorna caminho do backup mais recente"""
        backups = sorted(glob.glob(
            os.path.join(Config.BACKUP_DIR, "ordens_servico_*.csv")
        ))
        return backups[-1] if backups else None
    
    def listar_backups(self) -> list:
        """Lista todos os backups disponíveis"""
        return sorted(
            glob.glob(os.path.join(Config.BACKUP_DIR, "ordens_servico_*.csv")),
            reverse=True
        )
    
    def restaurar_backup(self, backup_path: str) -> bool:
        """Restaura dados de um backup específico"""
        try:
            shutil.copy(backup_path, Config.LOCAL_FILENAME)
            return True
        except Exception as e:
            st.error(f"Erro ao restaurar backup: {str(e)}")
            return False

# ==================== UI COMPONENTS ====================
class UIComponents:
    """Componentes reutilizáveis da interface"""
    
    @staticmethod
    def mostrar_header_com_logo(titulo: str):
        """Mostra header com logo"""
        logo = Utils.carregar_imagem(Config.LOGO_FILE)
        
        col1, col2 = st.columns([1, 15])
        with col1:
            if logo:
                st.markdown(
                    f'<div style="margin-top: 10px;"><img src="{logo}" width="60"></div>', 
                    unsafe_allow_html=True
                )
        with col2:
            st.markdown(
                f"<h1 style='font-size: 2.5em;'>{titulo}</h1>", 
                unsafe_allow_html=True
            )
    
    @staticmethod
    def mostrar_notificacoes(df: pd.DataFrame):
        """Mostra notificações de novas OS"""
        novas_os = df[df["Status"] == "Pendente"]
        
        if novas_os.empty:
            return
        
        ultimas_os = novas_os.tail(3).iloc[::-1]
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Limpar", key="limpar_notif"):
                st.session_state.notificacoes_limpas = True
                st.rerun()
        
        if not st.session_state.get('notificacoes_limpas', False):
            for _, os_data in ultimas_os.iterrows():
                if os_data.get("Urgente", "") == "Sim":
                    st.error(
                        f"🚨 URGENTE: OS #{os_data['ID']} - {os_data['Descrição']}"
                    )
                else:
                    st.warning(
                        f"⚠️ NOVA OS: #{os_data['ID']} - {os_data['Descrição']}"
                    )
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("✓ Notificações limpas")
            with col2:
                if st.button("🔄 Mostrar", key="mostrar_notif"):
                    st.session_state.notificacoes_limpas = False
                    st.rerun()
    
    @staticmethod
    def criar_grafico_pizza(dados, titulo: str, labels_func=None):
        """Cria gráfico de pizza padronizado e responsivo"""
        if dados.empty:
            st.warning("Nenhum dado disponível")
            return
        
        # Configurar estilo
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Usar figsize relativo (será escalado pelo Streamlit)
        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        
        # Cores modernas e profissionais
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
        
        wedges, texts, autotexts = ax.pie(
            dados.values,
            labels=None,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors[:len(dados)],
            wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2),
            textprops={'fontsize': 11, 'weight': 'bold', 'color': 'white'}
        )
        
        # Melhorar aparência dos textos de porcentagem
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')
        
        # Círculo central para efeito donut
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        ax.add_artist(centre_circle)
        
        # Legenda melhorada
        labels = dados.index if labels_func is None else labels_func(dados.index)
        legend = ax.legend(
            wedges,
            [f'{label}: {valor}' for label, valor in zip(labels, dados.values)],
            title=titulo,
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=10,
            title_fontsize=12,
            frameon=True,
            shadow=True,
            fancybox=True
        )
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_alpha(0.9)
        
        # Título centralizado
        ax.set_title(titulo, fontsize=14, weight='bold', pad=20)
        
        plt.tight_layout()
        # use_container_width=True faz o gráfico se ajustar ao contêiner
        st.pyplot(fig, use_container_width=True)
        plt.close()
    
    @staticmethod
    def criar_grafico_barras(dados, titulo: str):
        """Cria gráfico de barras padronizado e responsivo"""
        if dados.empty:
            st.warning("Nenhum dado disponível")
            return
        
        # Configurar estilo
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Usar figsize relativo (será escalado pelo Streamlit)
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
        
        # Cores gradientes modernas
        colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe']
        
        bars = ax.bar(
            range(len(dados)),
            dados.values,
            color=colors[:len(dados)],
            edgecolor='white',
            linewidth=2,
            alpha=0.85
        )
        
        # Adicionar valores nas barras com melhor formatação
        for i, (bar, valor) in enumerate(zip(bars, dados.values)):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2.,
                height,
                f'{int(valor)}',
                ha='center',
                va='bottom',
                fontsize=11,
                weight='bold',
                color='#333'
            )
            
            # Adicionar gradiente visual (simulado com borda)
            bar.set_edgecolor('#555')
            bar.set_linewidth(1.5)
        
        # Configurar eixos
        ax.set_xticks(range(len(dados)))
        ax.set_xticklabels(dados.index, rotation=45, ha='right', fontsize=10)
        ax.set_ylabel('Quantidade', fontsize=11, weight='bold')
        
        # Título
        ax.set_title(titulo, fontsize=14, weight='bold', pad=20)
        
        # Remover bordas superiores e direitas
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Grid sutil
        ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.7)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        # use_container_width=True faz o gráfico se ajustar ao contêiner
        st.pyplot(fig, use_container_width=True)
        plt.close()

# ==================== PÁGINAS ====================
class Paginas:
    """Gerencia todas as páginas do sistema"""
    
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
    
    def pagina_inicial(self):
        """Página inicial com notificações"""
        UIComponents.mostrar_header_com_logo(
            "GESTÃO DE ORDENS DE SERVIÇO DE MANUTENÇÃO"
        )
        
        st.markdown(
            "<p style='text-align: center; font-size: 2.0em;'>AKR BRANDS</p>", 
            unsafe_allow_html=True
        )
        st.markdown("---")
        
        df = self.dm.carregar()
        if not df.empty:
            UIComponents.mostrar_notificacoes(df)
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
        
        # Informações do sistema
        self._mostrar_info_sistema()
    
    def _mostrar_info_sistema(self):
        """Mostra informações sobre o sistema"""
        with st.expander("ℹ️ Informações do Sistema"):
            backups = self.dm.listar_backups()
            if backups:
                st.write(f"📁 Último backup: {os.path.basename(backups[0])}")
                st.write(f"📊 Total de backups: {len(backups)}")
            
            if self.dm.github.available and self.dm.github.repo:
                st.success("✅ Sincronização GitHub ativa")
            elif self.dm.github.available:
                st.warning("⚠️ Sincronização GitHub não configurada")
            else:
                st.info("ℹ️ GitHub não disponível")
    
    def cadastrar_os(self):
        """Página de cadastro de OS"""
        st.header("📝 Cadastrar Nova Ordem de Serviço")
        
        with st.form("cadastro_os_form", clear_on_submit=True):
            descricao = st.text_area("Descrição da atividade*", height=100)
            
            col1, col2 = st.columns(2)
            with col1:
                solicitante = st.text_input("Solicitante*")
            with col2:
                local = st.text_input("Local*")
            
            urgente = st.checkbox("⚠️ Marcar como urgente")
            
            submitted = st.form_submit_button("✅ Cadastrar OS", use_container_width=True)
            
            if submitted:
                if not all([descricao, solicitante, local]):
                    st.error("❌ Preencha todos os campos obrigatórios (*)")
                else:
                    if self._criar_nova_os(descricao, solicitante, local, urgente):
                        st.success("✅ OS cadastrada com sucesso!")
                        time.sleep(1)
                        st.rerun()
    
    def _criar_nova_os(self, descricao: str, solicitante: str, 
                       local: str, urgente: bool) -> bool:
        """Cria uma nova OS"""
        df = self.dm.carregar()
        novo_id = int(df["ID"].max()) + 1 if not df.empty else 1
        data, hora = Utils.obter_data_hora_local()
        
        nova_os = pd.DataFrame([{
            "ID": novo_id,
            "Descrição": descricao,
            "Data": data,
            "Hora Abertura": hora,
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
        return self.dm.salvar(df)
    
    def listar_os(self):
        """Página de listagem de OS"""
        st.header("📋 Listagem Completa de OS")
        
        df = self.dm.carregar()
        
        if df.empty:
            st.warning("Nenhuma ordem de serviço cadastrada.")
            return
        
        # Filtros
        with st.expander("🔍 Filtros"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filtro_status = st.selectbox(
                    "Status",
                    ["Todos"] + list(Config.STATUS_OPCOES.values())
                )
            
            with col2:
                filtro_tipo = st.selectbox(
                    "Tipo",
                    ["Todos"] + list(Config.TIPOS_MANUTENCAO.values())
                )
            
            with col3:
                filtro_urgente = st.selectbox(
                    "Urgência",
                    ["Todos", "Sim", "Não"]
                )
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if filtro_status != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Status"] == filtro_status]
        
        if filtro_tipo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Tipo"] == filtro_tipo]
        
        if filtro_urgente != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Urgente"] == filtro_urgente]
        
        # Estatísticas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total", len(df_filtrado))
        col2.metric("Pendentes", len(df_filtrado[df_filtrado["Status"] == "Pendente"]))
        col3.metric("Em Execução", len(df_filtrado[df_filtrado["Status"] == "Em execução"]))
        col4.metric("Concluídas", len(df_filtrado[df_filtrado["Status"] == "Concluído"]))
        
        # Tabela
        st.dataframe(
            df_filtrado,
            use_container_width=True,
            hide_index=True
        )
    
    def buscar_os(self):
        """Página de busca avançada"""
        st.header("🔍 Busca Avançada")
        
        df = self.dm.carregar()
        
        if df.empty:
            st.warning("Nenhuma OS cadastrada.")
            return
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            criterio = st.radio(
                "Buscar por:",
                ["Status", "ID", "Tipo", "Solicitante", "Local", 
                 "Executante1", "Executante2", "Observações"]
            )
        
        with col2:
            resultado = self._realizar_busca(df, criterio)
        
        if not resultado.empty:
            st.success(f"✅ {len(resultado)} OS encontrada(s)")
            st.dataframe(resultado, use_container_width=True, hide_index=True)
        else:
            st.warning("❌ Nenhuma OS encontrada")
    
    def _realizar_busca(self, df: pd.DataFrame, criterio: str) -> pd.DataFrame:
        """Realiza busca baseada no critério"""
        if criterio == "ID":
            busca = st.number_input("Digite o ID", min_value=1)
            return df[df["ID"] == busca]
        
        elif criterio == "Status":
            busca = st.selectbox("Selecione", list(Config.STATUS_OPCOES.values()))
            return df[df["Status"] == busca]
        
        elif criterio == "Tipo":
            busca = st.selectbox("Selecione", list(Config.TIPOS_MANUTENCAO.values()))
            return df[df["Tipo"] == busca]
        
        else:
            busca = st.text_input(f"Digite {criterio}")
            if busca:
                return df[df[criterio].astype(str).str.contains(busca, case=False, na=False)]
        
        return pd.DataFrame()
    
    def dashboard(self):
        """Página de dashboard"""
        st.header("📊 Dashboard Analítico")
        
        df = self.dm.carregar()
        
        if df.empty:
            st.warning("Nenhuma OS cadastrada.")
            return
        
        # Métricas gerais
        self._mostrar_metricas_gerais(df)
        
        st.markdown("---")
        
        # Gráficos
        tab1, tab2, tab3 = st.tabs(["📊 Status", "🔧 Tipos", "👥 Executantes"])
        
        with tab1:
            self._grafico_status(df)
        
        with tab2:
            self._grafico_tipos(df)
        
        with tab3:
            self._grafico_executantes(df)
    
    def _mostrar_metricas_gerais(self, df: pd.DataFrame):
        """Mostra métricas gerais do sistema"""
        col1, col2, col3, col4 = st.columns(4)
        
        total = len(df)
        pendentes = len(df[df["Status"] == "Pendente"])
        em_exec = len(df[df["Status"] == "Em execução"])
        concluidas = len(df[df["Status"] == "Concluído"])
        
        # Calcular porcentagem de conclusão
        perc_conclusao = (concluidas / total * 100) if total > 0 else 0
        
        col1.metric("📊 Total de OS", total)
        col2.metric("⏳ Pendentes", pendentes, delta=f"-{pendentes}" if pendentes > 0 else "0")
        col3.metric("🔧 Em Execução", em_exec, delta=f"{em_exec}" if em_exec > 0 else "0")
        col4.metric("✅ Concluídas", concluidas, delta=f"{perc_conclusao:.1f}%")
    
    def _grafico_status(self, df: pd.DataFrame):
        """Gráfico de distribuição por status"""
        st.subheader("Distribuição por Status")
        status_counts = df["Status"].value_counts()
        UIComponents.criar_grafico_barras(status_counts, "OS por Status")
    
    def _grafico_tipos(self, df: pd.DataFrame):
        """Gráfico de distribuição por tipo"""
        st.subheader("Distribuição por Tipo de Manutenção")
        tipo_counts = df[df["Tipo"] != ""]["Tipo"].value_counts()
        UIComponents.criar_grafico_pizza(tipo_counts, "Tipos de Manutenção")
    
    def _grafico_executantes(self, df: pd.DataFrame):
        """Gráfico de distribuição por executantes"""
        st.subheader("OS por Executantes")
        
        # Filtro de período
        col1, col2 = st.columns(2)
        with col1:
            periodo = st.selectbox("Período", ["Todos", "Por Mês/Ano"])
        
        df_filtrado = df[df["Status"] == "Concluído"].copy()
        
        if periodo == "Por Mês/Ano":
            df_filtrado['Data Conclusão'] = pd.to_datetime(
                df_filtrado['Data Conclusão'], 
                dayfirst=True, 
                errors='coerce'
            )
            
            with col2:
                mes = st.selectbox("Mês", list(range(1, 13)), format_func=lambda x: f"{x:02d}")
                ano = st.selectbox("Ano", list(range(2024, 2031)))
            
            df_filtrado = df_filtrado[
                (df_filtrado['Data Conclusão'].dt.month == mes) & 
                (df_filtrado['Data Conclusão'].dt.year == ano)
            ]
        
        # Concatenar executantes
        executantes = pd.concat([
            df_filtrado["Executante1"],
            df_filtrado["Executante2"]
        ])
        executantes = executantes[~executantes.isin(['', 'nan', 'None'])]
        
        if not executantes.empty:
            exec_counts = executantes.value_counts()
            UIComponents.criar_grafico_pizza(exec_counts, "Executantes")
        else:
            st.warning("Nenhuma OS concluída no período selecionado")
    
    def supervisao(self):
        """Página de supervisão"""
        st.header("🔐 Área de Supervisão")
        
        if not self._autenticar():
            return
        
        st.success("✅ Acesso autorizado")
        
        opcao = st.selectbox(
            "Selecione a operação:",
            ["🔄 Atualizar OS", "💾 Gerenciar Backups", "⚙️ Configurar GitHub"]
        )
        
        if opcao == "🔄 Atualizar OS":
            self._atualizar_os()
        elif opcao == "💾 Gerenciar Backups":
            self._gerenciar_backups()
        elif opcao == "⚙️ Configurar GitHub":
            self._configurar_github()
    
    def _autenticar(self) -> bool:
        """Autentica acesso à supervisão"""
        if st.session_state.get('autenticado', False):
            return True
        
        senha = st.text_input("Digite a senha:", type="password")
        
        if senha:
            if Utils.validar_senha(senha):
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta!")
        
        return False
    
    def _atualizar_os(self):
        """Atualiza uma OS existente"""
        st.subheader("🔄 Atualizar Ordem de Serviço")
        
        df = self.dm.carregar()
        nao_concluidas = df[df["Status"] != "Concluído"]
        
        if nao_concluidas.empty:
            st.warning("Nenhuma OS pendente de atualização")
            return
        
        os_id = st.selectbox(
            "Selecione a OS",
            nao_concluidas["ID"],
            format_func=lambda x: f"OS #{x} - {df[df['ID']==x]['Descrição'].iloc[0][:50]}"
        )
        
        os_data = df[df["ID"] == os_id].iloc[0]
        
        with st.form("form_atualizar"):
            # Informações da OS
            st.info(f"""
            **Descrição:** {os_data['Descrição']}  
            **Solicitante:** {os_data['Solicitante']}  
            **Local:** {os_data['Local']}
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Determinar índice do tipo atual
                tipo_idx = 0
                if os_data["Tipo"] and os_data["Tipo"] in Config.TIPOS_MANUTENCAO.values():
                    tipo_idx = list(Config.TIPOS_MANUTENCAO.values()).index(os_data["Tipo"]) + 1
                
                tipo = st.selectbox(
                    "Tipo de Serviço",
                    [""] + list(Config.TIPOS_MANUTENCAO.values()),
                    index=tipo_idx
                )
                
                status = st.selectbox(
                    "Status*",
                    list(Config.STATUS_OPCOES.values()),
                    index=list(Config.STATUS_OPCOES.values()).index(os_data["Status"])
                )
                
                # Determinar índice do executante 1
                exec1_idx = 0
                if os_data["Executante1"] and os_data["Executante1"] in Config.EXECUTANTES_PREDEFINIDOS:
                    exec1_idx = Config.EXECUTANTES_PREDEFINIDOS.index(os_data["Executante1"])
                
                executante1 = st.selectbox(
                    "Executante Principal*",
                    Config.EXECUTANTES_PREDEFINIDOS,
                    index=exec1_idx
                )
            
            with col2:
                # Determinar índice do executante 2
                exec2_idx = 0
                if os_data["Executante2"] and os_data["Executante2"] in Config.EXECUTANTES_PREDEFINIDOS:
                    exec2_idx = Config.EXECUTANTES_PREDEFINIDOS.index(os_data["Executante2"]) + 1
                
                executante2 = st.selectbox(
                    "Executante Secundário",
                    [""] + Config.EXECUTANTES_PREDEFINIDOS,
                    index=exec2_idx
                )
                
                if status == "Concluído":
                    data, hora = Utils.obter_data_hora_local()
                    st.text_input("Data Conclusão", value=data, disabled=True)
                    st.text_input("Hora Conclusão", value=hora, disabled=True)
            
            observacoes = st.text_area(
                "Observações",
                value=os_data.get("Observações", ""),
                height=100
            )
            
            submitted = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
            
            if submitted:
                if status in ["Em execução", "Concluído"] and not executante1:
                    st.error("❌ Selecione um executante principal!")
                else:
                    if self._salvar_atualizacao(df, os_id, tipo, status, 
                                               executante1, executante2, observacoes):
                        st.success("✅ OS atualizada com sucesso!")
                        time.sleep(1)
                        st.rerun()
    
    def _salvar_atualizacao(self, df: pd.DataFrame, os_id: int, tipo: str,
                           status: str, exec1: str, exec2: str, obs: str) -> bool:
        """Salva atualizações da OS"""
        df.loc[df["ID"] == os_id, "Tipo"] = tipo
        df.loc[df["ID"] == os_id, "Status"] = status
        df.loc[df["ID"] == os_id, "Executante1"] = exec1
        df.loc[df["ID"] == os_id, "Executante2"] = exec2 if exec2 else ""
        df.loc[df["ID"] == os_id, "Observações"] = obs
        
        if status == "Concluído":
            data, hora = Utils.obter_data_hora_local()
            df.loc[df["ID"] == os_id, "Data Conclusão"] = data
            df.loc[df["ID"] == os_id, "Hora Conclusão"] = hora
        else:
            df.loc[df["ID"] == os_id, "Data Conclusão"] = ""
            df.loc[df["ID"] == os_id, "Hora Conclusão"] = ""
        
        return self.dm.salvar(df)
    
    def _gerenciar_backups(self):
        """Gerencia backups do sistema"""
        st.subheader("💾 Gerenciamento de Backups")
        
        backups = self.dm.listar_backups()
        
        if not backups:
            st.warning("Nenhum backup disponível")
            return
        
        st.info(f"""
        **Total de backups:** {len(backups)}  
        **Último backup:** {os.path.basename(backups[0])}
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Criar Backup Agora", use_container_width=True):
                self.dm._fazer_backup()
                st.success("✅ Backup criado!")
                time.sleep(1)
                st.rerun()
        
        with col2:
            if st.button("🧹 Limpar Antigos", use_container_width=True):
                self.dm._limpar_backups_antigos()
                st.success(f"✅ Mantidos {Config.MAX_BACKUPS} backups")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        st.subheader("Restaurar Backup")
        
        backup_selecionado = st.selectbox(
            "Selecione um backup:",
            [os.path.basename(b) for b in backups]
        )
        
        if st.button("🔙 Restaurar", use_container_width=True):
            backup_path = os.path.join(Config.BACKUP_DIR, backup_selecionado)
            if self.dm.restaurar_backup(backup_path):
                st.success(f"✅ Dados restaurados: {backup_selecionado}")
                time.sleep(2)
                st.rerun()
    
    def _configurar_github(self):
        """Configura integração com GitHub"""
        st.subheader("⚙️ Configuração do GitHub")
        
        if not self.dm.github.available:
            st.error("""
            ❌ PyGithub não está instalado.
            
            Para ativar a sincronização com GitHub:
            ```
            pip install PyGithub
            ```
            """)
            return
        
        with st.form("form_github"):
            repo = st.text_input(
                "Repositório (user/repo)",
                value=self.dm.github.repo or ""
            )
            
            filepath = st.text_input(
                "Caminho do arquivo",
                value=self.dm.github.filepath or "ordens_servico.csv"
            )
            
            token = st.text_input(
                "Token de acesso",
                type="password",
                value=self.dm.github.token or ""
            )
            
            submitted = st.form_submit_button("💾 Salvar Configurações", use_container_width=True)
            
            if submitted:
                if not all([repo, filepath, token]):
                    st.error("❌ Preencha todos os campos!")
                else:
                    if self._validar_e_salvar_github(repo, filepath, token):
                        st.success("✅ Configurações salvas!")
                        time.sleep(1)
                        st.rerun()
    
    def _validar_e_salvar_github(self, repo: str, filepath: str, token: str) -> bool:
        """Valida e salva configurações do GitHub"""
        try:
            from github import Github
            g = Github(token)
            g.get_repo(repo).get_contents(filepath)
            
            if self.dm.github.salvar_config(repo, filepath, token):
                self.dm.github.baixar()
                return True
        except Exception as e:
            st.error(f"❌ Erro na validação: {str(e)}")
        
        return False

# ==================== APLICAÇÃO PRINCIPAL ====================
def main():
    """Função principal da aplicação"""
    
    # Configurar página
    st.set_page_config(
        page_title="Gestão de OS",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inicializar gerenciadores
    if 'github_manager' not in st.session_state:
        st.session_state.github_manager = GitHubManager()
    
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager(st.session_state.github_manager)
    
    # Inicializar estado
    if 'notificacoes_limpas' not in st.session_state:
        st.session_state.notificacoes_limpas = False
    
    # Criar instância de páginas
    paginas = Paginas(st.session_state.data_manager)
    
    # Sidebar
    st.sidebar.title("📋 Menu Principal")
    
    opcao = st.sidebar.radio(
        "Navegação:",
        [
            "🏠 Página Inicial",
            "📝 Cadastrar OS",
            "📋 Listar OS",
            "🔍 Buscar OS",
            "📊 Dashboard",
            "🔐 Supervisão"
        ],
        label_visibility="collapsed"
    )
    
    # Renderizar página selecionada
    if opcao == "🏠 Página Inicial":
        paginas.pagina_inicial()
    elif opcao == "📝 Cadastrar OS":
        paginas.cadastrar_os()
    elif opcao == "📋 Listar OS":
        paginas.listar_os()
    elif opcao == "🔍 Buscar OS":
        paginas.buscar_os()
    elif opcao == "📊 Dashboard":
        paginas.dashboard()
    elif opcao == "🔐 Supervisão":
        paginas.supervisao()
    
    # Rodapé
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    **Sistema de Gestão de OS**  
    Versão 3.0 - Refatorada  
    Desenvolvedor: Robson Vilela  
    © 2025 - Todos os direitos reservados
    """)
    
    # Auto-refresh apenas na página inicial (10 minutos)
    if opcao == "🏠 Página Inicial":
        st.markdown("""
        <script>
        setTimeout(function() {
            window.location.reload();
        }, 600000);
        </script>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
