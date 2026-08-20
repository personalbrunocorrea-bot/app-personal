import streamlit as st
import secrets
import json
from datetime import datetime, date, time
import pandas as pd
from supabase import create_client, Client
from postgrest.exceptions import APIError

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DE PÁGINA E CONEXÃO
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Gestão de Estúdio & Treinos", layout="wide", page_icon="🏋️‍♂️")

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("⚠️ Configurações do Supabase ausentes em .streamlit/secrets.toml")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()

def preparar_cliente():
    """Garante a inicialização do estado de sessão e ID do usuário autenticado."""
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = "00000000-0000-0000-0000-000000000000"
    return st.session_state["user_id"]

USER_ID = preparar_cliente()

def exibir_erro_api(e: APIError, contexto: str):
    """Trata e exibe os detalhes do erro do PostgREST/Supabase no Streamlit."""
    st.error(f"🚨 **Erro de Banco de Dados [{contexto}]:**")
    st.warning(f"**Mensagem:** {e.message}")
    st.code(f"Código: {getattr(e, 'code', 'N/A')}\nDetalhes: {getattr(e, 'details', 'N/A')}\nDica: {getattr(e, 'hint', 'N/A')}")

# -----------------------------------------------------------------------------
# MENU LATERAL
# -----------------------------------------------------------------------------
st.sidebar.title("🏋️ Studio & Personal Trainer")
menu = st.sidebar.radio(
    "Navegação", 
    ["Dashboard", "Alunos & Ficha de Treino", "Agenda & Presenças", "Financeiro", "Responder PAR-Q (Público)"]
)

# -----------------------------------------------------------------------------
# 1. DASHBOARD
# -----------------------------------------------------------------------------
if menu == "Dashboard":
    st.title("📊 Painel Geral do Estúdio")

    try:
        preparar_cliente()
        res_alunos = supabase.table("alunos").select("id, status, aulas_restantes").eq("user_id", USER_ID).execute()
        res_agendamentos = supabase.table("agendamentos").select("id, data_hora, status").eq("user_id", USER_ID).execute()
        res_transacoes = supabase.table("transacoes").select("valor, tipo").eq("user_id", USER_ID).execute()

        alunos_ativos = len([a for a in res_alunos.data if a.get("status") == "Ativo"])
        aulas_pendentes = sum([a.get("aulas_restantes", 0) for a in res_alunos.data])
        
        receitas = sum([t["valor"] for t in res_transacoes.data if t["tipo"] == "Receita"])
        despesas = sum([t["valor"] for t in res_transacoes.data if t["tipo"] == "Despesa"])
        saldo = receitas - despesas

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Alunos Ativos", alunos_ativos)
        col2.metric("Aulas Restantes (Pacotes)", aulas_pendentes)
        col3.metric("Receitas Acumuladas", f"R$ {receitas:,.2f}")
        col4.metric("Saldo Líquido", f"R$ {saldo:,.2f}")

        st.divider()
        st.subheader("🗓️ Treinos de Hoje")
        hoje_inicio = datetime.combine(date.today(), time.min).isoformat()
        hoje_fim = datetime.combine(date.today(), time.max).isoformat()

        res_hoje = supabase.table("agendamentos").select("id, data_hora, status, alunos(nome)").eq("user_id", USER_ID).gte("data_hora", hoje_inicio).lte("data_hora", hoje_fim).execute()
        
        if res_hoje.data:
            df_hoje = pd.DataFrame([{
                "Horário": datetime.fromisoformat(item["data_hora"]).strftime("%H:%M"),
                "Aluno": item["alunos"]["nome"] if item.get("alunos") else "N/A",
                "Status": item["status"]
            } for item in res_hoje.data])
            st.dataframe(df_hoje, use_container_width=True)
        else:
            st.info("Nenhum treino agendado para hoje.")

    except APIError as e:
        exibir_erro_api(e, "Dashboard")

# -----------------------------------------------------------------------------
# 2. ALUNOS & FICHA DE TREINO
# -----------------------------------------------------------------------------
elif menu == "Alunos & Ficha de Treino":
    st.title("👥 Gestão de Alunos e Montagem de Treinos")

    tab_lista, tab_novo, tab_ficha = st.tabs(["Lista de Alunos", "Cadastrar Aluno", "Montar / Atualizar Treino"])

    # --- LISTA DE ALUNOS ---
    with tab_lista:
        try:
            preparar_cliente()
            res = supabase.table("alunos").select("*").eq("user_id", USER_ID).order("nome").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                cols_view = ["nome", "telefone", "status", "tipo_cobranca", "aulas_restantes", "parq_status"]
                st.dataframe(df[cols_view], use_container_width=True)

                st.subheader("📲 Anamnese PAR-Q")
                aluno_parq = st.selectbox("Selecione o aluno para gerar link do PAR-Q:", res.data, format_func=lambda x: x["nome"], key="sel_parq")
                if st.button("Gerar Token de Anamnese"):
                    token = secrets.token_urlsafe(12)
                    supabase.table("alunos").update({"parq_token": token, "parq_status": "Pendente"}).eq("id", aluno_parq["id"]).execute()
                    st.success(f"Token gerado para {aluno_parq['nome']}: `{token}`")
            else:
                st.info("Nenhum aluno cadastrado.")
        except APIError as e:
            exibir_erro_api(e, "Listagem de Alunos")

    # --- CADASTRAR ALUNO ---
    with tab_novo:
        with st.form("form_novo_aluno", clear_on_submit=True):
            st.subheader("Novo Aluno")
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome Completo *")
            email = c2.text_input("E-mail")
            
            c3, c4 = st.columns(2)
            telefone = c3.text_input("Telefone (WhatsApp)")
            dt_nasc = c4.date_input("Data de Nascimento", value=date(1995, 1, 1))

            c5, c6, c7 = st.columns(3)
            cobranca = c5.selectbox("Tipo de Cobrança", ["Mensal", "Pacote de Aulas", "Aula Avulsa"])
            valor_p = c6.number_input("Valor do Plan/Pacote (R$)", min_value=0.0, step=10.0)
            aulas_p = c7.number_input("Total de Aulas (se pacote)", min_value=0, value=12)

            objetivo = st.text_input("Objetivo (ex: Hipertrofia, Emagrecimento)")

            if st.form_submit_button("Salvar Aluno"):
                if not nome:
                    st.warning("O nome é obrigatório.")
                else:
                    try:
                        preparar_cliente()
                        payload = {
                            "user_id": USER_ID,
                            "nome": nome,
                            "email": email,
                            "telefone": telefone,
                            "data_nascimento": dt_nasc.isoformat(),
                            "tipo_cobranca": cobranca,
                            "valor_pacote": float(valor_p),
                            "total_aulas_pacote": int(aulas_p),
                            "aulas_restantes": int(aulas_p) if cobranca == "Pacote de Aulas" else 0,
                            "objetivo": objetivo,
                            "status": "Ativo"
                        }
                        supabase.table("alunos").insert(payload).execute()
                        st.success(f"Aluno {nome} adicionado!")
                        st.rerun()
                    except APIError as e:
                        exibir_erro_api(e, "Cadastro de Aluno")

    # --- MONTAR / ATUALIZAR TREINO ---
    with tab_ficha:
        try:
            preparar_cliente()
            res_al = supabase.table("alunos").select("id, nome, ficha_treino").eq("user_id", USER_ID).order("nome").execute()
            if res_al.data:
                aluno_sel = st.selectbox("Selecione o Aluno para Editar a Ficha:", res_al.data, format_func=lambda x: x["nome"], key="sel_ficha")
                
                ficha_atual = aluno_sel.get("ficha_treino") or []
                st.write("### Ficha de Treino Atual")
                
                if ficha_atual:
                    for ex in ficha_atual:
                        st.write(f"- **{ex.get('bloco', 'Treino A')}**: {ex.get('exercicio')} | {ex.get('series')}x{ex.get('repeticoes')} | Carga: {ex.get('carga')} kg | Obs: {ex.get('obs', '')}")
                else:
                    st.info("Este aluno ainda não possui exercícios cadastrados.")

                st.divider()
                st.subheader("Adicionar Novo Exercício à Ficha")
                with st.form("form_exercicio", clear_on_submit=True):
                    col_b, col_ex = st.columns([1, 2])
                    bloco = col_b.selectbox("Divisão", ["Treino A", "Treino B", "Treino C", "Treino D"])
                    nome_ex = col_ex.text_input("Nome do Exercício (ex: Supino Reto)")

                    col_s, col_r, col_c = st.columns(3)
                    series = col_s.number_input("Séries", min_value=1, value=3)
                    reps = col_r.text_input("Repetições", value="10-12")
                    carga = col_c.number_input("Carga (kg)", min_value=0.0, step=2.5)

                    obs = st.text_input("Observações (ex: Intervalo 60s)")

                    if st.form_submit_button("Adicionar Exercício ao Treino"):
                        if not nome_ex:
                            st.warning("Informe o nome do exercício.")
                        else:
                            novo_item = {
                                "bloco": bloco,
                                "exercicio": nome_ex,
                                "series": int(series),
                                "repeticoes": reps,
                                "carga": float(carga),
                                "obs": obs
                            }
                            ficha_atual.append(novo_item)
                            supabase.table("alunos").update({"ficha_treino": ficha_atual}).eq("id", aluno_sel["id"]).execute()
                            st.success("Exercício adicionado à ficha do aluno!")
                            st.rerun()

                if ficha_atual and st.button("🗑️ Limpar Toda a Ficha deste Aluno"):
                    supabase.table("alunos").update({"ficha_treino": []}).eq("id", aluno_sel["id"]).execute()
                    st.warning("Ficha de treino zerada.")
                    st.rerun()
            else:
                st.info("Nenhum aluno cadastrado.")
        except APIError as e:
            exibir_erro_api(e, "Montagem de Treino")

# -----------------------------------------------------------------------------
# 3. AGENDA & PRESENÇAS
# -----------------------------------------------------------------------------
elif menu == "Agenda & Presenças":
    st.title("📅 Agenda de Treinos e Presença")

    col_ag, col_list = st.columns([1, 2])

    try:
        preparar_cliente()
        res_al = supabase.table("alunos").select("id, nome, aulas_restantes, presencas, faltas").eq("user_id", USER_ID).eq("status", "Ativo").execute()
        alunos_lista = res_al.data or []

        with col_ag:
            st.subheader("Marcar Sessão")
            if alunos_lista:
                with st.form("form_novo_agendamento", clear_on_submit=True):
                    aluno_opcao = st.selectbox("Aluno", alunos_lista, format_func=lambda x: x["nome"])
                    d_treino = st.date_input("Data", value=date.today())
                    h_treino = st.time_input("Horário", value=time(8, 0))
                    local = st.text_input("Local", value="Estúdio")

                    if st.form_submit_button("Agendar"):
                        dt_combo = datetime.combine(d_treino, h_treino).isoformat()
                        supabase.table("agendamentos").insert({
                            "user_id": USER_ID,
                            "aluno_id": aluno_opcao["id"],
                            "data_hora": dt_combo,
                            "local": local,
                            "status": "Agendado"
                        }).execute()
                        st.success("Sessão agendada!")
                        st.rerun()
            else:
                st.warning("Cadastre alunos ativos para realizar agendamentos.")

        with col_list:
            st.subheader("Sessões Agendadas")
            res_ag = supabase.table("agendamentos").select("id, data_hora, local, status, aluno_id, alunos(nome)").eq("user_id", USER_ID).order("data_hora", desc=True).execute()
            
            if res_ag.data:
                for item in res_ag.data[:15]: # Exibe os 15 mais recentes
                    dt_f = datetime.fromisoformat(item["data_hora"]).strftime("%d/%m/%Y às %H:%M")
                    nome_aluno = item["alunos"]["nome"] if item.get("alunos") else "Aluno"
                    st.write(f"📌 **{dt_f}** - {nome_aluno} ({item['local']}) - *Status: {item['status']}*")
                    
                    if item["status"] == "Agendado":
                        c_pres, c_falt, c_canc = st.columns(3)
                        
                        if c_pres.button("✅ Presença", key=f"p_{item['id']}"):
                            # Atualiza agendamento
                            supabase.table("agendamentos").update({"status": "Concluído"}).eq("id", item["id"]).execute()
                            # Atualiza saldo do aluno
                            al_data = supabase.table("alunos").select("aulas_restantes, presencas").eq("id", item["aluno_id"]).single().execute().data
                            novas_restantes = max(0, (al_data.get("aulas_restantes") or 0) - 1)
                            novas_presencas = (al_data.get("presencas") or 0) + 1
                            supabase.table("alunos").update({"aulas_restantes": novas_restantes, "presencas": novas_presencas}).eq("id", item["aluno_id"]).execute()
                            st.success("Presença registrada e aula descontada!")
                            st.rerun()

                        if c_falt.button("❌ Falta", key=f"f_{item['id']}"):
                            supabase.table("agendamentos").update({"status": "Falta"}).eq("id", item["id"]).execute()
                            al_data = supabase.table("alunos").select("faltas").eq("id", item["aluno_id"]).single().execute().data
                            supabase.table("alunos").update({"faltas": (al_data.get("faltas") or 0) + 1}).eq("id", item["aluno_id"]).execute()
                            st.warning("Falta registrada.")
                            st.rerun()

                        if c_canc.button("🚫 Cancelar", key=f"c_{item['id']}"):
                            supabase.table("agendamentos").update({"status": "Cancelado"}).eq("id", item["id"]).execute()
                            st.rerun()
                    st.divider()
            else:
                st.info("Nenhum agendamento encontrado.")

    except APIError as e:
        exibir_erro_api(e, "Módulo de Agenda")

# -----------------------------------------------------------------------------
# 4. FINANCEIRO
# -----------------------------------------------------------------------------
elif menu == "Financeiro":
    st.title("💰 Financeiro do Estúdio")

    col_f1, col_f2 = st.columns([1, 2])

    with col_f1:
        st.subheader("Nova Transação")
        with st.form("form_fin", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            valor = st.number_input("Valor (R$)", min_value=0.01, step=10.0)
            categoria = st.selectbox("Categoria", ["Mensalidade", "Pacote de Aulas", "Equipamentos", "Aluguel", "Outros"])
            descricao = st.text_input("Descrição / Observação")
            dt_t = st.date_input("Data da Transação", value=date.today())

            if st.form_submit_button("Lançar"):
                try:
                    preparar_cliente()
                    supabase.table("transacoes").insert({
                        "user_id": USER_ID,
                        "tipo": tipo,
                        "valor": float(valor),
                        "categoria": categoria,
                        "descricao": descricao,
                        "data_transacao": dt_t.isoformat()
                    }).execute()
                    st.success("Transação salva!")
                    st.rerun()
                except APIError as e:
                    exibir_erro_api(e, "Lançamento Financeiro")

    with col_f2:
        st.subheader("Extrato")
        try:
            preparar_cliente()
            res_t = supabase.table("transacoes").select("*").eq("user_id", USER_ID).order("data_transacao", desc=True).execute()
            if res_t.data:
                df_t = pd.DataFrame(res_t.data)
                st.dataframe(df_t[["data_transacao", "tipo", "categoria", "valor", "descricao"]], use_container_width=True)
            else:
                st.info("Nenhuma transação cadastrada.")
        except APIError as e:
            exibir_erro_api(e, "Extrato Financeiro")

# -----------------------------------------------------------------------------
# 5. FORMULÁRIO PÚBLICO PAR-Q (RESPOSTA VIA TOKEN)
# -----------------------------------------------------------------------------
elif menu == "Responder PAR-Q (Público)":
    st.title("📋 Questionário PAR-Q e Anamnese")
    st.caption("Esta aba simula a tela que o seu aluno acessa ao receber o Token de Anamnese.")

    token_digitado = st.text_input("Insira o Token do Aluno:")

    if token_digitado:
        try:
            res_p = supabase.table("alunos").select("id, nome, parq_status").eq("parq_token", token_digitado).execute()
            
            if res_p.data:
                aluno = res_p.data[0]
                st.success(f"Aluno: **{aluno['nome']}**")

                with st.form("form_parq_aluno"):
                    st.write("##### Responda com atenção às questões abaixo:")
                    q1 = st.radio("1. Seu médico já disse que você possui algum problema cardíaco e que só deve realizar atividade física supervisionada?", ["Não", "Sim"])
                    q2 = st.radio("2. Você sente dores no peito quando pratica atividade física?", ["Não", "Sim"])
                    q3 = st.radio("3. No último mês, você sentiu dor no peito ao realizar atividades do dia a dia?", ["Não", "Sim"])
                    q4 = st.radio("4. Você apresenta algum problema ósseo ou articular que poderia ser agravado pela atividade?", ["Não", "Sim"])
                    q5 = st.radio("5. Você toma atualmente algum medicamento para pressão arterial ou problema de coração?", ["Não", "Sim"])

                    if st.form_submit_button("Enviar Anamnese"):
                        respostas = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5}
                        supabase.table("alunos").update({
                            "parq_status": "Concluído",
                            "parq_respostas": respostas,
                            "parq_data": datetime.utcnow().isoformat()
                        }).eq("id", aluno["id"]).execute()
                        st.balloons()
                        st.success("Anamnese enviada com sucesso! Seu personal trainer receberá os dados.")
            else:
                st.error("Token não encontrado no sistema.")
        except APIError as e:
            exibir_erro_api(e, "Validação de Token PAR-Q")
