import streamlit as st
import pandas as pd
import os

# 1. Configuração da página
st.set_page_config(page_title="Dashboard de Retenção", layout="wide")
st.title("📊 Dashboard de Atendimentos: Retenção")

# Lista de filas exatas baseadas na imagem enviada
FILAS_ALVO = [
    "RETENCAO",
    "RETENCAO 5G",
    "RETENCAO 5G DIGITAL",
    "RETENCAO 5G DIGITAL FH",
    "RETENCAO AGILITY",
    "RETENCAO AGILITY DIGITAL",
    "RETENCAO CALLBACK",
    "RETENCAO DIGITAL",
    "RETENCAO DIGITAL ATIVO",
    "RETENCAO DIGITAL FH",
    "RETENCAO MULTISKILL",
    "RETENCAO OMNI MULTISKILL"
]

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

if btn_adicionar:
    if arquivo_carregado is not None and mes_referencia != "":
        df_novo = pd.read_csv(arquivo_carregado)
        df_novo['Mês de Referência'] = mes_referencia
        
        if os.path.exists(ARQUIVO_HISTORICO):
            df_historico = pd.read_csv(ARQUIVO_HISTORICO)
            if mes_referencia in df_historico['Mês de Referência'].values:
                st.sidebar.warning(f"Os dados de {mes_referencia} já estão no histórico!")
            else:
                df_atualizado = pd.concat([df_historico, df_novo], ignore_index=True)
                df_atualizado.to_csv(ARQUIVO_HISTORICO, index=False)
                st.sidebar.success(f"✅ {mes_referencia} adicionado com sucesso!")
        else:
            df_novo.to_csv(ARQUIVO_HISTORICO, index=False)
            st.sidebar.success(f"✅ Base iniciada com os dados de {mes_referencia}!")
    else:
        st.sidebar.error("Por favor, insira o arquivo E digite o mês.")

# ==========================================
# ÁREA DO DASHBOARD (TELA PRINCIPAL)
# ==========================================
st.markdown("---")

if os.path.exists(ARQUIVO_HISTORICO):
    df = pd.read_csv(ARQUIVO_HISTORICO)
    
    # Preenche valores vazios para evitar erros na busca
    df['Fila'] = df['Fila'].fillna("")
    df['Finalização'] = df['Finalização'].fillna("Sem Tabulação")
    
    # FILTRO AUTOMÁTICO: Mantém apenas as linhas onde a 'Fila' contém alguma das filas alvo
    # (Usamos compreensão de lista para checar se alguma fila da nossa lista está dentro da string da coluna)
    mascara_filas = df['Fila'].apply(lambda x: any(fila_alvo in x for fila_alvo in FILAS_ALVO))
    df_filtrado = df[mascara_filas].copy()
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Visualização")
    
    opcoes_mes = df_filtrado['Mês de Referência'].dropna().unique().tolist()
    filtro_mes = st.sidebar.multiselect("Filtrar por Mês:", options=opcoes_mes, default=opcoes_mes)
    
    if filtro_mes:
        df_filtrado = df_filtrado[df_filtrado['Mês de Referência'].isin(filtro_mes)]
        
    # Indicadores principais
    col1, col2 = st.columns(2)
    col1.metric("Total de Atendimentos (Apenas Filas de Retenção)", f"{len(df_filtrado):,}".replace(",", "."))
    col2.metric("Meses Analisados", df_filtrado['Mês de Referência'].nunique())
    
    # AGRUPAMENTO POR FINALIZAÇÃO
    st.markdown("### 🎯 Volume por Finalização (Tabulação)")
    
    if not df_filtrado.empty:
        # Conta quantas vezes cada finalização aparece
        resumo_finalizacao = df_filtrado['Finalização'].value_counts().reset_index()
        resumo_finalizacao.columns = ['Finalização', 'Quantidade']
        
        # Divide a tela: Gráfico de um lado, Tabela do outro
        col_grafico, col_tabela = st.columns([2, 1])
        
        with col_tabela:
            st.dataframe(resumo_finalizacao, use_container_width=True, hide_index=True)
            
        with col_grafico:
            # Mostra um gráfico de barras com as 10 finalizações mais usadas para não poluir
            top_10_finalizacoes = resumo_finalizacao.head(10)
            st.bar_chart(data=top_10_finalizacoes.set_index('Finalização'))
            
        # Tabela Detalhada (Histórico completo filtrado)
        st.markdown("### 📋 Detalhamento dos Registros")
        colunas_exibicao = ['Mês de Referência', 'Data', 'Usuários', 'Fila', 'Finalização']
        colunas_presentes = [col for col in colunas_exibicao if col in df_filtrado.columns]
        
        st.dataframe(df_filtrado[colunas_presentes], use_container_width=True, hide_index=True)
        
    else:
        st.warning("Nenhum dado encontrado para as filas de Retenção selecionadas neste mês.")

else:
    st.info("👆 O seu banco de dados está vazio. Use o menu lateral esquerdo para fazer o upload do seu primeiro arquivo CSV.")
