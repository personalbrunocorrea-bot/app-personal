import streamlit as st
from datetime import datetime, date, timedelta
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# ==========================================
# CONFIGURAÇÃO E CSS
# ==========================================
st.set_page_config(page_title="Assistente Personal Trainer", layout="wide", initial_sidebar_state="expanded")

def aplicar_estilo_customizado():
    st.markdown("""
        <style>
        .stButton>button { border-radius: 10px !important; font-weight: 600 !important; }
        .sessao-ativa-btn>button { background-color: #E74C3C !important; color: white !important; height: 60px !important; font-size: 20px !important;}
        [data-testid="stMetricValue"] { color: #2ECC71 !important; }
        </style>
    """, unsafe_allow_html=True)

aplicar_estilo_customizado()

# ==========================================
# CONEXÃO SUPABASE
# ==========================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

if "user" not in st.session_state: st.session_state.user = None
if "session" not in st.session_state: st.session_state.session = None

def preparar_cliente():
    if st.session_state.session:
        supabase.postgrest.auth(st.session_state.session.access_token)

def carregar_alunos(user_id):
    preparar_cliente()
    res = supabase.table("alunos").select("*").eq("user_id", user_id).order("nome").execute()
    return res.data if res.data else []

dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
hoje = date.today()

# ==========================================
# APLICAÇÃO PRINCIPAL
# ==========================================
if st.session_state.user is not None:
    user_id = st.session_state.user.id
    alunos_todos = carregar_alunos(user_id)

    with st.sidebar:
        menu = option_menu(
            "Menu do Personal",
            ["Assistente (Resumo)", "🔴 Aula Agora (Sessão)", "📅 Agenda & Locais", "👤 Cadastrar / CRM"],
            icons=["bell", "play-circle", "calendar-range", "people"],
            default_index=0
        )
        if st.button("🚪 Sair"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    # ------------------------------------------
    # 1. CRM E ALERTAS DA ASSISTENTE (RESUMO)
    # ------------------------------------------
    if menu == "Assistente (Resumo)":
        st.title("👋 Olá! Aqui está o resumo de hoje:")
        
        alertas_niver = []
        alertas_marcos = []
        
        for al in alunos_todos:
            # CRM: Aniversários
            if al.get("data_nascimento"):
                dt_nasc = datetime.strptime(al["data_nascimento"], "%Y-%m-%d").date()
                if dt_nasc.month == hoje.month and dt_nasc.day == hoje.day:
                    alertas_niver.append(f"🎂 Hoje é aniversário de **{al['nome']}**! Mande os parabéns.")
            
            # CRM: Marcos de Aulas (Fidelização)
            presencas = al.get("presencas") or 0
            if presencas > 0 and presencas % 50 == 0:
                alertas_marcos.append(f"⭐ **{al['nome']}** completou {presencas} aulas com você!")

        col1, col2 = st.columns(2)
        with col1:
            st.info("### 🔔 Relacionamento (CRM)")
            if alertas_niver or alertas_marcos:
                for a in alertas_niver: st.write(a)
                for a in alertas_marcos: st.write(a)
            else:
                st.write("Sem alertas de relacionamento para hoje.")
                
        with col2:
            st.warning("### 💰 Alertas Financeiros")
            st.write("*(Seus alertas de vencimento aparecerão aqui)*")

    # ------------------------------------------
    # 2. MODO SESSÃO ATIVA (MOBILE-FIRST)
    # ------------------------------------------
    elif menu == "🔴 Aula Agora (Sessão)":
        st.title("🔴 Sessão Ativa")
        st.caption("Interface simplificada para uso durante o treino.")
        
        if not alunos_todos:
            st.warning("Cadastre alunos primeiro.")
        else:
            mapa_nomes = {al["nome"]: al for al in alunos_todos}
            aluno_sel = st.selectbox("Quem está treinando agora?", list(mapa_nomes.keys()))
            aluno_dados = mapa_nomes[aluno_sel]
            
            st.markdown(f"### Aluno: {aluno_sel}")
            st.write(f"**Aulas restantes no pacote:** {aluno_dados.get('aulas_restantes', 0)}")
            
            obs_treino = st.text_area("📝 Notas rápidas do treino (cargas, dores, evolução):", height=100)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ CONCLUIR E DAR CHECK-IN", use_container_width=True, type="primary"):
                    # Atualiza presenças
                    upd = {"presencas": (aluno_dados.get("presencas") or 0) + 1}
                    if aluno_dados.get("tipo_cobranca") == "pacote":
                        upd["aulas_restantes"] = max(0, (aluno_dados.get("aulas_restantes") or 0) - 1)
                    preparar_cliente()
                    supabase.table("alunos").update(upd).eq("id", aluno_dados["id"]).execute()
                    
                    # Salvar histórico (opcional: criar tabela de histórico depois para salvar as notas)
                    st.success(f"Aula de {aluno_sel} registrada com sucesso!")
            with c2:
                if st.button("❌ ALUNO FALTOU", use_container_width=True):
                    upd = {"faltas": (aluno_dados.get("faltas") or 0) + 1}
                    if aluno_dados.get("tipo_cobranca") == "pacote":
                        upd["aulas_restantes"] = max(0, (aluno_dados.get("aulas_restantes") or 0) - 1)
                    preparar_cliente()
                    supabase.table("alunos").update(upd).eq("id", aluno_dados["id"]).execute()
                    st.warning("Falta cobrada registrada.")

    # ------------------------------------------
    # 3. AGENDA & GESTÃO DE LOCAIS
    # ------------------------------------------
    elif menu == "📅 Agenda & Locais":
        st.title("📅 Agenda com Locais")
        
        with st.expander("➕ Agendar Aula"):
            mapa_nomes = {al["nome"]: al["id"] for al in alunos_todos}
            al_nome = st.selectbox("Aluno", list(mapa_nomes.keys()))
            dt_ag = st.date_input("Data", value=hoje)
            hr_ag = st.time_input("Horário", value=datetime.now().time())
            local_ag = st.text_input("📍 Local da Aula (Ex: Praça, Smart Fit, Condomínio)")
            
            if st.button("Agendar", use_container_width=True):
                dt_final = datetime.combine(dt_ag, hr_ag)
                preparar_cliente()
                supabase.table("agendamentos").insert({
                    "user_id": user_id,
                    "aluno_id": mapa_nomes[al_nome],
                    "data_hora": dt_final.isoformat(),
                    "local": local_ag,
                    "status": "agendado"
                }).execute()
                st.success("Agendado!")
                st.rerun()

        st.divider()
        preparar_cliente()
        res_ag = supabase.table("agendamentos").select("*").eq("user_id", user_id).gte("data_hora", hoje.isoformat()).order("data_hora").execute()
        
        for item in (res_ag.data if res_ag.data else []):
            dt = datetime.fromisoformat(item["data_hora"])
            aluno_id = item["aluno_id"]
            nome_aluno = next((al["nome"] for al in alunos_todos if al["id"] == aluno_id), "Desconhecido")
            local_str = item.get("local", "Local não informado")
            
            with st.container(border=True):
                st.markdown(f"**{dt.strftime('%d/%m às %H:%M')}** - 👤 {nome_aluno}")
                st.caption(f"📍 **Local:** {local_str}")

    # ------------------------------------------
    # 4. CADASTRO (Adicionado Data de Nascimento)
    # ------------------------------------------
    elif menu == "👤 Cadastrar / CRM":
        st.title("➕ Cadastrar Aluno")
        with st.form("form_novo"):
            nome = st.text_input("Nome")
            data_nasc = st.date_input("Data de Nascimento (Para o CRM)", min_value=date(1930, 1, 1), max_value=hoje)
            telefone = st.text_input("Telefone")
            tipo_cob = st.selectbox("Cobrança", ["pacote", "por_aula"])
            
            if st.form_submit_button("Salvar Aluno"):
                preparar_cliente()
                supabase.table("alunos").insert({
                    "user_id": user_id,
                    "nome": nome,
                    "data_nascimento": data_nasc.isoformat(),
                    "telefone": telefone,
                    "tipo_cobranca": tipo_cob,
                    "presencas": 0, "faltas": 0
                }).execute()
                st.success("Salvo com sucesso!")
