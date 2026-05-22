import streamlit as st
import pandas as pd
import glob
import os

# 1. Configuração da página
st.set_page_config(page_title="Dashboard de Filas", layout="wide")

# 2. Função para carregar os dados (com cache para ficar rápido)
@st.cache_data
def carregar_dados():
    # Procura todos os arquivos .csv dentro da pasta 'dados'
    arquivos_csv = glob.glob("dados/*.csv")
    
    if not arquivos_csv:
        return pd.DataFrame() # Retorna vazio se não achar nada
    
    # Lê e junta todos os meses em um único DataFrame
    lista_dfs = []
    for arquivo in arquivos_csv:
        df_temp = pd.read_csv(arquivo)
        lista_dfs.append(df_temp)
        
    df_final = pd.concat(lista_dfs, ignore_index=True)
    return df_final

# 3. Carregando a base
df = carregar_dados()

st.title("📊 Dashboard Analítico de Atendimentos")

if df.empty:
    st.warning("Nenhum dado encontrado. Adicione seus arquivos CSV na pasta 'dados/'.")
else:
    # 4. Criando os Filtros na Barra Lateral (Sidebar)
    st.sidebar.header("Filtros do Dashboard")
    
    # Pegando os valores únicos para os filtros e removendo nulos
    opcoes_fila = df['Fila'].dropna().unique().tolist()
    opcoes_fin = df['Finalização'].dropna().unique().tolist()
    
    # Multiselect permite escolher mais de uma fila/tabulação por vez
    filtro_fila = st.sidebar.multiselect("Selecione a(s) Fila(s):", options=opcoes_fila)
    filtro_fin = st.sidebar.multiselect("Selecione a(s) Finalização(ões):", options=opcoes_fin)
    
    # 5. Aplicando os filtros no DataFrame
    df_filtrado = df.copy()
    
    if filtro_fila:
        df_filtrado = df_filtrado[df_filtrado['Fila'].isin(filtro_fila)]
        
    if filtro_fin:
        df_filtrado = df_filtrado[df_filtrado['Finalização'].isin(filtro_fin)]
        
    # 6. Exibindo os Indicadores (Cards)
    st.markdown("### Resumo")
    col1, col2 = st.columns(2)
    col1.metric("Total de Registros", f"{len(df_filtrado):,}".replace(",", "."))
    col2.metric("Total de Usuários Diferentes", df_filtrado['Usuários'].nunique())
    
    st.divider()
    
    # 7. Exibindo a Tabela de Dados Interativa
    st.markdown("### Detalhamento dos Dados")
    
    # Selecionando apenas as colunas mais importantes para não poluir a tela
    colunas_exibicao = ['Data', 'Usuários', 'Direção', 'Fila', 'Finalização']
    
    # Verifica se as colunas existem antes de exibir (evita erros)
    colunas_presentes = [col for col in colunas_exibicao if col in df_filtrado.columns]
    
    st.dataframe(
        df_filtrado[colunas_presentes],
        use_container_width=True,
        hide_index=True
    )
