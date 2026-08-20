import uuid
from datetime import datetime, timedelta, timezone
import streamlit as st
from supabase import create_client, Client

# -------------------------------------------------------------------
# CONFIGURAÇÃO DE PÁGINA E CREDENCIAIS
# -------------------------------------------------------------------
st.set_page_config(page_title="Studio Fitness - Gestão & PAR-Q", layout="wide")

# Recupera variáveis de ambiente ou segredos do Streamlit (.streamlit/secrets.toml)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://sua-url.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sua-chave-anon-publica")

# -------------------------------------------------------------------
# 1. INICIALIZAÇÃO SEGURA DO SUPABASE (SESSÃO ISOLADA)
# -------------------------------------------------------------------
def get_supabase_client() -> Client:
    """
    Instancia e armazena o cliente Supabase individualmente no st.session_state.
    NUNCA use @st.cache_resource para clientes autenticados no Streamlit.
    """
    if "supabase" not in st.session_state:
        st.session_state.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return st.session_state.supabase


# -------------------------------------------------------------------
# 2. GERENCIAMENTO DE AUTENTICAÇÃO DO PERSONAL
# -------------------------------------------------------------------
def login_personal():
    st.subheader("🔑 Login do Personal Trainer")
    
    with st.form("form_login"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        btn_login = st.form_submit_button("Entrar")

        if btn_login:
            try:
                client = get_supabase_client()
                resposta = client.auth.sign_in_with_password({"email": email, "password": senha})
                
                if resposta.user:
                    st.session_state.usuario_logado = resposta.user
                    st.success("Login realizado com sucesso!")
                    st.rerun()
            except Exception as e:
                st.error("Falha na autenticação. Verifique e-mail e senha.")

def logout_personal():
    client = get_supabase_client()
    client.auth.sign_out()
    if "usuario_logado" in st.session_state:
        del st.session_state.usuario_logado
    st.rerun()


# -------------------------------------------------------------------
# 3. GERAÇÃO E RENOVAÇÃO DO LINK DO PAR-Q (UUID + EXPIRAÇÃO)
# -------------------------------------------------------------------
def gerar_link_parq(aluno_id: str) -> str:
    """
    Gera um token UUID4 completo (36 caracteres) válido por 72 horas.
    """
    token_seguro = str(uuid.uuid4()) # UUID completo
    data_expiracao = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    
    client = get_supabase_client()
    
    # Atualiza o token e a data de expiração no banco
    client.table("alunos").update({
        "parq_token": token_seguro,
        "parq_expires_at": data_expiracao
    }).eq("id", aluno_id).execute()
    
    return token_seguro


# -------------------------------------------------------------------
# 4. PAINEL PRIVADO DO PERSONAL
# -------------------------------------------------------------------
def pagina_painel_personal():
    client = get_supabase_client()
    user = st.session_state.usuario_logado
    
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        st.title("🏋️ Painel de Alunos")
        st.caption(f"Logado como: {user.email}")
    with col_head2:
        if st.button("Sair / Logout"):
            logout_personal()

    st.divider()

    # --- Cadastrar Novo Aluno ---
    st.subheader("➕ Cadastrar Novo Aluno")
    with st.form("form_novo_aluno"):
        nome_aluno = st.text_input("Nome do Aluno")
        email_aluno = st.text_input("E-mail do Aluno")
        btn_cadastrar = st.form_submit_button("Cadastrar Aluno")

        if btn_cadastrar and nome_aluno:
            # Insere vinculando obrigatoriamente ao user_id do personal logado
            novo_aluno = client.table("alunos").insert({
                "nome": nome_aluno,
                "email": email_aluno,
                "user_id": user.id
            }).execute()
            
            st.success(f"Aluno {nome_aluno} cadastrado com sucesso!")
            st.rerun()

    st.divider()

    # --- Lista de Alunos e Links de PAR-Q ---
    st.subheader("📋 Meus Alunos e Status do PAR-Q")
    
    # Busca apenas os alunos pertencentes ao personal logado
    resposta_alunos = client.table("alunos").select("*").eq("user_id", user.id).execute()
    alunos = resposta_alunos.data if resposta_alunos else []

    if not alunos:
        st.info("Nenhum aluno cadastrado até o momento.")
        return

    for aluno in alunos:
        with st.expander(f"👤 {aluno['nome']} - ({aluno.get('email', 'Sem e-mail')})"):
            st.write(f"**Status PAR-Q:** {aluno.get('parq_status', 'Pendente')}")
            
            # Verificar expiração atual
            expiracao_str = aluno.get("parq_expires_at")
            if expiracao_str:
                expiracao_dt = datetime.fromisoformat(expiracao_str)
                esta_expirado = datetime.now(timezone.utc) > expiracao_dt
                st.write(f"**Validade do Link:** {expiracao_dt.strftime('%d/%m/%Y %H:%M UTC')} "
                         f"({'❌ Expirado' if esta_expirado else '✅ Válido'})")

            # Botão para gerar/renovar token do PAR-Q
            if st.button(f"🔄 Gerar Novo Link PAR-Q para {aluno['nome']}", key=f"btn_{aluno['id']}"):
                novo_token = gerar_link_parq(aluno['id'])
                url_base = st.secrets.get("BASE_URL", "http://localhost:8501")
                link_completo = f"{url_base}/?token={novo_token}"
                
                st.success("Novo link seguro gerado com sucesso (Válido por 72h):")
                st.code(link_completo, language="text")


# -------------------------------------------------------------------
# 5. PÁGINA PÚBLICA DO ALUNO (PREENCHIMENTO DO PAR-Q VIA TOKEN)
# -------------------------------------------------------------------
def pagina_parq_aluno(token_url: str):
    st.title("📋 Questionário de Prontidão para Atividade Física (PAR-Q)")
    
    client = get_supabase_client()
    
    # Busca o aluno correspondente ao token da URL
    res = client.table("alunos").select("*").eq("parq_token", token_url).execute()

    if not res.data:
        st.error("🚫 Link inválido ou não encontrado. Solicite um novo acesso ao seu Personal Trainer.")
        return

    aluno = res.data[0]

    # Validação rigorosa da data de expiração
    if aluno.get("parq_expires_at"):
        data_expiracao = datetime.fromisoformat(aluno["parq_expires_at"])
        if datetime.now(timezone.utc) > data_expiracao:
            st.error("⏰ Este link do PAR-Q expirou por medida de segurança. Por favor, peça um novo link ao seu Personal Trainer.")
            return

    if aluno.get("parq_status") == "Concluído":
        st.success(f"Obrigado, {aluno['nome']}! Seu questionário já foi respondido e enviado.")
        return

    st.info(f"Olá, **{aluno['nome']}**! Responda às perguntas abaixo com responsabilidade antes de iniciar seus treinos.")

    # Formulário de saúde PAR-Q
    with st.form("form_parq_aluno"):
        p1 = st.checkbox("1. Algum médico já disse que você possui algum problema de coração e que só deve realizar atividade física supervisionada?")
        p2 = st.checkbox("2. Você sente dores no peito quando pratica atividade física?")
        p3 = st.checkbox("3. No último mês, você sentiu dores no peito quando NÃO estava praticando atividade física?")
        p4 = st.checkbox("4. Você apresenta perda de balanço devido a tontura ou alguma vez perdeu a consciência?")
        p5 = st.checkbox("5. Você possui algum problema ósseo ou articular que poderia ser agravado pela atividade física?")
        p6 = st.checkbox("6. Algum médico já prescreveu medicamentos para pressão arterial ou problema de coração?")
        p7 = st.checkbox("7. Sabe de alguma outra razão pela qual você não deve praticar atividade física?")
        
        observacoes = st.text_area("Se respondeu 'SIM' a alguma das perguntas acima, detalhe aqui:")

        btn_enviar = st.form_submit_button("Enviar Respostas")

        if btn_enviar:
            tem_restricao = any([p1, p2, p3, p4, p5, p6, p7])
            
            # Atualiza o registro do aluno no Supabase
            client.table("alunos").update({
                "parq_status": "Concluído",
                "parq_respostas": {
                    "p1": p1, "p2": p2, "p3": p3, "p4": p4, 
                    "p5": p5, "p6": p6, "p7": p7, 
                    "observacoes": observacoes
                },
                "tem_restricao_saude": tem_restricao,
                "parq_respondido_em": datetime.now(timezone.utc).isoformat()
            }).eq("id", aluno["id"]).execute()

            st.success("Formulário enviado com sucesso! Seus dados foram salvos com segurança.")
            st.rerun()


# -------------------------------------------------------------------
# 6. ROTEADOR DA APLICAÇÃO (MAIN)
# -------------------------------------------------------------------
def main():
    # Captura parâmetros da URL (ex: ?token=abc-123-uuid)
    query_params = st.query_params
    token_parq = query_params.get("token")

    if token_parq:
        # Modo Aluno: Acessou diretamente via link com token
        pagina_parq_aluno(token_parq)
    else:
        # Modo Personal: Requer autenticação
        if "usuario_logado" not in st.session_state:
            login_personal()
        else:
            pagina_painel_personal()


if __name__ == "__main__":
    main()
