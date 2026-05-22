import streamlit as st
import pandas as pd
from github import Github, GithubException
import io
import plotly.express as px

# 1. Configuração da página
st.set_page_config(page_title="Dashboard de Retenção", layout="wide")

# ==========================================
# CONFIGURAÇÕES DO GITHUB VIA SECRETS
# ==========================================
try:
    token_github = st.secrets["GITHUB_TOKEN"]
    nome_repo = st.secrets["GITHUB_REPO"]
    
    g = Github(token_github)
    repo = g.get_repo(nome_repo)
except Exception as e:
    st.error("Erro ao ligar ao GitHub. Verifique as Secrets.")
    st.stop()

FILAS_ALVO = [
    "RETENCAO", "RETENCAO 5G", "RETENCAO 5G DIGITAL", "RETENCAO 5G DIGITAL FH",
    "RETENCAO AGILITY", "RETENCAO AGILITY DIGITAL", "RETENCAO CALLBACK",
    "RETENCAO DIGITAL", "RETENCAO DIGITAL ATIVO", "RETENCAO DIGITAL FH",
    "RETENCAO MULTISKILL", "RETENCAO OMNI MULTISKILL"
]

# ==========================================
# NOVA ARQUITETURA: MÚLTIPLOS FICHEIROS
# ==========================================
@st.cache_data(ttl=60)
def carregar_historico_github():
    try:
        # Lê a pasta inteira
        contents = repo.get_contents("dados")
        dfs = []
        for file_obj in contents:
            # Pega apenas os ficheiros CSV
            if file_obj.name.endswith('.csv'):
                # Usa o URL de download direto (Muito mais rápido e foge de limites de leitura)
                df = pd.read_csv(file_obj.download_url)
                dfs.append(df)
        
        if dfs:
            # Junta todos os meses num só para o Dashboard
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def salvar_novo_mes(df, mes_referencia):
    # Cria um nome de ficheiro único para o mês (ex: "mes_Maio_2026.csv")
    nome_seguro = mes_referencia.replace("/", "_").replace(" ", "_").lower()
    caminho_arquivo = f"dados/mes_{nome_seguro}.csv"
    
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    conteudo_str = csv_buffer.getvalue()
    mensagem_commit = f"Adicionado dados do mês: {mes_referencia}"
    
    try:
        # Se o mês já existe, atualiza SÓ esse mês
        contents = repo.get_contents(caminho_arquivo)
        repo.update_file(caminho_arquivo, mensagem_commit, conteudo_str, contents.sha)
        return True, ""
    except GithubException as e:
        # Se o mês não existe, cria um novo ficheiro
        if e.status == 404:
            repo.create_file(caminho_arquivo, mensagem_commit, conteudo_str)
            return True, ""
        return False, f"Erro: {e.data.get('message', str(e))}"

# ==========================================
# ÁREA DE UPLOAD (BARRA LATERAL)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8956/8956600.png", width=80)
    st.header("📥 Alimentar Histórico")
    arquivo_carregado = st.file_uploader("1. Selecione o CSV", type=["csv"])
    mes_referencia = st.text_input("2. Mês/Ano (Ex: Maio/2026)")
    btn_adicionar = st.button("3. Adicionar ao Histórico", use_container_width=True, type="primary")

df_historico = carregar_historico_github()

if btn_adicionar:
    if arquivo_carregado is not None and mes_referencia != "":
        with st.spinner(f'A guardar {mes_referencia} como um novo ficheiro...'):
            # Prepara APENAS os dados deste mês
            df_novo = pd.read_csv(arquivo_carregado)
            df_novo['Mês de Referência'] = mes_referencia
            
            # Envia apenas este pequeno bloco para o GitHub
            sucesso, erro_msg = salvar_novo_mes(df_novo, mes_referencia)
            
            if sucesso:
                st.sidebar.success("✅ Guardado com sucesso no GitHub!")
                st.cache_data.clear() # Força a atualização do ecrã
                st.rerun() 
            else:
                st.sidebar.error(f"Falha ao salvar: {erro_msg}")
    else:
        st.sidebar.error("Insira o ficheiro E digite o mês.")

# ==========================================
# ÁREA DO DASHBOARD (TELA PRINCIPAL)
# ==========================================
st.title("📊 Painel de Retenção e Tabulações")
st.markdown("Acompanhamento de volumetria e ofensores das filas de retenção.")

if not df_historico.empty:
    df = df_historico.copy()
    
    # Tratamento caso a coluna não exista
    if 'Fila' not in df.columns or 'Finalização' not in df.columns:
        st.error("As colunas 'Fila' ou 'Finalização' não foram encontradas no CSV.")
        st.stop()
        
    df['Fila'] = df['Fila'].fillna("")
    df['Finalização'] = df['Finalização'].fillna("Sem Tabulação")
    
    mascara_filas = df['Fila'].apply(lambda x: any(fila_alvo in x for fila_alvo in FILAS_ALVO))
    df_filtrado = df[mascara_filas].copy()
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Visualização")
    
    opcoes_mes = df_filtrado['Mês de Referência'].dropna().unique().tolist()
    filtro_mes = st.sidebar.multiselect("Filtrar por Mês:", options=opcoes_mes, default=opcoes_mes)
    
    if filtro_mes:
        df_filtrado = df_filtrado[df_filtrado['Mês de Referência'].isin(filtro_mes)]
        
    resumo_finalizacao = df_filtrado['Finalização'].value_counts().reset_index()
    resumo_finalizacao.columns = ['Finalização', 'Quantidade']
    top_tabulacao = resumo_finalizacao.iloc[0]['Finalização'] if not resumo_finalizacao.empty else "N/A"
    
    st.markdown("### 🎯 Indicadores Principais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Atendimentos", f"{len(df_filtrado):,}".replace(",", "."))
    col2.metric("Meses Analisados", df_filtrado['Mês de Referência'].nunique())
    col3.metric("Principal Tabulação (Ofensor)", top_tabulacao.split(';')[0][:30] + "...") 
    
    st.markdown("---")
    aba1, aba2, aba3 = st.tabs(["📈 Visão Geral", "🎯 Análise de Tabulações", "📋 Base de Dados"])

    with aba1:
        st.markdown("#### Evolução Mensal")
        if not df_filtrado.empty:
            df_evolucao = df_filtrado.groupby('Mês de Referência').size().reset_index(name='Volume')
            fig_linha = px.line(df_evolucao, x='Mês de Referência', y='Volume', markers=True, 
                               title="Volume de Atendimentos de Retenção por Mês")
            fig_linha.update_traces(line_color='#0068c9', line_width=3, marker_size=10)
            st.plotly_chart(fig_linha, use_container_width=True)

    with aba2:
        if not df_filtrado.empty:
            st.markdown("#### Top 10 Tabulações Mais Utilizadas")
            col_graf, col_donut = st.columns([2, 1])
            
            top_10 = resumo_finalizacao.head(10).sort_values('Quantidade', ascending=True) 
            
            with col_graf:
                fig_barras = px.bar(
                    top_10, 
                    x='Quantidade', 
                    y='Finalização', 
                    orientation='h',
                    text='Quantidade',
                    color='Quantidade',
                    color_continuous_scale='Blues'
                )
                fig_barras.update_layout(yaxis_title="", xaxis_title="", showlegend=False, height=500, yaxis=dict(tickmode='linear', automargin=True))
                fig_barras.update_traces(textposition='outside')
                st.plotly_chart(fig_barras, use_container_width=True)
                
            with col_donut:
                st.markdown("#### Concentração (Top 5)")
                top_5 = resumo_finalizacao.head(5)
                fig_donut = px.pie(top_5, values='Quantidade', names='Finalização', hole=0.4)
                fig_donut.update_traces(textposition='inside', textinfo='percent')
                fig_donut.update_layout(showlegend=False) 
                st.plotly_chart(fig_donut, use_container_width=True)
                
            st.markdown("#### Tabela Completa de Tabulações")
            st.dataframe(resumo_finalizacao.style.background_gradient(cmap='Blues', subset=['Quantidade']), use_container_width=True, hide_index=True)

    with aba3:
        st.markdown("#### Detalhamento de Registros Filtrados")
        colunas_exibicao = ['Mês de Referência', 'Data', 'Usuários', 'Fila', 'Finalização']
        colunas_presentes = [col for col in colunas_exibicao if col in df_filtrado.columns]
        st.dataframe(df_filtrado[colunas_presentes], use_container_width=True, hide_index=True)

else:
    st.info("👆 O seu banco de dados no GitHub está vazio. Utilize o menu lateral esquerdo para fazer o upload do seu primeiro ficheiro CSV.")
