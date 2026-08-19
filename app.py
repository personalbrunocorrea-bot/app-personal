import streamlit as st
import pandas as pd
from datetime import datetime, date, time
from supabase import create_client, Client

st.set_page_config(page_title="SaaS Personal Trainer", layout="wide")

SUPABASE_URL = "https://vkanwxrjtajiivghyapb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZrYW53eHJqdGFqaWl2Z2h5YXBiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcxNDgzNTYsImV4cCI6MjEwMjcyNDM1Nn0._JhswzxjiNuXnRXHMcpgEbZiEE017RUyn5AHR_pzslo"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Gerenciamento de Sessao
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
    menu = st.sidebar.radio("Navegação", ["Agenda (Estilo Google Agenda)", "Check-in Diário", "Cadastrar Aluno", "Painel Financeiro"])

    def carregar_alunos():
        preparar_cliente()
        res = supabase.table("alunos").select("*").eq("user_id", user_id).execute()
        return res.data

    # 1. CADASTRO DE ALUNOS
    if menu == "Cadastrar Aluno":
        st.header("Cadastrar Novo Aluno")
        with st.form("form_cadastro"):
            nome = st.text_input("Nome do Aluno")
            tipo_cobranca = st.selectbox("Tipo de Cobrança", ["Aula Avulsa", "Pacote de Aulas"])
            
            c1, c2 = st.columns(2)
            with c1:
                valor_aula = st.number_input("Valor p/ Aula (R$)", min_value=0.0, value=80.0, disabled=(tipo_cobranca == "Pacote de Aulas"))
                valor_pacote = st.number_input("Valor do Pacote (R$)", min_value=0.0, value=600.0, disabled=(tipo_cobranca == "Aula Avulsa"))
            with c2:
                total_aulas_pacote = st.number_input("Qtd de Aulas no Pacote", min_value=1, value=10, disabled=(tipo_cobranca == "Aula Avulsa"))
                vencimento = st.number_input("Dia do Vencimento", min_value=1, max_value=31, value=10)
                
            btn_salvar = st.form_submit_button("Salvar Aluno")
            
            if btn_salvar:
                if not nome:
                    st.warning("Por favor, preencha o nome do aluno.")
                else:
                    tipo = "pacote" if tipo_cobranca == "Pacote de Aulas" else "avulso"
                    try:
                        preparar_cliente()
                        dados = {
                            "user_id": user_id,
                            "nome": nome,
                            "tipo_cobranca": tipo,
                            "valor_aula": float(valor_aula) if tipo == "avulso" else 0.0,
                            "valor_pacote": float(valor_pacote) if tipo == "pacote" else 0.0,
                            "total_aulas_pacote": int(total_aulas_pacote) if tipo == "pacote" else 0,
                            "aulas_restantes": int(total_aulas_pacote) if tipo == "pacote" else 0,
                            "vencimento": int(vencimento),
                            "presencas": 0,
                            "faltas": 0,
                            "valor_pago": 0.0
                        }
                        supabase.table("alunos").insert(dados).execute()
                        st.success(f"Aluno {nome} cadastrado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco de dados: {e}")

    # 2. AGENDA - ESTILO GOOGLE AGENDA COM CANCELAMENTO
    elif menu == "Agenda (Estilo Google Agenda)":
        st.header("📅 Agenda Visual do Professor")
        
        col_esq, col_dir = st.columns([1, 2])
        alunos = carregar_alunos()
        
        with col_esq:
            st.subheader("Agendar Nova Aula")
            if not alunos:
                st.warning("Cadastre um aluno primeiro.")
            else:
                mapa_alunos = {a["nome"]: a for a in alunos}
                with st.form("form_agendar"):
                    aluno_sel = st.selectbox("Aluno", list(mapa_alunos.keys()))
                    data_aula = st.date_input("Data", value=date.today())
                    hora_aula = st.time_input("Horário", value=time(8, 0))
                    
                    if st.form_submit_button("Confirmar Agendamento", use_container_width=True):
                        preparar_cliente()
                        dt_completa = datetime.combine(data_aula, hora_aula).isoformat()
                        supabase.table("agendamentos").insert({
                            "user_id": user_id,
                            "aluno_id": mapa_alunos[aluno_sel]["id"],
                            "data_hora": dt_completa,
                            "status": "agendado"
                        }).execute()
                        st.success("Aula agendada!")
                        st.rerun()

        with col_dir:
            st.subheader("Grade Horária")
            data_filtro = st.date_input("Selecionar Dia para Visualizar", value=date.today())
            
            preparar_cliente()
            res_agenda = supabase.table("agendamentos").select("*, alunos(nome)").eq("user_id", user_id).execute()
            
            # Mapeamento de agendamentos por hora no dia selecionado
            agendamentos_dia = {}
            if res_agenda.data:
                for item in res_agenda.data:
                    dt = datetime.fromisoformat(item["data_hora"])
                    if dt.date() == data_filtro:
                        agendamentos_dia[dt.hour] = {
                            "id": item["id"],
                            "aluno": item["alunos"]["nome"] if item.get("alunos") else "Desconhecido",
                            "minuto": dt.strftime("%M"),
                            "status": item.get("status", "agendado")
                        }

            # Visualização em linha do tempo (6h às 22h)
            for h in range(6, 23):
                hora_str = f"{h:02d}:00"
                if h in agendamentos_dia:
                    info = agendamentos_dia[h]
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.info(f"⏰ **{hora_str}** (às {h:02d}:{info['minuto']}) — 👤 **{info['aluno']}** [{info['status'].upper()}]")
                    with col_btn:
                        if st.button("🗑️ Desmarcar", key=f"del_{info['id']}", use_container_width=True):
                            preparar_cliente()
                            supabase.table("agendamentos").delete().eq("id", info["id"]).execute()
                            st.success("Agendamento desmarcado!")
                            st.rerun()
                else:
                    st.write(f"⏱️ `{hora_str}` — *Livre*")

    # 3. CHECK-IN DIÁRIO (PRESENÇA E FALTA)
    elif menu == "Check-in Diário":
        st.header("Apontamento Diário e Faltas")
        alunos = carregar_alunos()
        
        if alunos:
            mapa_alunos = {a["nome"]: a for a in alunos}
            aluno = mapa_alunos[st.selectbox("Selecione o Aluno", list(mapa_alunos.keys()))]
            
            aulas_computadas = aluno["presencas"] + aluno["faltas"]
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Modalidade", "Pacote" if aluno["tipo_cobranca"] == "pacote" else "Aula Avulsa")
            
            if aluno["tipo_cobranca"] == "pacote":
                col2.metric("Aulas Restantes", f"{aluno['aulas_restantes']} / {aluno['total_aulas_pacote']}")
                total_devido = float(aluno["valor_pacote"])
            else:
                col2.metric("Aulas Computadas (Presença + Falta)", aulas_computadas)
                total_devido = aulas_computadas * float(aluno["valor_aula"])
                
            col3.metric("Valor Total Devido", f"R$ {total_devido:.2f}")
            
            st.caption(f"📌 **Resumo:** {aluno['presencas']} Presenças | {aluno['faltas']} Faltas Não Justificadas")
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            
            if c1.button("✅ Confirmar Aula (+1)", use_container_width=True):
                preparar_cliente()
                novas_presencas = aluno["presencas"] + 1
                update_data = {"presencas": novas_presencas}
                if aluno["tipo_cobranca"] == "pacote" and aluno["aulas_restantes"] > 0:
                    update_data["aulas_restantes"] = aluno["aulas_restantes"] - 1
                
                supabase.table("alunos").update(update_data).eq("id", aluno["id"]).execute()
                st.success("Presença registrada!")
                st.rerun()
                
            if c2.button("❌ Falta Não Justificada (+1)", use_container_width=True):
                preparar_cliente()
                novas_faltas = aluno["faltas"] + 1
                update_data = {"faltas": novas_faltas}
                if aluno["tipo_cobranca"] == "pacote" and aluno["aulas_restantes"] > 0:
                    update_data["aulas_restantes"] = aluno["aulas_restantes"] - 1
                    
                supabase.table("alunos").update(update_data).eq("id", aluno["id"]).execute()
                st.warning("Falta registrada e computada no valor!")
                st.rerun()
                
            with c3:
                pago = st.number_input("Registrar Pagamento (R$)", min_value=0.0, step=10.0)
                if st.button("💰 Confirmar Pagamento", use_container_width=True):
                    preparar_cliente()
                    novo_total_pago = float(aluno["valor_pago"]) + pago
                    supabase.table("alunos").update({"valor_pago": novo_total_pago}).eq("id", aluno["id"]).execute()
                    st.success("Pagamento registrado!")
                    st.rerun()

    # 4. PAINEL FINANCEIRO
    elif menu == "Painel Financeiro":
        st.header("Resumo Financeiro")
        alunos = carregar_alunos()
        if alunos:
            relatorio = []
            for d in alunos:
                aulas_computadas = d["presencas"] + d["faltas"]
                devido = float(d["valor_pacote"]) if d["tipo_cobranca"] == "pacote" else (aulas_computadas * float(d["valor_aula"]))
                saldo = devido - float(d["valor_pago"])
                relatorio.append({
                    "Aluno": d["nome"],
                    "Tipo": "Pacote" if d["tipo_cobranca"] == "pacote" else "Avulso",
                    "Presenças": d["presencas"],
                    "Faltas Cobradas": d["faltas"],
                    "Total Devido": f"R$ {devido:.2f}",
                    "Valor Pago": f"R$ {float(d['valor_pago']):.2f}",
                    "Saldo Pendente": f"R$ {saldo:.2f}"
                })
            st.dataframe(pd.DataFrame(relatorio), use_container_width=True)
