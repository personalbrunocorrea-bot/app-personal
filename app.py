import streamlit as st
from datetime import datetime, date, timedelta
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import urllib.parse
import re

# ==========================================
# CONFIGURAÇÃO E CSS
# ==========================================
st.set_page_config(page_title="Assistente Personal Trainer", layout="wide", initial_sidebar_state="expanded")

def aplicar_estilo_customizado():
    st.markdown("""
        <style>
        .stButton>button { border-radius: 10px !important; font-weight: 600 !important; transition: 0.2s; }
        .stButton>button:hover { transform: scale(1.02); }
        [data-testid="stMetricValue"] { color: #2ECC71 !important; font-size: 24px !important;}
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
if "chave_pix" not in st.session_state: st.session_state.chave_pix = ""

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
# TELA DE LOGIN
# ==========================================
if st.session_state.user is None:
    st.title("🏋️ Assistente do Personal")
    aba_login, aba_cad = st.tabs(["🔐 Entrar", "📝 Criar Conta"])
    
    with aba_login:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.session_state.session = res.session
                st.rerun()
            except Exception as e:
                st.error("Erro ao entrar. Verifique suas credenciais.")

    with aba_cad:
        email_cad = st.text_input("E-mail novo")
        senha_cad = st.text_input("Senha nova", type="password")
        if st.button("Cadastrar", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                st.success("Conta criada! Faça login.")
            except Exception as e:
                st.error("Erro no cadastro.")

# ==========================================
# APLICAÇÃO PRINCIPAL
# ==========================================
else:
    user_id = st.session_state.user.id
    alunos_todos = carregar_alunos(user_id)

    with st.sidebar:
        menu = option_menu(
            "Navegação",
            ["🔔 Assistente (Resumo)", "🔴 Aula Agora (Sessão)", "📅 Agenda & Locais", "👤 Alunos & CRM", "💰 Financeiro Geral"],
            icons=["bell", "play-circle", "calendar-range", "people", "cash-coin"],
            default_index=0
        )
        if st.button("🚪 Sair", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    # ------------------------------------------
    # 1. ASSISTENTE (RESUMO)
    # ------------------------------------------
    if menu == "🔔 Assistente (Resumo)":
        st.title("👋 Resumo do Dia")
        
        alertas_niver = []
        alertas_marcos = []
        alertas_financeiros = []
        
        for al in alunos_todos:
            if al.get("data_nascimento"):
                try:
                    dt_nasc = datetime.strptime(al["data_nascimento"], "%Y-%m-%d").date()
                    if dt_nasc.month == hoje.month and dt_nasc.day == hoje.day:
                        alertas_niver.append(f"🎂 Hoje é aniversário de **{al['nome']}**! Mande os parabéns.")
                except:
                    pass
            
            pres = al.get("presencas") or 0
            if pres > 0 and pres % 50 == 0:
                alertas_marcos.append(f"⭐ **{al['nome']}** completou {pres} aulas com você!")

            # Alerta financeiro simplificado
            devido = float(al.get("valor_pacote") or 0.0) if al.get("tipo_cobranca") == "pacote" else ((pres + (al.get("faltas") or 0)) * float(al.get("valor_aula") or 0.0))
            pago = float(al.get("valor_pago") or 0.0)
            if (devido - pago) > 0.5 and hoje.day > (al.get("vencimento") or 10):
                alertas_financeiros.append(f"🚨 O pacote de **{al['nome']}** está pendente de renovação.")

        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("### 🔔 Relacionamento")
                if alertas_niver or alertas_marcos:
                    for a in alertas_niver + alertas_marcos: st.write(a)
                else:
                    st.write("Sem alertas de relacionamento para hoje.")
        with c2:
            with st.container(border=True):
                st.markdown("### 💰 Avisos Financeiros")
                if alertas_financeiros:
                    for a in alertas_financeiros: st.write(a)
                else:
                    st.write("Nenhum pagamento pendente para hoje. Tudo em dia!")

    # ------------------------------------------
    # 2. SESSÃO ATIVA
    # ------------------------------------------
    elif menu == "🔴 Aula Agora (Sessão)":
        st.title("🔴 Sessão Ativa")
        if not alunos_todos:
            st.warning("Cadastre alunos primeiro.")
        else:
            mapa_nomes = {al["nome"]: al for al in alunos_todos}
            aluno_sel = st.selectbox("Quem está treinando agora?", list(mapa_nomes.keys()))
            aluno_dados = mapa_nomes[aluno_sel]
            
            st.write(f"**Aulas restantes no pacote:** {aluno_dados.get('aulas_restantes', 0)}")
            
            obs_treino = st.text_area("📝 Notas rápidas do treino (Opcional):", height=100)
            
            c1, c2 = st.columns(2)
            if c1.button("✅ DAR CHECK-IN (Presença)", use_container_width=True, type="primary"):
                upd = {"presencas": (aluno_dados.get("presencas") or 0) + 1}
                if aluno_dados.get("tipo_cobranca") == "pacote":
                    upd["aulas_restantes"] = max(0, (aluno_dados.get("aulas_restantes") or 0) - 1)
                preparar_cliente()
                supabase.table("alunos").update(upd).eq("id", aluno_dados["id"]).execute()
                st.success("Presença registrada!")
                
            if c2.button("❌ COBRAR FALTA", use_container_width=True):
                upd = {"faltas": (aluno_dados.get("faltas") or 0) + 1}
                if aluno_dados.get("tipo_cobranca") == "pacote":
                    upd["aulas_restantes"] = max(0, (aluno_dados.get("aulas_restantes") or 0) - 1)
                preparar_cliente()
                supabase.table("alunos").update(upd).eq("id", aluno_dados["id"]).execute()
                st.warning("Falta registrada.")

    # ------------------------------------------
    # 3. AGENDA & LOCAIS
    # ------------------------------------------
    elif menu == "📅 Agenda & Locais":
        st.title("📅 Agenda")
        with st.expander("➕ Agendar Nova Aula"):
            mapa_nomes = {al["nome"]: al["id"] for al in alunos_todos}
            if mapa_nomes:
                al_nome = st.selectbox("Aluno", list(mapa_nomes.keys()))
                dt_ag = st.date_input("Data", value=hoje)
                hr_ag = st.time_input("Horário", value=datetime.now().time())
                local_ag = st.text_input("📍 Local da Aula (Ex: Calçadão, Smart Fit)")
                if st.button("Agendar"):
                    dt_final = datetime.combine(dt_ag, hr_ag)
                    preparar_cliente()
                    supabase.table("agendamentos").insert({
                        "user_id": user_id, "aluno_id": mapa_nomes[al_nome],
                        "data_hora": dt_final.isoformat(), "local": local_ag, "status": "agendado"
                    }).execute()
                    st.success("Agendado!")
                    st.rerun()

        preparar_cliente()
        res_ag = supabase.table("agendamentos").select("*").eq("user_id", user_id).gte("data_hora", hoje.isoformat()).order("data_hora").execute()
        st.divider()
        st.markdown("### Próximos Treinos")
        for item in (res_ag.data if res_ag.data else []):
            dt = datetime.fromisoformat(item["data_hora"])
            aluno_id = item["aluno_id"]
            nome_aluno = next((al["nome"] for al in alunos_todos if al["id"] == aluno_id), "Desconhecido")
            with st.container(border=True):
                st.markdown(f"**{dt.strftime('%d/%m às %H:%M')}** - 👤 {nome_aluno}")
                st.caption(f"📍 **Local:** {item.get('local') or 'Não informado'}")

    # ------------------------------------------
    # 4. ALUNOS E CRM
    # ------------------------------------------
    elif menu == "👤 Alunos & CRM":
        st.title("👤 Gestão de Alunos")
        with st.expander("➕ Cadastrar Novo Aluno"):
            with st.form("form_novo"):
                nome = st.text_input("Nome")
                data_nasc = st.date_input("Data de Nascimento", min_value=date(1930, 1, 1), max_value=hoje)
                telefone = st.text_input("WhatsApp (com DDD, só números)")
                tipo_cob = st.selectbox("Cobrança", ["pacote", "por_aula"])
                
                c_v1, c_v2 = st.columns(2)
                with c_v1:
                    valor_pacote = st.number_input("Valor Pacote (R$)", min_value=0.0)
                    aulas_pacote = st.number_input("Aulas por Pacote", min_value=0, value=10)
                with c_v2:
                    valor_aula = st.number_input("Valor Avulso (R$)", min_value=0.0)
                    dia_venc = st.number_input("Dia de Vencimento", min_value=1, max_value=31, value=10)

                if st.form_submit_button("Salvar Aluno"):
                    preparar_cliente()
                    supabase.table("alunos").insert({
                        "user_id": user_id, "nome": nome, "data_nascimento": data_nasc.isoformat(),
                        "telefone": telefone, "tipo_cobranca": tipo_cob,
                        "valor_pacote": valor_pacote, "total_aulas_pacote": aulas_pacote, "aulas_restantes": aulas_pacote,
                        "valor_aula": valor_aula, "vencimento": dia_venc,
                        "presencas": 0, "faltas": 0, "valor_pago": 0.0
                    }).execute()
                    st.success("Salvo com sucesso!")
                    st.rerun()

    # ------------------------------------------
    # 5. FINANCEIRO GERAL
    # ------------------------------------------
    elif menu == "💰 Financeiro Geral":
        st.title("💰 Gestão Financeira")
        
        tab_alunos, tab_caixa, tab_config = st.tabs(["Mensalidades (Cobrança)", "Fluxo de Caixa e Metas", "Configuração PIX"])
        
        # --- ABA 3: CONFIGURAÇÃO ---
        with tab_config:
            st.markdown("### Configurar Mensagem de Cobrança")
            chave = st.text_input("Digite sua chave de recebimento (PIX, Link, etc):", value=st.session_state.chave_pix)
            if st.button("Salvar Chave"):
                st.session_state.chave_pix = chave
                st.success("Chave salva para esta sessão!")

        # --- ABA 1: MENSALIDADES ---
        with tab_alunos:
            st.markdown("### Status de Pagamento dos Alunos")
            for al in alunos_todos:
                pres = al.get("presencas") or 0
                fal = al.get("faltas") or 0
                devido = float(al.get("valor_pacote") or 0.0) if al.get("tipo_cobranca") == "pacote" else ((pres + fal) * float(al.get("valor_aula") or 0.0))
                pago = float(al.get("valor_pago") or 0.0)
                saldo = devido - pago

                with st.container(border=True):
                    col_info, col_acao = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"**{al['nome']}**")
                        if saldo > 0:
                            st.error(f"Pendente: R$ {saldo:.2f}")
                        else:
                            st.success("Em dia ✅")
                    
                    with col_acao:
                        if saldo > 0:
                            msg = f"Fala {al['nome']}! Tudo bem? Passando só para avisar que o seu pacote de aulas venceu. Segue a chave para renovação: {st.session_state.chave_pix}. Valeu!"
                            tel = re.sub(r'\D', '', str(al.get("telefone") or ""))
                            if tel:
                                link_whats = f"https://wa.me/55{tel}?text={urllib.parse.quote(msg)}"
                                st.markdown(f"<a href='{link_whats}' target='_blank'><button style='background-color:#25D366; color:white; border:none; padding:8px; border-radius:5px; width:100%;'>📱 Cobrar WhatsApp</button></a>", unsafe_allow_html=True)
                            else:
                                st.caption("Sem telefone cadastrado")
                            
                            # Botão para zerar a dívida
                            if st.button("Baixar Pgto", key=f"pg_{al['id']}", use_container_width=True):
                                preparar_cliente()
                                upd = {"valor_pago": devido, "aulas_restantes": al.get("total_aulas_pacote", 0), "presencas": 0, "faltas": 0}
                                supabase.table("alunos").update(upd).eq("id", al["id"]).execute()
                                # Salva como receita no fluxo de caixa
                                supabase.table("transacoes").insert({"user_id": user_id, "tipo": "Receita", "valor": saldo, "categoria": "Mensalidade", "descricao": f"Pgto {al['nome']}", "data_transacao": hoje.isoformat()}).execute()
                                st.rerun()

        # --- ABA 2: FLUXO DE CAIXA ---
        with tab_caixa:
            c_add, c_resumo = st.columns([1, 2])
            with c_add:
                st.markdown("### Lançar Transação")
                with st.form("form_trans"):
                    tipo_t = st.selectbox("Tipo", ["Receita", "Despesa"])
                    valor_t = st.number_input("Valor (R$)", min_value=0.0)
                    cat_t = st.selectbox("Categoria", ["Mensalidade", "Combustível", "Equipamento", "Curso/Evento", "Outros"])
                    desc_t = st.text_input("Descrição breve")
                    
                    if st.form_submit_button("Registrar no Caixa"):
                        preparar_cliente()
                        supabase.table("transacoes").insert({"user_id": user_id, "tipo": "Receita" if tipo_t == "Receita" else "Despesa", "valor": valor_t, "categoria": cat_t, "descricao": desc_t, "data_transacao": hoje.isoformat()}).execute()
                        st.success("Registrado!")
                        st.rerun()
                        
            with c_resumo:
                st.markdown("### Resumo do Mês")
                preparar_cliente()
                iso_inicio_mes = date(hoje.year, hoje.month, 1).isoformat()
                res_t = supabase.table("transacoes").select("*").eq("user_id", user_id).gte("data_transacao", iso_inicio_mes).execute()
                dados_t = res_t.data if res_t.data else []
                
                tot_rec = sum(float(t["valor"]) for t in dados_t if t["tipo"] == "Receita")
                tot_desp = sum(float(t["valor"]) for t in dados_t if t["tipo"] == "Despesa")
                lucro = tot_rec - tot_desp
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Entradas", f"R$ {tot_rec:.2f}")
                m2.metric("Saídas", f"R$ {tot_desp:.2f}")
                m3.metric("Lucro Líquido", f"R$ {lucro:.2f}")
                
                st.divider()
                st.markdown("### 🎯 Metas e Reservas")
                st.caption("Planejamento para longo prazo (ex: Viagem Itália, Compra de Equipamentos)")
                meta_nome = st.text_input("Nome do Objetivo", value="Viagem Itália 2026")
                meta_valor = st.number_input("Custo Estimado (R$)", value=15000.0, min_value=1.0)
                meta_guardado = st.number_input("Já reservado (R$)", value=0.0)
                
                if meta_valor > 0:
                    progresso = min(meta_guardado / meta_valor, 1.0)
                    st.progress(progresso)
                    st.write(f"**Progresso:** {progresso*100:.1f}% concluído (R$ {meta_guardado:.2f} de R$ {meta_valor:.2f})")
