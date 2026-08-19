import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client

st.set_page_config(page_title="SaaS Personal Trainer", layout="wide")

# Credenciais do Supabase
SUPABASE_URL = "https://vkanwxrjtajiivghyapb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZrYW53eHJqdGFqaWl2Z2h5YXBiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcxNDgzNTYsImV4cCI6MjEwMjcyNDM1Nn0._JhswzxjiNuXnRXHMcpgEbZiEE017RUyn5AHR_pzslo"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if "user" not in st.session_state:
    st.session_state.user = None

# --- TELA DE LOGIN / CADASTRO ---
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
                    st.success("Conta criada! Faça login ao lado.")
                except Exception as e:
                    st.error(f"Erro: {e}")

# --- APLICAÇÃO PRINCIPAL ---
else:
    user_id = st.session_state.user.id
    
    st.sidebar.write(f"Logado como: **{st.session_state.user.email}**")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    st.sidebar.divider()
    menu = st.sidebar.radio("Navegação", ["Calendário / Agenda", "Check-in Diário", "Cadastrar Aluno", "Painel Financeiro"])

    def carregar_alunos():
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
                
            if st.form_submit_button("Salvar Aluno") and nome:
                tipo = "pacote" if tipo_cobranca == "Pacote de Aulas" else "avulso"
                supabase.table("alunos").insert({
                    "user_id": user_id,
                    "nome": nome,
                    "tipo_cobranca": tipo,
                    "valor_aula": valor_aula if tipo == "avulso" else 0.0,
                    "valor_pacote": valor_pacote if tipo == "pacote" else 0.0,
                    "total_aulas_pacote": total_aulas_pacote if tipo == "pacote" else 0,
                    "aulas_restantes": total_aulas_pacote if tipo == "pacote" else 0,
                    "vencimento": vencimento,
                    "presencas": 0,
                    "faltas": 0,
                    "valor_pago": 0.0
                }).execute()
                st.success(f"Aluno {nome} cadastrado!")

    # 2. CALENDÁRIO / AGENDA DE ROTINA
    elif menu == "Calendário / Agenda":
        st.header("📅 Agendamento de Aulas")
        alunos = carregar_alunos()
        
        if not alunos:
            st.warning("Cadastre um aluno primeiro.")
        else:
            mapa_alunos = {a["nome"]: a for a in alunos}
            
            with st.form("form_agendar"):
                aluno_sel = st.selectbox("Aluno", list(mapa_alunos.keys()))
                data_aula = st.date_input("Data", min_value=date.today())
                hora_aula = st.time_input("Horário")
                
                if st.form_submit_button("Marcar na Agenda"):
                    dt_completa = datetime.combine(data_aula, hora_aula).isoformat()
                    supabase.table("agendamentos").insert({
                        "user_id": user_id,
                        "aluno_id": mapa_alunos[aluno_sel]["id"],
                        "data_hora": dt_completa
                    }).execute()
                    st.success("Aula agendada!")

            st.divider()
            st.subheader("Sua Agenda de Hoje e Próximos Dias")
            
            res_agenda = supabase.table("agendamentos").select("*, alunos(nome)").eq("user_id", user_id).order("data_hora").execute()
            if res_agenda.data:
                agenda_df = []
                for item in res_agenda.data:
                    dt = datetime.fromisoformat(item["data_hora"])
                    agenda_df.append({
                        "Data": dt.strftime("%d/%m/%Y"),
                        "Horário": dt.strftime("%H:%M"),
                        "Aluno": item["alunos"]["nome"] if item.get("alunos") else "N/A",
                        "Status": item["status"]
                    })
                st.dataframe(pd.DataFrame(agenda_df), use_container_width=True)

    # 3. CHECK-IN DIÁRIO
    elif menu == "Check-in Diário":
        st.header("Apontamento Diário")
        alunos = carregar_alunos()
        
        if alunos:
            mapa_alunos = {a["nome"]: a for a in alunos}
            aluno = mapa_alunos[st.selectbox("Selecione o Aluno", list(mapa_alunos.keys()))]
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Modalidade", "Pacote" if aluno["tipo_cobranca"] == "pacote" else "Avulso")
            
            if aluno["tipo_cobranca"] == "pacote":
                col2.metric("Aulas Restantes", f"{aluno['aulas_restantes']} / {aluno['total_aulas_pacote']}")
                total_devido = float(aluno["valor_pacote"])
            else:
                col2.metric("Presenças no Mês", aluno["presencas"])
                total_devido = aluno["presencas"] * float(aluno["valor_aula"])
                
            col3.metric("Valor Total Devido", f"R$ {total_devido:.2f}")
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            
            if c1.button("✅ Confirmar Aula (+1)", use_container_width=True):
                novas_presencas = aluno["presencas"] + 1
                update_data = {"presencas": novas_presencas}
                if aluno["tipo_cobranca"] == "pacote" and aluno["aulas_restantes"] > 0:
                    update_data["aulas_restantes"] = aluno["aulas_restantes"] - 1
                
                supabase.table("alunos").update(update_data).eq("id", aluno["id"]).execute()
                st.rerun()
                
            if c2.button("❌ Registrar Falta (+1)", use_container_width=True):
                supabase.table("alunos").update({"faltas": aluno["faltas"] + 1}).eq("id", aluno["id"]).execute()
                st.rerun()
                
            with c3:
                pago = st.number_input("Registrar Pagamento (R$)", min_value=0.0, step=10.0)
                if st.button("💰 Confirmar Pagamento", use_container_width=True):
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
                devido = float(d["valor_pacote"]) if d["tipo_cobranca"] == "pacote" else (d["presencas"] * float(d["valor_aula"]))
                saldo = devido - float(d["valor_pago"])
                relatorio.append({
                    "Aluno": d["nome"],
                    "Tipo": "Pacote" if d["tipo_cobranca"] == "pacote" else "Avulso",
                    "Aulas Restantes": d["aulas_restantes"] if d["tipo_cobranca"] == "pacote" else "N/A",
                    "Total Devido": f"R$ {devido:.2f}",
                    "Valor Pago": f"R$ {float(d['valor_pago']):.2f}",
                    "Saldo Pendente": f"R$ {saldo:.2f}"
                })
            st.dataframe(pd.DataFrame(relatorio), use_container_width=True)
