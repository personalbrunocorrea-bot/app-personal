import streamlit as st
from datetime import datetime, date, timedelta
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar
import urllib.parse
import re
import uuid

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

# ==========================================
# MODO AUTOATENDIMENTO: PAR-Q DO ALUNO
# ==========================================
token_aluno = st.query_params.get("token", None)

if token_aluno:
    try:
        res_p = supabase.table("alunos").select("*").eq("parq_token", token_aluno).execute()
        aluno_parq = res_p.data[0] if res_p.data else None
    except Exception as e:
        aluno_parq = None

    if not aluno_parq:
        st.error("❌ Link do PAR-Q inválido, expirado ou aluno não encontrado. Por favor, solicite um novo link ao seu Personal Trainer.")
        st.stop()

    st.title("📋 Questionário de Prontidão para Atividade Física (PAR-Q)")
    st.markdown(f"Olá, **{aluno_parq['nome']}**! Para garantir sua segurança durante os treinos, por favor responda com atenção às perguntas abaixo.")
    
    if aluno_parq.get("parq_status") == "assinado":
        dt_ass = aluno_parq.get("parq_data", "")[:10]
        st.success(f"✅ Você já preencheu e assinou este questionário em **{dt_ass}**. Obrigado pela cooperação!")
        st.stop()

    with st.form("form_parq_aluno"):
        st.markdown("##### Responda com 'Sim' ou 'Não':")
        
        q1 = st.radio("1. Seu médico já disse que você possui algum problema de coração e recomendou que só fizesse atividade física sob supervisão médica?", ["Não", "Sim"])
        q2 = st.radio("2. Você sente dores no peito quando pratica atividade física?", ["Não", "Sim"])
        q3 = st.radio("3. No último mês, você sentiu dor no peito quando NÃO estava praticando atividade física?", ["Não", "Sim"])
        q4 = st.radio("4. Você apresenta algum problema ósseo ou articular que poderia ser agravado pela atividade física?", ["Não", "Sim"])
        q5 = st.radio("5. Você perde o equilíbrio devido a tontura ou alguma vez perdeu a consciência?", ["Não", "Sim"])
        q6 = st.radio("6. Você toma atualmente algum medicamento para pressão arterial ou problema de coração?", ["Não", "Sim"])
        q7 = st.radio("7. Sabe de nenhuma outra razão pela qual você não deva praticar atividade física?", ["Não", "Sim"])

        st.divider()
        st.markdown("### 📝 Termo de Responsabilidade")
        st.caption("Declaro que respondi com verdade a todas as perguntas acima e estou ciente de que é minha responsabilidade comunicar qualquer alteração em meu estado de saúde ao meu Personal Trainer.")
        
        aceito = st.checkbox("Li, concordo e declaro que as informações prestadas são verdadeiras.")

        if st.form_submit_button("✅ Enviar e Assinar PAR-Q", type="primary", use_container_width=True):
            if not aceito:
                st.error("Você precisa marcar a caixa de confirmação para enviar o termo.")
            else:
                respostas_json = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6, "q7": q7}
                data_hoje_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                supabase.table("alunos").update({
                    "parq_status": "assinado",
                    "parq_respostas": respostas_json,
                    "parq_data": data_hoje_str
                }).eq("id", aluno_parq["id"]).execute()
                
                st.balloons()
                st.success("✅ PAR-Q enviado com sucesso! O seu Personal Trainer já recebeu sua confirmação. Bons treinos!")
    st.stop()


# ==========================================
# ÁREA DO PERSONAL TRAINER
# ==========================================
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

hoje = date.today()

# ------------------------------------------
# TELA DE LOGIN
# ------------------------------------------
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

# ------------------------------------------
# APLICAÇÃO PRINCIPAL LOGADA
# ------------------------------------------
else:
    user_id = st.session_state.user.id
    alunos_todos = carregar_alunos(user_id)

    with st.sidebar:
        menu = option_menu(
            "Navegação",
            ["📊 Dashboard", "🔔 Assistente (Resumo)", "📅 Agenda Visual", "👤 Alunos & CRM", "💰 Financeiro"],
            icons=["bar-chart", "bell", "calendar-week", "people", "cash-coin"],
            default_index=0
        )
        if st.button("🚪 Sair", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    # ------------------------------------------
    # 0. DASHBOARD GERAL
    # ------------------------------------------
    if menu == "📊 Dashboard":
        st.title("📊 Painel de Controle (Dashboard)")
        st.caption("Visão geral do seu estúdio e alunos")

        total_alunos = len(alunos_todos)
        total_treinos_dados = sum([(al.get("presencas") or 0) for al in alunos_todos])
        
        total_pago = 0.0
        total_pendente = 0.0

        for al in alunos_todos:
            pres = al.get("presencas") or 0
            fal = al.get("faltas") or 0
            devido = float(al.get("valor_pacote") or 0.0) if al.get("tipo_cobranca") == "pacote" else ((pres + fal) * float(al.get("valor_aula") or 0.0))
            pago = float(al.get("valor_pago") or 0.0)
            
            saldo = devido - pago
            if saldo > 0:
                total_pendente += saldo
            
            total_pago += pago

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total de Alunos", total_alunos)
        c2.metric("Treinos Realizados", f"{total_treinos_dados} aulas")
        c3.metric("Caixa Atual (Recebido)", f"R$ {total_pago:.2f}")
        c4.metric("Valores Pendentes", f"R$ {total_pendente:.2f}", delta="-A receber", delta_color="inverse")

        st.divider()
        st.markdown("### Perfil Rápido dos Alunos")
        if not alunos_todos:
            st.info("Cadastre alunos para ver as estatísticas.")
        else:
            col_list1, col_list2 = st.columns(2)
            with col_list1:
                st.markdown("**🏃‍♂️ Maiores Frequências (Top 5)**")
                alunos_top = sorted(alunos_todos, key=lambda x: x.get("presencas") or 0, reverse=True)[:5]
                for al in alunos_top:
                    st.write(f"- {al['nome']} ({al.get('presencas') or 0} aulas)")
            
            with col_list2:
                st.markdown("**⚠️ Alunos com Pagamento Pendente**")
                pendentes_lista = [al for al in alunos_todos if (float(al.get("valor_pacote") or 0.0) if al.get("tipo_cobranca") == "pacote" else ((al.get("presencas") or 0) + (al.get("faltas") or 0)) * float(al.get("valor_aula") or 0.0)) - float(al.get("valor_pago") or 0.0) > 0]
                if pendentes_lista:
                    for al in pendentes_lista:
                        st.write(f"- {al['nome']}")
                else:
                    st.write("Nenhum! Todos estão em dia ✅")

    # ------------------------------------------
    # 1. ASSISTENTE (RESUMO)
    # ------------------------------------------
    elif menu == "🔔 Assistente (Resumo)":
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
    # 2. AGENDA VISUAL (GOOGLE AGENDA)
    # ------------------------------------------
    elif menu == "📅 Agenda Visual":
        st.title("📅 Agenda de Aulas")
        
        preparar_cliente()
        inicio_mes = (hoje.replace(day=1) - timedelta(days=7)).isoformat()
        res_ag = supabase.table("agendamentos").select("*").eq("user_id", user_id).gte("data_hora", inicio_mes).execute()
        agendamentos = res_ag.data if res_ag.data else []

        mapa_alunos_id = {al["id"]: al for al in alunos_todos}
        
        eventos_calendario = []
        cores_status = {
            "agendado": "#3788d8",        
            "presenca": "#2ECC71",        
            "falta_cobrada": "#E74C3C",   
            "falta_nao_cobrada": "#F39C12",
            "desmarcado": "#95A5A6"       
        }

        for ag in agendamentos:
            aluno = mapa_alunos_id.get(ag["aluno_id"], {})
            nome = aluno.get("nome", "Desconhecido")
            status = ag.get("status", "agendado")
            cor = cores_status.get(status, "#3788d8")
            dt_inicio = ag["data_hora"]
            
            try:
                dt_fim_obj = datetime.fromisoformat(dt_inicio) + timedelta(hours=1)
                dt_fim = dt_fim_obj.isoformat()
            except:
                dt_fim = dt_inicio

            eventos_calendario.append({
                "title": f"{nome} ({status.replace('_', ' ').title()})",
                "start": dt_inicio,
                "end": dt_fim,
                "backgroundColor": cor,
                "borderColor": cor
            })

        opcoes_calendario = {
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "timeGridDay,timeGridWeek,dayGridMonth"
            },
            "initialView": "timeGridWeek",
            "slotMinTime": "05:00:00",
            "slotMaxTime": "23:00:00",
            "locale": "pt-br"
        }

        calendar(events=eventos_calendario, options=opcoes_calendario, custom_css="""
            .fc-event-title { font-weight: bold; font-size: 14px; }
        """)

        st.divider()

        c_agendar, c_gerenciar = st.columns(2)
        
        with c_agendar:
            st.markdown("### ➕ Novo Agendamento")
            mapa_nomes = {al["nome"]: al["id"] for al in alunos_todos}
            if mapa_nomes:
                with st.form("form_agendar"):
                    al_nome = st.selectbox("Selecione o Aluno", list(mapa_nomes.keys()))
                    dt_ag = st.date_input("Data", value=hoje)
                    hr_ag = st.time_input("Horário", value=datetime.now().time())
                    local_ag = st.text_input("📍 Local da Aula")
                    if st.form_submit_button("Agendar Horário"):
                        dt_final = datetime.combine(dt_ag, hr_ag)
                        preparar_cliente()
                        supabase.table("agendamentos").insert({
                            "user_id": user_id, "aluno_id": mapa_nomes[al_nome],
                            "data_hora": dt_final.isoformat(), "local": local_ag, "status": "agendado"
                        }).execute()
                        st.success("Agendado!")
                        st.rerun()

        with c_gerenciar:
            st.markdown("### ⚙️ Gerenciar Presenças / Faltas")
            agendamentos_ativos = [ag for ag in agendamentos if ag["status"] == "agendado"]
            
            if not agendamentos_ativos:
                st.info("Nenhum agendamento pendente no momento.")
            else:
                opcoes_gerenciar = {}
                for ag in agendamentos_ativos:
                    nome = mapa_alunos_id.get(ag["aluno_id"], {}).get("nome", "Desconhecido")
                    dt_str = datetime.fromisoformat(ag["data_hora"]).strftime("%d/%m às %H:%M")
                    label = f"{nome} - {dt_str}"
                    opcoes_gerenciar[label] = ag
                
                aula_selecionada = st.selectbox("Selecione a Aula:", list(opcoes_gerenciar.keys()))
                ag_selecionado = opcoes_gerenciar[aula_selecionada]
                aluno_dados = mapa_alunos_id.get(ag_selecionado["aluno_id"])
                
                novo_status = st.radio("Qual o resultado da aula?", 
                    ["Presença ✅", "Falta Cobrada ❌", "Falta Não Cobrada ⚠️", "Desmarcado ⚪"], horizontal=True)
                
                if st.button("Confirmar Status", type="primary", use_container_width=True):
                    upd_aluno = {}
                    str_status_db = "agendado"
                    
                    if "Presença" in novo_status:
                        str_status_db = "presenca"
                        upd_aluno["presencas"] = (aluno_dados.get("presencas") or 0) + 1
                        if aluno_dados.get("tipo_cobranca") == "pacote":
                            upd_aluno["aulas_restantes"] = max(0, (aluno_dados.get("aulas_restantes") or 0) - 1)
                    
                    elif "Falta Cobrada" in novo_status:
                        str_status_db = "falta_cobrada"
                        upd_aluno["faltas"] = (aluno_dados.get("faltas") or 0) + 1
                        if aluno_dados.get("tipo_cobranca") == "pacote":
                            upd_aluno["aulas_restantes"] = max(0, (aluno_dados.get("aulas_restantes") or 0) - 1)
                    
                    elif "Falta Não Cobrada" in novo_status:
                        str_status_db = "falta_nao_cobrada"
                    
                    elif "Desmarcado" in novo_status:
                        str_status_db = "desmarcado"
                        
                    preparar_cliente()
                    supabase.table("agendamentos").update({"status": str_status_db}).eq("id", ag_selecionado["id"]).execute()
                    
                    if upd_aluno:
                        supabase.table("alunos").update(upd_aluno).eq("id", aluno_dados["id"]).execute()
                        
                    st.success("Status atualizado com sucesso!")
                    st.rerun()

    # ------------------------------------------
    # 3. ALUNOS & CRM (EDIÇÃO COMPLETA DE PERFIL)
    # ------------------------------------------
    elif menu == "👤 Alunos & CRM":
        st.title("👤 Gestão de Alunos e PAR-Q")

        base_app_url = st.text_input("🔗 URL Base do seu App Streamlit:", value="https://meustudio.streamlit.app")

        # --- SEÇÃO PAR-Q ---
        if alunos_todos:
            st.markdown("### 📜 Status e PAR-Q dos Alunos")
            for al in alunos_todos:
                st_parq = al.get("parq_status", "pendente")
                
                with st.container(border=True):
                    c_info, c_status, c_acao = st.columns([2, 1, 1.5])
                    
                    with c_info:
                        st.markdown(f"**{al['nome']}**")
                        st.caption(f"Tel: {al.get('telefone', 'Não informado')} | Presenças: {al.get('presencas', 0)}")
                    
                    with c_status:
                        if st_parq == "assinado":
                            st.success("✅ PAR-Q Assinado")
                            dt_a = al.get("parq_data", "")[:10]
                            st.caption(f"Data: {dt_a}")
                        else:
                            st.warning("⚠️ PAR-Q Pendente")

                    with c_acao:
                        token = al.get("parq_token")
                        if not token:
                            if st.button("🔑 Gerar Link", key=f"token_{al['id']}"):
                                novo_token = str(uuid.uuid4())[:10]
                                preparar_cliente()
                                supabase.table("alunos").update({"parq_token": novo_token}).eq("id", al["id"]).execute()
                                st.rerun()
                        else:
                            link_parq = f"{base_app_url}/?token={token}"
                            msg_parq = f"Olá {al['nome']}! Para iniciarmos nossos treinos com toda a segurança, por favor preencha e assine seu PAR-Q online no link a seguir: {link_parq}"
                            
                            tel_num = re.sub(r'\D', '', str(al.get("telefone", "")))
                            if tel_num:
                                link_wsp = f"https://wa.me/55{tel_num}?text={urllib.parse.quote(msg_parq)}"
                                st.markdown(f"<a href='{link_wsp}' target='_blank'><button style='background-color:#25D366; color:white; border:none; padding:8px; border-radius:5px; width:100%;'>📱 Enviar PAR-Q</button></a>", unsafe_allow_html=True)
                            else:
                                st.caption("Cadastre o telefone")

                        if st_parq == "assinado":
                            with st.expander("👁️ Ver Respostas"):
                                resp = al.get("parq_respostas") or {}
                                for k, v in resp.items():
                                    cor = "🔴" if v == "Sim" else "🟢"
                                    st.write(f"{cor} {k.upper()}: **{v}**")

        st.divider()

        # --- SEÇÃO DE EDIÇÃO COMPLETA DE PERFIL ---
        if alunos_todos:
            with st.expander("✏️ Editar Perfil Completo do Aluno", expanded=False):
                mapa_edicao = {al["nome"]: al for al in alunos_todos}
                aluno_sel_nome = st.selectbox("Selecione o Aluno para Editar", list(mapa_edicao.keys()))
                aluno_sel = mapa_edicao[aluno_sel_nome]

                with st.form("form_editar_perfil_completo"):
                    st.markdown("#### 👤 Dados Pessoais e Contato")
                    f_nome = st.text_input("Nome Completo", value=aluno_sel.get("nome", ""))
                    
                    try:
                        dt_nasc_val = datetime.strptime(aluno_sel["data_nascimento"], "%Y-%m-%d").date() if aluno_sel.get("data_nascimento") else hoje
                    except:
                        dt_nasc_val = hoje
                        
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        f_data_nasc = st.date_input("Data de Nascimento", value=dt_nasc_val, min_value=date(1930,1,1), max_value=hoje)
                    with col_p2:
                        f_telefone = st.text_input("WhatsApp", value=aluno_sel.get("telefone", ""))
                    with col_p3:
                        f_email = st.text_input("E-mail", value=aluno_sel.get("email", ""))

                    col_p4, col_p5 = st.columns(2)
                    with col_p4:
                        f_cpf = st.text_input("CPF", value=aluno_sel.get("cpf", ""))
                    with col_p5:
                        f_status = st.selectbox("Status da Matrícula", ["Ativo", "Inativo", "Suspenso"], index=["Ativo", "Inativo", "Suspenso"].index(aluno_sel.get("status", "Ativo") if aluno_sel.get("status") in ["Ativo", "Inativo", "Suspenso"] else "Ativo"))

                    st.markdown("#### 🚨 Contato de Emergência")
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        f_emg_nome = st.text_input("Nome do Contato de Emergência", value=aluno_sel.get("contato_emergencia_nome", ""))
                    with col_e2:
                        f_emg_fone = st.text_input("Telefone de Emergência", value=aluno_sel.get("contato_emergencia_fone", ""))

                    st.markdown("#### 🩺 Anamnese e Objetivos")
                    f_restricoes = st.text_area("Restrições de Saúde / Lesões / Observações", value=aluno_sel.get("restricoes_saude", ""), help="Ex: Lesão no joelho esquerdo, hipertensão, etc.")
                    
                    col_o1, col_o2 = st.columns(2)
                    with col_o1:
                        f_objetivo = st.text_input("Objetivo Principal", value=aluno_sel.get("objetivo", ""), placeholder="Ex: Emagrecimento, Hipertrofia")
                    with col_o2:
                        f_nivel = st.selectbox("Nível de Experiência", ["Iniciante", "Intermediário", "Avançado"], index=["Iniciante", "Intermediário", "Avançado"].index(aluno_sel.get("nivel", "Iniciante") if aluno_sel.get("nivel") in ["Iniciante", "Intermediário", "Avançado"] else "Iniciante"))

                    st.markdown("#### 💰 Plano e Frequência")
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        f_valor_pacote = st.number_input("Valor Pacote (R$)", value=float(aluno_sel.get("valor_pacote") or 0.0), min_value=0.0)
                        f_presencas = st.number_input("Presenças", value=int(aluno_sel.get("presencas") or 0), min_value=0)
                    with col_f2:
                        f_valor_aula = st.number_input("Valor Avulso (R$)", value=float(aluno_sel.get("valor_aula") or 0.0), min_value=0.0)
                        f_faltas = st.number_input("Faltas", value=int(aluno_sel.get("faltas") or 0), min_value=0)
                    with col_f3:
                        f_valor_pago = st.number_input("Valor Já Pago (R$)", value=float(aluno_sel.get("valor_pago") or 0.0), min_value=0.0)
                        f_aulas_restantes = st.number_input("Aulas Restantes", value=int(aluno_sel.get("aulas_restantes") or 0), min_value=0)

                    if st.form_submit_button("💾 Salvar Perfil Completo", type="primary", use_container_width=True):
                        preparar_cliente()
                        supabase.table("alunos").update({
                            "nome": f_nome,
                            "data_nascimento": f_data_nasc.isoformat(),
                            "telefone": f_telefone,
                            "email": f_email,
                            "cpf": f_cpf,
                            "status": f_status,
                            "contato_emergencia_nome": f_emg_nome,
                            "contato_emergencia_fone": f_emg_fone,
                            "restricoes_saude": f_restricoes,
                            "objetivo": f_objetivo,
                            "nivel": f_nivel,
                            "valor_pacote": f_valor_pacote,
                            "valor_aula": f_valor_aula,
                            "presencas": f_presencas,
                            "faltas": f_faltas,
                            "valor_pago": f_valor_pago,
                            "aulas_restantes": f_aulas_restantes
                        }).eq("id", aluno_sel["id"]).execute()
                        st.success("Perfil do aluno atualizado com sucesso!")
                        st.rerun()

        # --- SEÇÃO CADASTRO ---
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
                    token_inicial = str(uuid.uuid4())[:10]
                    supabase.table("alunos").insert({
                        "user_id": user_id, "nome": nome, "data_nascimento": data_nasc.isoformat(),
                        "telefone": telefone, "tipo_cobranca": tipo_cob,
                        "valor_pacote": valor_pacote, "total_aulas_pacote": aulas_pacote, "aulas_restantes": aulas_pacote,
                        "valor_aula": valor_aula, "vencimento": dia_venc,
                        "presencas": 0, "faltas": 0, "valor_pago": 0.0,
                        "parq_token": token_inicial, "parq_status": "pendente"
                    }).execute()
                    st.success("Salvo com sucesso!")
                    st.rerun()

    # ------------------------------------------
    # 4. FINANCEIRO GERAL
    # ------------------------------------------
    elif menu == "💰 Financeiro":
        st.title("💰 Gestão Financeira")
        
        tab_alunos, tab_caixa, tab_config = st.tabs(["Mensalidades (Cobrança)", "Fluxo de Caixa e Metas", "Configuração PIX"])
        
        with tab_config:
            st.markdown("### Configurar Mensagem de Cobrança")
            chave = st.text_input("Digite sua chave de recebimento (PIX, Link, etc):", value=st.session_state.chave_pix)
            if st.button("Salvar Chave"):
                st.session_state.chave_pix = chave
                st.success("Chave salva para esta sessão!")

        with tab_alunos:
            st.markdown("### Status de Pagamento")
            if not alunos_todos:
                st.info("Nenhum aluno cadastrado.")
            else:
                for al in alunos_todos:
                    pres = al.get("presencas") or 0
                    fal = al.get("faltas") or 0
                    devido = float(al.get("valor_pacote") or 0.0) if al.get("tipo_cobranca") == "pacote" else ((pres + fal) * float(al.get("valor_aula") or 0.0))
                    pago = float(al.get("valor_pago") or 0.0)
                    saldo = devido - pago

                    with st.container(border=True):
                        col_info, col_acao = st.columns([2.5, 1.5])
                        with col_info:
                            st.markdown(f"**{al['nome']}**")
                            st.caption(f"Cobrança: {al.get('tipo_cobranca', 'pacote').upper()} | Pago: R$ {pago:.2f} | Devido: R$ {devido:.2f}")
                            if saldo > 0:
                                st.error(f"Pendente: R$ {saldo:.2f}")
                            else:
                                st.success("Em dia ✅")
                        
                        with col_acao:
                            if saldo > 0:
                                msg = f"Fala {al['nome']}! Tudo bem? Passando só para avisar que o seu pacote de aulas venceu. Segue a chave para renovação: {st.session_state.chave_pix}. Valeu!"
                                
                                telefone_salvo = al.get("telefone")
                                telefone_texto = str(telefone_salvo) if telefone_salvo is not None else ""
                                tel = re.sub(r'\D', '', telefone_texto)
                                
                                if tel:
                                    link_whats = f"https://wa.me/55{tel}?text={urllib.parse.quote(msg)}"
                                    st.markdown(f"<a href='{link_whats}' target='_blank'><button style='background-color:#25D366; color:white; border:none; padding:8px; border-radius:5px; width:100%; margin-bottom: 5px;'>📱 Cobrar via WhatsApp</button></a>", unsafe_allow_html=True)
                                else:
                                    st.caption("Sem telefone")
                                
                                if st.button("✅ Registrar Pagamento", key=f"pag_{al['id']}", use_container_width=True):
                                    preparar_cliente()
                                    novas_aulas = (al.get("total_aulas_pacote") or 10) if al.get("tipo_cobranca") == "pacote" else 0
                                    supabase.table("alunos").update({
                                        "valor_pago": devido,
                                        "aulas_restantes": (al.get("aulas_restantes") or 0) + novas_aulas
                                    }).eq("id", al["id"]).execute()
                                    st.success("Pagamento registrado!")
                                    st.rerun()
                            else:
                                if st.button("🔄 Renovar Pacote", key=f"renovar_{al['id']}", use_container_width=True):
                                    preparar_cliente()
                                    novas_aulas = al.get("total_aulas_pacote") or 10
                                    supabase.table("alunos").update({
                                        "valor_pago": 0.0,
                                        "aulas_restantes": (al.get("aulas_restantes") or 0) + novas_aulas,
                                        "presencas": 0,
                                        "faltas": 0
                                    }).eq("id", al["id"]).execute()
                                    st.success("Pacote renovado!")
                                    st.rerun()

        with tab_caixa:
            st.markdown("### 📈 Fluxo de Caixa e Metas")
            
            meta_faturamento = st.number_input("Definir Meta de Faturamento Mensal (R$):", value=5000.0, step=500.0)
            
            total_pago_caixa = sum([float(al.get("valor_pago") or 0.0) for al in alunos_todos])
            total_a_receber = sum([
                max(0.0, (float(al.get("valor_pacote") or 0.0) if al.get("tipo_cobranca") == "pacote" else ((al.get("presencas") or 0) + (al.get("faltas") or 0)) * float(al.get("valor_aula") or 0.0)) - float(al.get("valor_pago") or 0.0))
                for al in alunos_todos
            ])
            
            progresso = min(1.0, total_pago_caixa / meta_faturamento) if meta_faturamento > 0 else 0.0
            
            st.markdown(f"**Progresso da Meta ({progresso*100:.1f}%): R$ {total_pago_caixa:.2f} / R$ {meta_faturamento:.2f}**")
            st.progress(progresso)
            
            st.divider()
            c_c1, c_c2 = st.columns(2)
            c_c1.metric("Total Recebido (Caixa)", f"R$ {total_pago_caixa:.2f}")
            c_c2.metric("Previsão a Receber", f"R$ {total_a_receber:.2f}")
