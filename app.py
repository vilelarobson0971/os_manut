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
    
    SENHA_HASH = hashlib.sha256("king@2025".encode()).hexdigest()
    EXECUTANTES_PREDEFINIDOS = ["Guilherme", "Ismael"]
    
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
    
    COLUNAS_NECESSARIAS = [
        "ID", "Descrição", "Data", "Hora Abertura", "Solicitante", 
        "Local", "Tipo", "Status", "Data Conclusão", "Hora Conclusão", 
        "Executante1", "Executante2", "Urgente", "Observações"
    ]
    
    CORES_GRAFICOS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe', '#fa709a']

# ==================== UTILIDADES ====================
class Utils:
    """Classe com funções utilitárias"""
    
    @staticmethod
    def carregar_imagem(caminho_arquivo: str) -> str:
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
        data_hora_utc = datetime.utcnow()
        data_hora_local = data_hora_utc - timedelta(hours=3)
        return (
            data_hora_local.strftime("%d/%m/%Y"),
            data_hora_local.strftime("%H:%M")
        )
    
    @staticmethod
    def validar_senha(senha: str) -> bool:
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
        try:
            from github import Github
            self.available = True
            self._carregar_config()
        except ImportError:
            self.available = False
    
    def _carregar_config(self):
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
        if not self.available or not all([self.repo, self.filepath, self.token]):
            st.warning("⚠️ GitHub não configurado completamente")
            return False
        
        try:
            from github import Github
            
            # Verificar se o arquivo existe
            if not os.path.exists(Config.LOCAL_FILENAME):
                st.error(f"❌ Arquivo local não encontrado: {Config.LOCAL_FILENAME}")
                return False
            
            g = Github(self.token)
            repo = g.get_repo(self.repo)
            
            with open(Config.LOCAL_FILENAME, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                contents = repo.get_contents(self.filepath)
                repo.update_file(
                    contents.path, 
                    f"Atualização automática - {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                    content, 
                    contents.sha
                )
                st.info(f"✅ Arquivo atualizado no GitHub: {self.filepath}")
            except:
                repo.create_file(
                    self.filepath, 
                    f"Criação inicial - {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                    content
                )
                st.info(f"✅ Arquivo criado no GitHub: {self.filepath}")
            
            return True
            
        except Exception as e:
            st.error(f"❌ Erro ao enviar para GitHub: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False

# ==================== DATA MANAGER ====================
class DataManager:
    """Gerencia operações com dados (CSV e backups)"""
    
    def __init__(self, github_manager: GitHubManager):
        self.github = github_manager
        self._inicializar_arquivos()
    
    def _inicializar_arquivos(self):
        os.makedirs(Config.BACKUP_DIR, exist_ok=True)
        
        if not os.path.exists(Config.LOCAL_FILENAME) or \
           os.path.getsize(Config.LOCAL_FILENAME) == 0:
            if not self.github.baixar():
                self._criar_csv_vazio()
    
    def _criar_csv_vazio(self):
        df = pd.DataFrame(columns=Config.COLUNAS_NECESSARIAS)
        df.to_csv(Config.LOCAL_FILENAME, index=False, encoding='utf-8')
    
    @staticmethod
    def _converter_tipos(df: pd.DataFrame) -> pd.DataFrame:
        colunas_str = ["Executante1", "Executante2", "Data Conclusão", 
                       "Hora Conclusão", "Urgente", "Observações"]
        for col in colunas_str:
            if col in df.columns:
                df[col] = df[col].astype(str)
        return df
    
    @staticmethod
    def _garantir_colunas(df: pd.DataFrame) -> pd.DataFrame:
        for coluna in Config.COLUNAS_NECESSARIAS:
            if coluna not in df.columns:
                df[coluna] = ""
        return df
    
    def carregar(self) -> pd.DataFrame:
        try:
            if not os.path.exists(Config.LOCAL_FILENAME):
                self._inicializar_arquivos()
            
            df = pd.read_csv(Config.LOCAL_FILENAME, dtype=str)  # Ler tudo como string primeiro
            df = self._garantir_colunas(df)
            
            # Converter ID para inteiro
            if "ID" in df.columns and not df.empty:
                df["ID"] = pd.to_numeric(df["ID"], errors='coerce').fillna(0).astype(int)
            
            df = self._converter_tipos(df)
            
            return df
            
        except Exception as e:
            st.error(f"Erro ao carregar dados: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return self._restaurar_do_backup()
    
    def _restaurar_do_backup(self) -> pd.DataFrame:
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
        try:
            df = self._garantir_colunas(df)
            
            # Garantir que ID é inteiro
            if "ID" in df.columns and not df.empty:
                df["ID"] = pd.to_numeric(df["ID"], errors='coerce').fillna(0).astype(int)
            
            df = self._converter_tipos(df)
            
            # Salvar localmente
            df.to_csv(Config.LOCAL_FILENAME, index=False, encoding='utf-8')
            
            # Fazer backup
            self._fazer_backup()
            
            # Sincronizar com GitHub (com tratamento de erro independente)
            if self.github.available and self.github.repo:
                try:
                    if self.github.enviar():
                        st.success("✅ Sincronizado com GitHub")
                    else:
                        st.warning("⚠️ Salvo localmente, mas falha na sincronização com GitHub")
                except Exception as e:
                    st.warning(f"⚠️ Salvo localmente, mas erro no GitHub: {str(e)}")
            
            return True
            
        except Exception as e:
            st.error(f"Erro ao salvar dados: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False
    
    def _fazer_backup(self):
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
        backups = sorted(glob.glob(
            os.path.join(Config.BACKUP_DIR, "ordens_servico_*.csv")
        ))
        return backups[-1] if backups else None
    
    def listar_backups(self) -> list:
        return sorted(
            glob.glob(os.path.join(Config.BACKUP_DIR, "ordens_servico_*.csv")),
            reverse=True
        )
    
    def restaurar_backup(self, backup_path: str) -> bool:
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
                f"""<h1 style='font-size: 2.5em; color: #667eea; 
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);'>{titulo}</h1>""", 
                unsafe_allow_html=True
            )
    
    @staticmethod
    def mostrar_notificacoes(df: pd.DataFrame):
        novas_os = df[df["Status"] == "Pendente"]
        
        if novas_os.empty:
            return
        
        ultimas_os = novas_os.tail(3).iloc[::-1]
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Limpar", key="limpar_notif", use_container_width=True):
                st.session_state.notificacoes_limpas = True
                st.rerun()
        
        if not st.session_state.get('notificacoes_limpas', False):
            for _, os_data in ultimas_os.iterrows():
                if os_data.get("Urgente", "") == "Sim":
                    st.error(
                        f"🚨 **URGENTE:** OS #{os_data['ID']} - {os_data['Descrição'][:50]}..."
                    )
                else:
                    st.warning(
                        f"⚠️ **NOVA OS:** #{os_data['ID']} - {os_data['Descrição'][:50]}..."
                    )
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("✓ Notificações ocultas")
            with col2:
                if st.button("🔄 Mostrar", key="mostrar_notif", use_container_width=True):
                    st.session_state.notificacoes_limpas = False
                    st.rerun()
    
    @staticmethod
    def criar_grafico_padrao(dados, titulo: str, tipo: str = "pizza"):
        if dados.empty:
            st.warning("Nenhum dado disponível para o gráfico")
            return
        
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        
        if tipo == "pizza":
            wedges, texts, autotexts = ax.pie(
                dados.values,
                labels=None,
                autopct='%1.1f%%',
                startangle=90,
                colors=Config.CORES_GRAFICOS[:len(dados)],
                wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2),
                textprops={'fontsize': 10, 'weight': 'bold', 'color': 'white'}
            )
            
            centre_circle = plt.Circle((0, 0), 0.70, fc='white')
            ax.add_artist(centre_circle)
            
            legend = ax.legend(
                wedges,
                [f'{label}: {valor}' for label, valor in zip(dados.index, dados.values)],
                title=titulo,
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
                fontsize=9,
                title_fontsize=11,
                frameon=True,
                shadow=True,
                fancybox=True
            )
            legend.get_frame().set_facecolor('white')
            legend.get_frame().set_alpha(0.95)
            
        else:
            bars = ax.bar(
                range(len(dados)),
                dados.values,
                color=Config.CORES_GRAFICOS[:len(dados)],
                edgecolor='#555',
                linewidth=1.5,
                alpha=0.85
            )
            
            for bar, valor in zip(bars, dados.values):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{int(valor)}',
                    ha='center',
                    va='bottom',
                    fontsize=10,
                    weight='bold',
                    color='#333'
                )
            
            ax.set_xticks(range(len(dados)))
            ax.set_xticklabels(dados.index, rotation=45, ha='right', fontsize=9)
            ax.set_ylabel('Quantidade', fontsize=10, weight='bold')
            
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.7)
            ax.set_axisbelow(True)
        
        ax.set_title(titulo, fontsize=13, weight='bold', pad=15, color='#333')
        
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()

# ==================== PÁGINAS ====================
class Paginas:
    """Gerencia todas as páginas do sistema"""
    
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
    
    def pagina_inicial(self):
        UIComponents.mostrar_header_com_logo(
            "GESTÃO DE ORDENS DE SERVIÇO DE MANUTENÇÃO"
        )
        
        st.markdown(
            """<p style='text-align: center; font-size: 2.2em; color: #764ba2; 
            font-weight: bold;'>AKR BRANDS</p>""", 
            unsafe_allow_html=True
        )
        st.markdown("---")
        
        df = self.dm.carregar()
        if not df.empty:
            UIComponents.mostrar_notificacoes(df)
            st.markdown("---")
        
        st.markdown("### 🎯 Funcionalidades Disponíveis")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("📝 **Cadastro** de novas ordens de serviço")
            st.info("🔍 **Busca** avançada por diversos critérios")
            st.info("🔐 **Supervisão** (área restrita)")
        
        with col2:
            st.info("📋 **Listagem** completa de OS cadastradas")
            st.info("📊 **Dashboard** com análises gráficas")
            st.info("💾 **Backup** automático dos dados")
        
        st.markdown("---")
        self._mostrar_info_sistema()
    
    def _mostrar_info_sistema(self):
        with st.expander("ℹ️ Informações do Sistema", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                backups = self.dm.listar_backups()
                if backups:
                    st.metric("📁 Total de Backups", len(backups))
                    st.caption(f"Último: {os.path.basename(backups[0])}")
            
            with col2:
                if self.dm.github.available and self.dm.github.repo:
                    st.success("✅ GitHub Sincronizado")
                elif self.dm.github.available:
                    st.warning("⚠️ GitHub Não Configurado")
                else:
                    st.info("ℹ️ GitHub Indisponível")
    
    def cadastrar_os(self):
        st.markdown("""
        <h2 style='color: #667eea;'>📝 Cadastrar Nova Ordem de Serviço</h2>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        with st.form("cadastro_os_form", clear_on_submit=True):
            descricao = st.text_area(
                "📄 Descrição da atividade*", 
                height=120,
                placeholder="Descreva detalhadamente o serviço a ser realizado..."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                solicitante = st.text_input(
                    "👤 Solicitante*",
                    placeholder="Nome do solicitante"
                )
            with col2:
                local = st.text_input(
                    "📍 Local*",
                    placeholder="Local do serviço"
                )
            
            urgente = st.checkbox("🚨 Marcar como urgente", help="Ativa notificação de prioridade")
            
            st.markdown("---")
            
            submitted = st.form_submit_button(
                "✅ Cadastrar OS", 
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if not all([descricao, solicitante, local]):
                    st.error("❌ Preencha todos os campos obrigatórios (*)")
                else:
                    if self._criar_nova_os(descricao, solicitante, local, urgente):
                        st.success("✅ OS cadastrada com sucesso!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
    
    def _criar_nova_os(self, descricao: str, solicitante: str, 
                       local: str, urgente: bool) -> bool:
        try:
            df = self.dm.carregar()
            
            # Garantir que ID é numérico
            if not df.empty:
                df["ID"] = pd.to_numeric(df["ID"], errors='coerce').fillna(0).astype(int)
                novo_id = int(df["ID"].max()) + 1
            else:
                novo_id = 1
            
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
            
            # Garantir que ID permanece inteiro
            df["ID"] = df["ID"].astype(int)
            
            sucesso = self.dm.salvar(df)
            
            if sucesso:
                st.write("✅ OS salva localmente")
                if self.dm.github.available and self.dm.github.repo:
                    st.write("🔄 Sincronizando com GitHub...")
            
            return sucesso
            
        except Exception as e:
            st.error(f"❌ Erro ao criar OS: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False
    
    def listar_os(self):
        st.markdown("""
        <h2 style='color: #667eea;'>📋 Listagem Completa de OS</h2>
        """, unsafe_allow_html=True)
        
        df = self.dm.carregar()
        
        if df.empty:
            st.warning("📭 Nenhuma ordem de serviço cadastrada.")
            return
        
        with st.expander("🔍 Filtros Avançados", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filtro_status = st.selectbox(
                    "📊 Status",
                    ["Todos"] + list(Config.STATUS_OPCOES.values()),
                    key="filtro_status_list"
                )
            
            with col2:
                filtro_tipo = st.selectbox(
                    "🔧 Tipo",
                    ["Todos"] + list(Config.TIPOS_MANUTENCAO.values()),
                    key="filtro_tipo_list"
                )
            
            with col3:
                filtro_urgente = st.selectbox(
                    "⚡ Urgência",
                    ["Todos", "Sim", "Não"],
                    key="filtro_urgente_list"
                )
        
        df_filtrado = df.copy()
        
        if filtro_status != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Status"] == filtro_status]
        
        if filtro_tipo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Tipo"] == filtro_tipo]
        
        if filtro_urgente != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Urgente"] == filtro_urgente]
        
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Total", len(df_filtrado))
        col2.metric("⏳ Pendentes", len(df_filtrado[df_filtrado["Status"] == "Pendente"]))
        col3.metric("🔧 Em Execução", len(df_filtrado[df_filtrado["Status"] == "Em execução"]))
        col4.metric("✅ Concluídas", len(df_filtrado[df_filtrado["Status"] == "Concluído"]))
        
        st.markdown("---")
        
        st.dataframe(
            df_filtrado,
            use_container_width=True,
            hide_index=True,
            height=400
        )
    
    def buscar_os(self):
        st.markdown("""
        <h2 style='color: #667eea;'>🔍 Busca Avançada</h2>
        """, unsafe_allow_html=True)
        
        df = self.dm.carregar()
        
        if df.empty:
            st.warning("📭 Nenhuma OS cadastrada.")
            return
        
        st.markdown("---")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("**Critério de Busca:**")
            criterio = st.radio(
                "Selecione:",
                ["Status", "ID", "Tipo", "Solicitante", "Local", 
                 "Executante1", "Executante2", "Observações"],
                label_visibility="collapsed"
            )
        
        with col2:
            st.markdown("**Parâmetros:**")
            resultado = self._realizar_busca(df, criterio)
        
        st.markdown("---")
        
        if not resultado.empty:
            st.success(f"✅ {len(resultado)} OS encontrada(s)")
            st.dataframe(resultado, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("ℹ️ Nenhuma OS encontrada com os critérios informados")
    
    def _realizar_busca(self, df: pd.DataFrame, criterio: str) -> pd.DataFrame:
        if criterio == "ID":
            busca = st.number_input("Digite o ID:", min_value=1, step=1)
            return df[df["ID"] == busca]
        
        elif criterio == "Status":
            busca = st.selectbox("Selecione o status:", list(Config.STATUS_OPCOES.values()))
            return df[df["Status"] == busca]
        
        elif criterio == "Tipo":
            busca = st.selectbox("Selecione o tipo:", list(Config.TIPOS_MANUTENCAO.values()))
            return df[df["Tipo"] == busca]
        
        else:
            busca = st.text_input(f"Digite o texto para buscar em {criterio}:")
            if busca:
                return df[df[criterio].astype(str).str.contains(busca, case=False, na=False)]
        
        return pd.DataFrame()
    
    def dashboard(self):
        st.markdown("""
        <h2 style='color: #667eea;'>📊 Dashboard Analítico</h2>
        """, unsafe_allow_html=True)
        
        df = self.dm.carregar()
        
        if df.empty:
            st.warning("📭 Nenhuma OS cadastrada para análise.")
            return
          # CONTINUAÇÃO DO CÓDIGO - Cole após a Parte 1

    def dashboard(self):
        st.markdown("""
        <h2 style='color: #667eea;'>📊 Dashboard Analítico</h2>
        """, unsafe_allow_html=True)
        
        df = self.dm.carregar()
        
        if df.empty:
            st.warning("📭 Nenhuma OS cadastrada para análise.")
            return
        
        self._mostrar_metricas_gerais(df)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Distribuição por Status")
            self._grafico_status(df)
        
        with col2:
            st.markdown("#### 🔧 Tipos de Manutenção")
            self._grafico_tipos(df)
        
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 👥 Produtividade dos Executantes")
            self._grafico_executantes(df)
    
    def _mostrar_metricas_gerais(self, df: pd.DataFrame):
        col1, col2, col3, col4 = st.columns(4)
        
        total = len(df)
        pendentes = len(df[df["Status"] == "Pendente"])
        em_exec = len(df[df["Status"] == "Em execução"])
        concluidas = len(df[df["Status"] == "Concluído"])
        
        perc_conclusao = (concluidas / total * 100) if total > 0 else 0
        
        col1.metric("📊 Total de OS", total)
        col2.metric("⏳ Pendentes", pendentes, delta=f"-{pendentes}" if pendentes > 0 else "0")
        col3.metric("🔧 Em Execução", em_exec, delta=f"{em_exec}" if em_exec > 0 else "0")
        col4.metric("✅ Concluídas", concluidas, delta=f"{perc_conclusao:.1f}%")
    
    def _grafico_status(self, df: pd.DataFrame):
        status_counts = df["Status"].value_counts()
        UIComponents.criar_grafico_padrao(status_counts, "Status das OS", tipo="pizza")
    
    def _grafico_tipos(self, df: pd.DataFrame):
        tipo_counts = df[df["Tipo"] != ""]["Tipo"].value_counts()
        UIComponents.criar_grafico_padrao(tipo_counts, "Tipos de Manutenção", tipo="pizza")
    
    def _grafico_executantes(self, df: pd.DataFrame):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            periodo = st.selectbox("📅 Período:", ["Todos", "Por Mês/Ano"], key="periodo_exec")
        
        df_filtrado = df[df["Status"] == "Concluído"].copy()
        
        if periodo == "Por Mês/Ano":
            df_filtrado['Data Conclusão'] = pd.to_datetime(
                df_filtrado['Data Conclusão'], 
                dayfirst=True, 
                errors='coerce'
            )
            
            with col2:
                mes = st.selectbox("Mês:", list(range(1, 13)), format_func=lambda x: f"{x:02d}", key="mes_exec")
            with col3:
                ano = st.selectbox("Ano:", list(range(2024, 2031)), key="ano_exec")
            
            df_filtrado = df_filtrado[
                (df_filtrado['Data Conclusão'].dt.month == mes) & 
                (df_filtrado['Data Conclusão'].dt.year == ano)
            ]
        
        executantes = pd.concat([
            df_filtrado["Executante1"],
            df_filtrado["Executante2"]
        ])
        executantes = executantes[~executantes.isin(['', 'nan', 'None'])]
        
        if not executantes.empty:
            exec_counts = executantes.value_counts()
            UIComponents.criar_grafico_padrao(exec_counts, "Produtividade por Executante", tipo="pizza")
        else:
            st.warning("⚠️ Nenhuma OS concluída no período selecionado")
    
    def supervisao(self):
        st.markdown("""
        <h2 style='color: #667eea;'>🔐 Área de Supervisão</h2>
        """, unsafe_allow_html=True)
        
        if not self._autenticar():
            return
        
        st.success("✅ Acesso autorizado")
        st.markdown("---")
        
        opcao = st.selectbox(
            "Selecione a operação:",
            ["🔄 Atualizar OS", "💾 Gerenciar Backups", "⚙️ Configurar GitHub"]
        )
        
        st.markdown("---")
        
        if opcao == "🔄 Atualizar OS":
            self._atualizar_os()
        elif opcao == "💾 Gerenciar Backups":
            self._gerenciar_backups()
        elif opcao == "⚙️ Configurar GitHub":
            self._configurar_github()
    
    def _autenticar(self) -> bool:
        if st.session_state.get('autenticado', False):
            return True
        
        st.markdown("### 🔒 Autenticação Necessária")
        senha = st.text_input("Digite a senha:", type="password", key="senha_supervisao")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔓 Entrar", use_container_width=True, type="primary"):
                if Utils.validar_senha(senha):
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta!")
        
        return False
    
    def _atualizar_os(self):
        st.markdown("### 🔄 Atualizar Ordem de Serviço")
        
        df = self.dm.carregar()
        nao_concluidas = df[df["Status"] != "Concluído"]
        
        if nao_concluidas.empty:
            st.warning("⚠️ Nenhuma OS pendente de atualização")
            return
        
        os_id = st.selectbox(
            "Selecione a OS:",
            nao_concluidas["ID"],
            format_func=lambda x: f"OS #{x} - {df[df['ID']==x]['Descrição'].iloc[0][:50]}..."
        )
        
        os_data = df[df["ID"] == os_id].iloc[0]
        
        with st.form("form_atualizar"):
            st.info(f"""
            **📄 Descrição:** {os_data['Descrição']}  
            **👤 Solicitante:** {os_data['Solicitante']}  
            **📍 Local:** {os_data['Local']}  
            **📅 Data Abertura:** {os_data['Data']} às {os_data['Hora Abertura']}
            """)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                tipo_idx = 0
                if os_data["Tipo"] and os_data["Tipo"] in Config.TIPOS_MANUTENCAO.values():
                    tipo_idx = list(Config.TIPOS_MANUTENCAO.values()).index(os_data["Tipo"]) + 1
                
                tipo = st.selectbox(
                    "🔧 Tipo de Serviço",
                    [""] + list(Config.TIPOS_MANUTENCAO.values()),
                    index=tipo_idx
                )
                
                status = st.selectbox(
                    "📊 Status*",
                    list(Config.STATUS_OPCOES.values()),
                    index=list(Config.STATUS_OPCOES.values()).index(os_data["Status"])
                )
                
                exec1_idx = 0
                if os_data["Executante1"] and os_data["Executante1"] in Config.EXECUTANTES_PREDEFINIDOS:
                    exec1_idx = Config.EXECUTANTES_PREDEFINIDOS.index(os_data["Executante1"])
                
                executante1 = st.selectbox(
                    "👤 Executante Principal*",
                    Config.EXECUTANTES_PREDEFINIDOS,
                    index=exec1_idx
                )
            
            with col2:
                exec2_idx = 0
                if os_data["Executante2"] and os_data["Executante2"] in Config.EXECUTANTES_PREDEFINIDOS:
                    exec2_idx = Config.EXECUTANTES_PREDEFINIDOS.index(os_data["Executante2"]) + 1
                
                executante2 = st.selectbox(
                    "👥 Executante Secundário",
                    [""] + Config.EXECUTANTES_PREDEFINIDOS,
                    index=exec2_idx
                )
                
                if status == "Concluído":
                    data, hora = Utils.obter_data_hora_local()
                    st.text_input("📅 Data Conclusão", value=data, disabled=True)
                    st.text_input("🕐 Hora Conclusão", value=hora, disabled=True)
            
            observacoes = st.text_area(
                "📝 Observações",
                value=os_data.get("Observações", ""),
                height=120,
                placeholder="Adicione observações sobre a execução..."
            )
            
            st.markdown("---")
            
            submitted = st.form_submit_button(
                "💾 Salvar Alterações", 
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if status in ["Em execução", "Concluído"] and not executante1:
                    st.error("❌ Selecione um executante principal!")
                else:
                    if self._salvar_atualizacao(df, os_id, tipo, status, 
                                               executante1, executante2, observacoes):
                        st.success("✅ OS atualizada com sucesso!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
    
    def _salvar_atualizacao(self, df: pd.DataFrame, os_id: int, tipo: str,
                           status: str, exec1: str, exec2: str, obs: str) -> bool:
        try:
            # Garantir que ID é numérico
            df["ID"] = pd.to_numeric(df["ID"], errors='coerce').fillna(0).astype(int)
            
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
            
            sucesso = self.dm.salvar(df)
            
            if sucesso:
                st.write("✅ OS atualizada localmente")
                if self.dm.github.available and self.dm.github.repo:
                    st.write("🔄 Sincronizando com GitHub...")
            
            return sucesso
            
        except Exception as e:
            st.error(f"❌ Erro ao atualizar OS: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False
    
    def _gerenciar_backups(self):
        st.markdown("### 💾 Gerenciamento de Backups")
        
        backups = self.dm.listar_backups()
        
        if not backups:
            st.warning("⚠️ Nenhum backup disponível")
            return
        
        st.info(f"""
        **📊 Total de backups:** {len(backups)}  
        **📅 Último backup:** {os.path.basename(backups[0])}  
        **💾 Limite de backups:** {Config.MAX_BACKUPS}
        """)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Criar Backup Agora", use_container_width=True, type="primary"):
                self.dm._fazer_backup()
                st.success("✅ Backup criado com sucesso!")
                time.sleep(1)
                st.rerun()
        
        with col2:
            if st.button("🧹 Limpar Backups Antigos", use_container_width=True):
                self.dm._limpar_backups_antigos()
                st.success(f"✅ Mantidos {Config.MAX_BACKUPS} backups mais recentes")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 🔙 Restaurar Backup")
        
        backup_selecionado = st.selectbox(
            "Selecione um backup para restaurar:",
            [os.path.basename(b) for b in backups]
        )
        
        st.warning("⚠️ **Atenção:** Restaurar um backup substituirá todos os dados atuais!")
        
        if st.button("🔙 Restaurar Backup Selecionado", use_container_width=True, type="primary"):
            backup_path = os.path.join(Config.BACKUP_DIR, backup_selecionado)
            if self.dm.restaurar_backup(backup_path):
                st.success(f"✅ Dados restaurados: {backup_selecionado}")
                time.sleep(2)
                st.rerun()
    
    def _configurar_github(self):
        st.markdown("### ⚙️ Configuração do GitHub")
        
        if not self.dm.github.available:
            st.error("""
            ❌ **PyGithub não está instalado.**
            
            Para ativar a sincronização com GitHub, execute:
            ```bash
            pip install PyGithub
            ```
            """)
            return
        
        st.info("""
        ℹ️ **Sincronização com GitHub**  
        Configure aqui a sincronização automática dos dados com um repositório GitHub.
        Você precisará de um token de acesso pessoal (PAT) com permissões de repositório.
        """)
        
        st.markdown("---")
        
        with st.form("form_github"):
            repo = st.text_input(
                "📁 Repositório (formato: usuario/repositorio)",
                value=self.dm.github.repo or "",
                placeholder="exemplo: usuario/meu-repositorio"
            )
            
            filepath = st.text_input(
                "📄 Caminho do arquivo no repositório",
                value=self.dm.github.filepath or "ordens_servico.csv",
                placeholder="ordens_servico.csv"
            )
            
            token = st.text_input(
                "🔑 Token de acesso pessoal (PAT)",
                type="password",
                value=self.dm.github.token or "",
                placeholder="ghp_xxxxxxxxxxxx"
            )
            
            st.markdown("---")
            
            submitted = st.form_submit_button(
                "💾 Salvar Configurações", 
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if not all([repo, filepath, token]):
                    st.error("❌ Preencha todos os campos!")
                else:
                    with st.spinner("🔄 Validando configurações..."):
                        if self._validar_e_salvar_github(repo, filepath, token):
                            st.success("✅ Configurações salvas e validadas com sucesso!")
                            time.sleep(1)
                            st.rerun()
    
    def _validar_e_salvar_github(self, repo: str, filepath: str, token: str) -> bool:
        try:
            from github import Github
            g = Github(token)
            repo_obj = g.get_repo(repo)
            
            try:
                repo_obj.get_contents(filepath)
            except:
                st.info("ℹ️ Arquivo não existe no repositório. Será criado na próxima sincronização.")
            
            if self.dm.github.salvar_config(repo, filepath, token):
                self.dm.github.baixar()
                return True
        except Exception as e:
            st.error(f"❌ Erro na validação: {str(e)}")
        
        return False

# ==================== APLICAÇÃO PRINCIPAL ====================
def main():
    st.set_page_config(
        page_title="Gestão de OS - AKR Brands",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
    <style>
        .stMetric {
            background-color: #f0f2f6;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stButton>button {
            border-radius: 5px;
            font-weight: bold;
        }
        .stSelectbox {
            border-radius: 5px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    if 'github_manager' not in st.session_state:
        st.session_state.github_manager = GitHubManager()
    
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager(st.session_state.github_manager)
    
    if 'notificacoes_limpas' not in st.session_state:
        st.session_state.notificacoes_limpas = False
    
    paginas = Paginas(st.session_state.data_manager)
    
    st.sidebar.markdown("""
    <h2 style='text-align: center; color: #667eea;'>📋 Menu Principal</h2>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
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
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center;'>
        <p style='font-size: 0.9em; color: #666;'>
            <strong>Sistema de Gestão de OS</strong><br>
            Versão 4.0 - Corrigida<br>
            Desenvolvedor: Robson Vilela<br>
            © 2025 - Todos os direitos reservados
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
        
        self._mostrar_metricas_gerais(
