import streamlit as st
from supabase import create_client

st.title("🧪 Teste de Conexão com Supabase")

# 1. Teste de Leitura dos Secrets
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    st.success(f"✅ Secrets lidos com sucesso!\nURL: {url}")
except Exception as e:
    st.error(f"❌ Erro ao ler st.secrets: {e}")
    st.stop()

# 2. Teste de Conexão com o Servidor
if st.button("Testar Conexão com Supabase"):
    try:
        supabase = create_client(url, key)
        # Faz uma consulta simples à API de autenticação
        res = supabase.auth.get_session()
        st.success("✅ Conexão estabelecida com sucesso com o servidor do Supabase!")
    except Exception as e:
        st.error(f"❌ Falha de Conexão:\n\n{e}")
