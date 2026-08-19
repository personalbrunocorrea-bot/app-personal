import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="SaaS Personal Trainer", layout="wide")

# Configuração do Supabase com suas credenciais
SUPABASE_URL = "https://vkanwxrjtajiivghyapb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZrYW53eHJqdGFqaWl2Z2h5YXBiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcxNDgzNTYsImV4cCI6MjEwMjcyNDM1Nn0._JhswzxjiNuXnRXHMcpgEbZiEE017RUyn5AHR_pzslo"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Gerenciamento de Sessão de Login
if "user" not in st.session_state:
    st.session_state.user = None

# --- TELA DE LOGIN / CADASTRO (SE NÃO ESTIVER LOGADO) ---
if st.session_state.user is None:
    st.title("🏋️ Painel do Personal Trainer - Login")
    
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Conta"])
    
    with aba_login:
        with st.form("form_login"):
            email_login = st.text_input("E-mail")
            senha_login = st.text_input("Senha", type="password")
            btn_entrar = st.form_submit_button("Entrar no Sistema")
            
            if btn_entrar:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                    st.session_state.user = res.user
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error("E-mail ou senha incorretos.")
                    
    with aba_cadastro:
        with st.form("form_cad_user"):
            email_cad = st.text_input("E-mail para Cadastro")
            senha_cad = st.text_input("Crie uma Senha", type="password")
            btn_cad = st.form_submit_button("Cadastrar Conta")
            
            if btn_cad:
                try:
                    res = supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                    st.success("Conta criada! Verifique seu e-mail ou faça login na aba ao lado.")
                except Exception as e:
                    st.error(f"Erro ao criar conta: {e}")

# --- APLICAÇÃO PRINCIPAL (QUANDO LOGADO) ---
else:
    user_id = st.session_state.user.id
    
    # Barra lateral com dados do usuário e botão de saída
    st.sidebar.write(f"Logado como: **{st.session_state.user.email}**")
    if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    st.sidebar.divider()
    menu = st.sidebar.radio("Navegação", ["Check-in / Agenda", "Cadastrar Aluno", "Painel Financeiro"])

    st.title("🏋️ Gestão de Alunos & Presença")

    # Função para carregar alunos apenas do personal logado
    def carregar_alunos():
        res = supabase.table("alunos").select("*").eq("user_id", user_id).execute()
        return res.data

    # 1. TELA DE CADASTRO
    if menu == "Cadastrar Aluno":
        st.header("Cadastrar Novo Aluno")
        
        with st.form("form_cadastro"):
            nome = st.text_input("Nome do Aluno")
            valor_aula = st.number_input("Valor por Aula (R$)", min_value=0.0, value=80.0, step=5.0)
            vencimento = st.number_input("Dia do Vencimento", min_value=1, max_value=31, value=10)
            
            btn_cadastrar = st.form_submit_button("Salvar Aluno")
            
            if btn_cadastrar and nome:
                try:
                    supabase.table("alunos").insert({
                        "user_id": user_id,
                        "nome": nome,
                        "valor_aula": valor_aula,
                        "vencimento": vencimento,
                        "presencas": 0,
                        "faltas": 0,
                        "valor_pago": 0.0
                    }).execute()
                    st.success(f"Aluno {nome} salvo com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")

    # 2. TELA DE CHECK-IN DIÁRIO
    elif menu == "Check-in / Agenda":
        st.header("Apontamento Diário de Aulas")
        alunos = carregar_alunos()
        
        if not alunos:
            st.warning("Nenhum aluno cadastrado ainda.")
        else:
            mapa_alunos = {a["nome"]: a for a in alunos}
            aluno_sel_nome = st.selectbox("Selecione o Aluno", list(mapa_alunos.keys()))
            aluno = mapa_alunos[aluno_sel_nome]
            
            total_devido = aluno["presencas"] * float(aluno["valor_aula"])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Presenças no Mês", aluno["presencas"])
            col2.metric("Faltas no Mês", aluno["faltas"])
            col3.metric("Valor a Pagar", f"R$ {total_devido:.2f}")
            
            st.divider()
            
            c1, c2, c3 = st.columns(3)
            if c1.button("✅ Registrar Presença (+1)", use_container_width=True):
                nova_presenca = aluno["presencas"] + 1
                supabase.table("alunos").update({"presencas": nova_presenca}).eq("id", aluno["id"]).execute()
                st.rerun()
                
            if c2.button("❌ Registrar Falta (+1)", use_container_width=True):
                nova_falta = aluno["faltas"] + 1
                supabase.table("alunos").update({"faltas": nova_falta}).eq("id", aluno["id"]).execute()
                st.rerun()
                
            with c3:
                pagamento = st.number_input("Registrar Pagamento (R$)", min_value=0.0, step=10.0)
                if st.button("💰 Confirmar Pagamento", use_container_width=True):
                    novo_pago = float(aluno["valor_pago"]) + pagamento
                    supabase.table("alunos").update({"valor_pago": novo_pago}).eq("id", aluno["id"]).execute()
                    st.success("Pagamento registrado!")
                    st.rerun()

    # 3. PAINEL FINANCEIRO
    elif menu == "Painel Financeiro":
        st.header("Resumo do Mês")
        alunos = carregar_alunos()
        
        if not alunos:
            st.info("Nenhum dado para exibir.")
        else:
            relatorio = []
            for d in alunos:
                total_devido = d["presencas"] * float(d["valor_aula"])
                saldo = total_devido - float(d["valor_pago"])
                
                relatorio.append({
                    "Aluno": d["nome"],
                    "Vencimento": f"Dia {d['vencimento']}",
                    "Presenças": d["presencas"],
                    "Faltas": d["faltas"],
                    "Total Devido (R$)": f"R$ {total_devido:.2f}",
                    "Valor Pago (R$)": f"R$ {float(d['valor_pago']):.2f}",
                    "Saldo Pendente (R$)": f"R$ {saldo:.2f}"
                })
                
            st.dataframe(pd.DataFrame(relatorio), use_container_width=True)
