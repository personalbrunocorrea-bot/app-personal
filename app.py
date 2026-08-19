import streamlit as st  
from datetime import datetime, date, timedelta  
from supabase import create_client, Client  
from streamlit_option_menu import option_menu

# ==========================================  
# 1. CONFIGURAÇÃO DA PÁGINA E CSS CUSTOMIZADO
# ==========================================  
st.set_page_config(
    page_title="Gestão de Alunos - Studio Personal", 
    layout="wide", 
    initial_sidebar_state="expanded"
)  

def aplicar_estilo_customizado():
    st.markdown("""
        <style>
        /* Estilização dos textos das métricas/cards */
        [data-testid="stMetricValue"] {
            font-size: 22px !important;
            font-weight: bold;
            color: #2ECC71 !important;
        }
        
        /* Arredondamento e efeito hover nos botões */
        .stButton>button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease-in-out;
        }
        .stButton>button:hover {
            transform: scale(1.02);
        }

        /* Suavizar bordas das caixas/containers */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px !important;
        }

        /* Linha sutil para separar a barra lateral */
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        </style>
    """, unsafe_allow_html=True)

aplicar_estilo_customizado()

# ==========================================  
# 2. CONEXÃO SUPABASE & AUTENTICAÇÃO
# ==========================================  
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")  
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")  

@st.cache_resource  
def init_supabase():  
    return create_client(SUPABASE_URL, SUPABASE_KEY)  

supabase: Client = init_supabase()  

if "user" not in st.session_state:  
    st.session_state.user = None  
if "session" not in st.session_state:  
    st.session_state.session = None  

def preparar_cliente():  
    if st.session_state.session:  
        supabase.postgrest.auth(st.session_state.session.access_token)  

def carregar_alunos(user_id):  
    preparar_cliente()  
    res = supabase.table("alunos").select("*").eq("user_id", user_id).order("nome").execute()  
    return res.data if res.data else []  

def desfazer_computo_aula(aluno_data, status_antigo):  
    if not aluno_data:  
        return  
    upd = {}  
    if status_antigo == "realizada":  
        pres = aluno_data.get("presencas") or 0  
        if pres > 0:  
            upd["presencas"] = pres - 1  
        if aluno_data.get("tipo_cobranca") == "pacote":  
            upd["aulas_restantes"] = (aluno_data.get("aulas_restantes") or 0) + 1  
    elif status_antigo == "falta_cobrada":  
        fal = aluno_data.get("faltas") or 0  
        if fal > 0:  
            upd["faltas"] = fal - 1  
        if aluno_data.get("tipo_cobranca") == "pacote":  
            upd["aulas_restantes"] = (aluno_data.get("aulas_restantes") or 0) + 1  
    if upd:  
        supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()  

dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]  

# ==========================================  
# 3. TELA DE LOGIN / CADASTRO
# ==========================================  
if st.session_state.user is None:  
    st.title("🏋️ Studio Personal - Acesso")  
    aba_login, aba_cadastro = st.tabs(["🔐 Entrar", "📝 Criar Conta"])  
      
    with aba_login:  
        with st.form("form_login"):  
            email = st.text_input("E-mail")  
            senha = st.text_input("Senha", type="password")  
            btn_entrar = st.form_submit_button("Entrar", use_container_width=True)  
            if btn_entrar:  
                try:  
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})  
                    st.session_state.user = res.user  
                    st.session_state.session = res.session  
                    st.success("Login realizado com sucesso!")  
                    st.rerun()  
                except Exception as e:  
                    st.error(f"Erro ao entrar: {e}")  
                      
    with aba_cadastro:  
        with st.form("form_cad"):  
            email_cad = st.text_input("E-mail para cadastro")  
            senha_cad = st.text_input("Senha (mínimo 6 caracteres)", type="password")  
            btn_cad = st.form_submit_button("Cadastrar", use_container_width=True)  
            if btn_cad:  
                try:  
                    res = supabase.auth.sign_up({"email": email_cad, "password": senha_cad})  
                    st.success("Conta criada! Se necessário, confirme o e-mail ou faça login.")  
                except Exception as e:  
                    st.error(f"Erro ao cadastrar: {e}")  

# ==========================================  
# 4. APLICAÇÃO PRINCIPAL (USUÁRIO LOGADO)
# ==========================================  
else:  
    user_id = st.session_state.user.id  
    preparar_cliente()  
    alunos_todos = carregar_alunos(user_id)  
      
    st.sidebar.write(f"Logado como: **{st.session_state.user.email}**")  
    if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):  
        supabase.auth.sign_out()  
        st.session_state.user = None  
        st.session_state.session = None  
        st.rerun()  
          
    st.sidebar.divider()  

    with st.sidebar:
        menu = option_menu(
            menu_title="Navegação",
            options=[
                "Agenda Semanal (Com Check-in)", 
                "👤 Perfil do Aluno (Frequência e Financeiro)", 
                "Cadastrar Aluno", 
                "Painel Financeiro Geral"
            ],
            icons=["calendar-week", "person-badge", "person-plus", "bar-chart-line"],
            menu_icon="ui-checks-grid",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#2ECC71", "font-size": "16px"}, 
                "nav-link": {
                    "font-size": "14px", 
                    "text-align": "left", 
                    "margin": "2px 0px", 
                    "border-radius": "8px",
                    "--hover-color": "#262730"
                },
                "nav-link-selected": {"background-color": "#262730", "font-weight": "bold"},
            }
        )

    # ==========================================  
    # CARDS DE ALERTAS INTELIGENTES EM DESTAQUE
    # ==========================================  
    hoje_dia = date.today().day  
    alertas_pacotes = []  
    alertas_financeiros = []  

    for al in alunos_todos:  
        if al.get("tipo_cobranca") == "pacote" and (al.get("aulas_restantes") or 0) <= 2:  
            alertas_pacotes.append(f"**{al['nome']}** — {al.get('aulas_restantes', 0)} aula(s) restante(s)")  
          
        aulas_comp = (al.get("presencas") or 0) + (al.get("faltas") or 0)  
        devido = float(al.get("valor_pacote") or 0.0) if al.get("tipo_cobranca") == "pacote" else (aulas_comp * float(al.get("valor_aula") or 0.0))  
        pago = float(al.get("valor_pago") or 0.0)  
        venc = int(al.get("vencimento") or 10)  
          
        if (devido - pago) > 0.5 and hoje_dia > venc:  
            alertas_financeiros.append(f"**{al['nome']}** — Pendente: R$ {(devido - pago):.2f} (Venc.: dia {venc})")  

    if alertas_pacotes or alertas_financeiros:  
        c_al1, c_al2 = st.columns(2)  
        with c_al1:  
            if alertas_pacotes:  
                with st.container(border=True):  
                    st.markdown("### ⚠️ Pacotes no Fim")  
                    for item in alertas_pacotes:
                        st.markdown(f"• {item}")
        with c_al2:  
            if alertas_financeiros:  
                with st.container(border=True):  
                    st.markdown("### 🚨 Pagamentos Atrasados")  
                    for item in alertas_financeiros:
                        st.markdown(f"• {item}")
        st.divider()

    # ==========================================
    # MENU 1: CADASTRO DE ALUNO
    # ==========================================
    if menu == "Cadastrar Aluno":  
        st.title("➕ Cadastrar Novo Aluno")  
        with st.form("form_novo_aluno"):  
            nome = st.text_input("Nome do Aluno")  
            telefone = st.text_input("Telefone / WhatsApp")  
            tipo_cobranca = st.selectbox("Tipo de Cobrança", ["pacote", "por_aula"], format_func=lambda x: "Pacote Fechado" if x == "pacote" else "Valor por Aula")  
              
            col_a, col_b = st.columns(2)  
            with col_a:  
                valor_pacote = st.number_input("Valor do Pacote (R$)", min_value=0.0, step=10.0)  
                total_aulas_pacote = st.number_input("Qtd Aulas do Pacote", min_value=0, step=1, value=10)  
            with col_b:  
                valor_aula = st.number_input("Valor por Aula Avulsa (R$)", min_value=0.0, step=5.0)  
                vencimento = st.number_input("Dia de Vencimento", min_value=1, max_value=31, value=10)  
              
            submitted = st.form_submit_button("Salvar Aluno", use_container_width=True)  
            if submitted and nome:  
                dados = {  
                    "user_id": user_id,  
                    "nome": nome,  
                    "telefone": telefone,  
                    "tipo_cobranca": tipo_cobranca,  
                    "valor_pacote": valor_pacote if tipo_cobranca == "pacote" else 0.0,  
                    "total_aulas_pacote": total_aulas_pacote if tipo_cobranca == "pacote" else 0,  
                    "aulas_restantes": total_aulas_pacote if tipo_cobranca == "pacote" else 0,  
                    "valor_aula": valor_aula if tipo_cobranca == "por_aula" else 0.0,  
                    "vencimento": vencimento,  
                    "presencas": 0,  
                    "faltas": 0,  
                    "valor_pago": 0.0  
                }  
                preparar_cliente()  
                supabase.table("alunos").insert(dados).execute()  
                st.success(f"Aluno **{nome}** cadastrado com sucesso!")  
                st.rerun()  

    # ==========================================
    # MENU 2: AGENDA SEMANAL
    # ==========================================
    elif menu == "Agenda Semanal (Com Check-in)":  
        st.title("📅 Agenda Semanal")  
          
        hoje = date.today()  
        inicio_semana = hoje - timedelta(days=hoje.weekday())  
        datas_da_semana = [inicio_semana + timedelta(days=i) for i in range(7)]  
          
        c_head1, c_head2 = st.columns([2, 1])  
        with c_head1:  
            modo_exibicao = st.radio("Formato de Visualização:", ["📱 Cartões por Dia (Mobile)", "🖥️ Grade Completa (Desktop)"], horizontal=True)  
          
        st.divider()  

        with st.expander("➕ Agendar Novo Treino"):  
            if not alunos_todos:  
                st.warning("Cadastre alunos antes de agendar.")  
            else:  
                mapa_nomes = {al["nome"]: al["id"] for al in alunos_todos}  
                aluno_sel_nome = st.selectbox("Selecione o Aluno", list(mapa_nomes.keys()))  
                data_ag = st.date_input("Data do Treino", value=hoje)  
                hora_ag = st.time_input("Horário", value=datetime.now().time())  
                  
                if st.button("Confirmar Agendamento", use_container_width=True):  
                    dt_final = datetime.combine(data_ag, hora_ag)  
                    preparar_cliente()  
                    supabase.table("agendamentos").insert({  
                        "user_id": user_id,  
                        "aluno_id": mapa_nomes[aluno_sel_nome],  
                        "data_hora": dt_final.isoformat(),  
                        "status": "agendado"  
                    }).execute()  
                    st.success("Treino agendado com sucesso!")  
                    st.rerun()  

        iso_inicio = datas_da_semana[0].isoformat()  
        iso_fim = (datas_da_semana[6] + timedelta(days=1)).isoformat()  
        preparar_cliente()  
        res_ag = supabase.table("agendamentos").select("*").eq("user_id", user_id).gte("data_hora", iso_inicio).lt("data_hora", iso_fim).execute()  
        dados_agenda = res_ag.data if res_ag.data else []  
        mapa_alunos_id = {al["id"]: al for al in alunos_todos}  

        # VISUALIZAÇÃO EM CARDS
        if modo_exibicao == "📱 Cartões por Dia (Mobile)":  
            dia_selecionado = st.selectbox("Selecione o Dia da Semana", [f"{dias_semana[i]} ({datas_da_semana[i].strftime('%d/%m')})" for i in range(7)])  
            idx_dia = [f"{dias_semana[i]} ({datas_da_semana[i].strftime('%d/%m')})" for i in range(7)].index(dia_selecionado)  
            dt_alvo = datas_da_semana[idx_dia]  
              
            agendamentos_dia = []  
            for item in dados_agenda:  
                dt = datetime.fromisoformat(item["data_hora"])  
                if dt.date() == dt_alvo:  
                    aluno_obj = mapa_alunos_id.get(item["aluno_id"], {})  
                    agendamentos_dia.append({  
                        "id": item["id"],  
                        "hora_dt": dt,  
                        "hora_str": dt.strftime("%H:%M"),  
                        "aluno_obj": aluno_obj,  
                        "aluno_nome": aluno_obj.get("nome", "Indefinido"),  
                        "telefone": aluno_obj.get("telefone", ""),  
                        "status": item.get("status", "agendado"),  
                        "data_str": dt.strftime("%d/%m/%Y")  
                    })  
            agendamentos_dia.sort(key=lambda x: x["hora_dt"])  
  
            if not agendamentos_dia:  
                st.info("Nenhum treino agendado para este dia.")  
            else:  
                for item in agendamentos_dia:  
                    aluno_data = item["aluno_obj"]  
                    with st.container(border=True):  
                        c_m1, c_m2, c_m3 = st.columns([2, 2, 3])  
                        with c_m1:  
                            st.markdown(f"### ⏰ {item['hora_str']}")  
                            st.markdown(f"👤 **{item['aluno_nome']}**")  
                        with c_m2:  
                            if item["status"] == "realizada":
                                status_tag = '<span style="background-color: #2ECC71; color: white; padding: 3px 8px; border-radius: 6px; font-weight: bold; font-size: 12px;">✅ REALIZADA</span>'
                            elif item["status"] == "falta_cobrada":
                                status_tag = '<span style="background-color: #E74C3C; color: white; padding: 3px 8px; border-radius: 6px; font-weight: bold; font-size: 12px;">❌ FALTA COBRADA</span>'
                            else:
                                status_tag = '<span style="background-color: #3498DB; color: white; padding: 3px 8px; border-radius: 6px; font-weight: bold; font-size: 12px;">🔵 AGENDADO</span>'
                            
                            st.markdown(f"Status: {status_tag}", unsafe_allow_html=True)  
                            if aluno_data:  
                                st.caption(f"Aulas restantes: {aluno_data.get('aulas_restantes', 0)}")  
                        with c_m3:  
                            ca1, ca2, ca3 = st.columns(3)  
                            if ca1.button("✅ Presença", key=f"mp_{item['id']}", use_container_width=True):  
                                preparar_cliente()  
                                supabase.table("agendamentos").update({"status": "realizada"}).eq("id", item["id"]).execute()  
                                if aluno_data:  
                                    upd = {"presencas": (aluno_data.get("presencas") or 0) + 1}  
                                    restantes = aluno_data.get("aulas_restantes") or 0  
                                    if aluno_data.get("tipo_cobranca") == "pacote" and restantes > 0:  
                                        upd["aulas_restantes"] = restantes - 1  
                                    supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()  
                                st.rerun()  
  
                            if ca2.button("❌ Falta", key=f"mfc_{item['id']}", use_container_width=True):  
                                preparar_cliente()  
                                supabase.table("agendamentos").update({"status": "falta_cobrada"}).eq("id", item["id"]).execute()  
                                if aluno_data:  
                                    upd = {"faltas": (aluno_data.get("faltas") or 0) + 1}  
                                    restantes = aluno_data.get("aulas_restantes") or 0  
                                    if aluno_data.get("tipo_cobranca") == "pacote" and restantes > 0:  
                                        upd["aulas_restantes"] = restantes - 1  
                                    supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()  
                                st.rerun()  
  
                            if ca3.button("🗑️", key=f"mdel_{item['id']}", use_container_width=True):  
                                preparar_cliente()  
                                desfazer_computo_aula(aluno_data, item["status"])
                                supabase.table("agendamentos").delete().eq("id", item["id"]).execute()  
                                st.rerun()  

        # VISUALIZAÇÃO EM GRADE DESKTOP
        else:  
            cols = st.columns(7)  
            for idx, col in enumerate(cols):  
                dt_col = datas_da_semana[idx]  
                with col:  
                    st.markdown(f"### {dias_semana[idx]}\n**{dt_col.strftime('%d/%m')}**")  
                    st.divider()  
                      
                    ag_col = []  
                    for item in dados_agenda:  
                        dt = datetime.fromisoformat(item["data_hora"])  
                        if dt.date() == dt_col:  
                            aluno_obj = mapa_alunos_id.get(item["aluno_id"], {})  
                            ag_col.append({  
                                "id": item["id"],  
                                "hora_dt": dt,  
                                "hora_str": dt.strftime("%H:%M"),  
                                "aluno_obj": aluno_obj,  
                                "aluno_nome": aluno_obj.get("nome", "Indefinido"),  
                                "status": item.get("status", "agendado")  
                            })  
                    ag_col.sort(key=lambda x: x["hora_dt"])  
                      
                    for item in ag_col:  
                        aluno_data = item["aluno_obj"]  
                        with st.container(border=True):  
                            st.write(f"⏰ **{item['hora_str']}**")  
                            st.write(f"👤 {item['aluno_nome']}")  
                            if item["status"] == "realizada":  
                                st.caption("✅ Realizada")  
                            elif item["status"] == "falta_cobrada":  
                                st.caption("❌ Falta Cobrada")  
                            else:  
                                st.caption("🔵 Agendado")  
                              
                            b1, b2, b3 = st.columns(3)  
                            if b1.button("✅", key=f"g_p_{item['id']}", help="Marcar Presença"):  
                                preparar_cliente()  
                                supabase.table("agendamentos").update({"status": "realizada"}).eq("id", item["id"]).execute()  
                                if aluno_data:  
                                    upd = {"presencas": (aluno_data.get("presencas") or 0) + 1}  
                                    restantes = aluno_data.get("aulas_restantes") or 0  
                                    if aluno_data.get("tipo_cobranca") == "pacote" and restantes > 0:  
                                        upd["aulas_restantes"] = restantes - 1  
                                    supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()  
                                st.rerun()  
                                  
                            if b2.button("❌", key=f"g_f_{item['id']}", help="Marcar Falta"):  
                                preparar_cliente()  
                                supabase.table("agendamentos").update({"status": "falta_cobrada"}).eq("id", item["id"]).execute()  
                                if aluno_data:  
                                    upd = {"faltas": (aluno_data.get("faltas") or 0) + 1}  
                                    restantes = aluno_data.get("aulas_restantes") or 0  
                                    if aluno_data.get("tipo_cobranca") == "pacote" and restantes > 0:  
                                        upd["aulas_restantes"] = restantes - 1  
                                    supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()  
                                st.rerun()  
                                  
                            if b3.button("🗑️", key=f"g_d_{item['id']}", help="Apagar Agendamento"):  
                                preparar_cliente()  
                                desfazer_computo_aula(aluno_data, item["status"])  
                                supabase.table("agendamentos").delete().eq("id", item["id"]).execute()  
                                st.rerun()  

    # ==========================================
    # MENU 3: PERFIL DO ALUNO
    # ==========================================
    elif menu == "👤 Perfil do Aluno (Frequência e Financeiro)":  
        st.title("👤 Perfil Individual do Aluno")  
        if not alunos_todos:  
            st.warning("Nenhum aluno cadastrado.")  
        else:  
            mapa_alunos_nome = {al["nome"]: al for al in alunos_todos}  
            aluno_sel_nome = st.selectbox("Selecione o Aluno para visualizar", list(mapa_alunos_nome.keys()))  
            aluno = mapa_alunos_nome[aluno_sel_nome]  
              
            st.divider()  
              
            c_perf1, c_perf2 = st.columns(2)  
            with c_perf1:  
                with st.container(border=True):  
                    st.markdown("### 📋 Dados de Cadastro")  
                    st.write(f"**Nome:** {aluno['nome']}")  
                    st.write(f"**Telefone:** {aluno.get('telefone', 'Não informado')}")  
                    tipo_str = "Pacote Fechado" if aluno.get("tipo_cobranca") == "pacote" else "Valor por Aula"  
                    st.write(f"**Tipo de Cobrança:** {tipo_str}")  
                    if aluno.get("tipo_cobranca") == "pacote":  
                        st.write(f"**Valor do Pacote:** R$ {float(aluno.get('valor_pacote') or 0.0):.2f}")  
                        st.write(f"**Aulas Restantes no Pacote:** {aluno.get('aulas_restantes', 0)} / {aluno.get('total_aulas_pacote', 0)}")  
                    else:  
                        st.write(f"**Valor por Aula:** R$ {float(aluno.get('valor_aula') or 0.0):.2f}")  
                    st.write(f"**Vencimento do Pagamento:** Dia {aluno.get('vencimento', 10)}")  
                      
            with c_perf2:  
                with st.container(border=True):  
                    st.markdown("### 📊 Frequência e Financeiro")  
                    presencas = aluno.get("presencas") or 0  
                    faltas = aluno.get("faltas") or 0  
                    total_computado = presencas + faltas  
                      
                    st.metric("Aulas Presenciais Realizadas", presencas)  
                    st.metric("Faltas Cobradas", faltas)  
                      
                    if aluno.get("tipo_cobranca") == "pacote":  
                        valor_devido = float(aluno.get("valor_pacote") or 0.0)  
                    else:  
                        valor_devido = total_computado * float(aluno.get("valor_aula") or 0.0)  
                          
                    valor_pago = float(aluno.get("valor_pago") or 0.0)  
                    saldo_devedor = valor_devido - valor_pago  
                      
                    st.write("---")  
                    st.write(f"**Total Devido (Calculado):** R$ {valor_devido:.2f}")  
                    st.write(f"**Total Já Pago:** R$ {valor_pago:.2f}")  
                    if saldo_devedor > 0:  
                        st.error(f"**Saldo Devedor Pendente:** R$ {saldo_devedor:.2f}")  
                    else:  
                        st.success("✅ Pagamentos em dia / Sem pendências!")  

            st.divider()  
            st.markdown("### 💳 Registrar Pagamento ou Renovar Pacote")  
            with st.form("form_pagamento"):  
                c_p1, c_p2 = st.columns(2)  
                with c_p1:  
                    novo_pagamento = st.number_input("Adicionar Valor Pago (R$)", min_value=0.0, step=10.0)  
                with c_p2:  
                    renovar_pacote = st.checkbox("Renovar Pacote / Resetar Contadores de Aula")  
                      
                btn_pag = st.form_submit_button("Confirmar Atualização Financeira", use_container_width=True)  
                if btn_pag:  
                    upd = {}  
                    if novo_pagamento > 0:  
                        upd["valor_pago"] = valor_pago + novo_pagamento  
                    if renovar_pacote:  
                        upd["aulas_restantes"] = aluno.get("total_aulas_pacote", 10)  
                        upd["presencas"] = 0  
                        upd["faltas"] = 0  
                        upd["valor_pago"] = 0.0  
                      
                    if upd:  
                        preparar_cliente()  
                        supabase.table("alunos").update(upd).eq("id", aluno["id"]).execute()  
                        st.success("Dados financeiros atualizados com sucesso!")  
                        st.rerun()  

    # ==========================================
    # MENU 4: PAINEL FINANCEIRO GERAL
    # ==========================================
    elif menu == "Painel Financeiro Geral":  
        st.title("📈 Painel Financeiro e Relatório Geral")  
        if not alunos_todos:  
            st.warning("Nenhum dado cadastrado.")  
        else:  
            total_arrecadado = 0.0  
            total_pendente = 0.0  
            lista_tabela = []  
              
            for al in alunos_todos:  
                pres = al.get("presencas") or 0  
                fal = al.get("faltas") or 0  
                aulas_comp = pres + fal  
                  
                if al.get("tipo_cobranca") == "pacote":  
                    devido = float(al.get("valor_pacote") or 0.0)  
                else:  
                    devido = aulas_comp * float(al.get("valor_aula") or 0.0)  
                      
                pago = float(al.get("valor_pago") or 0.0)  
                saldo = devido - pago  
                  
                total_arrecadado += pago  
                if saldo > 0:  
                    total_pendente += saldo  
                      
                lista_tabela.append({  
                    "Aluno": al["nome"],  
                    "Tipo": "Pacote" if al.get("tipo_cobranca") == "pacote" else "Por Aula",  
                    "Presenças": pres,  
                    "Faltas": fal,  
                    "Total Devido": f"R$ {devido:.2f}",  
                    "Total Pago": f"R$ {pago:.2f}",  
                    "Saldo Pendente": f"R$ {max(0.0, saldo):.2f}"  
                })  
              
            m1, m2, m3 = st.columns(3)  
            m1.metric("Total de Alunos", len(alunos_todos))  
            m2.metric("Total Arrecadado (Recebido)", f"R$ {total_arrecadado:.2f}")  
            m3.metric("Total a Receber (Pendente)", f"R$ {total_pendente:.2f}")  
              
            st.divider()  
            st.markdown("### 📄 Resumo por Aluno")  
            st.dataframe(lista_tabela, use_container_width=True)
