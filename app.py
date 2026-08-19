import streamlit as st  
import pandas as pd  
import urllib.parse  
from datetime import datetime, date, time, timedelta  
from supabase import create_client, Client  
  
st.set_page_config(page_title="SaaS Personal Trainer", layout="wide")  
  
SUPABASE_URL = "https://vkanwxrjtajiivghyapb.supabase.co"  
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZrYW53eHJqdGFqaWl2Z2h5YXBiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcxNDgzNTYsImV4cCI6MjEwMjcyNDM1Nn0._JhswzxjiNuXnRXHMcpgEbZiEE017RUyn5AHR_pzslo"  
  
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)  
  
if "user" not in st.session_state:  
    st.session_state.user = None  
if "session" not in st.session_state:  
    st.session_state.session = None  
  
def preparar_cliente():  
    if st.session_state.session:  
        token = st.session_state.session.access_token  
        supabase.postgrest.auth(token)  
  
def carregar_alunos(user_id):  
    preparar_cliente()  
    res = supabase.table("alunos").select("*").eq("user_id", user_id).execute()  
    return res.data or []  

def desfazer_computo_aula(aluno_data, status_atual):
    """Estorna presenças, faltas e devolução de aulas no pacote ao excluir um treino computado."""
    if not aluno_data or status_atual not in ["realizada", "falta_cobrada"]:
        return
    
    upd = {}
    if status_atual == "realizada":
        upd["presencas"] = max(0, (aluno_data.get("presencas") or 0) - 1)
    elif status_atual == "falta_cobrada":
        upd["faltas"] = max(0, (aluno_data.get("faltas") or 0) - 1)
        
    if aluno_data.get("tipo_cobranca") == "pacote":
        upd["aulas_restantes"] = (aluno_data.get("aulas_restantes") or 0) + 1
        
    if upd:
        supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()
  
# --- LOGIN / CADASTRO ---  
if st.session_state.user is None:  
    st.title("🏋️ Painel do Personal Trainer - Login")  
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Conta"])  
      
    with aba_login:  
        with st.form("form_login"):  
            email_login = st.text_input("E-mail")  
            senha_login = st.text_input("Senha", type="password")  
            if st.form_submit_button("Entrar no Sistema"):  
                try:  
                    res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})  
                    st.session_state.user = res.user  
                    st.session_state.session = res.session  
                    st.success("Login realizado com sucesso!")  
                    st.rerun()  
                except Exception:  
                    st.error("E-mail ou senha incorretos.")  
                      
    with aba_cadastro:  
        with st.form("form_cad_user"):  
            email_cad = st.text_input("E-mail para Cadastro")  
            senha_cad = st.text_input("Crie uma Senha", type="password")  
            if st.form_submit_button("Cadastrar Conta"):  
                try:  
                    supabase.auth.sign_up({"email": email_cad, "password": senha_cad})  
                    st.success("Conta criada! Faça login na aba ao lado.")  
                except Exception as e:  
                    st.error(f"Erro ao criar conta: {e}")  
  
# --- APLICAÇÃO PRINCIPAL ---  
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
    menu = st.sidebar.radio("Navegação", [  
        "Agenda Semanal (Com Check-in)",   
        "👤 Perfil do Aluno (Frequência e Financeiro)",   
        "Cadastrar Aluno",   
        "Painel Financeiro Geral"  
    ])  
  
    # ==========================================  
    # 📌 CARDS DE ALERTAS INTELIGENTES NO TOPO  
    # ==========================================  
    hoje_dia = date.today().day  
    alertas_pacotes = []  
    alertas_financeiros = []  
  
    for al in alunos_todos:  
        if al.get("tipo_cobranca") == "pacote" and (al.get("aulas_restantes") or 0) <= 2:  
            alertas_pacotes.append(f"**{al['nome']}** ({al.get('aulas_restantes', 0)} rest/ total: {al.get('total_aulas_pacote', 0)})")  
          
        aulas_comp = (al.get("presencas") or 0) + (al.get("faltas") or 0)  
        devido = float(al.get("valor_pacote") or 0.0) if al.get("tipo_cobranca") == "pacote" else (aulas_comp * float(al.get("valor_aula") or 0.0))  
        pago = float(al.get("valor_pago") or 0.0)  
        venc = int(al.get("vencimento") or 10)  
          
        if (devido - pago) > 0.5 and hoje_dia > venc:  
            alertas_financeiros.append(f"**{al['nome']}** (Venceu dia {venc} | Pendente: R$ {(devido - pago):.2f})")  
  
    if alertas_pacotes or alertas_financeiros:  
        st.markdown("### 🔔 Central de Avisos Rápidos")  
        c_al1, c_al2 = st.columns(2)  
        with c_al1:  
            if alertas_pacotes:  
                with st.container(border=True):  
                    st.warning("⚠️ **Pacotes no fim (≤ 2 aulas):**\n\n" + "\n".join([f"• {a}" for a in alertas_pacotes]))  
        with c_al2:  
            if alertas_financeiros:  
                with st.container(border=True):  
                    st.error("🚨 **Pagamentos Pendentes (Após Vencimento):**\n\n" + "\n".join([f"• {a}" for a in alertas_financeiros]))  
  
    # 1. CADASTRO DE ALUNOS  
    if menu == "Cadastrar Aluno":  
        st.header("Cadastrar Novo Aluno")  
          
        tipo_cobranca = st.radio("Selecione o Tipo de Plano", ["Pacote de Aulas", "Aula Avulsa"], horizontal=True)  
        is_pacote = (tipo_cobranca == "Pacote de Aulas")  
          
        with st.container(border=True):  
            with st.form("form_cadastro"):  
                nome = st.text_input("Nome do Aluno")  
                telefone = st.text_input("Telefone (WhatsApp com DDD - Ex: 5521999999999)")  
                  
                c1, c2 = st.columns(2)  
                with c1:  
                    valor_aula = st.number_input("Valor por Aula Avulsa (R$)", min_value=0.0, value=80.0, disabled=is_pacote)  
                    valor_pacote = st.number_input("Valor Total do Pacote (R$)", min_value=0.0, value=600.0, disabled=not is_pacote)  
                with c2:  
                    total_aulas_pacote = st.number_input("Quantidade de Aulas no Pacote", min_value=1, value=10, step=1, disabled=not is_pacote)  
                    vencimento = st.number_input("Dia do Vencimento do Pagamento", min_value=1, max_value=31, value=10)  
                      
                btn_salvar = st.form_submit_button("Salvar Cadastramento do Aluno", use_container_width=True)  
                  
                if btn_salvar:  
                    if not nome:  
                        st.warning("Por favor, preencha o nome do aluno.")  
                    else:  
                        tipo = "pacote" if is_pacote else "avulso"  
                        try:  
                            preparar_cliente()  
                            qtd_aulas = int(total_aulas_pacote) if is_pacote else 0  
                            dados = {  
                                "user_id": user_id,  
                                "nome": nome,  
                                "telefone": telefone.strip(),  
                                "tipo_cobranca": tipo,  
                                "valor_aula": float(valor_aula) if not is_pacote else 0.0,  
                                "valor_pacote": float(valor_pacote) if is_pacote else 0.0,  
                                "total_aulas_pacote": qtd_aulas,  
                                "aulas_restantes": qtd_aulas,  
                                "vencimento": int(vencimento),  
                                "presencas": 0,  
                                "faltas": 0,  
                                "valor_pago": 0.0  
                            }  
                            supabase.table("alunos").insert(dados).execute()  
                            st.success(f"Aluno {nome} cadastrado com sucesso!")  
                            st.rerun()  
                        except Exception as e:  
                            st.error(f"Erro ao salvar no banco de dados: {e}")  
  
    # 2. AGENDA SEMANAL COM CARDS INDIVIDUAIS  
    elif menu == "Agenda Semanal (Com Check-in)":  
        st.header("📅 Agenda de Treinos")  
          
        if "semana_inicio" not in st.session_state:  
            hoje = date.today()  
            st.session_state.semana_inicio = hoje - timedelta(days=hoje.weekday())  
  
        c_nav1, c_nav2, c_nav3, c_nav4 = st.columns([1, 1, 1, 2])  
        with c_nav1:  
            if st.button("⬅️ Semana Anterior", use_container_width=True):  
                st.session_state.semana_inicio -= timedelta(days=7)  
                st.rerun()  
        with c_nav2:  
            if st.button("📅 Esta Semana", use_container_width=True):  
                hoje = date.today()  
                st.session_state.semana_inicio = hoje - timedelta(days=hoje.weekday())  
                st.rerun()  
        with c_nav3:  
            if st.button("Próxima Semana ➡️", use_container_width=True):  
                st.session_state.semana_inicio += timedelta(days=7)  
                st.rerun()  
        with c_nav4:  
            semana_fim = st.session_state.semana_inicio + timedelta(days=6)  
            st.markdown(f"### 🗓️ `{st.session_state.semana_inicio.strftime('%d/%m/%Y')}` a `{semana_fim.strftime('%d/%m/%Y')}`")  
  
        st.divider()  
  
        modo_exibicao = st.radio("Modo de Visualização", ["📱 Cartões por Dia (Mobile)", "🖥️ Grade Semanal (7 Colunas)"], horizontal=True)  
  
        alunos = alunos_todos  
        mapa_alunos_id = {a["id"]: a for a in alunos}  
          
        tab_avulso, tab_recorrente = st.tabs(["📌 Agendar Aula Avulsa", "🔄 Gerar Horários Recorrentes (4 Semanas)"])  
          
        with tab_avulso:  
            if not alunos:  
                st.warning("Cadastre um aluno primeiro.")  
            else:  
                mapa_alunos_nome = {a["nome"]: a for a in alunos}  
                with st.form("form_agendar_semanal"):  
                    col_f1, col_f2, col_f3 = st.columns(3)  
                    with col_f1:  
                        aluno_sel = st.selectbox("Aluno", list(mapa_alunos_nome.keys()))  
                    with col_f2:  
                        data_aula = st.date_input("Data da Aula", value=date.today())  
                    with col_f3:  
                        hora_aula = st.time_input("Horário", value=time(8, 0))  
                      
                    if st.form_submit_button("Confirmar Agendamento", use_container_width=True):  
                        preparar_cliente()  
                        dt_completa = datetime.combine(data_aula, hora_aula).isoformat()  
                        supabase.table("agendamentos").insert({  
                            "user_id": user_id,  
                            "aluno_id": mapa_alunos_nome[aluno_sel]["id"],  
                            "data_hora": dt_completa,  
                            "status": "agendado"  
                        }).execute()  
                        st.success("Aula agendada!")  
                        st.rerun()  
  
        with tab_recorrente:  
            if not alunos:  
                st.warning("Cadastre um aluno primeiro.")  
            else:  
                mapa_alunos_nome = {a["nome"]: a for a in alunos}  
                with st.form("form_agendar_recorrente"):  
                    st.caption("Gere automaticamente as aulas para o aluno nas próximas semanas de uma vez só.")  
                    al_rec = st.selectbox("Aluno", list(mapa_alunos_nome.keys()), key="rec_aluno")  
                    dias_semana_sel = st.multiselect("Dias da Semana", ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"], default=["Segunda", "Quarta"])  
                    hora_rec = st.time_input("Horário Fixo", value=time(8, 0), key="rec_hora")  
                    qtd_semanas = st.slider("Gerar para quantas semanas à frente?", min_value=1, max_value=8, value=4)  
                      
                    if st.form_submit_button("🔁 Gerar Agenda Recorrente", use_container_width=True):  
                        preparar_cliente()  
                        aluno_obj_rec = mapa_alunos_nome[al_rec]  
                        mapa_dias = {"Segunda": 0, "Terça": 1, "Quarta": 2, "Quinta": 3, "Sexta": 4, "Sábado": 5, "Domingo": 6}  
                        dias_indices = [mapa_dias[d] for d in dias_semana_sel]  
                          
                        novos_agendamentos = []  
                        data_base = date.today()  
                          
                        for dia_i in range(qtd_semanas * 7):  
                            dt_curr = data_base + timedelta(days=dia_i)  
                            if dt_curr.weekday() in dias_indices:  
                                dt_comp = datetime.combine(dt_curr, hora_rec).isoformat()  
                                novos_agendamentos.append({  
                                    "user_id": user_id,  
                                    "aluno_id": aluno_obj_rec["id"],  
                                    "data_hora": dt_comp,  
                                    "status": "agendado"  
                                })  
                          
                        if novos_agendamentos:  
                            supabase.table("agendamentos").insert(novos_agendamentos).execute()  
                            st.success(f"{len(novos_agendamentos)} treinos criados com sucesso para {al_rec}!")  
                            st.rerun()  
  
        st.divider()  
  
        preparar_cliente()  
        try:  
            res_agenda = supabase.table("agendamentos").select("*").eq("user_id", user_id).execute()  
            dados_agenda = res_agenda.data or []  
        except Exception as e:  
            st.error(f"Erro ao carregar agenda: {e}")  
            dados_agenda = []  
  
        dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]  
        datas_da_semana = [st.session_state.semana_inicio + timedelta(days=i) for i in range(7)]  
          
        # VISUALIZAÇÃO EM CARDS POR DIA  
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
                    # CARD DE AULA  
                    with st.container(border=True):  
                        c_m1, c_m2, c_m3 = st.columns([2, 2, 3])  
                        with c_m1:  
                            st.markdown(f"### ⏰ {item['hora_str']}")  
                            st.markdown(f"👤 **{item['aluno_nome']}**")  
                        with c_m2:  
                            status_tag = "🔵 AGENDADO"  
                            if item["status"] == "realizada": status_tag = "✅ REALIZADA"  
                            elif item["status"] == "falta_cobrada": status_tag = "❌ FALTA COBRADA"  
                            st.write(f"Status: **{status_tag}**")  
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
  
        # VISUALIZAÇÃO EM GRADE  
        else:  
            cols_dias = st.columns(7)  
            for i, col in enumerate(cols_dias):  
                dia_dt = datas_da_semana[i]  
                nome_dia = dias_semana[i]  
                é_hoje = (dia_dt == date.today())  
                  
                with col:  
                    header_str = f"**{nome_dia}**\n\n`{dia_dt.strftime('%d/%m')}`"  
                    if é_hoje:  
                        st.success(f"📌 {header_str}")  
                    else:  
                        st.markdown(f"### {header_str}")  
                    st.divider()  
  
                    agendamentos_dia = []  
                    for item in dados_agenda:  
                        dt = datetime.fromisoformat(item["data_hora"])  
                        if dt.date() == dia_dt:  
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
                        st.caption("*Nenhum treino*")  
                    else:  
                        for item in agendamentos_dia:  
                            aluno_data = item["aluno_obj"]  
                            with st.container(border=True):  
                                status_tag = "🔵"  
                                if item["status"] == "realizada": status_tag = "✅"  
                                elif item["status"] == "falta_cobrada": status_tag = "❌"  
  
                                st.markdown(f"{status_tag} **{item['hora_str']}**")  
                                st.markdown(f"**{item['aluno_nome']}**")  
                                  
                                with st.popover("⚙️ Ações"):  
                                    if st.button("✅ Presença", key=f"p_{item['id']}", use_container_width=True):  
                                        preparar_cliente()  
                                        supabase.table("agendamentos").update({"status": "realizada"}).eq("id", item["id"]).execute()  
                                        if aluno_data:  
                                            upd = {"presencas": (aluno_data.get("presencas") or 0) + 1}  
                                            restantes = aluno_data.get("aulas_restantes") or 0  
                                            if aluno_data.get("tipo_cobranca") == "pacote" and restantes > 0:  
                                                upd["aulas_restantes"] = restantes - 1  
                                            supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()  
                                        st.rerun()  
  
                                    if st.button("❌ Falta Cobrada", key=f"fc_{item['id']}", use_container_width=True):  
                                        preparar_cliente()  
                                        supabase.table("agendamentos").update({"status": "falta_cobrada"}).eq("id", item["id"]).execute()  
                                        if aluno_data:  
                                            upd = {"faltas": (aluno_data.get("faltas") or 0) + 1}  
                                            restantes = aluno_data.get("aulas_restantes") or 0  
                                            if aluno_data.get("tipo_cobranca") == "pacote" and restantes > 0:  
                                                upd["aulas_restantes"] = restantes - 1  
                                            supabase.table("alunos").update(upd).eq("id", aluno_data["id"]).execute()  
                                        st.rerun()  
  
                                    if item["telefone"]:  
                                        msg = f"Olá {item['aluno_nome']}! Confirmado nosso treino em {item['data_str']} às {item['hora_str']}?"  
                                        link_wsp = f"https://wa.me/{item['telefone']}?text={urllib.parse.quote(msg)}"  
                                        st.link_button("💬 WhatsApp", link_wsp, use_container_width=True)  
  
                                    if st.button("🗑️ Excluir", key=f"del_{item['id']}", use_container_width=True, type="primary"):  
                                        preparar_cliente()  
                                        desfazer_computo_aula(aluno_data, item["status"])
                                        supabase.table("agendamentos").delete().eq("id", item["id"]).execute()  
                                        st.rerun()  
  
    # 3. PERFIL DO ALUNO EM CARDS DETALHADOS  
    elif menu == "👤 Perfil do Aluno (Frequência e Financeiro)":  
        st.header("👤 Perfil Individual do Aluno")  
        alunos = alunos_todos  
          
        if not alunos:  
            st.warning("Nenhum aluno cadastrado.")  
        else:  
            busca_nome = st.text_input("🔍 Buscar Aluno por Nome", "")  
            alunos_filtrados = [a for a in alunos if busca_nome.lower() in a.get("nome", "").lower()]  
              
            if not alunos_filtrados:  
                st.info("Nenhum aluno encontrado.")  
            else:  
                mapa_alunos = {a["nome"]: a for a in alunos_filtrados}  
                aluno_sel = st.selectbox("Selecione o Aluno", list(mapa_alunos.keys()))  
                aluno = mapa_alunos[aluno_sel]  
                  
                st.divider()  
                  
                # CARD DE RESUMO DO PLANO  
                with st.container(border=True):  
                    st.subheader("1️⃣ Frequência & Resumo do Plano")  
                    c_freq1, c_freq2, c_freq3, c_freq4 = st.columns(4)  
                    c_freq1.metric("Presenças Confirmadas", aluno.get("presencas", 0))  
                    c_freq2.metric("Faltas Cobradas", aluno.get("faltas", 0))  
                      
                    if aluno.get("tipo_cobranca") == "pacote":  
                        c_freq3.metric("Aulas Restantes", f"{aluno.get('aulas_restantes', 0)} / {aluno.get('total_aulas_pacote', 0)}")  
                        with c_freq4:  
                            st.write("")  
                            if st.button("🔄 Renovar Pacote", use_container_width=True):  
                                preparar_cliente()  
                                novas_restantes = (aluno.get("aulas_restantes") or 0) + (aluno.get("total_aulas_pacote") or 0)  
                                supabase.table("alunos").update({"aulas_restantes": novas_restantes}).eq("id", aluno["id"]).execute()  
                                st.success("Pacote renovado!")  
                                st.rerun()  
                    else:  
                        aulas_computadas = (aluno.get("presencas") or 0) + (aluno.get("faltas") or 0)  
                        c_freq3.metric("Total Aulas Realizadas", aulas_computadas)  
                        c_freq4.caption("Modalidade: Aula Avulsa")  
  
                st.divider()  
  
                # CARD FINANCEIRO  
                with st.container(border=True):  
                    st.subheader("2️⃣ Controle Financeiro e Valores")  
                    aulas_computadas = (aluno.get("presencas") or 0) + (aluno.get("faltas") or 0)  
                    total_devido = float(aluno.get("valor_pacote") or 0.0) if aluno.get("tipo_cobranca") == "pacote" else (aulas_computadas * float(aluno.get("valor_aula") or 0.0))  
                    valor_pago = float(aluno.get("valor_pago") or 0.0)  
                    saldo_pendente = total_devido - valor_pago  
                      
                    f1, f2, f3, f4 = st.columns(4)  
                    f1.metric("Tipo de Plano", "Pacote" if aluno.get("tipo_cobranca") == "pacote" else "Avulso")  
                    f2.metric("Total Devido", f"R$ {total_devido:.2f}")  
                    f3.metric("Valor Já Pago", f"R$ {valor_pago:.2f}")  
                    f4.metric("Saldo Pendente", f"R$ {max(0.0, saldo_pendente):.2f}")  
  
                    col_pag1, col_pag2 = st.columns(2)  
                    with col_pag1:  
                        with st.expander("💰 Registrar Novo Pagamento"):  
                            with st.form(f"form_pag_{aluno['id']}"):  
                                v_pago = st.number_input("Valor Recebido (R$)", min_value=0.0, step=10.0, value=float(max(0.0, saldo_pendente)))  
                                if st.form_submit_button("Confirmar Recebimento", use_container_width=True):  
                                    preparar_cliente()  
                                    novo_pago = valor_pago + v_pago  
                                    supabase.table("alunos").update({"valor_pago": novo_pago}).eq("id", aluno["id"]).execute()  
                                    st.success("Pagamento registrado!")  
                                    st.rerun()  
                                      
                    with col_pag2:  
                        with st.expander("✏️ Ajustar Manualmente Valor Pago"):  
                            with st.form(f"form_set_pago_{aluno['id']}"):  
                                novo_pago_direto = st.number_input("Definir Valor Já Pago (R$)", min_value=0.0, value=valor_pago)  
                                if st.form_submit_button("Atualizar", use_container_width=True):  
                                    preparar_cliente()  
                                    supabase.table("alunos").update({"valor_pago": float(novo_pago_direto)}).eq("id", aluno["id"]).execute()  
                                    st.success("Valor atualizado!")  
                                    st.rerun()  
  
                st.divider()  
  
                # CARD DE EDIÇÃO LIVRE  
                with st.expander("🛠️ Ajustar Valores e Números do Aluno Manualmente"):  
                    with st.form(f"form_edicao_aluno_{aluno['id']}"):  
                        c_ed1, c_ed2, c_ed3 = st.columns(3)  
                        with c_ed1:  
                            novo_nome = st.text_input("Nome do Aluno", value=aluno.get("nome", ""))  
                            novo_tel = st.text_input("Telefone (WhatsApp)", value=aluno.get("telefone", ""))  
                            novo_venc = st.number_input("Dia Vencimento", min_value=1, max_value=31, value=max(1, min(31, int(aluno.get("vencimento") or 10))))  
                        with c_ed2:  
                            novas_presencas = st.number_input("Presenças Contadas", min_value=0, value=max(0, int(aluno.get("presencas") or 0)))  
                            novas_faltas = st.number_input("Faltas Cobradas", min_value=0, value=max(0, int(aluno.get("faltas") or 0)))  
                            novas_restantes = st.number_input("Aulas Restantes (Se Pacote)", min_value=0, value=max(0, int(aluno.get("aulas_restantes") or 0)))  
                        with c_ed3:  
                            novo_val_aula = st.number_input("Valor por Aula Avulsa (R$)", min_value=0.0, value=max(0.0, float(aluno.get("valor_aula") or 0.0)))  
                            novo_val_pacote = st.number_input("Valor Total Pacote (R$)", min_value=0.0, value=max(0.0, float(aluno.get("valor_pacote") or 0.0)))  
                            novo_tot_pacote = st.number_input("Tamanho do Pacote (Aulas)", min_value=0, value=max(0, int(aluno.get("total_aulas_pacote") or 0)))  
  
                        if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):  
                            preparar_cliente()  
                            dados_upd = {  
                                "nome": novo_nome,  
                                "telefone": novo_tel,  
                                "vencimento": int(novo_venc),  
                                "presencas": int(novas_presencas),  
                                "faltas": int(novas_faltas),  
                                "aulas_restantes": int(novas_restantes),  
                                "valor_aula": float(novo_val_aula),  
                                "valor_pacote": float(novo_val_pacote),  
                                "total_aulas_pacote": int(novo_tot_pacote)  
                            }  
                            supabase.table("alunos").update(dados_upd).eq("id", aluno["id"]).execute()  
                            st.success("Perfil atualizado!")  
                            st.rerun()  
  
    # 4. PAINEL FINANCEIRO GERAL COM CARDS  
    elif menu == "Painel Financeiro Geral":  
        st.header("📊 Painel Financeiro Geral")  
        alunos = alunos_todos  
          
        if alunos:  
            dados_fin = []  
            total_recebido = 0.0  
            total_pendente = 0.0  
              
            for d in alunos:  
                aulas_computadas = (d.get("presencas") or 0) + (d.get("faltas") or 0)  
                devido = float(d.get("valor_pacote") or 0.0) if d.get("tipo_cobranca") == "pacote" else (aulas_computadas * float(d.get("valor_aula") or 0.0))  
                pago = float(d.get("valor_pago") or 0.0)  
                saldo = devido - pago  
                  
                total_recebido += pago  
                total_pendente += max(0.0, saldo)  
                  
                dados_fin.append({  
                    "Aluno": d.get("nome", "Sem nome"),  
                    "Tipo": "Pacote" if d.get("tipo_cobranca") == "pacote" else "Avulso",  
                    "Presenças": d.get("presencas", 0),  
                    "Faltas": d.get("faltas", 0),  
                    "Total Devido": devido,  
                    "Valor Pago": pago,  
                    "Saldo Pendente": max(0.0, saldo)  
                })  
              
            with st.container(border=True):  
                m1, m2, m3 = st.columns(3)  
                m1.metric("Total Recebido", f"R$ {total_recebido:.2f}")  
                m2.metric("Total Pendente", f"R$ {total_pendente:.2f}")  
                m3.metric("Faturamento Esperado", f"R$ {(total_recebido + total_pendente):.2f}")  
              
            st.divider()  
            df_fin = pd.DataFrame(dados_fin)  
              
            with st.container(border=True):  
                st.subheader("Faturamento por Aluno (Pago vs Pendente)")  
                st.bar_chart(df_fin, x="Aluno", y=["Valor Pago", "Saldo Pendente"], color=["#2ECC71", "#E74C3C"])  
              
            with st.container(border=True):  
                st.subheader("Tabela Detalhada")  
                df_exibicao = df_fin.copy()  
                df_exibicao["Total Devido"] = df_exibicao["Total Devido"].apply(lambda x: f"R$ {x:.2f}")  
                df_exibicao["Valor Pago"] = df_exibicao["Valor Pago"].apply(lambda x: f"R$ {x:.2f}")  
                df_exibicao["Saldo Pendente"] = df_exibicao["Saldo Pendente"].apply(lambda x: f"R$ {x:.2f}")  
                  
                st.dataframe(df_exibicao, use_container_width=True)
