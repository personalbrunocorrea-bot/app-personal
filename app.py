import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, date, time
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
    
    st.sidebar.write(f"Logado como: **{st.session_state.user.email}**")
    if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.session = None
        st.rerun()
        
    st.sidebar.divider()
    menu = st.sidebar.radio("Navegação", ["Agenda (Estilo Google Agenda)", "Check-in Diário", "Cadastrar Aluno", "Painel Financeiro"])

    def carregar_alunos():
        preparar_cliente()
        res = supabase.table("alunos").select("*").eq("user_id", user_id).execute()
        return res.data or []

    # 1. CADASTRO DE ALUNOS
    if menu == "Cadastrar Aluno":
        st.header("Cadastrar Novo Aluno")
        with st.form("form_cadastro"):
            nome = st.text_input("Nome do Aluno")
            telefone = st.text_input("Telefone (WhatsApp com DDD - Ex: 5521999999999)")
            tipo_cobranca = st.selectbox("Tipo de Cobrança", ["Aula Avulsa", "Pacote de Aulas"])
            
            c1, c2 = st.columns(2)
            with c1:
                valor_aula = st.number_input("Valor p/ Aula (R$)", min_value=0.0, value=80.0, disabled=(tipo_cobranca == "Pacote de Aulas"))
                valor_pacote = st.number_input("Valor do Pacote (R$)", min_value=0.0, value=600.0, disabled=(tipo_cobranca == "Aula Avulsa"))
            with c2:
                total_aulas_pacote = st.number_input("Qtd de Aulas no Pacote", min_value=1, value=10, disabled=(tipo_cobranca == "Aula Avulsa"))
                vencimento = st.number_input("Dia do Vencimento", min_value=1, max_value=31, value=10)
                
            btn_salvar = st.form_submit_button("Salvar Aluno")
            
            if btn_salvar:
                if not nome:
                    st.warning("Por favor, preencha o nome do aluno.")
                else:
                    tipo = "pacote" if tipo_cobranca == "Pacote de Aulas" else "avulso"
                    try:
                        preparar_cliente()
                        dados = {
                            "user_id": user_id,
                            "nome": nome,
                            "telefone": telefone.strip(),
                            "tipo_cobranca": tipo,
                            "valor_aula": float(valor_aula) if tipo == "avulso" else 0.0,
                            "valor_pacote": float(valor_pacote) if tipo == "pacote" else 0.0,
                            "total_aulas_pacote": int(total_aulas_pacote) if tipo == "pacote" else 0,
                            "aulas_restantes": int(total_aulas_pacote) if tipo == "pacote" else 0,
                            "vencimento": int(vencimento),
                            "presencas": 0,
                            "faltas": 0,
                            "valor_pago": 0.0
                        }
                        supabase.table("alunos").insert(dados).execute()
                        st.success(f"Aluno {nome} cadastrado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco de dados: {e}")

    # 2. AGENDA
    elif menu == "Agenda (Estilo Google Agenda)":
        st.header("📅 Agenda Visual do Professor")
        
        col_esq, col_dir = st.columns([1, 2])
        alunos = carregar_alunos()
        mapa_alunos_id = {a["id"]: a for a in alunos}
        
        with col_esq:
            st.subheader("Agendar Nova Aula")
            if not alunos:
                st.warning("Cadastre um aluno primeiro.")
            else:
                mapa_alunos_nome = {a["nome"]: a for a in alunos}
                with st.form("form_agendar"):
                    aluno_sel = st.selectbox("Aluno", list(mapa_alunos_nome.keys()))
                    data_aula = st.date_input("Data", value=date.today())
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

        with col_dir:
            st.subheader("Grade Horária")
            data_filtro = st.date_input("Selecionar Dia para Visualizar", value=date.today())
            
            preparar_cliente()
            
            # Busca agendamentos simples com fallback local para evitar erros de JOIN
            try:
                res_agenda = supabase.table("agendamentos").select("*").eq("user_id", user_id).execute()
                dados_agenda = res_agenda.data or []
            except Exception as e:
                st.error(f"Erro ao carregar agenda: {e}")
                dados_agenda = []

            agendamentos_dia = {}
            for item in dados_agenda:
                dt = datetime.fromisoformat(item["data_hora"])
                if dt.date() == data_filtro:
                    aluno_obj = mapa_alunos_id.get(item["aluno_id"], {})
                    agendamentos_dia[dt.hour] = {
                        "id": item["id"],
                        "aluno": aluno_obj.get("nome", "Aluno Indefinido"),
                        "telefone": aluno_obj.get("telefone", ""),
                        "minuto": dt.strftime("%M"),
                        "status": item.get("status", "agendado"),
                        "data_str": dt.strftime("%d/%m/%Y"),
                        "hora_str": dt.strftime("%H:%M")
                    }

            for h in range(6, 23):
                hora_label = f"{h:02d}:00"
                if h in agendamentos_dia:
                    info = agendamentos_dia[h]
                    col_info, col_wsp, col_del = st.columns([3, 1.2, 1])
                    with col_info:
                        st.info(f"⏰ **{hora_label}** (às {h:02d}:{info['minuto']}) — 👤 **{info['aluno']}**")
                    with col_wsp:
                        if info["telefone"]:
                            msg = f"Olá {info['aluno']}! Passando para lembrar do nosso treino agendado para {info['data_str']} às {info['hora_str']}. Confirmado?"
                            msg_enc = urllib.parse.quote(msg)
                            link_wsp = f"https://wa.me/{info['telefone']}?text={msg_enc}"
                            st.link_button("💬 WhatsApp", link_wsp, use_container_width=True)
                        else:
                            st.caption("Sem telefone")
                    with col_del:
                        if st.button("🗑️ Cancelar", key=f"del_{info['id']}", use_container_width=True):
                            preparar_cliente()
                            supabase.table("agendamentos").delete().eq("id", info["id"]).execute()
                            st.success("Agendamento desmarcado!")
                            st.rerun()
                else:
                    st.write(f"⏱️ `{hora_label}` — *Livre*")

    # 3. CHECK-IN DIÁRIO
    elif menu == "Check-in Diário":
        st.header("Apontamento Diário, Ajuste de Aulas e Pagamentos")
        alunos = carregar_alunos()
        
        if alunos:
            mapa_alunos = {a["nome"]: a for a in alunos}
            aluno = mapa_alunos[st.selectbox("Selecione o Aluno", list(mapa_alunos.keys()))]
            
            aulas_computadas = aluno["presencas"] + aluno["faltas"]
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Modalidade", "Pacote" if aluno["tipo_cobranca"] == "pacote" else "Aula Avulsa")
            
            if aluno["tipo_cobranca"] == "pacote":
                col2.metric("Aulas Restantes", f"{aluno['aulas_restantes']} / {aluno['total_aulas_pacote']}")
                total_devido = float(aluno["valor_pacote"])
            else:
                col2.metric("Aulas Apenas Computadas", aulas_computadas)
                total_devido = aulas_computadas * float(aluno["valor_aula"])
                
            saldo_pendente = total_devido - float(aluno["valor_pago"])
            col3.metric("Saldo Pendente", f"R$ {saldo_pendente:.2f}", delta=f"Total Devido: R$ {total_devido:.2f}", delta_color="inverse")
            
            st.caption(f"📌 **Resumo:** {aluno['presencas']} Presenças | {aluno['faltas']} Faltas | Já Pago: R$ {float(aluno['valor_pago']):.2f}")
            
            st.divider()
            
            st.subheader("1️⃣ Apontamentos e Ajustes de Aulas")
            c1, c2, c3, c4 = st.columns(4)
            
            if c1.button("✅ Confirmar Aula (+1)", use_container_width=True):
                preparar_cliente()
                upd = {"presencas": aluno["presencas"] + 1}
                if aluno["tipo_cobranca"] == "pacote" and aluno["aulas_restantes"] > 0:
                    upd["aulas_restantes"] = aluno["aulas_restantes"] - 1
                supabase.table("alunos").update(upd).eq("id", aluno["id"]).execute()
                st.success("Presença registrada!")
                st.rerun()
                
            if c2.button("❌ Falta Cobrada (+1)", use_container_width=True):
                preparar_cliente()
                upd = {"faltas": aluno["faltas"] + 1}
                if aluno["tipo_cobranca"] == "pacote" and aluno["aulas_restantes"] > 0:
                    upd["aulas_restantes"] = aluno["aulas_restantes"] - 1
                supabase.table("alunos").update(upd).eq("id", aluno["id"]).execute()
                st.warning("Falta registrada!")
                st.rerun()

            if c3.button("➖ Estornar Presença (-1)", use_container_width=True):
                if aluno["presencas"] > 0:
                    preparar_cliente()
                    upd = {"presencas": aluno["presencas"] - 1}
                    if aluno["tipo_cobranca"] == "pacote":
                        upd["aulas_restantes"] = aluno["aulas_restantes"] + 1
                    supabase.table("alunos").update(upd).eq("id", aluno["id"]).execute()
                    st.info("Presença estornada!")
                    st.rerun()

            if c4.button("➖ Estornar Falta (-1)", use_container_width=True):
                if aluno["faltas"] > 0:
                    preparar_cliente()
                    upd = {"faltas": aluno["faltas"] - 1}
                    if aluno["tipo_cobranca"] == "pacote":
                        upd["aulas_restantes"] = aluno["aulas_restantes"] + 1
                    supabase.table("alunos").update(upd).eq("id", aluno["id"]).execute()
                    st.info("Falta estornada!")
                    st.rerun()

            st.divider()
            st.subheader("2️⃣ Registrar Pagamento")
            cp1, cp2 = st.columns([2, 1])
            with cp1:
                pago = st.number_input("Valor Recebido (R$)", min_value=0.0, step=10.0, value=float(max(0.0, saldo_pendente)))
            with cp2:
                st.write("")
                st.write("")
                if st.button("💰 Confirmar Pagamento", use_container_width=True):
                    preparar_cliente()
                    novo_pago = float(aluno["valor_pago"]) + pago
                    supabase.table("alunos").update({"valor_pago": novo_pago}).eq("id", aluno["id"]).execute()
                    st.success("Pagamento registrado!")
                    st.rerun()

    # 4. PAINEL FINANCEIRO
    elif menu == "Painel Financeiro":
        st.header("📊 Resumo Financeiro e Faturamento")
        alunos = carregar_alunos()
        
        if alunos:
            dados_fin = []
            total_recebido = 0.0
            total_pendente = 0.0
            
            for d in alunos:
                aulas_computadas = d["presencas"] + d["faltas"]
                devido = float(d["valor_pacote"]) if d["tipo_cobranca"] == "pacote" else (aulas_computadas * float(d["valor_aula"]))
                pago = float(d["valor_pago"])
                saldo = devido - pago
                
                total_recebido += pago
                total_pendente += max(0.0, saldo)
                
                dados_fin.append({
                    "Aluno": d["nome"],
                    "Tipo": "Pacote" if d["tipo_cobranca"] == "pacote" else "Avulso",
                    "Presenças": d["presencas"],
                    "Faltas": d["faltas"],
                    "Total Devido": devido,
                    "Valor Pago": pago,
                    "Saldo Pendente": max(0.0, saldo)
                })
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Recebido", f"R$ {total_recebido:.2f}")
            m2.metric("Total Pendente", f"R$ {total_pendente:.2f}")
            m3.metric("Faturamento Esperado", f"R$ {(total_recebido + total_pendente):.2f}")
            
            st.divider()
            
            df_fin = pd.DataFrame(dados_fin)
            st.subheader("Faturamento por Aluno (Pago vs Pendente)")
            st.bar_chart(df_fin, x="Aluno", y=["Valor Pago", "Saldo Pendente"], color=["#2ECC71", "#E74C3C"])
            
            st.subheader("Tabela Detalhada")
            df_exibicao = df_fin.copy()
            df_exibicao["Total Devido"] = df_exibicao["Total Devido"].apply(lambda x: f"R$ {x:.2f}")
            df_exibicao["Valor Pago"] = df_exibicao["Valor Pago"].apply(lambda x: f"R$ {x:.2f}")
            df_exibicao["Saldo Pendente"] = df_exibicao["Saldo Pendente"].apply(lambda x: f"R$ {x:.2f}")
            
            st.dataframe(df_exibicao, use_container_width=True)
