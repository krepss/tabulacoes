import streamlit as st
import pandas as pd
import os

# 1. Configuração da página
st.set_page_config(page_title="Dashboard de Filas", layout="wide")
st.title("📊 Dashboard Analítico de Atendimentos")

# Criar pasta 'dados' se não existir
os.makedirs("dados", exist_ok=True)
ARQUIVO_HISTORICO = "dados/historico_completo.csv"

# ==========================================
# ÁREA DE UPLOAD E ALIMENTAÇÃO (BARRA LATERAL)
# ==========================================
st.sidebar.header("📥 Alimentar Histórico")
st.sidebar.markdown("Faça o upload do mês e adicione à base.")

arquivo_carregado = st.sidebar.file_uploader("1. Selecione o CSV", type=["csv"])
mes_referencia = st.sidebar.text_input("2. Identifique o Mês/Ano (Ex: Maio/2026)")
btn_adicionar = st.sidebar.button("3. Adicionar ao Histórico")

# Lógica de salvar o novo arquivo
if btn_adicionar:
    if arquivo_carregado is not None and mes_referencia != "":
        # Lê o arquivo que você acabou de subir
        df_novo = pd.read_csv(arquivo_carregado)
        
        # Cria uma nova coluna para identificar de qual mês é essa informação
        df_novo['Mês de Referência'] = mes_referencia
        
        # Verifica se já existe um histórico salvo
        if os.path.exists(ARQUIVO_HISTORICO):
            df_historico = pd.read_csv(ARQUIVO_HISTORICO)
            
            # Evita duplicidade se você clicar no botão duas vezes sem querer
            if mes_referencia in df_historico['Mês de Referência'].values:
                st.sidebar.warning(f"Os dados de {mes_referencia} já estão no histórico! Se quiser substituir, precisaremos criar um botão de limpar.")
            else:
                # Junta o histórico antigo com o arquivo novo
                df_atualizado = pd.concat([df_historico, df_novo], ignore_index=True)
                df_atualizado.to_csv(ARQUIVO_HISTORICO, index=False)
                st.sidebar.success(f"✅ {mes_referencia} adicionado com sucesso!")
        else:
            # Se for a primeira vez, o arquivo novo vira o histórico
            df_novo.to_csv(ARQUIVO_HISTORICO, index=False)
            st.sidebar.success(f"✅ Base iniciada com os dados de {mes_referencia}!")
    else:
        st.sidebar.error("Por favor, insira o arquivo E digite o mês.")

# ==========================================
# ÁREA DO DASHBOARD (TELA PRINCIPAL)
# ==========================================
st.markdown("---")

if os.path.exists(ARQUIVO_HISTORICO):
    # Carrega o histórico completo
    df = pd.read_csv(ARQUIVO_HISTORICO)
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Visualização")
    
    # Filtros
    opcoes_mes = df['Mês de Referência'].dropna().unique().tolist()
    opcoes_fila = df['Fila'].dropna().unique().tolist()
    
    filtro_mes = st.sidebar.multiselect("Filtrar por Mês:", options=opcoes_mes, default=opcoes_mes)
    filtro_fila = st.sidebar.multiselect("Filtrar por Fila:", options=opcoes_fila)
    
    # Aplicando os filtros
    df_filtrado = df.copy()
    if filtro_mes:
        df_filtrado = df_filtrado[df_filtrado['Mês de Referência'].isin(filtro_mes)]
    if filtro_fila:
        df_filtrado = df_filtrado[df_filtrado['Fila'].isin(filtro_fila)]
        
    # Indicadores
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Atendimentos", f"{len(df_filtrado):,}".replace(",", "."))
    
    if 'Usuários' in df_filtrado.columns:
        col2.metric("Usuários Diferentes", df_filtrado['Usuários'].nunique())
        
    col3.metric("Meses Analisados", df_filtrado['Mês de Referência'].nunique())
    
    # Gráfico simples de evolução por mês (se houver dados)
    st.markdown("### 📈 Evolução por Mês")
    resumo_mes = df_filtrado.groupby('Mês de Referência').size().reset_index(name='Quantidade de Atendimentos')
    st.bar_chart(data=resumo_mes, x='Mês de Referência', y='Quantidade de Atendimentos')

    # Tabela
    st.markdown("### 📋 Detalhamento dos Dados")
    colunas_exibicao = ['Mês de Referência', 'Data', 'Usuários', 'Fila', 'Finalização']
    colunas_presentes = [col for col in colunas_exibicao if col in df_filtrado.columns]
    
    st.dataframe(df_filtrado[colunas_presentes], use_container_width=True, hide_index=True)

else:
    st.info("👆 O seu banco de dados está vazio. Use o menu lateral esquerdo para fazer o upload do seu primeiro arquivo CSV.")
