import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, timedelta
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar
import urllib.parse
import re
import uuid

# ==========================================
# CONFIGURAÇÃO E CSS (DESIGN REFINADO)
# ==========================================
st.set_page_config(page_title="Assistente Personal Trainer", layout="wide", initial_sidebar_state="expanded")

def aplicar_estilo_customizado():
    st.markdown("""
        <style>
        /* Importação da fonte moderna Plus Jakarta Sans */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        /* Estilização de Cards e Bloco de Métricas (Glassmorphism) */
        [data-testid="stMetric"], div[data-testid="stVerticalBlock"] > div[style*="border"] {
            background: rgba(30, 41, 59, 0.5) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 16px !important;
            backdrop-filter: blur(12px) !important;
            box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.2) !important;
            padding: 1.2rem !important;
            transition: all 0.3s ease !important;
        }

        /* Efeito de Elevação ao Passar o Mouse nos Cards */
        [data-testid="stMetric"]:hover, div[data-testid="stVerticalBlock"] > div[style*="border"]:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 12px 32px -4px rgba(0, 0, 0, 0.3) !important;
            border-color: rgba(46, 204, 113, 0.4) !important;
        }

        /* Destaque para os Valores das Métricas */
        [data-testid="stMetricValue"] {
            color: #2ECC71 !important;
            font-weight: 700 !important;
            font-size: 28px !important;
            letter-spacing: -0.5px !important;
        }

        /* Botões com Gradiente e Sombreamento */
        .stButton>button {
            border-radius: 12px !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, #2ECC71 0%, #27AE60 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            padding: 0.6rem 1.2rem !important;
            box-shadow: 0 4px 14px rgba(46, 204, 113, 0.25) !important;
            transition: all 0.25s ease-in-out !important;
        }

        /* Animação do Botão no Hover */
        .stButton>button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(46, 204, 113, 0.4) !important;
            background: linear-gradient(135deg, #27AE60 0%, #219653 100%) !important;
        }

        /* Campos de Entrada (Inputs, Selects e Data) */
        .stTextInput>div>div>input, 
        .stSelectbox>div>div>div, 
        .stNumberInput>div>div>input, 
        .stDateInput>div>div>input {
            border-radius: 10px !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            transition: border-color 0.2s ease !important;
        }

        .stTextInput>div>div>input:focus, 
        .stSelectbox>div>div>div:focus {
            border-color: #2ECC71 !important;
            box-shadow: 0 0 0 2px rgba(46, 204, 113, 0.2) !important;
        }

        /* Estilização das Abas (Tabs) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0 !important;
            padding: 10px 20px !important;
            font-weight: 500 !important;
        }

        .stTabs [aria-selected="true"] {
            background-color: rgba(46, 204, 113, 0.15) !important;
            color: #2ECC71 !important;
            font-weight: 600 !important;
        }

        /* Modificações de Divisores */
        hr {
            margin: 2rem 0 !important;
            border-color: rgba(255, 255, 255, 0.08) !important;
        }

        /* ==========================================
           AJUSTES DE UX PARA PWA / MOBILE
           ========================================== */

        /* Reduz o efeito de "puxar pra atualizar" do navegador, deixando
           a rolagem mais parecida com a de um app nativo instalado. */
        html, body {
            overscroll-behavior-y: contain;
            -webkit-tap-highlight-color: transparent;
            -webkit-text-size-adjust: 100%;
        }

        /* Respeita a área segura do iPhone (notch / status bar / home
           indicator) quando o app está instalado em tela cheia. */
        [data-testid="stAppViewContainer"] {
            padding-top: env(safe-area-inset-top) !important;
            padding-bottom: env(safe-area-inset-bottom) !important;
        }

        /* No Safari/iOS, campo de texto com fonte menor que 16px faz a
           tela dar zoom sozinha ao tocar. Isso trava esse comportamento. */
        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input,
        .stSelectbox [data-baseweb="select"] {
            font-size: 16px !important;
        }

        /* Alvo de toque mínimo confortável (~44px, referência Apple/Google
           HIG) nos botões, importante em tela sensível ao toque. */
        .stButton>button {
            min-height: 44px !important;
        }

        /* ==========================================
           BOTTOM SHEET (popup de ação rápida da Agenda)
           Mesmo padrão que WhatsApp/Instagram/Google Agenda mobile usam
           pra ação rápida: painel fixo na base da tela, com fundo
           escurecido atrás, em vez de um card que empurra o conteúdo.
           ========================================== */
        .agenda-popup-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 998;
            animation: agendaFadeIn 0.2s ease;
        }
        @keyframes agendaFadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes agendaSlideUp {
            from { transform: translateY(100%); }
            to { transform: translateY(0); }
        }
        .st-key-agenda_popup_sheet,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-agenda_popup_sheet),
        .st-key-agenda_novo_sheet,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-agenda_novo_sheet) {
            position: fixed !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            z-index: 999 !important;
            max-width: 480px !important;
            margin: 0 auto !important;
            background: #16241c !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            border-bottom: none !important;
            border-radius: 20px 20px 0 0 !important;
            box-shadow: 0 -10px 34px rgba(0, 0, 0, 0.45) !important;
            padding: 18px 18px calc(18px + env(safe-area-inset-bottom)) 18px !important;
            animation: agendaSlideUp 0.25s ease !important;
            max-height: 80vh !important;
            overflow-y: auto !important;
        }

        /* Botão de excluir agendamento — vermelho, pra ficar claramente
           diferente das ações normais de marcar status. */
        .st-key-pop_excluir button,
        .st-key-confirmar_excluir_sim button {
            background: rgba(231, 76, 60, 0.12) !important;
            border: 1px solid rgba(231, 76, 60, 0.4) !important;
            color: #E74C3C !important;
        }
        .st-key-pop_excluir button:hover,
        .st-key-confirmar_excluir_sim button:hover {
            background: rgba(231, 76, 60, 0.22) !important;
        }
        </style>
    """, unsafe_allow_html=True)

aplicar_estilo_customizado()

# ==========================================
# PWA: manifest, ícone e service worker
# ==========================================
# O Streamlit renderiza st.components.v1.html dentro de um <iframe>, então
# não dá pra simplesmente colocar <link rel="manifest"> num st.markdown —
# o navegador só reconhece isso se estiver no <head> do documento
# principal. Como o iframe é da mesma origem, o script consegue alcançar
# window.parent.document e injetar as tags lá. Isso precisa rodar em toda
# página (login, dashboard e a página pública do PAR-Q), por isso a
# chamada fica aqui em cima, antes de qualquer bifurcação de tela.
def injetar_pwa():
    components.html("""
        <script>
        (function() {
            const doc = window.parent.document;

            function addTag(tag, attrs) {
                const selector = tag + Object.entries(attrs)
                    .map(([k, v]) => k === 'href' || k === 'content' ? '' : `[${k}="${v}"]`)
                    .join('');
                if (doc.querySelector('link[rel="manifest"]') && attrs.rel === 'manifest') return;
                const el = doc.createElement(tag);
                Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
                doc.head.appendChild(el);
            }

            if (!doc.querySelector('link[rel="manifest"]')) {
                addTag('link', {rel: 'manifest', href: 'app/static/manifest.json'});
            }
            if (!doc.querySelector('meta[name="theme-color"]')) {
                addTag('meta', {name: 'theme-color', content: '#2ECC71'});
            }
            if (!doc.querySelector('link[rel="apple-touch-icon"]')) {
                addTag('link', {rel: 'apple-touch-icon', href: 'app/static/icon-192.png'});
            }
            if (!doc.querySelector('meta[name="apple-mobile-web-app-capable"]')) {
                addTag('meta', {name: 'apple-mobile-web-app-capable', content: 'yes'});
            }
            if (!doc.querySelector('meta[name="mobile-web-app-capable"]')) {
                addTag('meta', {name: 'mobile-web-app-capable', content: 'yes'});
            }
            if (!doc.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]')) {
                addTag('meta', {name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent'});
            }
            if (!doc.querySelector('meta[name="apple-mobile-web-app-title"]')) {
                addTag('meta', {name: 'apple-mobile-web-app-title', content: 'PT Assistente'});
            }

            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('app/static/sw.js').catch(function(err) {
                    console.log('Falha ao registrar service worker:', err);
                });
            }
        })();
        </script>
    """, height=0, width=0)

injetar_pwa()

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
# ALTERADO: em vez de consultar/gravar diretamente na tabela `alunos`
# (o que exigia RLS desativado para o anon funcionar), este bloco agora
# chama duas funções RPC (SECURITY DEFINER) no Postgres: get_aluno_por_token
# e responder_parq. A tabela `alunos` permanece protegida por RLS o tempo
# todo; só essas duas funções, bem estreitas, têm permissão de bypass.
token_aluno = st.query_params.get("token", None)

if token_aluno:
    try:
        res_p = supabase.rpc("get_aluno_por_token", {"p_token": token_aluno}).execute()
        aluno_parq = res_p.data[0] if res_p.data else None
    except Exception as e:
        aluno_parq = None

    if not aluno_parq:
        st.error("❌ Link do PAR-Q inválido, expirado ou aluno não encontrado. Por favor, solicite um novo link ao seu Personal Trainer.")
        st.stop()

    st.title("📋 Questionário de Prontidão para Atividade Física (PAR-Q)")
    st.markdown(f"Olá, **{aluno_parq['nome']}**! Para garantir sua segurança durante os treinos, por favor responda com atenção às perguntas abaixo.")
    
    if aluno_parq.get("parq_status") == "assinado":
        dt_ass = (aluno_parq.get("parq_data") or "")[:10]
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

                try:
                    res_ok = supabase.rpc("responder_parq", {
                        "p_token": token_aluno,
                        "p_respostas": respostas_json
                    }).execute()

                    if res_ok.data:
                        st.balloons()
                        st.success("✅ PAR-Q enviado com sucesso! O seu Personal Trainer já recebeu sua confirmação. Bons treinos!")
                    else:
                        st.error("Não foi possível confirmar o envio. Verifique se o link ainda é válido.")
                except Exception as e:
                    st.error(f"Erro ao salvar PAR-Q: {e}")
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

def parse_data_hora(valor_iso):
    """Faz parse de um timestamp vindo do Supabase e sempre devolve um
    datetime 'naive' (sem timezone). O Postgres devolve timestamptz com
    o fuso embutido (ex: '+00:00'), o que gera um datetime 'aware' — e
    comparar isso com datetime.now() (naive) quebra com TypeError. Como
    o resto do app já trabalha só com horário local naive (datetime.now(),
    datetime.combine(...)), a solução mais simples e consistente é
    descartar o fuso aqui, uma única vez, para todo mundo usar.
    """
    dt = datetime.fromisoformat(valor_iso)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt

def carregar_alunos(user_id):
    preparar_cliente()
    try:
        res = supabase.table("alunos").select("*").eq("user_id", user_id).order("nome").execute()
        return res.data if res.data else []
    except Exception as e:
        st.error(f"Erro ao carregar alunos: {e}")
        return []

def carregar_transacoes(user_id):
    preparar_cliente()
    try:
        res = supabase.table("transacoes").select("*").eq("user_id", user_id).execute()
        return res.data if res.data else []
    except Exception as e:
        st.error(f"Erro ao carregar transações: {e}")
        return []

def parse_data_pagamento(valor):
    if not valor:
        return None
    try:
        return parse_data_hora(valor).date()
    except Exception:
        try:
            return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
        except Exception:
            return None

def situacao_financeira(aluno, transacoes_todas, hoje_data):
    """Calcula a situação financeira real de um aluno a partir do
    histórico em `transacoes`, em vez de um único campo cumulativo.

    - por_aula: saldo devedor cumulativo (paga conforme usa) — soma tudo
      que já foi pago contra o total de aulas já dadas.
    - pacote: modelo de renovação — considera em dia se o pagamento mais
      recente aconteceu nos últimos 30 dias (o ciclo do pacote). Isso é
      o que corrige o bug original: antes, um único pagamento deixava o
      aluno "em dia" para sempre, porque não havia noção de ciclo.
    """
    transacoes_aluno = [t for t in transacoes_todas if t.get("aluno_id") == aluno.get("id")]
    pago_total = sum(float(t.get("valor") or 0.0) for t in transacoes_aluno)

    datas_pagamento = [parse_data_pagamento(t.get("data_pagamento")) for t in transacoes_aluno]
    datas_pagamento = [d for d in datas_pagamento if d is not None]
    ultimo_pagamento = max(datas_pagamento) if datas_pagamento else None

    pres = aluno.get("presencas") or 0
    fal = aluno.get("faltas") or 0
    tipo = aluno.get("tipo_cobranca")

    if tipo == "pacote":
        valor_pacote = float(aluno.get("valor_pacote") or 0.0)
        em_dia = ultimo_pagamento is not None and (hoje_data - ultimo_pagamento).days <= 30
        saldo = 0.0 if em_dia else valor_pacote
        devido_referencia = valor_pacote
    else:
        devido_referencia = (pres + fal) * float(aluno.get("valor_aula") or 0.0)
        saldo = max(0.0, devido_referencia - pago_total)
        em_dia = saldo <= 0.01

    return {
        "em_dia": em_dia,
        "saldo": round(saldo, 2),
        "devido": round(devido_referencia, 2),
        "pago_total": round(pago_total, 2),
        "ultimo_pagamento": ultimo_pagamento,
    }

DURACAO_AULA = timedelta(hours=1)

def horarios_conflitam(inicio1, inicio2, duracao=DURACAO_AULA):
    """Duas aulas conflitam se os intervalos [início, início+duração) se
    sobrepõem — não só quando começam no mesmo minuto exato. Ex: aula A
    às 14:00 e aula B às 14:30, ambas de 1h, conflitam mesmo sem começar
    no mesmo horário."""
    fim1 = inicio1 + duracao
    fim2 = inicio2 + duracao
    return inicio1 < fim2 and inicio2 < fim1

ROTULOS_STATUS = {
    "agendado": ("⏳", "Agendado", "#3788d8"),
    "presenca": ("✅", "Presença", "#2ECC71"),
    "falta_cobrada": ("❌", "Falta cobrada", "#E74C3C"),
    "falta_nao_cobrada": ("⚠️", "Falta não cobrada", "#F39C12"),
    "desmarcado": ("⚪", "Desmarcado", "#95A5A6"),
}

def calcular_efeito(status, tipo_cobranca):
    # Retorna (delta_presencas, delta_faltas, delta_aulas_restantes)
    # que um status causa no saldo do aluno.
    if status == "presenca":
        return (1, 0, -1 if tipo_cobranca == "pacote" else 0)
    elif status == "falta_cobrada":
        return (0, 1, -1 if tipo_cobranca == "pacote" else 0)
    return (0, 0, 0)  # falta_nao_cobrada, desmarcado, agendado

def aplicar_status(ag, aluno, novo_status):
    # Compartilhada pelo popup de clique no calendário e pela aba
    # "Gerenciar Presenças/Faltas" — um só lugar calcula o efeito no
    # saldo do aluno, então os dois pontos de entrada nunca divergem.
    status_antigo = ag.get("status", "agendado")
    if status_antigo == novo_status:
        return

    old_p, old_f, old_a = calcular_efeito(status_antigo, aluno.get("tipo_cobranca"))
    new_p, new_f, new_a = calcular_efeito(novo_status, aluno.get("tipo_cobranca"))

    upd_aluno = {
        "presencas": max(0, (aluno.get("presencas") or 0) - old_p + new_p),
        "faltas": max(0, (aluno.get("faltas") or 0) - old_f + new_f),
        "aulas_restantes": max(0, (aluno.get("aulas_restantes") or 0) - old_a + new_a),
    }

    preparar_cliente()
    try:
        supabase.table("agendamentos").update({"status": novo_status}).eq("id", ag["id"]).execute()
        supabase.table("alunos").update(upd_aluno).eq("id", aluno["id"]).execute()
        st.rerun()
    except Exception as e:
        st.error("Não foi possível atualizar o status. Tente novamente em instantes.")

def excluir_agendamento(ag, aluno):
    # Exclui o agendamento por completo (não é o mesmo que "Desmarcado" —
    # aquele mantém o registro, isso remove a linha do banco). Se a aula
    # já tinha sido marcada como presença/falta cobrada, desfaz o efeito
    # no saldo do aluno antes de excluir, senão o histórico fica errado.
    status_atual = ag.get("status", "agendado")
    old_p, old_f, old_a = calcular_efeito(status_atual, aluno.get("tipo_cobranca"))

    preparar_cliente()
    try:
        supabase.table("agendamentos").delete().eq("id", ag["id"]).execute()
        if old_p or old_f or old_a:
            upd_aluno = {
                "presencas": max(0, (aluno.get("presencas") or 0) - old_p),
                "faltas": max(0, (aluno.get("faltas") or 0) - old_f),
                "aulas_restantes": max(0, (aluno.get("aulas_restantes") or 0) - old_a),
            }
            supabase.table("alunos").update(upd_aluno).eq("id", aluno["id"]).execute()
        st.rerun()
    except Exception as e:
        st.error("Não foi possível excluir o agendamento. Tente novamente em instantes.")

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
    transacoes_todas = carregar_transacoes(user_id)

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
            sit = situacao_financeira(al, transacoes_todas, hoje)
            total_pendente += sit["saldo"]
            total_pago += sit["pago_total"]

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
                pendentes_lista = [al for al in alunos_todos if not situacao_financeira(al, transacoes_todas, hoje)["em_dia"]]
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

            sit = situacao_financeira(al, transacoes_todas, hoje)
            if not sit["em_dia"]:
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
        try:
            res_ag = supabase.table("agendamentos").select("*").eq("user_id", user_id).gte("data_hora", inicio_mes).execute()
            agendamentos = res_ag.data if res_ag.data else []
        except Exception as e:
            agendamentos = []
            st.error(f"Erro ao carregar agendamentos: {e}")

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

            try:
                # start e end precisam ser normalizados pela MESMA função.
                # Antes, start usava a string bruta do Supabase (com fuso
                # embutido) e end usava uma versão sem fuso — o FullCalendar
                # interpretava os dois de formas diferentes, deslocando o
                # horário de início e inflando a duração exibida.
                dt_inicio_obj = parse_data_hora(ag["data_hora"])
                dt_fim_obj = dt_inicio_obj + DURACAO_AULA
                dt_inicio = dt_inicio_obj.isoformat()
                dt_fim = dt_fim_obj.isoformat()
            except Exception:
                dt_inicio = ag["data_hora"]
                dt_fim = ag["data_hora"]

            eventos_calendario.append({
                "id": str(ag["id"]),
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
            # Grade Dia como padrão: mostra um dia só, então continua legível
            # no celular (o problema original da grade semanal de 7 colunas),
            # e ainda tem horário vazio pra tocar e agendar — o que a visão
            # em lista não permitia.
            "initialView": "timeGridDay",
            "slotMinTime": "06:00:00",
            "slotMaxTime": "22:00:00",
            "slotDuration": "00:30:00",
            "nowIndicator": True,
            "height": 620,
            "locale": "pt-br"
        }

        calendar_state = calendar(events=eventos_calendario, options=opcoes_calendario, key="agenda_calendario", callbacks=["eventClick", "dateClick"], custom_css="""
            .fc-event-title { font-weight: bold; font-size: 14px; }

            /* Botões da toolbar (hoje / navegação / trocar visão) na paleta do app */
            .fc .fc-button {
                background: rgba(46, 204, 113, 0.12) !important;
                border: 1px solid rgba(46, 204, 113, 0.35) !important;
                color: #2ECC71 !important;
                text-transform: capitalize !important;
                border-radius: 10px !important;
                padding: 8px 14px !important;
                min-height: 40px !important;
                box-shadow: none !important;
                font-weight: 600 !important;
            }
            .fc .fc-button:hover {
                background: rgba(46, 204, 113, 0.22) !important;
            }
            .fc .fc-button-primary:not(:disabled).fc-button-active,
            .fc .fc-button-primary:not(:disabled):active {
                background: #2ECC71 !important;
                border-color: #2ECC71 !important;
                color: #FFFFFF !important;
            }
            .fc .fc-toolbar-title {
                font-size: 17px !important;
                font-weight: 700 !important;
            }
            .fc .fc-toolbar {
                flex-wrap: wrap !important;
                gap: 8px !important;
                row-gap: 10px !important;
            }
            /* Dia atual em verde suave, em vez do azul padrão do FullCalendar */
            .fc .fc-day-today {
                background: rgba(46, 204, 113, 0.10) !important;
            }
            /* Alvo de toque maior nas células de horário da grade */
            .fc .fc-timegrid-slot {
                height: 2.6em !important;
            }
            .fc .fc-timegrid-slot-label-cushion {
                font-size: 12px !important;
            }
        """)

        # --- BOTTOM SHEETS: ação rápida (clique no evento) e novo
        # agendamento (clique em horário vazio) — igual ao padrão mobile
        # do Google Agenda: painel sobe da base, fundo escurece atrás.
        if "agenda_popup_ag_id" not in st.session_state:
            st.session_state.agenda_popup_ag_id = None
        if "agenda_novo_slot" not in st.session_state:
            st.session_state.agenda_novo_slot = None
        if "agenda_ultimo_clique" not in st.session_state:
            st.session_state.agenda_ultimo_clique = None

        # O componente do calendário devolve o último clique registrado em
        # TODA atualização da tela, não só quando um clique novo acontece —
        # inclusive logo depois de fechar o sheet pelo botão ✖. Sem esse
        # controle, o clique antigo reabria o sheet na hora, travando-o.
        # A solução é comparar com o último clique já processado e só agir
        # se for realmente diferente.
        assinatura_clique = None
        if calendar_state and calendar_state.get("callback") == "eventClick":
            assinatura_clique = ("eventClick", calendar_state.get("eventClick", {}).get("event", {}).get("id"))
        elif calendar_state and calendar_state.get("callback") == "dateClick":
            assinatura_clique = ("dateClick", calendar_state.get("dateClick", {}).get("dateStr"))

        if assinatura_clique and assinatura_clique != st.session_state.agenda_ultimo_clique:
            st.session_state.agenda_ultimo_clique = assinatura_clique

            if assinatura_clique[0] == "eventClick" and assinatura_clique[1]:
                st.session_state.agenda_popup_ag_id = assinatura_clique[1]
                st.session_state.agenda_novo_slot = None  # só um sheet por vez

            elif assinatura_clique[0] == "dateClick":
                info_clique = calendar_state.get("dateClick", {})
                all_day_clique = info_clique.get("allDay", True)
                try:
                    dt_slot = parse_data_hora(assinatura_clique[1])
                except Exception:
                    dt_slot = datetime.combine(hoje, datetime.now().time())
                if all_day_clique:
                    # Clicou num dia (visão de mês), sem horário — assume
                    # um horário padrão que o trainer ajusta no sheet.
                    dt_slot = datetime.combine(dt_slot.date(), datetime.strptime("08:00", "%H:%M").time())
                st.session_state.agenda_novo_slot = dt_slot.isoformat()
                st.session_state.agenda_popup_ag_id = None  # só um sheet por vez

        # --- Sheet 1: marcar presença/falta/desmarcação ---
        if st.session_state.agenda_popup_ag_id:
            ag_clicado = next((a for a in agendamentos if str(a["id"]) == str(st.session_state.agenda_popup_ag_id)), None)
            aluno_clicado = mapa_alunos_id.get(ag_clicado["aluno_id"]) if ag_clicado else None

            if ag_clicado and aluno_clicado:
                status_atual_pop = ag_clicado.get("status", "agendado")
                dt_pop = parse_data_hora(ag_clicado["data_hora"])

                st.markdown('<div class="agenda-popup-backdrop"></div>', unsafe_allow_html=True)
                with st.container(key="agenda_popup_sheet"):
                    col_pop_info, col_pop_fechar = st.columns([5, 1])
                    with col_pop_info:
                        st.markdown(f"**{dt_pop.strftime('%d/%m — %H:%M')} · {aluno_clicado['nome']}**")
                        emoji_pop, label_pop, cor_pop = ROTULOS_STATUS.get(status_atual_pop, ("⏳", "Agendado", "#3788d8"))
                        st.caption(f"Status atual: {emoji_pop} {label_pop}")
                    with col_pop_fechar:
                        if st.button("✖", key="fechar_popup_agenda", help="Fechar"):
                            st.session_state.agenda_popup_ag_id = None
                            st.rerun()

                    pb1, pb2 = st.columns(2)
                    with pb1:
                        if st.button("✅ Presença", key="pop_presenca", use_container_width=True,
                                     type="primary" if status_atual_pop == "presenca" else "secondary"):
                            aplicar_status(ag_clicado, aluno_clicado, "presenca")
                    with pb2:
                        if st.button("❌ Falta cobrada", key="pop_faltac", use_container_width=True,
                                     type="primary" if status_atual_pop == "falta_cobrada" else "secondary"):
                            aplicar_status(ag_clicado, aluno_clicado, "falta_cobrada")

                    pb3, pb4 = st.columns(2)
                    with pb3:
                        if st.button("⚠️ Falta não cobrada", key="pop_faltal", use_container_width=True,
                                     type="primary" if status_atual_pop == "falta_nao_cobrada" else "secondary"):
                            aplicar_status(ag_clicado, aluno_clicado, "falta_nao_cobrada")
                    with pb4:
                        if st.button("⚪ Desmarcado", key="pop_desm", use_container_width=True,
                                     type="primary" if status_atual_pop == "desmarcado" else "secondary"):
                            aplicar_status(ag_clicado, aluno_clicado, "desmarcado")

                    st.divider()
                    if "confirmar_exclusao_ag" not in st.session_state:
                        st.session_state.confirmar_exclusao_ag = None

                    if st.session_state.confirmar_exclusao_ag == ag_clicado["id"]:
                        st.warning("Excluir apaga o agendamento por completo — não dá pra desfazer. Se já tinha presença/falta marcada, o saldo do aluno é corrigido de volta.")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("🗑️ Sim, excluir", key="confirmar_excluir_sim", use_container_width=True):
                                st.session_state.confirmar_exclusao_ag = None
                                st.session_state.agenda_popup_ag_id = None
                                excluir_agendamento(ag_clicado, aluno_clicado)
                        with cc2:
                            if st.button("Cancelar", key="confirmar_excluir_nao", use_container_width=True):
                                st.session_state.confirmar_exclusao_ag = None
                                st.rerun()
                    else:
                        if st.button("🗑️ Excluir Agendamento", key="pop_excluir", use_container_width=True):
                            st.session_state.confirmar_exclusao_ag = ag_clicado["id"]
                            st.rerun()
            else:
                # A aula clicada não existe mais na lista atual (ex: fora do
                # intervalo carregado) — limpa pra não deixar sheet fantasma.
                st.session_state.agenda_popup_ag_id = None

        # --- Sheet 2: novo agendamento (clique em horário vazio) ---
        if st.session_state.agenda_novo_slot:
            dt_novo = parse_data_hora(st.session_state.agenda_novo_slot)
            mapa_nomes_sheet = {al["nome"]: al["id"] for al in alunos_todos}
            # As keys incluem o horário clicado (não são fixas) — se fossem
            # fixas, depois do primeiro clique o Streamlit ignora o valor
            # novo e mantém sempre o primeiro horário que já foi mostrado.
            sufixo_key = st.session_state.agenda_novo_slot

            st.markdown('<div class="agenda-popup-backdrop"></div>', unsafe_allow_html=True)
            with st.container(key="agenda_novo_sheet"):
                col_novo_info, col_novo_fechar = st.columns([5, 1])
                with col_novo_info:
                    st.markdown(f"**➕ Novo agendamento — {dt_novo.strftime('%d/%m/%Y')}**")
                with col_novo_fechar:
                    if st.button("✖", key="fechar_novo_sheet", help="Fechar"):
                        st.session_state.agenda_novo_slot = None
                        st.rerun()

                if not mapa_nomes_sheet:
                    st.warning("Cadastre um aluno primeiro, na aba Alunos & CRM.")
                else:
                    aluno_novo_nome = st.selectbox("Aluno", list(mapa_nomes_sheet.keys()), key=f"sheet_aluno_{sufixo_key}")
                    col_data_sheet, col_hora_sheet = st.columns(2)
                    with col_data_sheet:
                        data_novo_sheet = st.date_input("Data", value=dt_novo.date(), key=f"sheet_data_{sufixo_key}")
                    with col_hora_sheet:
                        hora_novo_sheet = st.time_input("Horário de início", value=dt_novo.time(), key=f"sheet_hora_{sufixo_key}")
                    local_novo_sheet = st.text_input("📍 Local", key=f"sheet_local_{sufixo_key}")

                    dt_inicio_preview = datetime.combine(data_novo_sheet, hora_novo_sheet)
                    dt_fim_preview = dt_inicio_preview + DURACAO_AULA
                    st.caption(f"🕐 Aula de 1 hora — vai ficar marcada das **{dt_inicio_preview.strftime('%H:%M')}** às **{dt_fim_preview.strftime('%H:%M')}**")

                    if st.button("Confirmar Agendamento", key=f"confirmar_sheet_{sufixo_key}", type="primary", use_container_width=True):
                        conflito = any(
                            horarios_conflitam(dt_inicio_preview, parse_data_hora(a["data_hora"]))
                            and a.get("status") == "agendado"
                            for a in agendamentos
                        )

                        with st.spinner("Agendando..."):
                            preparar_cliente()
                            try:
                                supabase.table("agendamentos").insert({
                                    "user_id": user_id,
                                    "aluno_id": mapa_nomes_sheet[aluno_novo_nome],
                                    "data_hora": dt_inicio_preview.isoformat(),
                                    "local": local_novo_sheet,
                                    "status": "agendado"
                                }).execute()
                                st.session_state.agenda_novo_slot = None
                                if conflito:
                                    st.toast("⚠️ Já existe outro aluno agendado nesse mesmo horário.", icon="⚠️")
                                st.rerun()
                            except Exception as e:
                                st.error("Não foi possível agendar. Tente novamente em instantes.")

        # Legenda de cores — os status só existem como cor no calendário,
        # então sem isso não dá pra saber o que cada cor significa.
        st.markdown("""
            <div style="display:flex; flex-wrap:wrap; gap:14px; padding:10px 4px 4px 4px; font-size:13px;">
                <span style="display:flex; align-items:center; gap:6px;"><span style="width:10px;height:10px;border-radius:50%;background:#3788d8;display:inline-block;"></span>Agendado</span>
                <span style="display:flex; align-items:center; gap:6px;"><span style="width:10px;height:10px;border-radius:50%;background:#2ECC71;display:inline-block;"></span>Presença</span>
                <span style="display:flex; align-items:center; gap:6px;"><span style="width:10px;height:10px;border-radius:50%;background:#E74C3C;display:inline-block;"></span>Falta cobrada</span>
                <span style="display:flex; align-items:center; gap:6px;"><span style="width:10px;height:10px;border-radius:50%;background:#F39C12;display:inline-block;"></span>Falta não cobrada</span>
                <span style="display:flex; align-items:center; gap:6px;"><span style="width:10px;height:10px;border-radius:50%;background:#95A5A6;display:inline-block;"></span>Desmarcado</span>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        tab_agendar, tab_gerenciar = st.tabs(["➕ Novo Agendamento", "⚙️ Gerenciar Presenças/Faltas"])

        with tab_agendar:
            mapa_nomes = {al["nome"]: al["id"] for al in alunos_todos}
            if mapa_nomes:
                al_nome = st.selectbox("Selecione o Aluno", list(mapa_nomes.keys()), key="tab_agendar_aluno")
                dt_ag = st.date_input("Data", value=hoje, key="tab_agendar_data")
                hr_ag = st.time_input("Horário de início", value=datetime.now().time(), key="tab_agendar_hora")
                local_ag = st.text_input("📍 Local da Aula", key="tab_agendar_local")

                dt_final_preview = datetime.combine(dt_ag, hr_ag)
                dt_fim_preview_tab = dt_final_preview + DURACAO_AULA
                st.caption(f"🕐 Aula de 1 hora — vai ficar marcada das **{dt_final_preview.strftime('%H:%M')}** às **{dt_fim_preview_tab.strftime('%H:%M')}**")

                if st.button("Agendar Horário", key="tab_agendar_confirmar", type="primary"):
                    conflito_ag = any(
                        horarios_conflitam(dt_final_preview, parse_data_hora(a["data_hora"]))
                        and a.get("status") == "agendado"
                        for a in agendamentos
                    )

                    with st.spinner("Agendando..."):
                        preparar_cliente()
                        try:
                            supabase.table("agendamentos").insert({
                                "user_id": user_id, "aluno_id": mapa_nomes[al_nome],
                                "data_hora": dt_final_preview.isoformat(), "local": local_ag, "status": "agendado"
                            }).execute()
                            if conflito_ag:
                                st.toast("⚠️ Já existe outro aluno agendado nesse mesmo horário.", icon="⚠️")
                            st.success("Agendado!")
                            st.rerun()
                        except Exception as e:
                            st.error("Não foi possível agendar. Tente novamente em instantes.")

        with tab_gerenciar:
            st.caption("Toque direto no status para marcar. Já marcou errado? É só tocar no status certo — o app corrige o saldo do aluno automaticamente.")

            data_filtro = st.date_input("Ver aulas do dia:", value=hoje, key="filtro_data_gerenciar")

            agendamentos_dia = [
                ag for ag in agendamentos
                if parse_data_hora(ag["data_hora"]).date() == data_filtro
            ]
            agendamentos_dia.sort(key=lambda ag: ag["data_hora"])

            if not agendamentos_dia:
                st.info(f"Nenhuma aula agendada para {data_filtro.strftime('%d/%m/%Y')}.")
            else:
                for ag in agendamentos_dia:
                    aluno_dados = mapa_alunos_id.get(ag["aluno_id"])
                    if not aluno_dados:
                        continue

                    status_atual = ag.get("status", "agendado")
                    hr_str = parse_data_hora(ag["data_hora"]).strftime("%H:%M")
                    atrasado = status_atual == "agendado" and parse_data_hora(ag["data_hora"]) < datetime.now()

                    with st.container(border=True):
                        col_info, col_badge = st.columns([3, 1.4])
                        with col_info:
                            st.markdown(f"**{hr_str} — {aluno_dados['nome']}**")
                            if ag.get("local"):
                                st.caption(f"📍 {ag['local']}")
                        with col_badge:
                            emoji, label, cor = ROTULOS_STATUS.get(status_atual, ("⏳", "Agendado", "#3788d8"))
                            texto_tag = "⏰ Atrasado" if atrasado else f"{emoji} {label}"
                            cor_tag = "#E74C3C" if atrasado else cor
                            st.markdown(
                                f"<div style='text-align:right; padding-top:6px;'>"
                                f"<span style='background:{cor_tag}22; color:{cor_tag}; padding:3px 10px; "
                                f"border-radius:20px; font-size:12px; font-weight:600;'>{texto_tag}</span></div>",
                                unsafe_allow_html=True
                            )

                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("✅ Presença", key=f"presenca_{ag['id']}", use_container_width=True,
                                         type="primary" if status_atual == "presenca" else "secondary"):
                                aplicar_status(ag, aluno_dados, "presenca")
                        with b2:
                            if st.button("❌ Falta cobrada", key=f"faltac_{ag['id']}", use_container_width=True,
                                         type="primary" if status_atual == "falta_cobrada" else "secondary"):
                                aplicar_status(ag, aluno_dados, "falta_cobrada")

                        b3, b4 = st.columns(2)
                        with b3:
                            if st.button("⚠️ Falta não cobrada", key=f"faltal_{ag['id']}", use_container_width=True,
                                         type="primary" if status_atual == "falta_nao_cobrada" else "secondary"):
                                aplicar_status(ag, aluno_dados, "falta_nao_cobrada")
                        with b4:
                            if st.button("⚪ Desmarcado", key=f"desm_{ag['id']}", use_container_width=True,
                                         type="primary" if status_atual == "desmarcado" else "secondary"):
                                aplicar_status(ag, aluno_dados, "desmarcado")

    # ------------------------------------------
    # 3. ALUNOS & CRM (EDIÇÃO DE PERFIL)
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
                                try:
                                    supabase.table("alunos").update({"parq_token": novo_token}).eq("id", al["id"]).execute()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao gerar token: {e}")
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

        # --- SEÇÃO DE EDIÇÃO DE PERFIL ---
        if alunos_todos:
            with st.expander("✏️ Editar Perfil do Aluno", expanded=False):
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

                    st.markdown("#### 💰 Plano e Cobrança")
                    tipos_cobranca_opcoes = ["pacote", "por_aula"]
                    col_t1, col_t2, col_t3 = st.columns(3)
                    with col_t1:
                        f_tipo_cobranca = st.selectbox("Tipo de Cobrança", tipos_cobranca_opcoes,
                            index=tipos_cobranca_opcoes.index(aluno_sel.get("tipo_cobranca")) if aluno_sel.get("tipo_cobranca") in tipos_cobranca_opcoes else 0)
                    with col_t2:
                        f_valor_pacote = st.number_input("Valor Pacote (R$)", value=float(aluno_sel.get("valor_pacote") or 0.0), min_value=0.0)
                    with col_t3:
                        f_valor_aula = st.number_input("Valor Avulso (R$)", value=float(aluno_sel.get("valor_aula") or 0.0), min_value=0.0)

                    col_t4, col_t5, col_t6 = st.columns(3)
                    with col_t4:
                        f_total_aulas_pacote = st.number_input("Aulas por Pacote", value=int(aluno_sel.get("total_aulas_pacote") or 10), min_value=0)
                    with col_t5:
                        f_aulas_restantes = st.number_input("Aulas Restantes", value=int(aluno_sel.get("aulas_restantes") or 0), min_value=0)
                    with col_t6:
                        f_vencimento = st.number_input("Dia de Vencimento", value=int(aluno_sel.get("vencimento") or 10), min_value=1, max_value=31)

                    st.markdown("#### 📊 Frequência e PAR-Q")
                    parq_opcoes = ["pendente", "assinado"]
                    col_g1, col_g2, col_g3 = st.columns(3)
                    with col_g1:
                        f_presencas = st.number_input("Presenças", value=int(aluno_sel.get("presencas") or 0), min_value=0)
                    with col_g2:
                        f_faltas = st.number_input("Faltas", value=int(aluno_sel.get("faltas") or 0), min_value=0)
                    with col_g3:
                        f_parq_status = st.selectbox("Status do PAR-Q", parq_opcoes,
                            index=parq_opcoes.index(aluno_sel.get("parq_status")) if aluno_sel.get("parq_status") in parq_opcoes else 0)

                    sit_edicao = situacao_financeira(aluno_sel, transacoes_todas, hoje)
                    ultimo_pag_edicao = sit_edicao["ultimo_pagamento"].strftime("%d/%m/%Y") if sit_edicao["ultimo_pagamento"] else "nunca"
                    st.caption(f"💵 Total pago (histórico real, via aba Financeiro): **R$ {sit_edicao['pago_total']:.2f}** — último pagamento: {ultimo_pag_edicao}. Esse valor não é editável aqui porque agora vem do extrato de pagamentos, não de um campo único.")

                    if st.form_submit_button("💾 Salvar Perfil", type="primary", use_container_width=True):
                        erros = []
                        if not f_nome or not f_nome.strip():
                            erros.append("O nome não pode ficar em branco.")
                        tel_digitos = re.sub(r'\D', '', f_telefone or "")
                        if f_telefone and len(tel_digitos) not in (10, 11):
                            erros.append("O WhatsApp precisa ter DDD + número (10 ou 11 dígitos).")

                        if erros:
                            for erro in erros:
                                st.error(erro)
                        else:
                            with st.spinner("Salvando alterações..."):
                                preparar_cliente()
                                try:
                                    supabase.table("alunos").update({
                                        "nome": f_nome.strip(),
                                        "data_nascimento": f_data_nasc.isoformat(),
                                        "telefone": f_telefone,
                                        "email": f_email,
                                        "cpf": f_cpf,
                                        "status": f_status,
                                        "contato_emergencia_nome": f_emg_nome,
                                        "contato_emergencia_fone": f_emg_fone,
                                        "tipo_cobranca": f_tipo_cobranca,
                                        "valor_pacote": f_valor_pacote,
                                        "valor_aula": f_valor_aula,
                                        "total_aulas_pacote": f_total_aulas_pacote,
                                        "aulas_restantes": f_aulas_restantes,
                                        "vencimento": f_vencimento,
                                        "presencas": f_presencas,
                                        "faltas": f_faltas,
                                        "parq_status": f_parq_status
                                    }).eq("id", aluno_sel["id"]).execute()
                                    st.success("Perfil do aluno atualizado com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error("Não foi possível salvar as alterações. Tente novamente em instantes.")

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
                    erros_novo = []
                    if not nome or not nome.strip():
                        erros_novo.append("O nome não pode ficar em branco.")
                    tel_digitos_novo = re.sub(r'\D', '', telefone or "")
                    if telefone and len(tel_digitos_novo) not in (10, 11):
                        erros_novo.append("O WhatsApp precisa ter DDD + número (10 ou 11 dígitos).")

                    if erros_novo:
                        for erro in erros_novo:
                            st.error(erro)
                    else:
                        with st.spinner("Salvando aluno..."):
                            preparar_cliente()
                            token_inicial = str(uuid.uuid4())[:10]
                            try:
                                supabase.table("alunos").insert({
                                    "user_id": user_id, 
                                    "nome": nome.strip(), 
                                    "data_nascimento": data_nasc.isoformat(),
                                    "telefone": telefone, 
                                    "tipo_cobranca": tipo_cob,
                                    "valor_pacote": valor_pacote, 
                                    "total_aulas_pacote": aulas_pacote, 
                                    "aulas_restantes": aulas_pacote,
                                    "valor_aula": valor_aula, 
                                    "vencimento": dia_venc,
                                    "presencas": 0, 
                                    "faltas": 0, 
                                    "valor_pago": 0.0,
                                    "parq_token": token_inicial, 
                                    "parq_status": "pendente"
                                }).execute()
                                st.success("Aluno salvo com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error("Não foi possível cadastrar o aluno. Tente novamente em instantes.")

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
                    sit = situacao_financeira(al, transacoes_todas, hoje)

                    with st.container(border=True):
                        col_info, col_acao = st.columns([2.5, 1.5])
                        with col_info:
                            st.markdown(f"**{al['nome']}**")
                            ultimo_pag_txt = sit["ultimo_pagamento"].strftime("%d/%m/%Y") if sit["ultimo_pagamento"] else "nunca"
                            st.caption(f"Cobrança: {al.get('tipo_cobranca', 'pacote').upper()} | Total pago: R$ {sit['pago_total']:.2f} | Último pagamento: {ultimo_pag_txt}")
                            if not sit["em_dia"]:
                                st.error(f"Pendente: R$ {sit['saldo']:.2f}")
                            else:
                                st.success("Em dia ✅")
                        
                        with col_acao:
                            if not sit["em_dia"]:
                                msg = f"Fala {al['nome']}! Tudo bem? Passando só para avisar que o seu pacote de aulas venceu. Segue a chave para renovação: {st.session_state.chave_pix}. Valeu!"
                                
                                telefone_salvo = al.get("telefone")
                                telefone_texto = str(telefone_salvo) if telefone_salvo is not None else ""
                                tel = re.sub(r'\D', '', telefone_texto)
                                
                                if tel:
                                    link_whats = f"https://wa.me/55{tel}?text={urllib.parse.quote(msg)}"
                                    st.markdown(f"<a href='{link_whats}' target='_blank'><button style='background-color:#25D366; color:white; border:none; padding:8px; border-radius:5px; width:100%; margin-bottom: 5px;'>📱 Cobrar via WhatsApp</button></a>", unsafe_allow_html=True)
                                else:
                                    st.caption("Sem telefone")

                        with st.expander(f"💵 Registrar pagamento — {al['nome']}"):
                            with st.form(f"form_pagamento_{al['id']}"):
                                valor_default = sit["saldo"] if sit["saldo"] > 0 else float(al.get("valor_pacote") or al.get("valor_aula") or 0.0)
                                f_valor_pag = st.number_input("Valor recebido (R$)", min_value=0.01, value=max(0.01, valor_default), key=f"valor_pag_{al['id']}")
                                f_desc_pag = st.text_input("Descrição", value="Renovação de pacote" if al.get("tipo_cobranca") == "pacote" else "Pagamento avulso", key=f"desc_pag_{al['id']}")

                                if st.form_submit_button("✅ Confirmar Pagamento", type="primary", use_container_width=True):
                                    with st.spinner("Registrando pagamento..."):
                                        preparar_cliente()
                                        try:
                                            supabase.table("transacoes").insert({
                                                "user_id": user_id,
                                                "aluno_id": al["id"],
                                                "valor": f_valor_pag,
                                                "descricao": f_desc_pag,
                                                "data_pagamento": hoje.isoformat()
                                            }).execute()

                                            if al.get("tipo_cobranca") == "pacote":
                                                novas_aulas = al.get("total_aulas_pacote") or 10
                                                supabase.table("alunos").update({
                                                    "aulas_restantes": (al.get("aulas_restantes") or 0) + novas_aulas
                                                }).eq("id", al["id"]).execute()

                                            st.success("Pagamento registrado!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error("Não foi possível registrar o pagamento. Tente novamente em instantes.")

        with tab_caixa:
            st.markdown("### 📈 Fluxo de Caixa e Metas")

            faturado_total = 0.0
            faturado_mes = 0.0
            a_receber = 0.0
            for al in alunos_todos:
                sit = situacao_financeira(al, transacoes_todas, hoje)
                faturado_total += sit["pago_total"]
                a_receber += sit["saldo"]

            for t in transacoes_todas:
                d_pag = parse_data_pagamento(t.get("data_pagamento"))
                if d_pag and d_pag.month == hoje.month and d_pag.year == hoje.year:
                    faturado_mes += float(t.get("valor") or 0.0)

            col_c1, col_c2 = st.columns(2)
            col_c1.metric("Total Arrecadado (histórico)", f"R$ {faturado_total:.2f}")
            col_c2.metric("Total Pendente", f"R$ {a_receber:.2f}")

            st.divider()
            st.markdown("#### 🎯 Meta Mensal de Faturamento")
            meta_input = st.number_input("Defina sua Meta Mensal (R$):", min_value=0.0, value=5000.0, step=500.0)
            
            if meta_input > 0:
                progresso = min(1.0, faturado_mes / meta_input)
                st.progress(progresso)
                st.caption(f"Você atingiu **{progresso * 100:.1f}%** da meta em {hoje.strftime('%m/%Y')} (R$ {faturado_mes:.2f} / R$ {meta_input:.2f}).")
