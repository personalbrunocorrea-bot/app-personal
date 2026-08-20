import uuid
from datetime import datetime, timedelta, timezone
import streamlit as st
from supabase import create_client, Client

# -------------------------------------------------------------------
# CONFIGURAÇÃO DE PÁGINA
# -------------------------------------------------------------------
st.set_page_config(page_title="Studio Fitness - Gestão Completa", layout="wide", page_icon="🏋️‍♂️")

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://sua-url.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sua-chave-anon-publica")


# -------------------------------------------------------------------
# INICIALIZAÇÃO SEGURA (ISOLADA POR SESSÃO - SEM CACHE GLOBAL)
# -------------------------------------------------------------------
def get_supabase_client() -> Client:
    """Instancia o Supabase no st.session_state individual de cada usuário."""
    if "supabase" not in st.session_state:
        st.session_state.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return st.session_state.supabase


# -------------------------------------------------------------------
# AUTENTICAÇÃO
# -------------------------------------------------------------------
def login_personal():
    st.title("🏋️ Studio Fitness - Acesso do Personal")
    with st.form("form_login", clear_on_submit=False):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        btn_login = st.form_submit_button("Entrar no Sistema")

        if btn_login:
            try:
                client = get_supabase_client()
                resposta = client.auth.sign_in_with_password({"email": email, "password": senha})
                if resposta.user:
                    st.session_state.usuario_logado = resposta.user
                    st.success("Acesso autorizado!")
                    st.rerun()
            except Exception:
                st.error("E-mail ou senha inválidos.")


def logout_personal():
    client = get_supabase_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    if "usuario_logado" in st.session_state:
        del st.session_state.usuario_logado
    st.rerun()


# -------------------------------------------------------------------
# FUNÇÃO AUXILIAR: GERAR TOKEN SEGURO DO PAR-Q
# -------------------------------------------------------------------
def gerar_token_parq(aluno_id: str) -> str:
    """Gera UUID v4 completo (36 caracteres) e validade de 72 horas."""
    token_seguro = str(uuid.uuid4())
    data_expiracao = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    
    client = get_supabase_client()
    client.table("alunos").update({
        "parq_token": token_seguro,
        "parq_expires_at": data_expiracao
    }).eq("id", aluno_id).execute()
    
    return token_seguro


# -------------------------------------------------------------------
# MÓDULOS DO PAINEL DO PERSONAL
# -------------------------------------------------------------------

def modulo_alunos(client, user_id):
    st.header("📋 Gestão de Alunos & PAR-Q")
    
    # Cadastrar Aluno
    with st.expander("➕ Cadastrar Novo Aluno", expanded=False):
        with st.form("form_novo_aluno", clear_on_submit=True):
            nome = st.text_input("Nome Completo")
            email = st.text_input("E-mail")
            telefone = st.text_input("Telefone / WhatsApp")
            objetivo = st.selectbox("Objetivo Principal", ["Hipertrofia", "Emagrecimento", "Condicionamento", "Reabilitação"])
            
            if st.form_submit_button("Salvar Aluno"):
                if nome:
                    client.table("alunos").insert({
                        "nome": nome,
                        "email": email,
                        "telefone": telefone,
                        "objetivo": objetivo,
                        "user_id": user_id
                    }).execute()
                    st.success(f"Aluno {nome} cadastrado!")
                    st.rerun()

    # Listagem de Alunos
    res = client.table("alunos").select("*").eq("user_id", user_id).order("nome").execute()
    alunos = res.data if res else []

    if not alunos:
        st.info("Nenhum aluno cadastrado.")
        return

    for aluno in alunos:
        with st.expander(f"👤 {aluno['nome']} | Telefone: {aluno.get('telefone', 'N/A')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**E-mail:** {aluno.get('email', 'N/A')}")
                st.write(f"**Objetivo:** {aluno.get('objetivo', 'N/A')}")
                st.write(f"**Status PAR-Q:** `{aluno.get('parq_status', 'Pendente')}`")

            with col2:
                # Gerador de Link do PAR-Q
                if st.button("🔄 Gerar Link de Avaliação PAR-Q", key=f"parq_{aluno['id']}"):
                    token = gerar_token_parq(aluno['id'])
                    url_base = st.secrets.get("BASE_URL", "http://localhost:8501")
                    link = f"{url_base}/?token={token}"
                    st.success("Link gerado (Válido por 72h):")
                    st.code(link, language="text")

            # Exibir respostas do PAR-Q se respondido
            if aluno.get("parq_status") == "Concluído":
                st.markdown("---")
                st.subheader("🩺 Respostas do PAR-Q / Saúde")
                if aluno.get("tem_restricao_saude"):
                    st.warning("⚠️ O aluno respondeu 'SIM' a uma ou mais perguntas de saúde.")
                else:
                    st.success("✅ O aluno respondeu 'NÃO' a todas as restrições.")
                
                respostas = aluno.get("parq_respostas", {})
                if respostas.get("observacoes"):
                    st.write(f"**Detalhamento:** {respostas.get('observacoes')}")


def modulo_agendamentos(client, user_id):
    st.header("📅 Agenda de Treinos e Aulas")
    
    # Buscar lista de alunos para o selectbox
    res_alunos = client.table("alunos").select("id, nome").eq("user_id", user_id).execute()
    alunos_dict = {a["nome"]: a["id"] for a in res_alunos.data} if res_alunos.data else {}

    col_form, col_lista = st.columns([1, 2])

    with col_form:
        st.subheader("Novo Agendamento")
        if not alunos_dict:
            st.warning("Cadastre ao menos um aluno para agendar.")
        else:
            with st.form("form_agendamento", clear_on_submit=True):
                aluno_nome = st.selectbox("Aluno", list(alunos_dict.keys()))
                data_agendamento = st.date_input("Data")
                hora_agendamento = st.time_input("Horário")
                tipo_treino = st.text_input("Tipo de Treino", value="Personal Training")
                
                if st.form_submit_button("Agendar Horário"):
                    data_hora = datetime.combine(data_agendamento, hora_agendamento).isoformat()
                    client.table("agendamentos").insert({
                        "aluno_id": alunos_dict[aluno_nome],
                        "data_hora": data_hora,
                        "tipo": tipo_treino,
                        "status": "Confirmado",
                        "user_id": user_id
                    }).execute()
                    st.success("Agendamento criado!")
                    st.rerun()

    with col_lista:
        st.subheader("Próximos Treinos")
        res_agenda = client.table("agendamentos").select("*, alunos(nome)").eq("user_id", user_id).order("data_hora").execute()
        agendamentos = res_agenda.data if res_agenda else []

        if not agendamentos:
            st.info("Nenhum treino agendado.")
        else:
            for item in agendamentos:
                nome_aluno = item.get("alunos", {}).get("nome", "Aluno") if item.get("alunos") else "Aluno"
                dh = datetime.fromisoformat(item["data_hora"])
                
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"**{nome_aluno}** ({item.get('tipo')})")
                c2.write(dh.strftime("%d/%m/%Y às %H:%M"))
                if c3.button("Cancelar", key=f"del_ag_{item['id']}"):
                    client.table("agendamentos").delete().eq("id", item['id']).execute()
                    st.rerun()


def modulo_treinos(client, user_id):
    st.header("🏋️ Prescrição de Treinos")
    
    res_alunos = client.table("alunos").select("id, nome").eq("user_id", user_id).execute()
    alunos_dict = {a["nome"]: a["id"] for a in res_alunos.data} if res_alunos.data else {}

    if not alunos_dict:
        st.info("Cadastre alunos para prescrever fichas de treino.")
        return

    aluno_sel = st.selectbox("Selecione o Aluno para Ver/Criar Treinos", list(alunos_dict.keys()))
    aluno_id = alunos_dict[aluno_sel]

    st.subheader(f"Ficha de Treino - {aluno_sel}")
    
    with st.form("form_treino", clear_on_submit=True):
        nome_treino = st.text_input("Nome da Ficha (ex: Treino A - Peito e Tríceps)")
        descricao_exercicios = st.text_area("Exercícios, Séries e Repetições (ex: Supino Reto 4x10, Tríceps Pulley 3x12)")
        
        if st.form_submit_button("Salvar Ficha de Treino"):
            if nome_treino and descricao_exercicios:
                client.table("treinos").insert({
                    "aluno_id": aluno_id,
                    "nome_ficha": nome_treino,
                    "detalhes": descricao_exercicios,
                    "user_id": user_id
                }).execute()
                st.success("Treino salvo com sucesso!")
                st.rerun()

    # Listar treinos cadastrados
    res_treinos = client.table("treinos").select("*").eq("aluno_id", aluno_id).execute()
    fichas = res_treinos.data if res_treinos else []

    for f in fichas:
        with st.expander(f"📌 {f['nome_ficha']}"):
            st.text(f["detalhes"])
            if st.button("Excluir Ficha", key=f"del_tr_{f['id']}"):
                client.table("treinos").delete().eq("id", f['id']).execute()
                st.rerun()


def modulo_financeiro(client, user_id):
    st.header("💰 Gestão Financeira do Studio")
    
    res_alunos = client.table("alunos").select("id, nome").eq("user_id", user_id).execute()
    alunos_dict = {a["nome"]: a["id"] for a in res_alunos.data} if res_alunos.data else {}

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Registrar Lançamento")
        with st.form("form_financeiro", clear_on_submit=True):
            aluno_nome = st.selectbox("Aluno (Opcional)", ["Nenhum"] + list(alunos_dict.keys()))
            descricao = st.text_input("Descrição (ex: Mensalidade Plano Anual)")
            valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
            tipo = st.radio("Tipo", ["Receita", "Despesa"])
            
            if st.form_submit_button("Registrar Transação"):
                aluno_id = alunos_dict[aluno_nome] if aluno_nome != "Nenhum" else None
                client.table("transacoes").insert({
                    "descricao": descricao,
                    "valor": valor if tipo == "Receita" else -valor,
                    "aluno_id": aluno_id,
                    "user_id": user_id,
                    "data_pagamento": datetime.now(timezone.utc).isoformat()
                }).execute()
                st.success("Lançamento efetuado!")
                st.rerun()

    with col2:
        st.subheader("Histórico Financeiro")
        res_fin = client.table("transacoes").select("*, alunos(nome)").eq("user_id", user_id).order("data_pagamento", desc=True).execute()
        transacoes = res_fin.data if res_fin else []

        if transacoes:
            total_receita = sum(t["valor"] for t in transacoes if t["valor"] > 0)
            total_despesa = sum(t["valor"] for t in transacoes if t["valor"] < 0)
            
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Receitas", f"R$ {total_receita:.2f}")
            kpi2.metric("Despesas", f"R$ {abs(total_despesa):.2f}")
            kpi3.metric("Saldo", f"R$ {(total_receita + total_despesa):.2f}")

            st.divider()
            for t in transacoes:
                aluno_txt = f" - {t['alunos']['nome']}" if t.get("alunos") else ""
                sinal = "🟢" if t["valor"] > 0 else "🔴"
                dt = datetime.fromisoformat(t["data_pagamento"]).strftime("%d/%m/%Y")
                st.write(f"{sinal} **{dt}** | {t['descricao']}{aluno_txt} | **R$ {abs(t['valor']):.2f}**")


# -------------------------------------------------------------------
# PAINEL PRINCIPAL DO PERSONAL (COM NAVEGAÇÃO POR ABAS)
# -------------------------------------------------------------------
def pagina_painel_personal():
    client = get_supabase_client()
    user = st.session_state.usuario_logado

    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.title("🏋️ Studio Fitness Manager")
        st.caption(f"Sessão ativa: {user.email}")
    with col_h2:
        if st.button("🔴 Encerrar Sessão"):
            logout_personal()

    st.divider()

    # Abas principais da aplicação
    tab_alunos, tab_agenda, tab_treinos, tab_fin = st.tabs([
        "📋 Alunos & PAR-Q", 
        "📅 Agendamentos", 
        "🏋️ Treinos", 
        "💰 Financeiro"
    ])

    with tab_alunos:
        modulo_alunos(client, user.id)

    with tab_agenda:
        modulo_agendamentos(client, user.id)

    with tab_treinos:
        modulo_treinos(client, user.id)

    with tab_fin:
        modulo_financeiro(client, user.id)


# -------------------------------------------------------------------
# PÁGINA PÚBLICA DO ALUNO (PAR-Q VIA TOKEN)
# -------------------------------------------------------------------
def pagina_parq_aluno(token_url: str):
    st.title("📋 Questionário PAR-Q")
    client = get_supabase_client()
    
    res = client.table("alunos").select("*").eq("parq_token", token_url).execute()
    if not res.data:
        st.error("🚫 Link inválido ou expirado. Peça um novo acesso ao seu Personal Trainer.")
        return

    aluno = res.data[0]

    if aluno.get("parq_expires_at"):
        if datetime.now(timezone.utc) > datetime.fromisoformat(aluno["parq_expires_at"]):
            st.error("⏰ Este link expirou por medidas de segurança. Peça um novo link ao seu Personal Trainer.")
            return

    if aluno.get("parq_status") == "Concluído":
        st.success(f"Obrigado, {aluno['nome']}! Suas respostas já foram gravadas.")
        return

    st.info(f"Olá, **{aluno['nome']}**! Preencha as perguntas de saúde abaixo:")

    with st.form("form_parq_publico"):
        p1 = st.checkbox("1. Possui algum problema de coração diagnosticado por médico?")
        p2 = st.checkbox("2. Sente dores no peito durante a prática de atividade física?")
        p3 = st.checkbox("3. Sentiu dores no peito no último mês sem estar praticando exercícios?")
        p4 = st.checkbox("4. Apresenta tonturas frequentes ou perda de consciência?")
        p5 = st.checkbox("5. Possui problema ósseo ou articular que pode piorar com o exercício?")
        p6 = st.checkbox("6. Toma medicamentos para pressão alta ou coração?")
        p7 = st.checkbox("7. Existe alguma outra razão médica para não praticar exercícios?")
        
        obs = st.text_area("Se respondeu SIM a algo, detalhe aqui:")

        if st.form_submit_button("Enviar Avaliação"):
            tem_restricao = any([p1, p2, p3, p4, p5, p6, p7])
            client.table("alunos").update({
                "parq_status": "Concluído",
                "parq_respostas": {"p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5, "p6": p6, "p7": p7, "observacoes": obs},
                "tem_restricao_saude": tem_restricao,
                "parq_respondido_em": datetime.now(timezone.utc).isoformat()
            }).eq("id", aluno["id"]).execute()
            
            st.success("Respostas salvas com sucesso!")
            st.rerun()


# -------------------------------------------------------------------
# ROTEADOR DA APLICAÇÃO
# -------------------------------------------------------------------
def main():
    token_parq = st.query_params.get("token")
    if token_parq:
        pagina_parq_aluno(token_parq)
    else:
        if "usuario_logado" not in st.session_state:
            login_personal()
        else:
            pagina_painel_personal()

if __name__ == "__main__":
    main()
