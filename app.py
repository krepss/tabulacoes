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
CAMINHO_ARQUIVO = "dados/historico_completo.csv"

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
# FUNÇÕES DE LIGAÇÃO AO GITHUB (SEM CACHE E AUTO-CURATIVAS)
# ==========================================
def carregar_historico_github():
    try:
        contents = repo.get_contents(CAMINHO_ARQUIVO)
        try:
            csv_string = contents.decoded_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_string))
            return df, contents.sha
        except Exception:
            # O arquivo existe mas está vazio/corrompido
            return pd.DataFrame(), contents.sha
    except GithubException as e:
        # 404 significa que o arquivo realmente não existe ainda
        if e.status == 404:
            return pd.DataFrame(), None
        return pd.DataFrame(), None

def salvar_historico_github(df, sha=None):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    conteudo_str = csv_buffer.getvalue()
    mensagem_commit = "Atualização de base de dados via Dashboard Streamlit"
    
    try:
        if sha:
            repo.update_file(CAMINHO_ARQUIVO, mensagem_commit, conteudo_str, sha)
        else:
            repo.create_file(CAMINHO_ARQUIVO, mensagem_commit, conteudo_str)
        return True, ""
    except GithubException as e:
        # Se tentou criar e deu erro 422 (O arquivo já existe no GitHub)
        if e.status == 422:
            try:
                # Sistema de autocura: busca o SHA atualizado e força o update
                contents = repo.get_contents(CAMINHO_ARQUIVO)
                repo.update_file(CAMINHO_ARQUIVO, mensagem_commit, conteudo_str, contents.sha)
                return True, ""
            except Exception as ex:
                return False, f"Tentou corrigir, mas falhou: {str(ex)}"
        # Retorna o erro exato do GitHub caso seja falta de permissão do Token
        return False, f"Erro {e.status}: {e.data.get('message', 'Sem detalhes')}"

# ==========================================
# ÁREA DE UPLOAD (BARRA LATERAL)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8956/8956600.png", width=80)
    st.header("📥 Alimentar Histórico")
    arquivo_carregado = st.file_uploader("1. Selecione o CSV", type=["csv"])
    mes_referencia = st.text_input("2. Mês/Ano (Ex: Maio/2026)")
    btn_adicionar = st.button("3. Adicionar ao Histórico", use_container_width=True, type="primary")

# Lê em tempo real (sem cache)
df_historico, file_sha = carregar_historico_github()

if btn_adicionar:
    if arquivo_carregado is not None and mes_referencia != "":
        with st.spinner('Salvando no GitHub... Isso pode levar alguns segundos.'):
            df_novo = pd.read_csv(arquivo_carregado)
            df_novo['Mês de Referência'] = mes_referencia
            
            if not df_historico.empty:
                if mes_referencia in df_historico['Mês de Referência'].values:
                    st.sidebar.warning(f"{mes_referencia} já está no histórico!")
                else:
                    df_atualizado = pd.concat([df_historico, df_novo], ignore_index=True)
                    sucesso, erro_msg = salvar_historico_github(df_atualizado, file_sha)
                    if sucesso:
                        st.sidebar.success("✅ Guardado com sucesso!")
                        st.rerun() 
                    else:
                        st.sidebar.error(f"Falha ao salvar: {erro_msg}")
            else:
                # Onde o erro acontecia. Agora está protegido pela autocura e retorna mensagem visível.
                sucesso, erro_msg = salvar_historico_github(df_novo, file_sha)
                if sucesso:
                    st.sidebar.success("✅ Base iniciada com sucesso!")
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
