import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import uuid
from supabase import create_client, Client

st.set_page_config(page_title="Studio Personal - Gestão", layout="wide")

# -------------------------------------------------------------------
# INICIALIZAÇÃO SUPABASE
# -------------------------------------------------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

def get_supabase_client() -> Client:
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return st.session_state.supabase_client

# -------------------------------------------------------------------
# ROTEAMENTO PÁGINA PÚBLICA (PAR-Q)
# -------------------------------------------------------------------
query_params = st.query_params
if "token" in query_params:
    token = query_params["token"]
    st.title("📋 Questionário PAR-Q")
    st.write("Por favor, responda ao questionário antes de iniciar seus treinos.")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    res = client.table("alunos").select("*").eq("parq_token", token).execute()
    
    if not res.data:
        st.error("Link inválido ou não encontrado.")
        st.stop()
        
    aluno = res.data[0]
    expira_em = datetime.fromisoformat(aluno["parq_expires_at"].replace("Z", "+00:00"))
    
    if datetime.now().astimezone() > expira_em:
        st.error("Este link do PAR-Q expirou. Solicite um novo ao seu Personal Trainer.")
        st.stop()

    if aluno.get("parq_status") == "Concluído":
        st.success("Obrigado! Você já respondeu este questionário.")
        st.stop()

    st.subheader(f"Olá, {aluno['nome']}!")
    
    perguntas = [
        "1. Seu médico já disse que você possui algum problema de coração e que só deve realizar atividade física supervisionada?",
        "2. Você sente dores no peito quando pratica atividade física?",
        "3. No último mês, você sentiu dor no peito quando não estava praticando atividade física?",
        "4. Você apresenta perda de balanço devido a tontura ou desmaio?",
        "5. Você tem algum problema ósseo ou articular que poderia ser agravado pela atividade física?",
        "6. Seu médico prescreve medicamentos para pressão alta ou problema cardíaco?",
        "7. Sabe de alguma outra razão pela qual você não deve praticar atividade física?"
    ]

    respostas = {}
    with st.form("parq_form"):
        for idx, q in enumerate(perguntas):
            respostas[f"q{idx+1}"] = st.radio(q, ["Não", "Sim"], index=0)
        
        obs = st.text_area("Observações de saúde adicionais (opcional):")
        submitted = st.form_submit_button("Enviar Respostas")

        if submitted:
            tem_restricao = any(r == "Sim" for r in respostas.values())
            respostas["observacoes"] = obs
            
            client.table("alunos").update({
                "parq_status": "Concluído",
                "parq_respostas": respostas,
                "tem_restricao_saude": tem_restricao,
                "parq_respondido_em": datetime.now().isoformat()
            }).eq("id", aluno["id"]).execute()

            st.success("Questionário enviado com sucesso!")
            st.rerun()

    st.stop()

# -------------------------------------------------------------------
# ÁREA PRIVADA (PERSONAL TRAINER)
# -------------------------------------------------------------------
supabase = get_supabase_client()

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login - Studio Personal")
    tab_login, tab_cadastro = st.tabs(["Entrar", "Criar Conta"])
    
    with tab_login:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao entrar: {e}")

    with tab_cadastro:
        novo_email = st.text_input("E-mail para Cadastro")
        nova_senha = st.text_input("Senha para Cadastro", type="password")
        if st.button("Cadastrar"):
            try:
                res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                st.success("Conta criada! Faça login.")
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")
    st.stop()

# -------------------------------------------------------------------
# MENU PRINCIPAL DO PERSONAL
# -------------------------------------------------------------------
user_id = st.session_state.user.id

st.sidebar.title("🏋️ Studio Manager")
if st.sidebar.button("Sair / Logout"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

menu = st.sidebar.radio("Navegação", ["📅 Calendário & Presença", "👤 Alunos & PAR-Q", "🏋️ Fichas de Treino", "💰 Financeiro & Hora-Aula"])

# -------------------------------------------------------------------
# 1. CALENDÁRIO, PRESENÇA, FALTA E HORA-AULA
# -------------------------------------------------------------------
if menu == "📅 Calendário & Presença":
    st.header("📅 Agenda de Aulas & Controle de Presença")
    
    alunos_res = supabase.table("alunos").select("id, nome, valor_hora_aula").eq("user_id", user_id).execute()
    dict_alunos = {a["nome"]: a for a in alunos_res.data} if alunos_res.data else {}

    col_form, col_cal = st.columns([1, 2])

    with col_form:
        st.subheader("➕ Agendar Nova Aula")
        if dict_alunos:
            aluno_sel = st.selectbox("Aluno", list(dict_alunos.keys()))
            data_aula = st.date_input("Data", datetime.now())
            hora_aula = st.time_input("Horário", time(8, 0))
            tipo_aula = st.selectbox("Tipo", ["Personal Training", "Avaliação Física", "Consultoria"])
            
            aluno_obj = dict_alunos[aluno_sel]
            valor_sugerido = float(aluno_obj.get("valor_hora_aula", 0.0))
            valor_aula = st.number_input("Valor da Aula (R$)", value=valor_sugerido, step=10.0)

            if st.button("Confirmar Agendamento"):
                dt_combinada = datetime.combine(data_aula, hora_aula).isoformat()
                supabase.table("agendamentos").insert({
                    "aluno_id": aluno_obj["id"],
                    "data_hora": dt_combinada,
                    "tipo": tipo_aula,
                    "status": "Agendado",
                    "valor_aula": valor_aula,
                    "user_id": user_id
                }).execute()
                st.success("Aula agendada!")
                st.rerun()
        else:
            st.info("Cadastre alunos primeiro para agendar aulas.")

    with col_cal:
        st.subheader("📋 Aulas Agendadas")
        filtro_data = st.date_input("Filtrar por Dia", datetime.now())
        
        inicio_dia = datetime.combine(filtro_data, time.min).isoformat()
        fim_dia = datetime.combine(filtro_data, time.max).isoformat()

        agendamentos = supabase.table("agendamentos")\
            .select("*, alunos(nome)")\
            .eq("user_id", user_id)\
            .gte("data_hora", inicio_dia)\
            .lte("data_hora", fim_dia)\
            .order("data_hora")\
            .execute()

        if agendamentos.data:
            for item in agendamentos.data:
                dt = datetime.fromisoformat(item["data_hora"].replace("Z", ""))
                aluno_nome = item["alunos"]["nome"] if item.get("alunos") else "Aluno Desconhecido"
                status_atual = item["status"]
                
                cor = "🔵" if status_atual == "Agendado" else ("🟢" if status_atual == "Presença" else ("🔴" if status_atual == "Falta" else "🟡"))

                with st.expander(f"{cor} {dt.strftime('%H:%M')} - {aluno_nome} ({status_atual})"):
                    st.write(f"**Tipo:** {item['tipo']} | **Valor:** R$ {item['valor_aula']:.2f}")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    if c1.button("🟢 Presença", key=f"p_{item['id']}"):
                        supabase.table("agendamentos").update({"status": "Presença"}).eq("id", item["id"]).execute()
                        st.rerun()

                    if c2.button("🔴 Falta", key=f"f_{item['id']}"):
                        supabase.table("agendamentos").update({"status": "Falta"}).eq("id", item["id"]).execute()
                        st.rerun()

                    if c3.button("🟡 Desmarcada", key=f"d_{item['id']}"):
                        supabase.table("agendamentos").update({"status": "Desmarcada"}).eq("id", item["id"]).execute()
                        st.rerun()

                    if c4.button("🗑️ Cancelar", key=f"del_{item['id']}"):
                        supabase.table("agendamentos").delete().eq("id", item["id"]).execute()
                        st.rerun()
        else:
            st.write("Nenhuma aula agendada para esta data.")

# -------------------------------------------------------------------
# 2. ALUNOS & HORA-AULA & PAR-Q
# -------------------------------------------------------------------
elif menu == "👤 Alunos & PAR-Q":
    st.header("👤 Gestão de Alunos & PAR-Q")
    
    with st.expander("➕ Cadastrar Novo Aluno", expanded=False):
        with st.form("form_aluno"):
            nome = st.text_input("Nome Completo*")
            email = st.text_input("E-mail")
            telefone = st.text_input("Telefone / WhatsApp")
            objetivo = st.text_input("Objetivo (ex: Hipertrofia, Emagrecimento)")
            valor_hora = st.number_input("Valor da Hora-Aula (R$)", value=80.0, step=5.0)
            
            if st.form_submit_button("Salvar Aluno"):
                if nome:
                    supabase.table("alunos").insert({
                        "nome": nome,
                        "email": email,
                        "telefone": telefone,
                        "objetivo": objetivo,
                        "valor_hora_aula": valor_hora,
                        "user_id": user_id
                    }).execute()
                    st.success("Aluno cadastrado!")
                    st.rerun()
                else:
                    st.error("O campo Nome é obrigatório.")

    # Listagem de Alunos
    alunos = supabase.table("alunos").select("*").eq("user_id", user_id).order("nome").execute()
    if alunos.data:
        for a in alunos.data:
            col_info, col_parq = st.columns([2, 1])
            with col_info:
                st.markdown(f"### {a['nome']}")
                st.write(f"📞 {a.get('telefone', 'N/A')} | ✉️ {a.get('email', 'N/A')}")
                st.write(f"🎯 **Objetivo:** {a.get('objetivo', 'N/A')} | 💵 **Hora-Aula:** R$ {a.get('valor_hora_aula', 0.0):.2f}")
                
            with col_parq:
                status_parq = a.get("parq_status", "Pendente")
                st.write(f"**PAR-Q:** {status_parq}")
                
                if a.get("tem_restricao_saude"):
                    st.error("⚠️ Possui restrição de saúde!")

                if st.button("🔗 Gerar Link PAR-Q", key=f"link_{a['id']}"):
                    token = str(uuid.uuid4())
                    expiracao = (datetime.now() + timedelta(hours=72)).isoformat()
                    
                    supabase.table("alunos").update({
                        "parq_token": token,
                        "parq_expires_at": expiracao,
                        "parq_status": "Aguardando Resposta"
                    }).eq("id", a["id"]).execute()
                    
                    st.success("Link gerado com validade de 72h!")
                    st.code(f"https://seu-app.streamlit.app/?token={token}")
            st.divider()

# -------------------------------------------------------------------
# 3. FICHAS DE TREINO
# -------------------------------------------------------------------
elif menu == "🏋️ Fichas de Treino":
    st.header("🏋️ Prescrição de Treinos")
    
    alunos_res = supabase.table("alunos").select("id, nome").eq("user_id", user_id).execute()
    if alunos_res.data:
        dict_alunos = {a["nome"]: a["id"] for a in alunos_res.data}
        aluno_sel = st.selectbox("Selecione o Aluno", list(dict_alunos.keys()))
        aluno_id = dict_alunos[aluno_sel]

        tab_nova, tab_ver = st.tabs(["➕ Criar Ficha", "📋 Fichas Ativas"])
        
        with tab_nova:
            nome_ficha = st.text_input("Nome da Ficha (ex: Treino A - Peito e Tríceps)")
            detalhes = st.text_area("Exercícios, Séries e Repetições", height=150)
            if st.button("Salvar Ficha"):
                if nome_ficha and detalhes:
                    supabase.table("treinos").insert({
                        "aluno_id": aluno_id,
                        "nome_ficha": nome_ficha,
                        "detalhes": detalhes,
                        "user_id": user_id
                    }).execute()
                    st.success("Ficha salva!")
                    st.rerun()

        with tab_ver:
            fichas = supabase.table("treinos").select("*").eq("aluno_id", aluno_id).execute()
            if fichas.data:
                for f in fichas.data:
                    st.subheader(f["nome_ficha"])
                    st.text(f["detalhes"])
                    if st.button("🗑️ Excluir Ficha", key=f"del_ficha_{f['id']}"):
                        supabase.table("treinos").delete().eq("id", f["id"]).execute()
                        st.rerun()
            else:
                st.info("Nenhuma ficha cadastrada para este aluno.")
    else:
        st.info("Cadastre alunos para prescrever treinos.")

# -------------------------------------------------------------------
# 4. FINANCEIRO & RESUMO DE HORA-AULA
# -------------------------------------------------------------------
elif menu == "💰 Financeiro & Hora-Aula":
    st.header("💰 Balanço Financeiro & Relatório de Aulas")

    st.subheader("📊 Relatório de Aulas Realizadas (Mês Atual)")
    
    agendamentos_mes = supabase.table("agendamentos")\
        .select("status, valor_aula, alunos(nome)")\
        .eq("user_id", user_id)\
        .execute()

    if agendamentos_mes.data:
        df_aulas = pd.DataFrame(agendamentos_mes.data)
        
        presencas = df_aulas[df_aulas["status"] == "Presença"]
        faltas = df_aulas[df_aulas["status"] == "Falta"]
        desmarcadas = df_aulas[df_aulas["status"] == "Desmarcada"]
        
        faturamento_aulas = presencas["valor_aula"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Aulas Realizadas", len(presencas))
        m2.metric("Faltas", len(faltas))
        m3.metric("Desmarcadas", len(desmarcadas))
        m4.metric("Total Aulas (R$)", f"R$ {faturamento_aulas:.2f}")

    st.divider()

    st.subheader("💵 Caixa Geral (Receitas e Despesas)")
    
    col_lancar, col_kpi = st.columns([1, 1])
    
    with col_lancar:
        with st.form("form_transacao"):
            desc = st.text_input("Descrição (ex: Mensalidade, Equipamento)")
            val = st.number_input("Valor (R$)", value=0.0, step=10.0)
            tipo_trans = st.radio("Tipo", ["Receita", "Despesa"], horizontal=True)
            
            if st.form_submit_button("Registrar no Caixa"):
                valor_final = val if tipo_trans == "Receita" else -val
                supabase.table("transacoes").insert({
                    "descricao": desc,
                    "valor": valor_final,
                    "user_id": user_id
                }).execute()
                st.success("Lançamento efetuado!")
                st.rerun()

    with col_kpi:
        trans = supabase.table("transacoes").select("*").eq("user_id", user_id).execute()
        if trans.data:
            df_t = pd.DataFrame(trans.data)
            rec = df_t[df_t["valor"] > 0]["valor"].sum()
            desp = df_t[df_t["valor"] < 0]["valor"].sum()
            saldo = rec + desp

            st.metric("Receitas Totais", f"R$ {rec:.2f}")
            st.metric("Despesas Totais", f"R$ {abs(desp):.2f}")
            st.metric("Saldo Líquido", f"R$ {saldo:.2f}")
