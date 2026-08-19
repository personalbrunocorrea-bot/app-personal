import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, date, time, timedelta
from supabase import create_client, Client

st.set_page_config(page_title="SaaS Personal Trainer", layout="wide")

SUPABASE_URL = "https://vkanwxrjtajiivghyapb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZrYW53eHJqdGFqaWl2Z2h5YXBiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcxNDgzNTYsImV4cCI6MjEwMjcyNDM1Nn0._JhswzxjiNuXnRXHMcpgEbZiEE017RUyn5AHR_pzslo"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if "user" not in st.session_state:
    st.session_state.user = None
if "session" not in st.session_state:
    st.session_state.session = None

def preparar_cliente():
    if st.session_state.session:
        token = st.session_state.session.access_token
        supabase.postgrest.auth(token)

# --- LOGIN / CADASTRO ---
if st.session_state.user is None:
    st.title("🏋️ Painel do Personal Trainer - Login")
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Conta"])
    
    with aba_login:
        with st.form("form_login"):
            email_login = st.text_input("E-mail")
            senha_login = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                    st.session_state.user = res.user
                    st.session_state.session = res.session
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                except Exception:
                    st.error("E-mail ou senha incorretos.")
                    
    with aba_cadastro:
        with st.form("form_cad_user"):
            email_cad = st.text_input("E-mail para Cadastro")
            senha_cad = st.text_input("Crie uma Senha", type="password")
            if st.form_submit_button("Cadastrar Conta"):
                try:
                    supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                    st.success("Conta criada! Faça login na aba ao lado.")
                except Exception as e:
                    st.error(f"Erro ao criar conta: {e}")

# --- APLICAÇÃO PRINCIPAL ---
else:
    user_id = st.session_state.user.id
    preparar_cliente()
    
    st.sidebar.write(f"Logado como: **{st.session_state.user.email}**")
    if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.session = None
        st.rerun()
        
    st.sidebar.divider()
    menu = st.sidebar.radio("Navegação", [
        "Agenda Semanal (Com Check-in)", 
        "👤 Perfil do Aluno (Frequência e Financeiro)", 
        "Cadastrar Aluno", 
        "Painel Financeiro Geral"
    ])

    def carregar_alunos():
        preparar_cliente()
        res = supabase.table("alunos").select("*").eq("user_id", user_id).execute()
        return res.data or []

    # 1. CADASTRO DE ALUNOS
    if menu == "Cadastrar Aluno":
        st.header("Cadastrar Novo Aluno")
        
        tipo_cobranca = st.radio("Selecione o Tipo de Plano", ["Pacote de Aulas", "Aula Avulsa"], horizontal=True)
        is_pacote = (tipo_cobranca == "Pacote de Aulas")
        
        with st.form("form_cadastro"):
            nome = st.text_input("Nome do Aluno")
            telefone = st.text_input("Telefone (WhatsApp com DDD - Ex: 5521999999999)")
            
            c1, c2 = st.columns(2)
            with c1:
                valor_aula = st.number_input("Valor por Aula Avulsa (R$)", min_value=0.0, value=80.0, disabled=is_pacote)
                valor_pacote = st.number_input("Valor Total do Pacote (R$)", min_value=0.0, value=600.0, disabled=not is_pacote)
            with c2:
                total_aulas_pacote = st.number_input("Quantidade de Aulas no Pacote", min_value=1, value=10, step=1, disabled=not is_pacote)
                vencimento = st.number_input("Dia do Vencimento do Pagamento", min_value=1, max_value=31, value=10)
                
            btn_salvar = st.form_submit_button("Salvar Cadastramento do Aluno")
            
            if btn_salvar:
                if not nome:
                    st.warning("Por favor, preencha o nome do aluno.")
                else:
                    tipo = "pacote" if is_pacote else "avulso"
                    try:
                        preparar_cliente()
                        qtd_aulas = int(total_aulas_pacote) if is_pacote else 0
                        dados = {
                            "user_id": user_id,
                            "nome": nome,
                            "telefone": telefone.strip(),
                            "tipo_cobranca": tipo,
                            "valor_aula": float(valor_aula) if not is_pacote else 0.0,
                            "valor_pacote": float(valor_pacote) if is_pacote else 0.0,
                            "total_aulas_pacote": qtd_aulas,
                            "aulas_restantes": qtd_aulas,
                            "vencimento": int(vencimento),
                            "presencas": 0,
                            "faltas": 0,
                            "valor_pago": 0.0
                        }
                        supabase.table("alunos").insert(dados).execute()
                        st.success(f"Aluno {nome} cadastrado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco de dados: {e}")

    # 2. AGENDA SEMANAL COM COLUNAS POR DIA DA SEMANA
    elif menu == "Agenda Semanal (Com Check-in)":
        st.header("📅 Agenda Semanal")
        
        # Controle de Estado do Início da Semana
        if "semana_inicio" not in st.session_state:
            hoje = date.today()
            st.session_state.semana_inicio = hoje - timedelta(days=hoje.weekday())  # Segunda-feira da semana atual

        # Navegação de Semanas
        c_nav1, c_nav2, c_nav3, c_nav4 = st.columns([1, 1, 1, 2])
        with c_nav1:
            if st.button("⬅️ Semana Anterior", use_container_width=True):
                st.session_state.semana_inicio -= timedelta(days=7)
                st.rerun()
        with c_nav2:
            if st.button("📅 Esta Semana", use_container_width=True):
                hoje = date.today()
                st.session_state.semana_inicio = hoje - timedelta(days=hoje.weekday())
                st.rerun()
        with c_nav3:
            if st.button("Próxima Semana ➡️", use_container_width=True):
                st.session_state.semana_inicio += timedelta(days=7)
                st.rerun()
        with c_nav4:
            semana_fim = st.session_state.semana_inicio + timedelta(days=6)
            st.markdown(f"### 🗓️ `{st.session_state.semana_inicio.strftime('%d/%m/%Y')}` até `{semana_fim.strftime('%d/%m/%Y')}`")

        st.divider()

        # FORMULÁRIO DE AGENDAMENTO (EXPANDER SUPERIOR)
        alunos = carregar_alunos()
        mapa_alunos_id = {a["id"]: a for a in alunos}
        
        with st.expander("📌 Agendar Nova Aula na Semana", expanded=False):
            if not alunos:
                st.warning("Cadastre um aluno primeiro.")
            else:
                mapa_alunos_nome = {a["nome"]: a for a in alunos}
                with st.form("form_agendar_semanal"):
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        aluno_sel = st.selectbox("Aluno", list(mapa_alunos_nome.keys()))
                    with col_f2:
                        data_aula = st.date_input("Data da Aula", value=date.today())
                    with col_f3:
                        hora_aula = st.time_input("Horário", value=time(8, 0))
                    
                    if st.form_submit_button("Confirmar Agendamento"):
                        preparar_cliente()
                        dt_completa = datetime.combine(data_aula, hora_aula).isoformat()
                        supabase.table("agendamentos").insert({
                            "user_id": user_id,
                            "aluno_id": mapa_alunos_nome[aluno_sel]["id"],
                            "data_hora": dt_completa,
                            "status": "agendado"
                        }).execute()
                        st.success("Aula agendada com sucesso!")
                        st.rerun()

        # CARREGAR DADOS DA AGENDA DA SEMANA
        preparar_cliente()
        try:
            res_agenda = supabase.table("agendamentos").select("*").eq("user_id", user_id).execute()
            dados_agenda = res_agenda.data or []
        except Exception as e:
            st.error(f"Erro ao carregar agenda: {e}")
            dados_agenda = []

        dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        datas_da_semana = [st.session_state.semana_inicio + timedelta(days=i) for i in range(7)]
        
        cols_dias = st.columns(7)

        for i, col in enumerate(cols_dias):
            dia_dt = datas_da_semana[i]
            nome_dia = dias_semana[i]
            é_hoje = (dia_dt == date.today())
            
            with col:
                header_str = f"**{nome_dia}**\n\n`{dia_dt.strftime('%d/%m')}`"
                if é_hoje:
                    st.success(f"📌 {header_str}")
                else:
                    st.markdown(f"### {header_str}")
                st.divider()

                # Filtrar agendamentos para este dia específico
                agendamentos_dia = []
                for item in dados_agenda:
                    dt = datetime.fromisoformat(item["data_hora"])
                    if dt.date() == dia_dt:
                        aluno_obj = mapa_alunos_id.get(item["aluno_id"], {})
                        agendamentos_dia.append({
                            "id": item["id"],
                            "hora_dt": dt,
                            "hora_str": dt.strftime("%H:%M"),
                            "aluno_obj": aluno_obj,
                            "aluno_nome": aluno_obj.get("nome", "Indefinido"),
                            "telefone": aluno_obj.get("telefone", ""),
                            "status": item.get("status", "agendado"),
                            "data_str": dt.strftime("%d/%m/%Y")
                        })
                
                # Ordenar por horário
                agendamentos_dia.sort(key=lambda x: x["hora_dt"])

                if not agendamentos_dia:
                    st.caption("*Nenhum treino*")
                else:
                    for item in agendamentos_dia:
                        aluno_data = item["aluno_obj"]
                        
                        # Definir badge visual de acordo com o status
                        status_tag = "🔵"
                        if item["status"] == "realizada":
                            status_tag = "✅"
                        elif item["status"] == "falta_cobrada":
                            status_tag = "❌"
                        elif item["status"] == "falta_isenta":
                            status_tag = "🟡"

                        st.markdown(f"{status_tag} **{item['hora_str']}** - **{item['aluno_nome']}**")
                        
                        if aluno_data:
                            st.caption(f"Rest: {aluno_data.get('aulas_restantes', 0)} | P: {aluno_data.get('presencas', 0)} | F: {aluno_data.get('faltas', 0)}")

                        # Ações Rápidas por Aula
                        with st.popover("⚙️ Ações"):
                            if st.button("✅ Confirmar Presença", key=f"p_{item['id']}", use_container_width=True):
                                preparar_cliente()
                                supabase.table("agendamentos").update({"status": "realizada"}).eq("id", item["id"]).execute()
                                if aluno_data:
                                    upd = {"presencas": (aluno_data.get("presencas") or 0) + 1}
                                    restantes = aluno_data.get("aulas_restantes") or 0
                                    if aluno_data.get("tipo_cobranca") == "pacote" and restantes > 0:
                                        upd["aulas_restantes"] = restantes - 1
                                    supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()
                                st.rerun()

                            if st.button("❌ Falta Cobrada", key=f"fc_{item['id']}", use_container_width=True):
                                preparar_cliente()
                                supabase.table("agendamentos").update({"status": "falta_cobrada"}).eq("id", item["id"]).execute()
                                if aluno_data:
                                    upd = {"faltas": (aluno_data.get("faltas") or 0) + 1}
                                    restantes = aluno_data.get("aulas_restantes") or 0
                                    if aluno_data.get("tipo_cobranca") == "pacote" and restantes > 0:
                                        upd["aulas_restantes"] = restantes - 1
                                    supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()
                                st.rerun()

                            if st.button("🟡 Falta Isenta", key=f"fi_{item['id']}", use_container_width=True):
                                preparar_cliente()
                                supabase.table("agendamentos").update({"status": "falta_isenta"}).eq("id", item["id"]).execute()
                                st.rerun()

                            if item["telefone"]:
                                msg = f"Olá {item['aluno_nome']}! Lembrando do nosso treino agendado para {item['data_str']} às {item['hora_str']}."
                                link_wsp = f"https://wa.me/{item['telefone']}?text={urllib.parse.quote(msg)}"
                                st.link_button("💬 WhatsApp", link_wsp, use_container_width=True)

                            if st.button("🗑️ Desmarcar", key=f"del_{item['id']}", use_container_width=True, type="primary"):
                                preparar_cliente()
                                supabase.table("agendamentos").delete().eq("id", item["id"]).execute()
                                st.rerun()
                        
                        st.divider()

    # 3. PERFIL DO ALUNO (COM EDIÇÃO TOTAL E CONTROLE MANUAL)
    elif menu == "👤 Perfil do Aluno (Frequência e Financeiro)":
        st.header("👤 Perfil Individual do Aluno")
        alunos = carregar_alunos()
        
        if not alunos:
            st.warning("Nenhum aluno cadastrado.")
        else:
            mapa_alunos = {a["nome"]: a for a in alunos}
            aluno_sel = st.selectbox("Selecione o Aluno", list(mapa_alunos.keys()))
            aluno = mapa_alunos[aluno_sel]
            
            st.divider()
            
            # BLOCO 1: MONITORAMENTO DE AULAS E FREQUÊNCIA
            st.subheader("1️⃣ Frequência & Resumo do Plano")
            
            c_freq1, c_freq2, c_freq3, c_freq4 = st.columns(4)
            c_freq1.metric("Presenças Confirmadas", aluno.get("presencas", 0))
            c_freq2.metric("Faltas Cobradas", aluno.get("faltas", 0))
            
            if aluno.get("tipo_cobranca") == "pacote":
                c_freq3.metric("Aulas Restantes", f"{aluno.get('aulas_restantes', 0)} / {aluno.get('total_aulas_pacote', 0)}")
                with c_freq4:
                    st.write("")
                    if st.button("🔄 Renovar Pacote", use_container_width=True):
                        preparar_cliente()
                        novas_restantes = (aluno.get("aulas_restantes") or 0) + (aluno.get("total_aulas_pacote") or 0)
                        supabase.table("alunos").update({"aulas_restantes": novas_restantes}).eq("id", aluno["id"]).execute()
                        st.success(f"Pacote renovado com +{aluno.get('total_aulas_pacote', 0)} aulas!")
                        st.rerun()
            else:
                aulas_computadas = (aluno.get("presencas") or 0) + (aluno.get("faltas") or 0)
                c_freq3.metric("Total Aulas Realizadas", aulas_computadas)
                c_freq4.caption("Modalidade: Aula Avulsa")

            # CONTROLE MANUAL DAS AULAS (AGENDAMENTOS DO ALUNO)
            st.markdown("##### ⚙️ Controle Manual do Histórico de Aulas")
            preparar_cliente()
            res_ag = supabase.table("agendamentos").select("*").eq("aluno_id", aluno["id"]).execute()
            historico_aulas = res_ag.data or []
            
            if historico_aulas:
                lista_hist = []
                for h in historico_aulas:
                    dt = datetime.fromisoformat(h["data_hora"])
                    lista_hist.append({
                        "ID": h["id"],
                        "Data": dt.strftime("%d/%m/%Y"),
                        "Horário": dt.strftime("%H:%M"),
                        "Status": h.get("status", "agendado")
                    })
                
                df_hist = pd.DataFrame(lista_hist).sort_values(by=["Data", "Horário"], ascending=False)
                
                edited_df = st.data_editor(
                    df_hist,
                    column_config={
                        "ID": st.column_config.TextColumn("ID", disabled=True),
                        "Data": st.column_config.TextColumn("Data", disabled=True),
                        "Horário": st.column_config.TextColumn("Horário", disabled=True),
                        "Status": st.column_config.SelectboxColumn(
                            "Status da Aula",
                            options=["agendado", "realizada", "falta_cobrada", "falta_isenta"],
                            required=True
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_aulas_{aluno['id']}"
                )
                
                col_salvar_hist, col_del_hist = st.columns([1.5, 2])
                with col_salvar_hist:
                    if st.button("💾 Salvar Alterações no Histórico", use_container_width=True):
                        preparar_cliente()
                        for index, row in edited_df.iterrows():
                            supabase.table("agendamentos").update({"status": row["Status"]}).eq("id", row["ID"]).execute()
                        st.success("Status das aulas atualizados!")
                        st.rerun()

                with col_del_hist:
                    aula_para_deletar = st.selectbox("Excluir Aula do Histórico", ["Nenhuma"] + [f"{r['Data']} às {r['Horário']} (ID: {r['ID']})" for r in lista_hist], key=f"del_sel_{aluno['id']}")
                    if aula_para_deletar != "Nenhuma" and st.button("🗑️ Confirmar Exclusão da Aula", type="primary"):
                        id_del = int(aula_para_deletar.split("ID: ")[1].replace(")", ""))
                        preparar_cliente()
                        supabase.table("agendamentos").delete().eq("id", id_del).execute()
                        st.success("Aula excluída!")
                        st.rerun()
            else:
                st.info("Nenhuma aula registrada para este aluno na agenda.")

            st.divider()

            # BLOCO 2: EDIÇÃO LIVRE DOS CAMPOS DO ALUNO (COM CORREÇÃO DE MIN_VALUE)
            with st.expander("🛠️ Ajustar Valores e Números do Aluno Manualmente (Liberdade Total)"):
                st.caption("Altere qualquer valor abaixo diretamente e salve para ajustar inconsistências ou dar descontos/créditos.")
                with st.form(f"form_edicao_aluno_{aluno['id']}"):
                    c_ed1, c_ed2, c_ed3 = st.columns(3)
                    with c_ed1:
                        novo_nome = st.text_input("Nome do Aluno", value=aluno.get("nome", ""))
                        novo_tel = st.text_input("Telefone (WhatsApp)", value=aluno.get("telefone", ""))
                        novo_venc = st.number_input("Dia Vencimento", min_value=1, max_value=31, value=max(1, min(31, int(aluno.get("vencimento") or 10))))
                    with c_ed2:
                        novas_presencas = st.number_input("Presenças Contadas", min_value=0, value=max(0, int(aluno.get("presencas") or 0)))
                        novas_faltas = st.number_input("Faltas Cobradas", min_value=0, value=max(0, int(aluno.get("faltas") or 0)))
                        novas_restantes = st.number_input("Aulas Restantes (Se Pacote)", min_value=0, value=max(0, int(aluno.get("aulas_restantes") or 0)))
                    with c_ed3:
                        novo_val_aula = st.number_input("Valor por Aula Avulsa (R$)", min_value=0.0, value=max(0.0, float(aluno.get("valor_aula") or 0.0)))
                        novo_val_pacote = st.number_input("Valor Total Pacote (R$)", min_value=0.0, value=max(0.0, float(aluno.get("valor_pacote") or 0.0)))
                        novo_tot_pacote = st.number_input("Tamanho do Pacote (Aulas)", min_value=0, value=max(0, int(aluno.get("total_aulas_pacote") or 0)))

                    if st.form_submit_button("💾 Salvar Alterações do Perfil", use_container_width=True):
                        preparar_cliente()
                        dados_upd = {
                            "nome": novo_nome,
                            "telefone": novo_tel,
                            "vencimento": int(novo_venc),
                            "presencas": int(novas_presencas),
                            "faltas": int(novas_faltas),
                            "aulas_restantes": int(novas_restantes),
                            "valor_aula": float(novo_val_aula),
                            "valor_pacote": float(novo_val_pacote),
                            "total_aulas_pacote": int(novo_tot_pacote)
                        }
                        supabase.table("alunos").update(dados_upd).eq("id", aluno["id"]).execute()
                        st.success("Perfil atualizado com sucesso!")
                        st.rerun()

            st.divider()

            # BLOCO 3: CONTROLE FINANCEIRO E PAGAMENTOS
            st.subheader("2️⃣ Controle Financeiro e Valores")
            
            aulas_computadas = (aluno.get("presencas") or 0) + (aluno.get("faltas") or 0)
            total_devido = float(aluno.get("valor_pacote") or 0.0) if aluno.get("tipo_cobranca") == "pacote" else (aulas_computadas * float(aluno.get("valor_aula") or 0.0))
            valor_pago = float(aluno.get("valor_pago") or 0.0)
            saldo_pendente = total_devido - valor_pago
            
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Tipo de Plano", "Pacote" if aluno.get("tipo_cobranca") == "pacote" else "Avulso")
            f2.metric("Total Devido", f"R$ {total_devido:.2f}")
            f3.metric("Valor Já Pago", f"R$ {valor_pago:.2f}")
            f4.metric("Saldo Pendente", f"R$ {max(0.0, saldo_pendente):.2f}", delta_color="inverse")

            st.caption(f"📅 Dia de Vencimento do Pagamento: Todo dia **{aluno.get('vencimento', 10)}**")
            
            col_pag1, col_pag2 = st.columns(2)
            with col_pag1:
                with st.expander("💰 Registrar Novo Pagamento Recebido"):
                    with st.form(f"form_pag_{aluno['id']}"):
                        v_pago = st.number_input("Valor Recebido (R$)", min_value=0.0, step=10.0, value=float(max(0.0, saldo_pendente)))
                        if st.form_submit_button("Confirmar Recebimento"):
                            preparar_cliente()
                            novo_pago = valor_pago + v_pago
                            supabase.table("alunos").update({"valor_pago": novo_pago}).eq("id", aluno["id"]).execute()
                            st.success("Pagamento registrado!")
                            st.rerun()
                            
            with col_pag2:
                with st.expander("✏️ Ajustar Manualmente o Total Já Pago"):
                    with st.form(f"form_set_pago_{aluno['id']}"):
                        novo_pago_direto = st.number_input("Definir Valor Já Pago (R$)", min_value=0.0, value=valor_pago)
                        if st.form_submit_button("Atualizar Valor Pago"):
                            preparar_cliente()
                            supabase.table("alunos").update({"valor_pago": float(novo_pago_direto)}).eq("id", aluno["id"]).execute()
                            st.success("Valor atualizado com sucesso!")
                            st.rerun()

    # 4. PAINEL FINANCEIRO GERAL
    elif menu == "Painel Financeiro Geral":
        st.header("📊 Painel Financeiro Geral")
        alunos = carregar_alunos()
        
        if alunos:
            dados_fin = []
            total_recebido = 0.0
            total_pendente = 0.0
            
            for d in alunos:
                aulas_computadas = (d.get("presencas") or 0) + (d.get("faltas") or 0)
                devido = float(d.get("valor_pacote") or 0.0) if d.get("tipo_cobranca") == "pacote" else (aulas_computadas * float(d.get("valor_aula") or 0.0))
                pago = float(d.get("valor_pago") or 0.0)
                saldo = devido - pago
                
                total_recebido += pago
                total_pendente += max(0.0, saldo)
                
                dados_fin.append({
                    "Aluno": d.get("nome", "Sem nome"),
                    "Tipo": "Pacote" if d.get("tipo_cobranca") == "pacote" else "Avulso",
                    "Presenças": d.get("presencas", 0),
                    "Faltas": d.get("faltas", 0),
                    "Total Devido": devido,
                    "Valor Pago": pago,
                    "Saldo Pendente": max(0.0, saldo)
                })
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Recebido", f"R$ {total_recebido:.2f}")
            m2.metric("Total Pendente", f"R$ {total_pendente:.2f}")
            m3.metric("Faturamento Esperado", f"R$ {(total_recebido + total_pendente):.2f}")
            
            st.divider()
            
            df_fin = pd.DataFrame(dados_fin)
            st.subheader("Faturamento por Aluno (Pago vs Pendente)")
            st.bar_chart(df_fin, x="Aluno", y=["Valor Pago", "Saldo Pendente"], color=["#2ECC71", "#E74C3C"])
            
            st.subheader("Tabela Detalhada")
            df_exibicao = df_fin.copy()
            df_exibicao["Total Devido"] = df_exibicao["Total Devido"].apply(lambda x: f"R$ {x:.2f}")
            df_exibicao["Valor Pago"] = df_exibicao["Valor Pago"].apply(lambda x: f"R$ {x:.2f}")
            df_exibicao["Saldo Pendente"] = df_exibicao["Saldo Pendente"].apply(lambda x: f"R$ {x:.2f}")
            
            st.dataframe(df_exibicao, use_container_width=True)
