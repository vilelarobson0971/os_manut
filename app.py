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
