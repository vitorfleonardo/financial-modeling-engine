import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Valuation Engine - 3 Statements", layout="wide")

st.title("📊 3-Statement Model Engine (Python & Streamlit)")
st.markdown("""
Este app demonstra a **linkagem lógica** entre DRE, Balanço e Fluxo de Caixa sem usar Excel.
A lógica segue o princípio: *DRE gera Lucro -> DFC ajusta Lucro p/ Caixa -> BP absorve o Caixa.*
""")

# --- 1. PREMISSAS (INPUTS) NA SIDEBAR ---
st.sidebar.header("⚙️ Drivers de Projeção")

# Drivers de Crescimento e Margem
growth_rate = st.sidebar.slider("Cresc. Receita (% a.a.)", 0.0, 50.0, 10.0) / 100
cogs_pct = st.sidebar.slider("CMV (% da Receita)", 10.0, 80.0, 40.0) / 100
sg_a_pct = st.sidebar.slider("Despesas SG&A (% da Receita)", 5.0, 50.0, 20.0) / 100
tax_rate = st.sidebar.slider("Alíquota de Imposto (%)", 0.0, 34.0, 34.0) / 100

st.sidebar.markdown("---")
st.sidebar.header("🏗️ Drivers de Balanço & Caixa")

# Drivers de Capital de Giro (Simplificado como % da Receita para o MVP)
# Em um modelo avançado, usariamos Dias (DSO, DIO, DPO)
ar_pct = st.sidebar.number_input("Contas a Receber (% Rec.)", value=10.0) / 100
inv_pct = st.sidebar.number_input("Estoques (% Rec.)", value=10.0) / 100
ap_pct = st.sidebar.number_input("Fornecedores (% Rec.)", value=8.0) / 100

# Investimento e Depreciação
capex_pct = st.sidebar.slider("Capex (% da Receita)", 0.0, 20.0, 5.0) / 100
depreciation_rate = st.sidebar.slider("Taxa Depreciação (% do PP&E)", 5.0, 20.0, 10.0) / 100

# --- 2. DADOS HISTÓRICOS (ANO 0) ---
# Baseado nos exemplos conceituais dos PDFs carregados
historical_data = {
    "Receita": 100000.0,
    "CMV": -40000.0,
    "Despesas_Op": -20000.0,
    "Depreciacao": -2000.0,
    "Impostos": -10000.0,
    # Balanço Inicial
    "Caixa": 20000.0,
    "Contas_Receber": 10000.0,
    "Estoques": 10000.0,
    "PPE_Liquido": 50000.0, # Imobilizado
    "Fornecedores": 8000.0,
    "Divida_Total": 20000.0,
    "Capital_Social": 30000.0,
    "Lucros_Acumulados": 32000.0
}

# --- 3. MOTOR DE CÁLCULO (THE ENGINE) ---
projections = []
years = 5

# Inicializa o loop com o Ano 0
current_state = historical_data.copy()
current_state['Ano'] = 0
projections.append(current_state)

for year in range(1, years + 1):
    prev = projections[-1]
    curr = {}
    curr['Ano'] = year
    
    # --- PASSO A: DRE (Income Statement) ---
    curr['Receita'] = prev['Receita'] * (1 + growth_rate)
    curr['CMV'] = curr['Receita'] * -cogs_pct
    curr['Lucro_Bruto'] = curr['Receita'] + curr['CMV']
    
    curr['Despesas_Op'] = curr['Receita'] * -sg_a_pct
    
    # Depreciação é baseada no Imobilizado do ano anterior (simplificação)
    curr['Depreciacao'] = prev['PPE_Liquido'] * -depreciation_rate
    
    curr['EBIT'] = curr['Lucro_Bruto'] + curr['Despesas_Op'] + curr['Depreciacao']
    
    # Simplificação: Juros zero por enquanto para focar na linkagem operacional
    juros = 0 
    curr['LAIR'] = curr['EBIT'] + juros
    
    curr['Impostos'] = curr['LAIR'] * -tax_rate
    curr['Lucro_Liquido'] = curr['LAIR'] + curr['Impostos']
    
    # --- PASSO B: BALANÇO PARCIAL (Working Capital & Capex) ---
    curr['Contas_Receber'] = curr['Receita'] * ar_pct
    curr['Estoques'] = curr['Receita'] * inv_pct
    curr['Fornecedores'] = curr['Receita'] * ap_pct
    
    capex = curr['Receita'] * capex_pct
    # PPE Final = PPE Inicial + Capex - Depreciação (positiva para cálculo)
    curr['PPE_Liquido'] = prev['PPE_Liquido'] + capex + curr['Depreciacao'] 
    
    # --- PASSO C: DFC (Fluxo de Caixa) - O LINK ---
    # Método Indireto 
    # 1. Operacional
    var_ar = curr['Contas_Receber'] - prev['Contas_Receber'] # Aumento de Ativo = Sai caixa
    var_inv = curr['Estoques'] - prev['Estoques']            # Aumento de Ativo = Sai caixa
    var_ap = curr['Fornecedores'] - prev['Fornecedores']     # Aumento de Passivo = Entra caixa
    
    # CFO: Lucro + Depr (estorno) - Variação Cap Giro
    curr['FCO'] = curr['Lucro_Liquido'] - curr['Depreciacao'] - var_ar - var_inv + var_ap
    
    # 2. Investimento
    curr['FCI'] = -capex # Saída de caixa
    
    # 3. Financiamento (Mantendo dívida constante p/ simplificar)
    curr['FCF_Fin'] = 0 
    
    # Variação Total de Caixa
    curr['Var_Caixa'] = curr['FCO'] + curr['FCI'] + curr['FCF_Fin']
    
    # --- PASSO D: FECHAMENTO DO BALANÇO (O Plug) ---
    # Aqui acontece a mágica: O caixa do BP é atualizado pelo DFC 
    curr['Caixa'] = prev['Caixa'] + curr['Var_Caixa']
    
    # Passivos Financeiros e PL
    curr['Divida_Total'] = prev['Divida_Total'] # Sem amortização no modelo simples
    curr['Capital_Social'] = prev['Capital_Social']
    curr['Lucros_Acumulados'] = prev['Lucros_Acumulados'] + curr['Lucro_Liquido']
    
    # Verificação (Ativo = Passivo + PL) 
    curr['Total_Ativo'] = curr['Caixa'] + curr['Contas_Receber'] + curr['Estoques'] + curr['PPE_Liquido']
    curr['Total_Passivo_PL'] = curr['Fornecedores'] + curr['Divida_Total'] + curr['Capital_Social'] + curr['Lucros_Acumulados']
    curr['Check_Balanço'] = curr['Total_Ativo'] - curr['Total_Passivo_PL']
    
    projections.append(curr)

# Transformando em DataFrame
df = pd.DataFrame(projections).set_index('Ano')

# --- 4. VISUALIZAÇÃO DOS DADOS ---

# Separando as Tabelas para Exibição
dre_cols = ['Receita', 'CMV', 'Lucro_Bruto', 'Despesas_Op', 'Depreciacao', 'EBIT', 'Impostos', 'Lucro_Liquido']
bp_cols = ['Caixa', 'Contas_Receber', 'Estoques', 'PPE_Liquido', 'Total_Ativo', 'Fornecedores', 'Divida_Total', 'Lucros_Acumulados', 'Total_Passivo_PL', 'Check_Balanço']
dfc_cols = ['Lucro_Liquido', 'Depreciacao', 'FCO', 'FCI', 'Var_Caixa', 'Caixa'] # Caixa final para conferência

tab1, tab2, tab3, tab4 = st.tabs(["DRE (Resultado)", "Balanço Patrimonial", "Fluxo de Caixa (Indireto)", "Gráficos"])

with tab1:
    st.subheader("Demonstrativo de Resultados")
    st.dataframe(df[dre_cols].style.format("{:,.2f}"))
    st.info("Nota: DRE apurado por Competência (Receita na venda, não no recebimento).")

with tab2:
    st.subheader("Balanço Patrimonial")
    st.dataframe(df[bp_cols].style.format("{:,.2f}").applymap(lambda x: 'color: red' if x > 1 or x < -1 else 'color: green', subset=['Check_Balanço']))
    
    if df['Check_Balanço'].abs().sum() < 1.0:
        st.success("✅ O Balanço está fechando! (Ativo = Passivo + PL)")
    else:
        st.error("❌ O Balanço não está batendo. Verifique a lógica.")

with tab3:
    st.subheader("Fluxo de Caixa (Método Indireto)")
    st.markdown("Começa no Lucro Líquido, ajusta itens não caixa (Depreciação) e variações de Capital de Giro.")
    st.dataframe(df[dfc_cols].style.format("{:,.2f}"))

with tab4:
    st.subheader("Evolução Financeira")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=df['Receita'], name='Receita'))
    fig.add_trace(go.Bar(x=df.index, y=df['Lucro_Liquido'], name='Lucro Líquido'))
    fig.add_trace(go.Scatter(x=df.index, y=df['Caixa'], name='Saldo de Caixa', mode='lines+markers', line=dict(color='green', width=3)))
    
    st.plotly_chart(fig, use_container_width=True)
