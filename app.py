import streamlit as st
import secrets
from datetime import datetime, date
import pandas as pd
from supabase import create_client, Client
from postgrest.exceptions import APIError

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA & CONEXÃO
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Sistema de Gestão - Estúdio", layout="wide", page_icon="🏋️‍♂️")

# Inicialização do Cliente Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("⚠️ Configurações do Supabase ausentes em .streamlit/secrets.toml")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()

# Auxiliar para lidar e exibir erros do PostgREST sem crashar a aplicação
def handle_api_error(e: APIError, context_message: str):
    st.error(f"🚨 **Erro no Supabase ({context_message}):**")
    st.warning(f"**Mensagem:** {e.message}")
    if hasattr(e, 'code') and e.code:
        st.caption(f"**Código:** {e.code} | **Detalhes:** {getattr(e, 'details', 'N/A')} | **Dica:** {getattr(e, 'hint', 'N/A')}")

# Simulador / Gerenciador de Usuário Autenticado
if "user_id" not in st.session_state:
    # Substitua pelo ID real obtido via Supabase Auth se houver login
    st.session_state["user_id"] = "00000000-0000-0000-0000-000000000000"

USER_ID = st.session_state["user_id"]

# -----------------------------------------------------------------------------
# BARRA LATERAL - NAVEGAÇÃO
# -----------------------------------------------------------------------------
st.sidebar.title("🏋️ Studio Management")
menu = st.sidebar.radio("Navegação", ["Dashboard", "Alunos", "Agendamentos", "Financeiro", "Questionário PAR-Q"])

# -----------------------------------------------------------------------------
# 1. DASHBOARD
# -----------------------------------------------------------------------------
if menu == "Dashboard":
    st.title("📊 Painel Geral")

    try:
        alunos_res = supabase.table("alunos").select("id", count="exact").eq("user_id", USER_ID).execute()
        agendamentos_res = supabase.table("agendamentos").select("id", count="exact").eq("user_id", USER_ID).execute()
        transacoes_res = supabase.table("transacoes").select("valor, tipo").eq("user_id", USER_ID).execute()

        total_alunos = alunos_res.count or 0
        total_agendamentos = agendamentos_res.count or 0
        
        receitas = sum([t['valor'] for t in transacoes_res.data if t['tipo'] == 'Receita'])
        despesas = sum([t['valor'] for t in transacoes_res.data if t['tipo'] == 'Despesa'])
        saldo = receitas - despesas

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Alunos", total_alunos)
        col2.metric("Agendamentos", total_agendamentos)
        col3.metric("Receitas do Mês", f"R$ {receitas:,.2f}")
        col4.metric("Saldo Líquido", f"R$ {saldo:,.2f}")

    except APIError as e:
        handle_api_error(e, "Carregamento do Dashboard")

# -----------------------------------------------------------------------------
# 2. GESTÃO DE ALUNOS
# -----------------------------------------------------------------------------
elif menu == "Alunos":
    st.title("👥 Gestão de Alunos")

    tab1, tab2 = st.tabs(["Listar / Editar", "Cadastrar Novo Aluno"])

    with tab1:
        try:
            res = supabase.table("alunos").select("*").eq("user_id", USER_ID).order("nome").execute()
            if res.data:
                df_alunos = pd.DataFrame(res.data)
                st.dataframe(
                    df_alunos[["nome", "telefone", "email", "status", "tipo_cobranca", "valor_pacote", "parq_status"]],
                    use_container_width=True
                )

                st.subheader("🔗 Gerar Link PAR-Q para Aluno")
                aluno_sel = st.selectbox("Selecione o Aluno", options=res.data, format_func=lambda x: x["nome"])
                if st.button("Gerar Token de Anamnese"):
                    token = secrets.token_urlsafe(16)
                    supabase.table("alunos").update({
                        "parq_token": token,
                        "parq_status": "Pendente"
                    }).eq("id", aluno_sel["id"]).execute()
                    st.success(f"Token Gerado com sucesso: `{token}`")
                    st.info("Envie esse token para o aluno responder a ficha PAR-Q.")
            else:
                st.info("Nenhum aluno cadastrado.")
        except APIError as e:
            handle_api_error(e, "Listagem de Alunos")

    with tab2:
        st.subheader("Novo Cadastro")
        with st.form("form_cadastrar_aluno", clear_on_submit=True):
            nome = st.text_input("Nome Completo *")
            col_a, col_b = st.columns(2)
            email = col_a.text_input("E-mail")
            telefone = col_b.text_input("Telefone")
            
            col_c, col_d = st.columns(2)
            dt_nasc = col_c.date_input("Data de Nascimento", value=date(1995, 1, 1))
            cpf = col_d.text_input("CPF")

            cobranca = st.selectbox("Tipo de Cobrança", ["Mensal", "Pacote de Aulas", "Aula Avulsa"])
            valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
            
            submitted = st.form_submit_button("Salvar Aluno")

            if submitted:
                if not nome:
                    st.warning("O nome é obrigatório.")
                else:
                    try:
                        dados = {
                            "user_id": USER_ID,
                            "nome": nome,
                            "email": email,
                            "telefone": telefone,
                            "data_nascimento": dt_nasc.isoformat(),
                            "cpf": cpf,
                            "tipo_cobranca": cobranca,
                            "valor_pacote": float(valor),
                            "status": "Ativo"
                        }
                        supabase.table("alunos").insert(dados).execute()
                        st.success(f"Aluno {nome} cadastrado com sucesso!")
                        st.rerun()
                    except APIError as e:
                        handle_api_error(e, "Cadastro de Aluno")

# -----------------------------------------------------------------------------
# 3. AGENDAMENTOS
# -----------------------------------------------------------------------------
elif menu == "Agendamentos":
    st.title("📅 Agendamento de Treinos")

    try:
        alunos_res = supabase.table("alunos").select("id, nome").eq("user_id", USER_ID).execute()
        lista_alunos = alunos_res.data or []

        col_form, col_list = st.columns([1, 2])

        with col_form:
            st.subheader("Novo Agendamento")
            if lista_alunos:
                with st.form("form_agendar", clear_on_submit=True):
                    aluno_opcao = st.selectbox("Aluno", options=lista_alunos, format_func=lambda x: x["nome"])
                    data_treino = st.date_input("Data", value=date.today())
                    hora_treino = st.time_input("Horário")
                    local = st.text_input("Local", value="Estúdio Main")
                    
                    if st.form_submit_button("Confirmar Agendamento"):
                        dt_full = datetime.combine(data_treino, hora_treino).isoformat()
                        supabase.table("agendamentos").insert({
                            "user_id": USER_ID,
                            "aluno_id": aluno_opcao["id"],
                            "data_hora": dt_full,
                            "local": local,
                            "status": "Agendado"
                        }).execute()
                        st.success("Sessão agendada!")
                        st.rerun()
            else:
                st.warning("Cadastre alunos antes de agendar sessões.")

        with col_list:
            st.subheader("Próximos Treinos")
            ag_res = supabase.table("agendamentos").select("id, data_hora, local, status, alunos(nome)").eq("user_id", USER_ID).order("data_hora").execute()
            
            if ag_res.data:
                formatados = []
                for item in ag_res.data:
                    nome_aluno = item["alunos"]["nome"] if item.get("alunos") else "Desconhecido"
                    formatados.append({
                        "Data/Hora": item["data_hora"],
                        "Aluno": nome_aluno,
                        "Local": item["local"],
                        "Status": item["status"]
                    })
                st.dataframe(pd.DataFrame(formatados), use_container_width=True)
            else:
                st.info("Nenhum agendamento futuro.")

    except APIError as e:
        handle_api_error(e, "Módulo de Agendamentos")

# -----------------------------------------------------------------------------
# 4. FINANCEIRO
# -----------------------------------------------------------------------------
elif menu == "Financeiro":
    st.title("💰 Controle Financeiro")

    col_add, col_view = st.columns([1, 2])

    with col_add:
        st.subheader("Lançar Transação")
        with st.form("form_financeiro", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            valor = st.number_input("Valor (R$)", min_value=0.01, step=5.0)
            categoria = st.selectbox("Categoria", ["Mensalidade", "Pacote", "Equipamentos", "Aluguel", "Outros"])
            descricao = st.text_input("Descrição")
            dt_trans = st.date_input("Data", value=date.today())

            if st.form_submit_button("Registrar Transação"):
                try:
                    supabase.table("transacoes").insert({
                        "user_id": USER_ID,
                        "tipo": tipo,
                        "valor": float(valor),
                        "categoria": categoria,
                        "descricao": descricao,
                        "data_transacao": dt_trans.isoformat()
                    }).execute()
                    st.success("Lançamento registrado!")
                    st.rerun()
                except APIError as e:
                    handle_api_error(e, "Lançamento Financeiro")

    with col_view:
        st.subheader("Histórico de Transações")
        try:
            trans_res = supabase.table("transacoes").select("*").eq("user_id", USER_ID).order("data_transacao", desc=True).execute()
            if trans_res.data:
                df_t = pd.DataFrame(trans_res.data)
                st.dataframe(df_t[["data_transacao", "tipo", "categoria", "valor", "descricao"]], use_container_width=True)
            else:
                st.info("Nenhuma transação registrada.")
        except APIError as e:
            handle_api_error(e, "Listagem Financeira")

# -----------------------------------------------------------------------------
# 5. RESPOSTA PÚBLICA PAR-Q (ACESSÍVEL VIA TOKEN)
# -----------------------------------------------------------------------------
elif menu == "Questionário PAR-Q":
    st.title("📋 Anamnese e PAR-Q")
    token_input = st.text_input("Digite o Token do Aluno para responder:")

    if token_input:
        try:
            aluno_res = supabase.table("alunos").select("id, nome, parq_status").eq("parq_token", token_input).execute()
            
            if aluno_res.data:
                aluno = aluno_res.data[0]
                st.success(f"Aluno localizado: **{aluno['nome']}**")

                with st.form("parq_form"):
                    st.write("Responda SIM ou NÃO para as perguntas de aptidão física:")
                    q1 = st.radio("Seu médico já disse que você possui algum problema cardíaco?", ["Não", "Sim"])
                    q2 = st.radio("Você sente dores no peito quando pratica atividade física?", ["Não", "Sim"])
                    q3 = st.radio("No último mês, você sentiu dores no peito sem praticar atividade física?", ["Não", "Sim"])
                    q4 = st.radio("Você apresenta algum problema ósseo ou articular que poderia ser agravado?", ["Não", "Sim"])
                    
                    sub_parq = st.form_submit_button("Enviar Anamnese")

                    if sub_parq:
                        respostas = {"q1": q1, "q2": q2, "q3": q3, "q4": q4}
                        supabase.table("alunos").update({
                            "parq_status": "Concluído",
                            "parq_respostas": respostas,
                            "parq_data": datetime.utcnow().isoformat()
                        }).eq("id", aluno["id"]).execute()
                        st.balloons()
                        st.success("Respostas enviadas com sucesso!")
            else:
                st.error("Token inválido ou não encontrado.")
        except APIError as e:
            handle_api_error(e, "Validação de Token PAR-Q")
