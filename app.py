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
st.set_page_config(page_title="Assistente Personal Trainer", page_icon="static/icon-192.png", layout="wide", initial_sidebar_state="expanded")

def aplicar_estilo_customizado():
    st.markdown("""
        <style>
        /* Importação da fonte moderna Plus Jakarta Sans */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        /* Fundo quase preto (identidade ProFit Control) em vez do
           azul-acinzentado anterior. */
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #0A0A0A !important;
        }
        [data-testid="stSidebar"] {
            background-color: #0D0D0D !important;
            border-right: 1px solid rgba(245, 130, 31, 0.15) !important;
        }

        /* Cards: fundo escuro sólido com borda fina laranja translúcida,
           em vez do glassmorphism verde/azul anterior. */
        [data-testid="stMetric"], div[data-testid="stVerticalBlock"] > div[style*="border"] {
            background: #0D0D0D !important;
            border: 1px solid rgba(245, 130, 31, 0.35) !important;
            border-radius: 14px !important;
            box-shadow: none !important;
            padding: 1.1rem !important;
            transition: all 0.2s ease !important;
        }

        [data-testid="stMetric"]:hover, div[data-testid="stVerticalBlock"] > div[style*="border"]:hover {
            border-color: rgba(245, 130, 31, 0.6) !important;
        }

        /* Destaque para os Valores das Métricas — laranja, cor de marca */
        [data-testid="stMetricValue"] {
            color: #F5821F !important;
            font-weight: 700 !important;
            font-size: 26px !important;
            letter-spacing: -0.5px !important;
        }
        [data-testid="stMetricLabel"] {
            color: #9CA3AF !important;
        }

        /* Botões: laranja sólido, sem gradiente/glow — mais próximo do
           estilo "pill" enxuto do app de referência. */
        .stButton>button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            background: #F5821F !important;
            color: #0A0A0A !important;
            border: none !important;
            padding: 0.6rem 1.2rem !important;
            box-shadow: none !important;
            transition: all 0.2s ease-in-out !important;
        }
        .stButton>button:hover {
            background: #FF9838 !important;
        }
        /* Botões "secondary" (não-primários) ficam com contorno, não
           preenchidos — pra não competir visualmente com o botão principal
           de cada tela. */
        .stButton>button[kind="secondary"] {
            background: rgba(245, 130, 31, 0.10) !important;
            border: 1px solid rgba(245, 130, 31, 0.4) !important;
            color: #F5821F !important;
        }
        .stButton>button[kind="secondary"]:hover {
            background: rgba(245, 130, 31, 0.20) !important;
        }

        /* Campos de Entrada (Inputs, Selects e Data) */
        .stTextInput>div>div>input, 
        .stSelectbox>div>div>div, 
        .stNumberInput>div>div>input, 
        .stDateInput>div>div>input {
            background: #0D0D0D !important;
            border-radius: 10px !important;
            border: 1px solid rgba(245, 130, 31, 0.25) !important;
            transition: border-color 0.2s ease !important;
        }

        .stTextInput>div>div>input:focus, 
        .stSelectbox>div>div>div:focus {
            border-color: #F5821F !important;
            box-shadow: 0 0 0 2px rgba(245, 130, 31, 0.2) !important;
        }

        /* Estilização das Abas (Tabs) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px !important;
            border-bottom: 1px solid rgba(245, 130, 31, 0.15) !important;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0 !important;
            padding: 10px 20px !important;
            font-weight: 500 !important;
            color: #9CA3AF !important;
        }

        .stTabs [aria-selected="true"] {
            background-color: rgba(245, 130, 31, 0.12) !important;
            color: #F5821F !important;
            font-weight: 600 !important;
        }

        /* Modificações de Divisores */
        hr {
            margin: 2rem 0 !important;
            border-color: rgba(245, 130, 31, 0.15) !important;
        }

        /* ==========================================
           STATUS PILLS — badges de status reutilizáveis
           (Pago/Pendente, Em dia/Atrasado etc.), no mesmo
           estilo de cápsula colorida do app de referência.
           ========================================== */
        .status-pill {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }
        .status-pill-verde { background: rgba(34, 197, 94, 0.15); color: #22C55E; }
        .status-pill-laranja { background: rgba(245, 130, 31, 0.15); color: #F5821F; }
        .status-pill-vermelho { background: rgba(239, 68, 68, 0.15); color: #EF4444; }
        .status-pill-cinza { background: rgba(156, 163, 175, 0.15); color: #9CA3AF; }

        /* Pills de filtro/mês (Jan Fev Mar..., Todos/Presencial/Online) */
        .filtro-pill {
            display: inline-block;
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.05);
            color: #9CA3AF;
            margin-right: 6px;
        }
        .filtro-pill-ativo {
            background: #F5821F;
            color: #0A0A0A;
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
            background: rgba(0, 0, 0, 0.6);
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
            background: #0D0D0D !important;
            border: 1px solid rgba(245, 130, 31, 0.3) !important;
            border-bottom: none !important;
            border-radius: 20px 20px 0 0 !important;
            box-shadow: 0 -10px 34px rgba(0, 0, 0, 0.6) !important;
            padding: 18px 18px calc(18px + env(safe-area-inset-bottom)) 18px !important;
            animation: agendaSlideUp 0.25s ease !important;
            max-height: 80vh !important;
            overflow-y: auto !important;
        }

        /* Botão de excluir agendamento — vermelho, pra ficar claramente
           diferente das ações normais de marcar status. */
        .st-key-pop_excluir button,
        .st-key-confirmar_excluir_sim button {
            background: rgba(239, 68, 68, 0.12) !important;
            border: 1px solid rgba(239, 68, 68, 0.4) !important;
            color: #EF4444 !important;
        }
        .st-key-pop_excluir button:hover,
        .st-key-confirmar_excluir_sim button:hover {
            background: rgba(239, 68, 68, 0.22) !important;
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

def calcular_efeito(status, tipo_cobranca, cortesia=False):
    # Retorna (delta_presencas, delta_faltas, delta_aulas_restantes)
    # que um status causa no saldo do aluno.
    if cortesia:
        return (0, 0, 0)  # cortesia nunca mexe no saldo, pacote ou por aula
    if status == "presenca":
        return (1, 0, -1 if tipo_cobranca == "pacote" else 0)
    elif status == "falta_cobrada":
        return (0, 1, -1 if tipo_cobranca == "pacote" else 0)
    return (0, 0, 0)  # falta_nao_cobrada, desmarcado, agendado

def aplicar_status(ag, aluno, novo_status, observacao=None):
    # Compartilhada pelo popup de clique no calendário e pela aba
    # "Gerenciar Presenças/Faltas" — um só lugar calcula o efeito no
    # saldo do aluno, então os dois pontos de entrada nunca divergem.
    status_antigo = ag.get("status", "agendado")
    mudou_status = status_antigo != novo_status
    mudou_obs = observacao is not None and observacao != (ag.get("observacao") or "")

    if not mudou_status and not mudou_obs:
        return

    upd_agendamento = {}
    upd_aluno = {}
    cortesia_ag = ag.get("cortesia", False)

    if mudou_status:
        upd_agendamento["status"] = novo_status
        old_p, old_f, old_a = calcular_efeito(status_antigo, aluno.get("tipo_cobranca"), cortesia_ag)
        new_p, new_f, new_a = calcular_efeito(novo_status, aluno.get("tipo_cobranca"), cortesia_ag)
        upd_aluno = {
            "presencas": max(0, (aluno.get("presencas") or 0) - old_p + new_p),
            "faltas": max(0, (aluno.get("faltas") or 0) - old_f + new_f),
            "aulas_restantes": max(0, (aluno.get("aulas_restantes") or 0) - old_a + new_a),
        }

    if mudou_obs:
        upd_agendamento["observacao"] = observacao

    preparar_cliente()
    try:
        if upd_agendamento:
            supabase.table("agendamentos").update(upd_agendamento).eq("id", ag["id"]).execute()
        if upd_aluno:
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
    old_p, old_f, old_a = calcular_efeito(status_atual, aluno.get("tipo_cobranca"), ag.get("cortesia", False))

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

HORIZONTE_RECORRENCIA_DIAS = 56  # 8 semanas — mantido sempre à frente automaticamente
DIAS_SEMANA_PT = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

def fmt_moeda(valor):
    """R$ 1234.5 -> 'R$ 1.234,50' (separador de milhar e decimal no
    padrão brasileiro, em vez do formato americano padrão do Python)."""
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

def desfazer_ultimo_pagamento(aluno, transacoes_todas):
    """Remove a transação mais recente do aluno (ordenada por created_at,
    não por data_pagamento — que o trainer pode ter editado). Se o aluno
    é de pacote, desfaz também a renovação de aulas que aquele pagamento
    gerou. Assume que o pagamento desfeito foi o mais recente de fato —
    então isso serve pra corrigir um erro logo depois que ele aconteceu,
    não pra editar um histórico antigo."""
    transacoes_aluno = sorted(
        [t for t in transacoes_todas if t.get("aluno_id") == aluno["id"]],
        key=lambda t: t.get("created_at") or t.get("data_pagamento") or "",
        reverse=True
    )
    if not transacoes_aluno:
        return False
    ultima = transacoes_aluno[0]
    preparar_cliente()
    supabase.table("transacoes").delete().eq("id", ultima["id"]).execute()
    if aluno.get("tipo_cobranca") == "pacote":
        novas_aulas = aluno.get("total_aulas_pacote") or 0
        supabase.table("alunos").update({
            "aulas_restantes": max(0, (aluno.get("aulas_restantes") or 0) - novas_aulas)
        }).eq("id", aluno["id"]).execute()
    return True

def proxima_ocorrencia(dia_semana, hora, a_partir_de):
    dias_ate = (dia_semana - a_partir_de.weekday()) % 7
    data_alvo = a_partir_de + timedelta(days=dias_ate)
    return datetime.combine(data_alvo, hora)

def criar_horario_fixo(user_id, aluno_id, primeira_data_hora, local, cortesia=False):
    """Registra um novo horário fixo (linha em series_recorrentes) e já
    gera as ocorrências semanais até o horizonte de 8 semanas. Se
    cortesia=True, toda ocorrência gerada (inclusive as futuras, geradas
    automaticamente por manter_series_recorrentes_atualizadas) nasce
    marcada como cortesia — não afeta o saldo do aluno."""
    preparar_cliente()
    dia_semana = primeira_data_hora.weekday()
    hora = primeira_data_hora.time()
    res = supabase.table("series_recorrentes").insert({
        "user_id": user_id, "aluno_id": aluno_id,
        "dia_semana": dia_semana, "hora": hora.strftime("%H:%M:%S"),
        "local": local, "ativa": True, "cortesia": cortesia
    }).execute()
    serie_id = res.data[0]["id"]

    limite = hoje + timedelta(days=HORIZONTE_RECORRENCIA_DIAS)
    novas_linhas = []
    cursor = primeira_data_hora
    while cursor.date() <= limite:
        novas_linhas.append({
            "user_id": user_id, "aluno_id": aluno_id, "data_hora": cursor.isoformat(),
            "local": local, "status": "agendado", "recorrencia_id": serie_id, "cortesia": cortesia
        })
        cursor += timedelta(days=7)
    if novas_linhas:
        supabase.table("agendamentos").insert(novas_linhas).execute()
    return serie_id

def parar_horario_fixo(serie_id):
    """Marca a série como inativa (para de gerar ocorrências novas) e
    remove só as ocorrências futuras ainda não realizadas — o histórico
    de aulas já dadas (presença/falta) permanece intacto."""
    preparar_cliente()
    supabase.table("series_recorrentes").update({"ativa": False}).eq("id", serie_id).execute()
    supabase.table("agendamentos").delete().eq("recorrencia_id", serie_id).eq("status", "agendado").gte("data_hora", datetime.now().isoformat()).execute()

def manter_series_recorrentes_atualizadas(user_id):
    """Roda a cada carregamento da Agenda: para cada horário fixo ATIVO
    (tabela series_recorrentes), garante que existam ocorrências geradas
    até 8 semanas à frente, completando o que faltar. O trainer nunca
    precisa 'renovar' manualmente."""
    preparar_cliente()
    try:
        res = supabase.table("series_recorrentes").select("*").eq("user_id", user_id).eq("ativa", True).execute()
        series_ativas = res.data if res.data else []
    except Exception:
        return False

    if not series_ativas:
        return False

    limite = hoje + timedelta(days=HORIZONTE_RECORRENCIA_DIAS)
    algo_mudou = False

    for serie in series_ativas:
        try:
            res_ult = supabase.table("agendamentos").select("data_hora").eq("recorrencia_id", serie["id"]).order("data_hora", desc=True).limit(1).execute()
            ultima = parse_data_hora(res_ult.data[0]["data_hora"]) if res_ult.data else None
        except Exception:
            ultima = None

        hora_serie = datetime.strptime(str(serie["hora"])[:8], "%H:%M:%S").time()
        proxima = (ultima + timedelta(days=7)) if ultima else proxima_ocorrencia(serie["dia_semana"], hora_serie, hoje)

        if proxima.date() > limite:
            continue

        novas_linhas = []
        cursor = proxima
        while cursor.date() <= limite:
            novas_linhas.append({
                "user_id": user_id, "aluno_id": serie["aluno_id"], "data_hora": cursor.isoformat(),
                "local": serie.get("local") or "", "status": "agendado", "recorrencia_id": serie["id"],
                "cortesia": serie.get("cortesia", False)
            })
            cursor += timedelta(days=7)
        if novas_linhas:
            supabase.table("agendamentos").insert(novas_linhas).execute()
            algo_mudou = True

    return algo_mudou

def agrupar_aulas_por_mes(lista_aulas):
    """Agrupa uma lista de agendamentos por (ano, mês), contando quantos
    caem em cada um — usado pra mostrar 'Ago: 2 · Set: 4 · Out: 1' em vez
    de só um número total que mistura vários meses (comum quando uma
    série fixa já gerou aulas bem à frente)."""
    contagem = {}
    for ag in lista_aulas:
        dt = parse_data_hora(ag["data_hora"])
        chave = (dt.year, dt.month)
        contagem[chave] = contagem.get(chave, 0) + 1
    return dict(sorted(contagem.items()))

def calcular_relatorio_mensal(alunos_todos, agendamentos_todos, ano, mes):
    """Aulas realizadas (status=presenca) por aluno no mês, e o valor
    correspondente. Pacote usa o valor proporcional por aula (valor do
    pacote dividido pelas aulas que ele contém); por_aula usa o valor
    avulso direto."""
    linhas = []
    for al in alunos_todos:
        aulas_mes = [
            ag for ag in agendamentos_todos
            if ag.get("aluno_id") == al["id"]
            and ag.get("status") == "presenca"
            and parse_data_hora(ag["data_hora"]).year == ano
            and parse_data_hora(ag["data_hora"]).month == mes
        ]
        qtd = len(aulas_mes)
        if qtd == 0:
            continue

        if al.get("tipo_cobranca") == "pacote":
            total_pacote = al.get("total_aulas_pacote") or 0
            valor_unit = (float(al.get("valor_pacote") or 0.0) / total_pacote) if total_pacote > 0 else 0.0
        else:
            valor_unit = float(al.get("valor_aula") or 0.0)

        linhas.append({
            "Aluno": al["nome"],
            "Aulas no mês": qtd,
            "Valor total (R$)": round(qtd * valor_unit, 2)
        })
    return linhas

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

    def carregar_series_recorrentes(user_id):
        preparar_cliente()
        try:
            res = supabase.table("series_recorrentes").select("*").eq("user_id", user_id).eq("ativa", True).execute()
            return res.data if res.data else []
        except Exception:
            return []

    series_recorrentes_todas = carregar_series_recorrentes(user_id)

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
        st.title("📊 Dashboard")

        if "dash_mes_sel" not in st.session_state:
            st.session_state.dash_mes_sel = hoje.month
        if "dash_ano_sel" not in st.session_state:
            st.session_state.dash_ano_sel = hoje.year

        col_mes_sel, col_ano_sel = st.columns([3, 1])
        with col_mes_sel:
            mes_sel = st.selectbox("Mês", list(range(1, 13)), index=st.session_state.dash_mes_sel - 1,
                                    format_func=lambda m: MESES_PT[m-1], key="dash_mes_selectbox", label_visibility="collapsed")
        with col_ano_sel:
            ano_sel = st.number_input("Ano", min_value=2020, max_value=2100, value=st.session_state.dash_ano_sel,
                                       step=1, key="dash_ano_input", label_visibility="collapsed")
        st.session_state.dash_mes_sel = mes_sel
        st.session_state.dash_ano_sel = ano_sel

        def faturado_do_mes(m, a):
            total = 0.0
            for t in transacoes_todas:
                d_pag = parse_data_pagamento(t.get("data_pagamento"))
                if d_pag and d_pag.month == m and d_pag.year == a:
                    total += float(t.get("valor") or 0.0)
            return total

        mes_ant = mes_sel - 1 if mes_sel > 1 else 12
        ano_ant = ano_sel if mes_sel > 1 else ano_sel - 1
        faturado_mes_sel = faturado_do_mes(mes_sel, ano_sel)
        faturado_mes_ant = faturado_do_mes(mes_ant, ano_ant)

        if faturado_mes_ant > 0:
            variacao_pct = (faturado_mes_sel - faturado_mes_ant) / faturado_mes_ant * 100
        else:
            variacao_pct = 100.0 if faturado_mes_sel > 0 else 0.0

        seta = "▲" if variacao_pct >= 0 else "▼"
        cor_var = "#22C55E" if variacao_pct >= 0 else "#EF4444"

        with st.container(border=True):
            st.caption(f"Faturamento — {MESES_PT[mes_sel-1]}/{ano_sel}")
            st.markdown(f"<div style='font-size:34px; font-weight:800; color:#F5821F; line-height:1.2;'>{fmt_moeda(faturado_mes_sel)}</div>", unsafe_allow_html=True)
            st.markdown(f"<span style='color:{cor_var}; font-size:13px; font-weight:700;'>{seta} {abs(variacao_pct):.0f}%</span> <span style='color:#9CA3AF; font-size:13px;'>vs mês anterior</span>", unsafe_allow_html=True)

        total_pendente = 0.0
        alunos_em_dia = 0
        alunos_pacote = 0
        alunos_por_aula = 0
        for al in alunos_todos:
            sit = situacao_financeira(al, transacoes_todas, hoje)
            total_pendente += sit["saldo"]
            if sit["em_dia"]:
                alunos_em_dia += 1
            if al.get("tipo_cobranca") == "pacote":
                alunos_pacote += 1
            else:
                alunos_por_aula += 1

        cg1, cg2 = st.columns(2)
        with cg1:
            with st.container(border=True):
                st.caption("Pendente")
                st.markdown(f"<span style='color:#EF4444; font-size:22px; font-weight:700;'>{fmt_moeda(total_pendente)}</span>", unsafe_allow_html=True)
        with cg2:
            with st.container(border=True):
                st.caption("Alunos em dia")
                st.markdown(f"<span style='color:#22C55E; font-size:22px; font-weight:700;'>{alunos_em_dia}</span>", unsafe_allow_html=True)

        cg3, cg4 = st.columns(2)
        with cg3:
            with st.container(border=True):
                st.caption("Pacote")
                st.markdown(f"<span style='font-size:22px; font-weight:700;'>{alunos_pacote}</span> <span style='color:#9CA3AF; font-size:12px;'>alunos</span>", unsafe_allow_html=True)
        with cg4:
            with st.container(border=True):
                st.caption("Por aula")
                st.markdown(f"<span style='font-size:22px; font-weight:700;'>{alunos_por_aula}</span> <span style='color:#9CA3AF; font-size:12px;'>alunos</span>", unsafe_allow_html=True)

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

        # Completa automaticamente qualquer série de aula fixa que esteja
        # ficando curta (menos de 8 semanas geradas à frente), sem precisar
        # que o trainer faça nada — só de abrir a Agenda já mantém em dia.
        try:
            if manter_series_recorrentes_atualizadas(user_id):
                res_ag = supabase.table("agendamentos").select("*").eq("user_id", user_id).gte("data_hora", inicio_mes).execute()
                agendamentos = res_ag.data if res_ag.data else []
        except Exception:
            pass  # manutenção de recorrência não deve travar a Agenda se falhar

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

            tag_cortesia = " 🎁" if ag.get("cortesia") else ""
            eventos_calendario.append({
                "id": str(ag["id"]),
                "title": f"{nome}{tag_cortesia} ({status.replace('_', ' ').title()})",
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
            "locale": "pt-br",
            "editable": True,          # permite arrastar o evento pra outro horário
            "eventStartEditable": True,
            "eventDurationEditable": False  # duração fixa de 1h, só a hora de início muda
        }

        calendar_state = calendar(events=eventos_calendario, options=opcoes_calendario, key="agenda_calendario", callbacks=["eventClick", "dateClick", "eventChange"], custom_css="""
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
        elif calendar_state and calendar_state.get("callback") == "eventChange":
            evento_mudado = calendar_state.get("eventChange", {}).get("event", {})
            assinatura_clique = ("eventChange", evento_mudado.get("id"), evento_mudado.get("start"))

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

            elif assinatura_clique[0] == "eventChange":
                # Arrastou o evento pra outro horário — reagendar do jeito
                # rápido, "arrastar e soltar" (mesma ideia do Google Agenda).
                ag_id_arrastado, novo_inicio_str = assinatura_clique[1], assinatura_clique[2]
                ag_arrastado = next((a for a in agendamentos if str(a["id"]) == str(ag_id_arrastado)), None)
                if ag_arrastado and novo_inicio_str:
                    try:
                        novo_inicio = parse_data_hora(novo_inicio_str)
                        preparar_cliente()
                        supabase.table("agendamentos").update({"data_hora": novo_inicio.isoformat()}).eq("id", ag_arrastado["id"]).execute()

                        conflito_drag = any(
                            horarios_conflitam(novo_inicio, parse_data_hora(a["data_hora"]))
                            and a.get("status") == "agendado" and str(a["id"]) != str(ag_arrastado["id"])
                            for a in agendamentos
                        )
                        st.toast("⚠️ Reagendado, mas já existe outro aluno nesse horário." if conflito_drag else "✅ Aula reagendada.", icon="⚠️" if conflito_drag else "✅")
                        st.rerun()
                    except Exception:
                        st.toast("⚠️ Não foi possível reagendar. Tente novamente.", icon="⚠️")

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
                        st.caption(f"Status atual: {emoji_pop} {label_pop}" + ("  ·  🎁 Cortesia" if ag_clicado.get("cortesia") else ""))
                    with col_pop_fechar:
                        if st.button("✖", key="fechar_popup_agenda", help="Fechar"):
                            st.session_state.agenda_popup_ag_id = None
                            st.rerun()

                    obs_pop = st.text_area("📝 O que foi treinado / observação", value=ag_clicado.get("observacao") or "",
                                            key=f"obs_{ag_clicado['id']}", height=68, placeholder="Ex: treino de pernas, aluno relatou dor no joelho...")

                    pb1, pb2 = st.columns(2)
                    with pb1:
                        if st.button("✅ Presença", key="pop_presenca", use_container_width=True,
                                     type="primary" if status_atual_pop == "presenca" else "secondary"):
                            aplicar_status(ag_clicado, aluno_clicado, "presenca", observacao=obs_pop)
                    with pb2:
                        if st.button("❌ Falta cobrada", key="pop_faltac", use_container_width=True,
                                     type="primary" if status_atual_pop == "falta_cobrada" else "secondary"):
                            aplicar_status(ag_clicado, aluno_clicado, "falta_cobrada", observacao=obs_pop)

                    pb3, pb4 = st.columns(2)
                    with pb3:
                        if st.button("⚠️ Falta não cobrada", key="pop_faltal", use_container_width=True,
                                     type="primary" if status_atual_pop == "falta_nao_cobrada" else "secondary"):
                            aplicar_status(ag_clicado, aluno_clicado, "falta_nao_cobrada", observacao=obs_pop)
                    with pb4:
                        if st.button("⚪ Desmarcado", key="pop_desm", use_container_width=True,
                                     type="primary" if status_atual_pop == "desmarcado" else "secondary"):
                            aplicar_status(ag_clicado, aluno_clicado, "desmarcado", observacao=obs_pop)

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

                    col_fixa_sheet, col_cortesia_sheet = st.columns(2)
                    with col_fixa_sheet:
                        fixa_sheet = st.checkbox("🔁 Aula fixa", key=f"sheet_fixa_{sufixo_key}", help="Repete toda semana neste mesmo dia e horário")
                    with col_cortesia_sheet:
                        cortesia_sheet = st.checkbox("🎁 Cortesia", key=f"sheet_cortesia_{sufixo_key}", help="Não desconta do pacote nem soma no valor devido — funciona também em aula fixa")

                    if st.button("Confirmar Agendamento", key=f"confirmar_sheet_{sufixo_key}", type="primary", use_container_width=True):
                        conflito = any(
                            horarios_conflitam(dt_inicio_preview, parse_data_hora(a["data_hora"]))
                            and a.get("status") == "agendado"
                            for a in agendamentos
                        )

                        with st.spinner("Agendando..."):
                            preparar_cliente()
                            try:
                                if fixa_sheet:
                                    criar_horario_fixo(user_id, mapa_nomes_sheet[aluno_novo_nome], dt_inicio_preview, local_novo_sheet, cortesia=cortesia_sheet)
                                else:
                                    supabase.table("agendamentos").insert({
                                        "user_id": user_id,
                                        "aluno_id": mapa_nomes_sheet[aluno_novo_nome],
                                        "data_hora": dt_inicio_preview.isoformat(),
                                        "local": local_novo_sheet,
                                        "status": "agendado",
                                        "cortesia": cortesia_sheet
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

                col_fixa_tab, col_cortesia_tab = st.columns(2)
                with col_fixa_tab:
                    fixa_tab = st.checkbox("🔁 Aula fixa", key="tab_agendar_fixa", help="Repete toda semana neste mesmo dia e horário")
                with col_cortesia_tab:
                    cortesia_tab = st.checkbox("🎁 Cortesia", key="tab_agendar_cortesia", help="Não desconta do pacote nem soma no valor devido — funciona também em aula fixa")

                if st.button("Agendar Horário", key="tab_agendar_confirmar", type="primary"):
                    conflito_ag = any(
                        horarios_conflitam(dt_final_preview, parse_data_hora(a["data_hora"]))
                        and a.get("status") == "agendado"
                        for a in agendamentos
                    )

                    with st.spinner("Agendando..."):
                        preparar_cliente()
                        try:
                            if fixa_tab:
                                criar_horario_fixo(user_id, mapa_nomes[al_nome], dt_final_preview, local_ag, cortesia=cortesia_tab)
                            else:
                                supabase.table("agendamentos").insert({
                                    "user_id": user_id, "aluno_id": mapa_nomes[al_nome],
                                    "data_hora": dt_final_preview.isoformat(), "local": local_ag, "status": "agendado",
                                    "cortesia": cortesia_tab
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
                            tag_cortesia_card = " 🎁" if ag.get("cortesia") else ""
                            st.markdown(f"**{hr_str} — {aluno_dados['nome']}{tag_cortesia_card}**")
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

                        with st.expander("📝 Observação" + (" (preenchida)" if ag.get("observacao") else "")):
                            obs_card = st.text_area("O que foi treinado / observação", value=ag.get("observacao") or "",
                                                     key=f"obs_card_{ag['id']}", height=68, label_visibility="collapsed",
                                                     placeholder="Ex: treino de pernas, aluno relatou dor no joelho...")

                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("✅ Presença", key=f"presenca_{ag['id']}", use_container_width=True,
                                         type="primary" if status_atual == "presenca" else "secondary"):
                                aplicar_status(ag, aluno_dados, "presenca", observacao=obs_card)
                        with b2:
                            if st.button("❌ Falta cobrada", key=f"faltac_{ag['id']}", use_container_width=True,
                                         type="primary" if status_atual == "falta_cobrada" else "secondary"):
                                aplicar_status(ag, aluno_dados, "falta_cobrada", observacao=obs_card)

                        b3, b4 = st.columns(2)
                        with b3:
                            if st.button("⚠️ Falta não cobrada", key=f"faltal_{ag['id']}", use_container_width=True,
                                         type="primary" if status_atual == "falta_nao_cobrada" else "secondary"):
                                aplicar_status(ag, aluno_dados, "falta_nao_cobrada", observacao=obs_card)
                        with b4:
                            if st.button("⚪ Desmarcado", key=f"desm_{ag['id']}", use_container_width=True,
                                         type="primary" if status_atual == "desmarcado" else "secondary"):
                                aplicar_status(ag, aluno_dados, "desmarcado", observacao=obs_card)

    # ------------------------------------------
    # 3. ALUNOS & CRM (LISTA + PERFIL DETALHADO)
    # ------------------------------------------
    elif menu == "👤 Alunos & CRM":
        if "aluno_detalhe_id" not in st.session_state:
            st.session_state.aluno_detalhe_id = None
        if "base_url_input" not in st.session_state:
            st.session_state.base_url_input = "https://meustudio.streamlit.app"

        aluno_sel = None
        if st.session_state.aluno_detalhe_id:
            aluno_sel = next((a for a in alunos_todos if a["id"] == st.session_state.aluno_detalhe_id), None)
            if not aluno_sel:
                st.session_state.aluno_detalhe_id = None  # aluno não existe mais (ex: foi excluído)

        # ============================================================
        # VISÃO DE DETALHE — abre ao tocar no nome, na lista abaixo
        # ============================================================
        if aluno_sel:
            if st.button("← Voltar para a lista"):
                st.session_state.aluno_detalhe_id = None
                st.rerun()

            st.title(f"👤 {aluno_sel['nome']}")

            sit_resumo = situacao_financeira(aluno_sel, transacoes_todas, hoje)
            horarios_fixos_aluno = [s for s in series_recorrentes_todas if s.get("aluno_id") == aluno_sel["id"]]

            preparar_cliente()
            try:
                res_ag_aluno = supabase.table("agendamentos").select("*").eq("aluno_id", aluno_sel["id"]).order("data_hora", desc=True).execute()
                agendamentos_aluno = res_ag_aluno.data if res_ag_aluno.data else []
            except Exception:
                agendamentos_aluno = []

            agora = datetime.now()
            aulas_futuras_aluno = [
                ag for ag in agendamentos_aluno
                if ag.get("status") == "agendado" and parse_data_hora(ag["data_hora"]) >= agora
            ]
            aulas_futuras_aluno.sort(key=lambda ag: ag["data_hora"])

            # "Aulas agendadas" mostra só o mês atual — não mistura meses
            # futuros que uma série fixa já tenha gerado.
            aulas_agendadas_mes_atual = [
                ag for ag in aulas_futuras_aluno
                if parse_data_hora(ag["data_hora"]).month == hoje.month
                and parse_data_hora(ag["data_hora"]).year == hoje.year
            ]
            aulas_agendadas_mes_cobraveis = [ag for ag in aulas_agendadas_mes_atual if not ag.get("cortesia")]

            if aluno_sel.get("tipo_cobranca") == "pacote":
                valor_a_pagar_projetado = float(aluno_sel.get("valor_pacote") or 0.0) if aulas_agendadas_mes_cobraveis else 0.0
            else:
                valor_a_pagar_projetado = len(aulas_agendadas_mes_cobraveis) * float(aluno_sel.get("valor_aula") or 0.0)

            with st.container(border=True):
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("Status", "Em dia ✅" if sit_resumo["em_dia"] else "Pendente 🚨")
                rc2.metric("PAR-Q", "Assinado ✅" if aluno_sel.get("parq_status") == "assinado" else "Pendente ⚠️")
                rc3.metric("Presenças", aluno_sel.get("presencas") or 0)
                rc4, rc5 = st.columns(2)
                rc4.metric(f"Agendadas em {MESES_PT[hoje.month-1]}", len(aulas_agendadas_mes_atual))
                rc5.metric("Horários fixos", len(horarios_fixos_aluno))

                st.markdown(f"💰 **Valor a pagar (baseado nas aulas agendadas este mês):** {fmt_moeda(valor_a_pagar_projetado)}")
                if len(aulas_agendadas_mes_cobraveis) < len(aulas_agendadas_mes_atual):
                    st.caption(f"🎁 {len(aulas_agendadas_mes_atual) - len(aulas_agendadas_mes_cobraveis)} aula(s) cortesia não entram nesse valor.")

            tab_dados, tab_parq, tab_horarios, tab_relatorio = st.tabs(["✏️ Dados e Plano", "📜 PAR-Q", "🗓️ Horários Fixos", "📄 Relatório"])

            # --- Aba PAR-Q ---
            with tab_parq:
                st_parq = aluno_sel.get("parq_status", "pendente")
                if st_parq == "assinado":
                    dt_a = (aluno_sel.get("parq_data") or "")[:10]
                    st.success(f"✅ PAR-Q assinado em {dt_a}")
                else:
                    st.warning("⚠️ PAR-Q pendente")

                token = aluno_sel.get("parq_token")
                if not token:
                    if st.button("🔑 Gerar Link do PAR-Q"):
                        novo_token = str(uuid.uuid4())[:10]
                        preparar_cliente()
                        try:
                            supabase.table("alunos").update({"parq_token": novo_token}).eq("id", aluno_sel["id"]).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao gerar token: {e}")
                else:
                    st.text_input("🔗 URL Base do seu App Streamlit:", key="base_url_input")
                    link_parq = f"{st.session_state.base_url_input}/?token={token}"
                    msg_parq = f"Olá {aluno_sel['nome']}! Para iniciarmos nossos treinos com toda a segurança, por favor preencha e assine seu PAR-Q online no link a seguir: {link_parq}"

                    tel_num = re.sub(r'\D', '', str(aluno_sel.get("telefone", "")))
                    if tel_num:
                        link_wsp = f"https://wa.me/55{tel_num}?text={urllib.parse.quote(msg_parq)}"
                        st.markdown(f"<a href='{link_wsp}' target='_blank'><button style='background-color:#25D366; color:white; border:none; padding:8px; border-radius:5px; width:100%;'>📱 Enviar PAR-Q</button></a>", unsafe_allow_html=True)
                    else:
                        st.caption("Cadastre o telefone pra poder enviar pelo WhatsApp")

                if st_parq == "assinado":
                    with st.expander("👁️ Ver Respostas"):
                        resp = aluno_sel.get("parq_respostas") or {}
                        for k, v in resp.items():
                            cor = "🔴" if v == "Sim" else "🟢"
                            st.write(f"{cor} {k.upper()}: **{v}**")

            # --- Aba Dados e Plano ---
            with tab_dados:
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

            # --- Aba Horários Fixos ---
            with tab_horarios:
                if not horarios_fixos_aluno:
                    st.caption("Nenhum horário fixo cadastrado.")
                else:
                    for serie in horarios_fixos_aluno:
                        hora_serie_fmt = str(serie["hora"])[:5]
                        tag_cortesia_hf = " 🎁 Cortesia" if serie.get("cortesia") else ""
                        col_hf1, col_hf2 = st.columns([4, 1])
                        with col_hf1:
                            st.write(f"🔁 {DIAS_SEMANA_PT[serie['dia_semana']]} às {hora_serie_fmt}" + (f" — {serie['local']}" if serie.get("local") else "") + tag_cortesia_hf)
                        with col_hf2:
                            if st.button("Parar", key=f"parar_fixo_{serie['id']}", use_container_width=True):
                                with st.spinner("Parando horário fixo..."):
                                    try:
                                        parar_horario_fixo(serie["id"])
                                        st.success("Horário fixo interrompido. As aulas já dadas continuam no histórico.")
                                        st.rerun()
                                    except Exception:
                                        st.error("Não foi possível parar o horário fixo. Tente novamente.")

                with st.expander("➕ Adicionar horário fixo"):
                    dia_novo_fixo = st.selectbox("Dia da semana", list(range(7)), format_func=lambda d: DIAS_SEMANA_PT[d], key=f"dia_fixo_{aluno_sel['id']}")
                    hora_novo_fixo = st.time_input("Horário", value=datetime.strptime("08:00", "%H:%M").time(), key=f"hora_fixo_{aluno_sel['id']}")
                    local_novo_fixo = st.text_input("📍 Local", key=f"local_fixo_{aluno_sel['id']}")
                    cortesia_novo_fixo = st.checkbox("🎁 Cortesia (nunca desconta do pacote nem soma no valor devido)", key=f"cortesia_fixo_{aluno_sel['id']}")

                    if st.button("Adicionar Horário Fixo", key=f"add_fixo_{aluno_sel['id']}", type="primary"):
                        with st.spinner("Criando horário fixo e gerando as próximas aulas..."):
                            try:
                                primeira_ocorrencia = proxima_ocorrencia(dia_novo_fixo, hora_novo_fixo, hoje)
                                criar_horario_fixo(user_id, aluno_sel["id"], primeira_ocorrencia, local_novo_fixo, cortesia=cortesia_novo_fixo)
                                st.success(f"Horário fixo criado! Próxima aula: {primeira_ocorrencia.strftime('%d/%m/%Y às %H:%M')}.")
                                st.rerun()
                            except Exception as e:
                                st.error("Não foi possível criar o horário fixo. Tente novamente.")

            # --- Aba Relatório ---
            with tab_relatorio:
                total_presencas_rel = aluno_sel.get("presencas") or 0
                total_faltas_rel = aluno_sel.get("faltas") or 0

                rr1, rr2, rr3 = st.columns(3)
                rr1.metric("Aulas realizadas", total_presencas_rel)
                rr2.metric("Faltas", total_faltas_rel)
                rr3.metric(f"Agendadas em {MESES_PT[hoje.month-1]}", len(aulas_agendadas_mes_atual))

                st.markdown(f"💰 **Valor a pagar (baseado nas aulas agendadas este mês):** {fmt_moeda(valor_a_pagar_projetado)}")
                if len(aulas_agendadas_mes_cobraveis) < len(aulas_agendadas_mes_atual):
                    st.caption(f"🎁 {len(aulas_agendadas_mes_atual) - len(aulas_agendadas_mes_cobraveis)} aula(s) cortesia não entram nesse valor.")

                proxima_aula_aluno = aulas_futuras_aluno[0] if aulas_futuras_aluno else None
                if proxima_aula_aluno:
                    dt_prox_aluno = parse_data_hora(proxima_aula_aluno["data_hora"])
                    st.caption(f"⏰ Próxima aula: {dt_prox_aluno.strftime('%d/%m/%Y às %H:%M')}")

                st.markdown("#### Histórico de aulas")
                if not agendamentos_aluno:
                    st.caption("Nenhuma aula registrada ainda.")
                else:
                    linhas_historico = []
                    for ag in agendamentos_aluno:
                        emoji_h, label_h, _ = ROTULOS_STATUS.get(ag.get("status", "agendado"), ("⏳", "Agendado", ""))
                        linhas_historico.append({
                            "Data": parse_data_hora(ag["data_hora"]).strftime("%d/%m/%Y %H:%M"),
                            "Status": f"{emoji_h} {label_h}",
                            "Observação": ag.get("observacao") or ""
                        })
                    st.dataframe(linhas_historico, use_container_width=True, hide_index=True, height=280)

                st.divider()
                st.markdown("#### 📱 Enviar relatório para o aluno")

                msg_relatorio = (
                    f"Olá {aluno_sel['nome']}! Aqui está um resumo do seu histórico de treinos até {hoje.strftime('%d/%m/%Y')}:\n\n"
                    f"✅ Aulas realizadas: {total_presencas_rel}\n"
                    f"❌ Faltas: {total_faltas_rel}\n"
                    f"📅 Aulas agendadas em {MESES_PT[hoje.month-1]}: {len(aulas_agendadas_mes_atual)}\n"
                    f"💰 Valor a pagar este mês: {fmt_moeda(valor_a_pagar_projetado)}\n"
                )
                if proxima_aula_aluno:
                    dt_prox_msg = parse_data_hora(proxima_aula_aluno["data_hora"])
                    msg_relatorio += f"\n⏰ Próxima aula: {dt_prox_msg.strftime('%d/%m/%Y às %H:%M')}\n"
                msg_relatorio += "\nContinue assim! 💪"

                with st.expander("Ver mensagem antes de enviar"):
                    st.text(msg_relatorio)

                tel_relatorio = re.sub(r'\D', '', str(aluno_sel.get("telefone", "")))
                if tel_relatorio:
                    link_relatorio = f"https://wa.me/55{tel_relatorio}?text={urllib.parse.quote(msg_relatorio)}"
                    st.markdown(
                        f"<a href='{link_relatorio}' target='_blank'>"
                        f"<button style='background-color:#25D366; color:white; border:none; padding:10px; "
                        f"border-radius:10px; width:100%; min-height:44px; font-weight:600;'>📱 Enviar Relatório via WhatsApp</button></a>",
                        unsafe_allow_html=True
                    )
                else:
                    st.caption("Cadastre o telefone do aluno pra poder enviar pelo WhatsApp.")

        # ============================================================
        # VISÃO DE LISTA — toca no nome do aluno pra abrir o perfil
        # ============================================================
        else:
            st.title("👤 Gestão de Alunos")

            busca_aluno = st.text_input("🔍 Buscar aluno pelo nome")
            alunos_lista = sorted(alunos_todos, key=lambda a: (a.get("nome") or "").lower())
            if busca_aluno:
                alunos_lista = [a for a in alunos_lista if busca_aluno.lower() in (a.get("nome") or "").lower()]

            if not alunos_lista:
                st.info("Nenhum aluno encontrado." if busca_aluno else "Cadastre seu primeiro aluno logo abaixo.")
            else:
                for al in alunos_lista:
                    sit_lista = situacao_financeira(al, transacoes_todas, hoje)
                    parq_ok = al.get("parq_status") == "assinado"
                    tag_cobranca = "Pacote" if al.get("tipo_cobranca") == "pacote" else "Por aula"
                    valor_exibido = sit_lista["saldo"] if not sit_lista["em_dia"] else sit_lista["pago_total"]
                    label_valor = "Pendente" if not sit_lista["em_dia"] else "Pago"

                    with st.container(border=True):
                        col_nome_tag, col_valor = st.columns([2.2, 1.3])
                        with col_nome_tag:
                            st.markdown(
                                f"**{al['nome']}** &nbsp; <span class='filtro-pill' style='padding:2px 10px; font-size:11px;'>{tag_cobranca}</span>",
                                unsafe_allow_html=True
                            )
                            st.caption(("PAR-Q ✅" if parq_ok else "PAR-Q ⚠️") + f"  ·  {al.get('presencas') or 0} presenças")
                        with col_valor:
                            cor_pill = "status-pill-vermelho" if not sit_lista["em_dia"] else "status-pill-verde"
                            st.markdown(
                                f"<div style='text-align:right;'>"
                                f"<div style='font-weight:700;'>{fmt_moeda(valor_exibido)}</div>"
                                f"<span class='status-pill {cor_pill}'>{label_valor}</span></div>",
                                unsafe_allow_html=True
                            )

                        if not sit_lista["em_dia"]:
                            col_btn_abrir, col_btn_cobrar = st.columns(2)
                            with col_btn_abrir:
                                if st.button("Abrir Perfil", key=f"abrir_{al['id']}", use_container_width=True, type="secondary"):
                                    st.session_state.aluno_detalhe_id = al["id"]
                                    st.rerun()
                            with col_btn_cobrar:
                                tel_lista = re.sub(r'\D', '', str(al.get("telefone", "")))
                                if tel_lista:
                                    msg_lista = f"Fala {al['nome']}! Passando pra avisar que seu pagamento está pendente. Chave para renovação: {st.session_state.chave_pix}. Valeu!"
                                    link_lista = f"https://wa.me/55{tel_lista}?text={urllib.parse.quote(msg_lista)}"
                                    st.markdown(f"<a href='{link_lista}' target='_blank'><button style='background:#25D366; color:white; border:none; padding:8px; border-radius:10px; width:100%; min-height:44px; font-weight:600;'>📱 Cobrar</button></a>", unsafe_allow_html=True)
                                else:
                                    st.button("📱 Sem telefone", key=f"semtel_{al['id']}", use_container_width=True, disabled=True)
                        else:
                            if st.button("Abrir Perfil", key=f"abrir_{al['id']}", use_container_width=True, type="secondary"):
                                st.session_state.aluno_detalhe_id = al["id"]
                                st.rerun()

            st.divider()

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
        
        tab_alunos, tab_caixa, tab_relatorio, tab_config = st.tabs(["Mensalidades (Cobrança)", "Fluxo de Caixa e Metas", "📄 Relatório Mensal", "Configuração PIX"])
        
        with tab_config:
            st.markdown("### Configurar Mensagem de Cobrança")
            chave = st.text_input("Digite sua chave de recebimento (PIX, Link, etc):", value=st.session_state.chave_pix)
            if st.button("Salvar Chave"):
                st.session_state.chave_pix = chave
                st.success("Chave salva para esta sessão!")

        with tab_relatorio:
            st.markdown("### 📄 Aulas realizadas por aluno, no mês")
            st.caption("Conta as aulas marcadas como Presença e calcula o valor correspondente (proporcional, no caso de pacote).")

            col_mes, col_ano = st.columns(2)
            with col_mes:
                mes_relatorio = st.selectbox("Mês", list(range(1, 13)), index=hoje.month - 1,
                                              format_func=lambda m: ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"][m-1])
            with col_ano:
                ano_relatorio = st.number_input("Ano", min_value=2020, max_value=2100, value=hoje.year, step=1)

            preparar_cliente()
            try:
                res_rel = supabase.table("agendamentos").select("*").eq("user_id", user_id).execute()
                agendamentos_relatorio = res_rel.data if res_rel.data else []
            except Exception as e:
                agendamentos_relatorio = []
                st.error("Não foi possível carregar os dados do relatório.")

            linhas_relatorio = calcular_relatorio_mensal(alunos_todos, agendamentos_relatorio, ano_relatorio, mes_relatorio)

            if not linhas_relatorio:
                st.info("Nenhuma aula com presença registrada nesse mês.")
            else:
                st.dataframe(linhas_relatorio, use_container_width=True, hide_index=True)

                total_aulas_rel = sum(l["Aulas no mês"] for l in linhas_relatorio)
                total_valor_rel = sum(l["Valor total (R$)"] for l in linhas_relatorio)
                cr1, cr2 = st.columns(2)
                cr1.metric("Total de aulas no mês", total_aulas_rel)
                cr2.metric("Valor total no mês", f"R$ {total_valor_rel:.2f}")

                import csv
                import io
                buffer_csv = io.StringIO()
                escritor = csv.DictWriter(buffer_csv, fieldnames=["Aluno", "Aulas no mês", "Valor total (R$)"])
                escritor.writeheader()
                escritor.writerows(linhas_relatorio)

                st.download_button(
                    "⬇️ Baixar relatório (CSV)",
                    data=buffer_csv.getvalue(),
                    file_name=f"relatorio_{ano_relatorio}_{mes_relatorio:02d}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with tab_alunos:
            st.markdown("### Status de Pagamento")
            if not alunos_todos:
                st.info("Nenhum aluno cadastrado.")
            else:
                for al in alunos_todos:
                    sit = situacao_financeira(al, transacoes_todas, hoje)
                    ultimo_pag_txt = sit["ultimo_pagamento"].strftime("%d/%m/%Y") if sit["ultimo_pagamento"] else "—"
                    vencimento_txt = f"Dia {al.get('vencimento')}" if al.get("tipo_cobranca") == "pacote" and al.get("vencimento") else "—"

                    with st.container(border=True):
                        col_info, col_valor = st.columns([2, 1.3])
                        with col_info:
                            st.markdown(f"**{al['nome']}**")
                            st.caption(f"{al.get('tipo_cobranca', 'pacote').replace('_', ' ').title()} · Total pago: {fmt_moeda(sit['pago_total'])}")
                        with col_valor:
                            cor_pill = "status-pill-verde" if sit["em_dia"] else "status-pill-laranja"
                            label_pill = "Pago" if sit["em_dia"] else "Pendente"
                            st.markdown(
                                f"<div style='text-align:right;'>"
                                f"<div style='font-weight:700;'>{fmt_moeda(sit['saldo'] if not sit['em_dia'] else sit['pago_total'])}</div>"
                                f"<span class='status-pill {cor_pill}'>{label_pill}</span></div>",
                                unsafe_allow_html=True
                            )

                        col_venc, col_pag = st.columns(2)
                        with col_venc:
                            st.caption(f"Vencimento: {vencimento_txt}")
                        with col_pag:
                            st.caption(f"Último pagamento: {ultimo_pag_txt}")

                        if sit["em_dia"]:
                            if st.button("↩️ Desfazer último pagamento", key=f"desfazer_{al['id']}", use_container_width=True, type="secondary"):
                                with st.spinner("Desfazendo..."):
                                    try:
                                        if desfazer_ultimo_pagamento(al, transacoes_todas):
                                            st.success("Último pagamento desfeito.")
                                            st.rerun()
                                        else:
                                            st.warning("Não há pagamento registrado pra desfazer.")
                                    except Exception:
                                        st.error("Não foi possível desfazer o pagamento. Tente novamente.")
                        else:
                            telefone_salvo = al.get("telefone")
                            tel = re.sub(r'\D', '', str(telefone_salvo) if telefone_salvo is not None else "")
                            if tel:
                                msg = f"Fala {al['nome']}! Tudo bem? Passando só para avisar que o seu pacote de aulas venceu. Segue a chave para renovação: {st.session_state.chave_pix}. Valeu!"
                                link_whats = f"https://wa.me/55{tel}?text={urllib.parse.quote(msg)}"
                                st.markdown(f"<a href='{link_whats}' target='_blank'><button style='background-color:#25D366; color:white; border:none; padding:8px; border-radius:10px; width:100%; min-height:44px; font-weight:600; margin-bottom:8px;'>📱 Cobrar via WhatsApp</button></a>", unsafe_allow_html=True)

                        with st.expander(f"✅ Marcar pago — {al['nome']}"):
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
