import streamlit as st
import pandas as pd
from github import Github, GithubException
import io
import plotly.express as px

# 1. Configuração da página
st.set_page_config(page_title="Dashboard de Retenção", layout="wide")

# ==========================================
# CONFIGURAÇÕES DO GITHUB
# ==========================================
CAMINHO_ARQUIVO = "historico_completo.csv"

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

COLUNAS_UTEIS = ['Mês de Referência', 'Data', 'Usuários', 'Direção', 'Fila', 'Finalização']

# ==========================================
# FUNÇÕES DE LIGAÇÃO
# ==========================================
def carregar_historico_github():
    try:
        contents = repo.get_contents(CAMINHO_ARQUIVO)
        df = pd.read_csv(contents.download_url)
        return df, contents.sha
    except Exception:
        return pd.DataFrame(), None

def salvar_historico_github(df, sha=None):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    conteudo_str = csv_buffer.getvalue()
    mensagem_commit = "Base de dados pareada exclusivamente com tabulações reais"
    
    try:
        contents = repo.get_contents(CAMINHO_ARQUIVO)
        sha_atualizado = contents.sha
    except:
        sha_atualizado = sha

    try:
        if sha_atualizado:
            repo.update_file(CAMINHO_ARQUIVO, mensagem_commit, conteudo_str, sha_atualizado)
        else:
            repo.create_file(CAMINHO_ARQUIVO, mensagem_commit, conteudo_str)
        return True, ""
    except GithubException as e:
        return False, f"Erro {e.status}: {e.data.get('message', str(e))}"

# ==========================================
# ÁREA DE UPLOAD (BARRA LATERAL)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8956/8956600.png", width=80)
    st.header("📥 Alimentar Histórico")
    st.markdown("O sistema capta apenas as tabulações exatas vinculadas às filas alvo.")
    arquivo_carregado = st.file_uploader("1. Selecione o CSV", type=["csv"])
    mes_referencia = st.text_input("2. Mês/Ano (Ex: Abril/2026)")
    btn_adicionar = st.button("3. Adicionar ao Histórico", use_container_width=True, type="primary")

df_historico, file_sha = carregar_historico_github()

if btn_adicionar:
    if arquivo_carregado is not None and mes_referencia != "":
        with st.spinner('A processar cruzamento estrito e a guardar no GitHub...'):
            df_bruto = pd.read_csv(arquivo_carregado)
            
            df_bruto['Usuários'] = df_bruto['Usuários'].fillna("")
            df_bruto['Fila'] = df_bruto['Fila'].fillna("")
            df_bruto['Finalização'] = df_bruto['Finalização'].fillna("")
            
            linhas_processadas = []
            
            for _, row in df_bruto.iterrows():
                # Separa as informações na exata ordem do CSV
                usuarios = [u.strip() for u in str(row['Usuários']).split(';')]
                filas = [f.strip() for f in str(row['Fila']).split(';')]
                tabulacoes = [t.strip() for t in str(row['Finalização']).split(';')]
                
                # O SEGREDO ESTÁ AQUI: Navegamos fila a fila pela ordem
                for i in range(len(filas)):
                    f_atual = filas[i]
                    
                    # Passo 1: Confirma se é uma Fila de Retenção
                    if f_atual in FILAS_ALVO:
                        # Passo 2: Confirma se EXISTE uma tabulação na mesma posição (ignora vazios)
                        if i < len(tabulacoes) and tabulacoes[i]:
                            t_atual = tabulacoes[i]
                            # Pega o utilizador ou marca como Desconhecido se o Genesys não exportou
                            u_atual = usuarios[i] if i < len(usuarios) and usuarios[i] else "Desconhecido"
                            
                            nova_linha = {
                                'Mês de Referência': mes_referencia,
                                'Data': row.get('Data', '-'),
                                'Usuários': u_atual,
                                'Direção': row.get('Direção', '-'),
                                'Fila': f_atual,
                                'Finalização': t_atual
                            }
                            linhas_processadas.append(nova_linha)
            
            df_novo_limpo = pd.DataFrame(linhas_processadas)
            
            if df_novo_limpo.empty:
                st.sidebar.error("Nenhuma tabulação válida foi encontrada para as filas de Retenção!")
            else:
                if not df_historico.empty:
                    if mes_referencia in df_historico['Mês de Referência'].values:
                        st.sidebar.warning(f"Os dados de {mes_referencia} já estão catalogados!")
                    else:
                        df_atualizado = pd.concat([df_historico, df_novo_limpo], ignore_index=True)
                        sucesso, erro_msg = salvar_historico_github(df_atualizado, file_sha)
                        if sucesso:
                            st.sidebar.success("✅ Adicionado com sucesso!")
                            st.rerun() 
                        else:
                            st.sidebar.error(f"Falha ao guardar: {erro_msg}")
                else:
                    sucesso, erro_msg = salvar_historico_github(df_novo_limpo, file_sha)
                    if sucesso:
                        st.sidebar.success("✅ Base iniciada com sucesso!")
                        st.rerun()
                    else:
                        st.sidebar.error(f"Falha ao guardar: {erro_msg}")
    else:
        st.sidebar.error("Insira o ficheiro E digite o mês.")

# ==========================================
# ÁREA DO DASHBOARD (TELA PRINCIPAL)
# ==========================================
st.title("📊 Painel de Retenção e Tabulações")
st.markdown("Acompanhamento de volumetria e ofensores das filas de retenção.")

if not df_historico.empty:
    df_filtrado = df_historico.copy()
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Visualização")
    
    opcoes_mes = df_filtrado['Mês de Referência'].dropna().unique().tolist()
    filtro_mes = st.sidebar.multiselect("Filtrar por Mês:", options=opcoes_mes, default=opcoes_mes)
    if filtro_mes:
        df_filtrado = df_filtrado[df_filtrado['Mês de Referência'].isin(filtro_mes)]
        
    opcoes_fila_limpas = sorted(df_filtrado['Fila'].unique().tolist())
    filtro_fila = st.sidebar.multiselect("Filtrar por Fila Específica:", options=opcoes_fila_limpas)
    if filtro_fila:
        df_filtrado = df_filtrado[df_filtrado['Fila'].isin(filtro_fila)]
        
    resumo_finalizacao = df_filtrado['Finalização'].value_counts().reset_index()
    resumo_finalizacao.columns = ['Finalização', 'Quantidade']
    top_tabulacao = resumo_finalizacao.iloc[0]['Finalização'] if not resumo_finalizacao.empty else "N/A"
    
    st.markdown("### 🎯 Indicadores Principais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Tabulações (Filtradas)", f"{len(df_filtrado):,}".replace(",", "."))
    col2.metric("Meses Analisados", df_filtrado['Mês de Referência'].nunique())
    col3.metric("Principal Tabulação (Ofensor)", top_tabulacao[:40] + "...") 
    
    st.markdown("---")
    
    aba1, aba2, aba3, aba4 = st.tabs([
        "📈 Visão Geral", 
        "🎯 Análise de Tabulações", 
        "👤 Análise por Operador", 
        "📋 Base de Dados"
    ])

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
                fig_barras = px.bar(top_10, x='Quantidade', y='Finalização', orientation='h',
                                    text='Quantidade', color='Quantidade', color_continuous_scale='Blues')
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
                
            st.divider()
            
            st.markdown("### 🏆 Colaboradores que mais utilizam esta Tabulação")
            opcoes_tab_aba2 = sorted(df_filtrado['Finalização'].unique().tolist())
            tab_selecionada_aba2 = st.selectbox("Escolha uma tabulação para ver o ranking de colaboradores:", options=opcoes_tab_aba2, key="aba2_tab")
            
            if tab_selecionada_aba2:
                df_tab_aba2 = df_filtrado[df_filtrado['Finalização'] == tab_selecionada_aba2]
                ranking_colaboradores = df_tab_aba2['Usuários'].value_counts().reset_index()
                ranking_colaboradores.columns = ['Colaborador (Usuário)', 'Quantidade de Vezes Usada']
                
                col_ranking_graf, col_ranking_tab = st.columns([2, 1])
                
                with col_ranking_graf:
                    top_10_colabs = ranking_colaboradores.head(10).sort_values('Quantidade de Vezes Usada', ascending=True)
                    fig_colabs = px.bar(top_10_colabs, x='Quantidade de Vezes Usada', y='Colaborador (Usuário)', 
                                        orientation='h', color='Quantidade de Vezes Usada', color_continuous_scale='Oranges',
                                        text='Quantidade de Vezes Usada')
                    fig_colabs.update_layout(yaxis_title="", xaxis_title="", showlegend=False, height=350)
                    fig_colabs.update_traces(textposition='outside')
                    st.plotly_chart(fig_colabs, use_container_width=True)
                    
                with col_ranking_tab:
                    st.dataframe(ranking_colaboradores.head(10), use_container_width=True, hide_index=True)
            
            st.divider()
            st.markdown("#### Tabela Completa Geral de Tabulações")
            st.dataframe(resumo_finalizacao.style.background_gradient(cmap='Blues', subset=['Quantidade']), use_container_width=True, hide_index=True)

    with aba3:
        st.markdown("#### Volumetria por Operador (Usuário)")
        if not df_filtrado.empty:
            resumo_operador = df_filtrado['Usuários'].value_counts().reset_index()
            resumo_operador.columns = ['Operador', 'Atendimentos']
            top_10_ops = resumo_operador.head(10).sort_values('Atendimentos', ascending=True)
            
            fig_ops = px.bar(top_10_ops, x='Atendimentos', y='Operador', orientation='h',
                             title="Top 10 Operadores com Maior Volume Global",
                             text='Atendimentos', color='Atendimentos', color_continuous_scale='Teal')
            fig_ops.update_layout(yaxis_title="", xaxis_title="", showlegend=False, height=400)
            fig_ops.update_traces(textposition='outside')
            st.plotly_chart(fig_ops, use_container_width=True)
            
            st.divider()
            
            st.markdown("#### Detalhamento Completo (Tabela Cruzada)")
            cruzamento_op_tab = df_filtrado.groupby(['Usuários', 'Finalização']).size().reset_index(name='Quantidade')
            cruzamento_op_tab = cruzamento_op_tab.sort_values(by=['Usuários', 'Quantidade'], ascending=[True, False])
            cruzamento_op_tab.columns = ['Operador (Usuário)', 'Tabulação (Finalização)', 'Quantidade de Vezes Usada']
            
            st.dataframe(
                cruzamento_op_tab.style.background_gradient(cmap='GnBu', subset=['Quantidade de Vezes Usada']),
                use_container_width=True,
                hide_index=True
            )

    with aba4:
        st.markdown("#### Detalhamento de Registros")
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

else:
    st.info("👆 O seu banco de dados no GitHub está vazio ou precisa ser reiniciado. Utilize o menu lateral esquerdo para fazer o upload do seu primeiro ficheiro CSV (ex: abril.csv).")
