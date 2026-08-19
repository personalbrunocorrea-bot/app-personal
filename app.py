import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, date, time
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
        "Agenda (Com Check-in)", 
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

    # 2. AGENDA - COM CHECK-IN INTEGRADO
    elif menu == "Agenda (Com Check-in)":
        st.header("📅 Agenda Visual & Registro de Presença")
        
        col_esq, col_dir = st.columns([1, 2.2])
        alunos = carregar_alunos()
        mapa_alunos_id = {a["id"]: a for a in alunos}
        
        with col_esq:
            st.subheader("📌 Agendar Aula")
            if not alunos:
                st.warning("Cadastre um aluno primeiro.")
            else:
                mapa_alunos_nome = {a["nome"]: a for a in alunos}
                with st.form("form_agendar"):
                    aluno_sel = st.selectbox("Selecione o Aluno", list(mapa_alunos_nome.keys()))
                    data_aula = st.date_input("Data da Aula", value=date.today())
                    hora_aula = st.time_input("Horário", value=time(8, 0))
                    
                    if st.form_submit_button("Confirmar Agendamento", use_container_width=True):
                        preparar_cliente()
                        dt_completa = datetime.combine(data_aula, hora_aula).isoformat()
                        supabase.table("agendamentos").insert({
                            "user_id": user_id,
                            "aluno_id": mapa_alunos_nome[aluno_sel]["id"],
                            "data_hora": dt_completa,
                            "status": "agendado"
                        }).execute()
                        st.success("Aula agendada!")
                        st.rerun()

        with col_dir:
            st.subheader("Grade do Dia")
            data_filtro = st.date_input("Visualizar Dia", value=date.today())
            
            preparar_cliente()
            try:
                res_agenda = supabase.table("agendamentos").select("*").eq("user_id", user_id).execute()
                dados_agenda = res_agenda.data or []
            except Exception as e:
                st.error(f"Erro ao carregar agenda: {e}")
                dados_agenda = []

            agendamentos_dia = {}
            for item in dados_agenda:
                dt = datetime.fromisoformat(item["data_hora"])
                if dt.date() == data_filtro:
                    aluno_obj = mapa_alunos_id.get(item["aluno_id"], {})
                    agendamentos_dia[dt.hour] = {
                        "id": item["id"],
                        "aluno_id": item["aluno_id"],
                        "aluno_obj": aluno_obj,
                        "aluno_nome": aluno_obj.get("nome", "Aluno Indefinido"),
                        "telefone": aluno_obj.get("telefone", ""),
                        "minuto": dt.strftime("%M"),
                        "status": item.get("status", "agendado"),
                        "data_str": dt.strftime("%d/%m/%Y"),
                        "hora_str": dt.strftime("%H:%M")
                    }

            for h in range(6, 23):
                hora_label = f"{h:02d}:00"
                if h in agendamentos_dia:
                    info = agendamentos_dia[h]
                    aluno_data = info["aluno_obj"]
                    
                    st.markdown(f"#### ⏰ {hora_label} — **{info['aluno_nome']}** `[{info['status'].upper()}]`")
                    
                    if aluno_data:
                        st.caption(f"📊 Restantes no Pacote: **{aluno_data.get('aulas_restantes', 0)}** | Presenças: {aluno_data.get('presencas', 0)} | Faltas: {aluno_data.get('faltas', 0)}")

                    c_pres, c_falta_cob, c_falta_isenta, c_wsp, c_del = st.columns([1.2, 1.2, 1.3, 1, 0.8])
                    
                    with c_pres:
                        if st.button("✅ Confirmar", key=f"pres_{info['id']}", use_container_width=True):
                            preparar_cliente()
                            supabase.table("agendamentos").update({"status": "realizada"}).eq("id", info["id"]).execute()
                            if aluno_data:
                                upd = {"presencas": aluno_data["presencas"] + 1}
                                if aluno_data["tipo_cobranca"] == "pacote" and aluno_data["aulas_restantes"] > 0:
                                    upd["aulas_restantes"] = aluno_data["aulas_restantes"] - 1
                                supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()
                            st.success("Presença computada!")
                            st.rerun()

                    with c_falta_cob:
                        if st.button("❌ F. Cobrada", key=f"fcob_{info['id']}", use_container_width=True):
                            preparar_cliente()
                            supabase.table("agendamentos").update({"status": "falta_cobrada"}).eq("id", info["id"]).execute()
                            if aluno_data:
                                upd = {"faltas": aluno_data["faltas"] + 1}
                                if aluno_data["tipo_cobranca"] == "pacote" and aluno_data["aulas_restantes"] > 0:
                                    upd["aulas_restantes"] = aluno_data["aulas_restantes"] - 1
                                supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()
                            st.warning("Falta cobrada registrada!")
                            st.rerun()

                    with c_falta_isenta:
                        if st.button("🟡 F. Isenta", key=f"fise_{info['id']}", use_container_width=True):
                            preparar_cliente()
                            supabase.table("agendamentos").update({"status": "falta_isenta"}).eq("id", info["id"]).execute()
                            st.info("Falta desconsiderada!")
                            st.rerun()

                    with c_wsp:
                        if info["telefone"]:
                            msg = f"Olá {info['aluno_nome']}! Lembrando do nosso treino agendado para {info['data_str']} às {info['hora_str']}."
                            link_wsp = f"https://wa.me/{info['telefone']}?text={urllib.parse.quote(msg)}"
                            st.link_button("💬 WSP", link_wsp, use_container_width=True)
                        else:
                            st.caption("Sem WSP")

                    with c_del:
                        if st.button("🗑️", key=f"del_{info['id']}", use_container_width=True):
                            preparar_cliente()
                            supabase.table("agendamentos").delete().eq("id", info["id"]).execute()
                            st.rerun()
                    
                    st.divider()
                else:
                    st.write(f"⏱️ `{hora_label}` — *Livre*")

    # 3. PERFIL DO ALUNO (SÓ FREQUÊNCIA E VALORES/FINANCEIRO)
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
            st.subheader("1️⃣ Monitoramento de Aulas e Frequência")
            
            c_freq1, c_freq2, c_freq3, c_freq4 = st.columns(4)
            c_freq1.metric("Presenças Confirmadas", aluno["presencas"])
            c_freq2.metric("Faltas Cobradas", aluno["faltas"])
            
            if aluno["tipo_cobranca"] == "pacote":
                c_freq3.metric("Aulas Restantes no Pacote", f"{aluno['aulas_restantes']} / {aluno['total_aulas_pacote']}")
                with c_freq4:
                    st.write("")
                    if st.button("🔄 Renovar Pacote", use_container_width=True):
                        preparar_cliente()
                        novas_restantes = aluno["aulas_restantes"] + aluno["total_aulas_pacote"]
                        supabase.table("alunos").update({"aulas_restantes": novas_restantes}).eq("id", aluno["id"]).execute()
                        st.success(f"Pacote renovado com +{aluno['total_aulas_pacote']} aulas!")
                        st.rerun()
            else:
                aulas_computadas = aluno["presencas"] + aluno["faltas"]
                c_freq3.metric("Total de Aulas Realizadas", aulas_computadas)
                c_freq4.caption("Modalidade: Aula Avulsa")

            # Histórico de Aulas da Agenda
            preparar_cliente()
            res_ag = supabase.table("agendamentos").select("*").eq("aluno_id", aluno["id"]).execute()
            historico_aulas = res_ag.data or []
            
            st.markdown("##### 📜 Histórico de Aulas Agendadas")
            if historico_aulas:
                lista_hist = []
                for h in historico_aulas:
                    dt = datetime.fromisoformat(h["data_hora"])
                    lista_hist.append({
                        "Data": dt.strftime("%d/%m/%Y"),
                        "Horário": dt.strftime("%H:%M"),
                        "Status": h.get("status", "agendado").upper()
                    })
                df_hist = pd.DataFrame(lista_hist).sort_values(by=["Data", "Horário"], ascending=False)
                st.dataframe(df_hist, use_container_width=True)
            else:
                st.info("Nenhuma aula registrada para este aluno na agenda.")

            st.divider()

            # BLOCO 2: CONTROLE FINANCEIRO E VALORES
            st.subheader("2️⃣ Controle Financeiro e Valores")
            
            aulas_computadas = aluno["presencas"] + aluno["faltas"]
            total_devido = float(aluno["valor_pacote"]) if aluno["tipo_cobranca"] == "pacote" else (aulas_computadas * float(aluno["valor_aula"]))
            valor_pago = float(aluno["valor_pago"])
            saldo_pendente = total_devido - valor_pago
            
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Tipo de Plano", "Pacote" if aluno["tipo_cobranca"] == "pacote" else "Avulso")
            f2.metric("Total Devido", f"R$ {total_devido:.2f}")
            f3.metric("Valor Já Pago", f"R$ {valor_pago:.2f}")
            f4.metric("Saldo Pendente", f"R$ {max(0.0, saldo_pendente):.2f}", delta_color="inverse")

            st.caption(f"📅 Dia de Vencimento do Pagamento: Todo dia **{aluno['vencimento']}**")
            
            with st.expander("💰 Registrar Novo Pagamento"):
                with st.form(f"form_pag_{aluno['id']}"):
                    v_pago = st.number_input("Valor Recebido (R$)", min_value=0.0, step=10.0, value=float(max(0.0, saldo_pendente)))
                    if st.form_submit_button("Confirmar Recebimento"):
                        preparar_cliente()
                        novo_pago = valor_pago + v_pago
                        supabase.table("alunos").update({"valor_pago": novo_pago}).eq("id", aluno["id"]).execute()
                        st.success("Pagamento registrado!")
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
                aulas_computadas = d["presencas"] + d["faltas"]
                devido = float(d["valor_pacote"]) if d["tipo_cobranca"] == "pacote" else (aulas_computadas * float(d["valor_aula"]))
                pago = float(d["valor_pago"])
                saldo = devido - pago
                
                total_recebido += pago
                total_pendente += max(0.0, saldo)
                
                dados_fin.append({
                    "Aluno": d["nome"],
                    "Tipo": "Pacote" if d["tipo_cobranca"] == "pacote" else "Avulso",
                    "Presenças": d["presencas"],
                    "Faltas": d["faltas"],
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
