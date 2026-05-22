import streamlit as st
import pandas as pd
from github import Github
import io

# 1. Configuração da página
st.set_page_config(page_title="Dashboard de Retenção", layout="wide")
st.title("📊 Dashboard de Atendimentos: Retenção")

# ==========================================
# CONFIGURAÇÕES DO GITHUB VIA SECRETS
# ==========================================
CAMINHO_ARQUIVO = "dados/historico_completo.csv"

# Autenticação no GitHub puxando diretamente do painel de Secrets
try:
    token_github = st.secrets["GITHUB_TOKEN"]
    nome_repo = st.secrets["GITHUB_REPO"]
    
    g = Github(token_github)
    repo = g.get_repo(nome_repo)
except Exception as e:
    st.error("Erro ao ligar ao GitHub. Verifique se configurou o GITHUB_TOKEN e o GITHUB_REPO nas Secrets do Streamlit de forma correta.")
    st.stop()

# Lista de filas alvo (baseado na imagem enviada anteriormente)
FILAS_ALVO = [
    "RETENCAO", "RETENCAO 5G", "RETENCAO 5G DIGITAL", "RETENCAO 5G DIGITAL FH",
    "RETENCAO AGILITY", "RETENCAO AGILITY DIGITAL", "RETENCAO CALLBACK",
    "RETENCAO DIGITAL", "RETENCAO DIGITAL ATIVO", "RETENCAO DIGITAL FH",
    "RETENCAO MULTISKILL", "RETENCAO OMNI MULTISKILL"
]

# ==========================================
# FUNÇÕES DE LIGAÇÃO AO GITHUB
# ==========================================
@st.cache_data(ttl=60) # Atualiza a leitura a cada 60s
def carregar_historico_github():
    try:
        contents = repo.get_contents(CAMINHO_ARQUIVO)
        csv_string = contents.decoded_content.decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_string))
        return df, contents.sha
    except:
        return pd.DataFrame(), None

def salvar_historico_github(df, sha=None):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    conteudo_str = csv_buffer.getvalue()
    
    mensagem_commit = "Atualização de base de dados via Dashboard Streamlit"
    
    if sha:
        repo.update_file(CAMINHO_ARQUIVO, mensagem_commit, conteudo_str, sha)
    else:
        repo.create_file(CAMINHO_ARQUIVO, mensagem_commit, conteudo_str)

# ==========================================
# ÁREA DE UPLOAD (BARRA LATERAL)
# ==========================================
st.sidebar.header("📥 Alimentar Histórico")
st.sidebar.markdown("Faça o upload do CSV mensal.")

arquivo_carregado = st.sidebar.file_uploader("1. Selecione o CSV", type=["csv"])
mes_referencia = st.sidebar.text_input("2. Mês/Ano (Ex: Maio/2026)")
btn_adicionar = st.sidebar.button("3. Adicionar ao Histórico")

df_historico, file_sha = carregar_historico_github()

if btn_adicionar:
    if arquivo_carregado is not None and mes_referencia != "":
        with st.spinner('A processar e a guardar os dados no GitHub...'):
            df_novo = pd.read_csv(arquivo_carregado)
            df_novo['Mês de Referência'] = mes_referencia
            
            if not df_historico.empty:
                if mes_referencia in df_historico['Mês de Referência'].values:
                    st.sidebar.warning(f"Os dados de {mes_referencia} já estão no histórico!")
                else:
                    df_atualizado = pd.concat([df_historico, df_novo], ignore_index=True)
                    salvar_historico_github(df_atualizado, file_sha)
                    st.sidebar.success(f"✅ {mes_referencia} guardado no GitHub com sucesso!")
                    st.rerun() 
            else:
                salvar_historico_github(df_novo)
                st.sidebar.success(f"✅ Base iniciada e guardada no GitHub com os dados de {mes_referencia}!")
                st.rerun()
    else:
        st.sidebar.error("Por favor, insira o ficheiro E digite o mês.")

# ==========================================
# ÁREA DO DASHBOARD (TELA PRINCIPAL)
# ==========================================
st.markdown("---")

if not df_historico.empty:
    df = df_historico.copy()
    
    df['Fila'] = df['Fila'].fillna("")
    df['Finalização'] = df['Finalização'].fillna("Sem Tabulação")
    
    # Filtra apenas as filas de Retenção
    mascara_filas = df['Fila'].apply(lambda x: any(fila_alvo in x for fila_alvo in FILAS_ALVO))
    df_filtrado = df[mascara_filas].copy()
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Visualização")
    
    opcoes_mes = df_filtrado['Mês de Referência'].dropna().unique().tolist()
    filtro_mes = st.sidebar.multiselect("Filtrar por Mês:", options=opcoes_mes, default=opcoes_mes)
    
    if filtro_mes:
        df_filtrado = df_filtrado[df_filtrado['Mês de Referência'].isin(filtro_mes)]
        
    col1, col2 = st.columns(2)
    col1.metric("Total de Atendimentos (Retenção)", f"{len(df_filtrado):,}".replace(",", "."))
    col2.metric("Meses Analisados", df_filtrado['Mês de Referência'].nunique())
    
    st.markdown("### 🎯 Volume por Finalização (Tabulação)")
    
    if not df_filtrado.empty:
        resumo_finalizacao = df_filtrado['Finalização'].value_counts().reset_index()
        resumo_finalizacao.columns = ['Finalização', 'Quantidade']
        
        col_grafico, col_tabela = st.columns([2, 1])
        
        with col_tabela:
            st.dataframe(resumo_finalizacao, use_container_width=True, hide_index=True)
            
        with col_grafico:
            top_10 = resumo_finalizacao.head(10)
            st.bar_chart(data=top_10.set_index('Finalização'))
            
        st.markdown("### 📋 Detalhamento dos Registros")
        colunas_exibicao = ['Mês de Referência', 'Data', 'Usuários', 'Fila', 'Finalização']
        colunas_presentes = [col for col in colunas_exibicao if col in df_filtrado.columns]
        
        st.dataframe(df_filtrado[colunas_presentes], use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum dado encontrado para as filas de Retenção selecionadas neste mês.")
else:
    st.info("👆 O seu banco de dados no GitHub está vazio. Utilize o menu lateral para fazer o upload do seu primeiro ficheiro CSV.")
