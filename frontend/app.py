import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.models.database import DatabaseManager
from backend.data.data_loader import DataLoader

# Page config
st.set_page_config(
    page_title="Wealth Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .big-number {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .positive {
        color: #2ca02c;
    }
    .negative {
        color: #d62728;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_user_data(user_id: str):
    """Load user data with caching"""
    db = DatabaseManager()
    investments_df = db.get_user_investments(user_id)
    cash_flows_df = db.get_user_cash_flows(user_id)
    return investments_df, cash_flows_df

def calculate_metrics(investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame):
    """Calculate key metrics"""
    metrics = {}
    
    if not investments_df.empty:
        # Total invested
        metrics['total_invested'] = investments_df['invested_amount'].sum()
        
        # Platform breakdown
        platform_breakdown = investments_df.groupby('platform')['invested_amount'].sum()
        metrics['platform_breakdown'] = platform_breakdown
        
        # Status breakdown
        status_counts = investments_df['status'].value_counts()
        metrics['status_breakdown'] = status_counts
        
        # Asset class breakdown
        asset_breakdown = investments_df.groupby('asset_class')['invested_amount'].sum()
        metrics['asset_breakdown'] = asset_breakdown
    
    if not cash_flows_df.empty:
        # Total returns
        cash_flows_df['transaction_date'] = pd.to_datetime(cash_flows_df['transaction_date'])
        
        inflows = cash_flows_df[cash_flows_df['flow_direction'] == 'in']['net_amount'].sum()
        outflows = abs(cash_flows_df[cash_flows_df['flow_direction'] == 'out']['net_amount'].sum())
        
        metrics['total_inflows'] = inflows
        metrics['total_outflows'] = outflows
        metrics['net_cash_flow'] = inflows - outflows
        
        # Monthly cash flows
        cash_flows_df['year_month'] = cash_flows_df['transaction_date'].dt.to_period('M')
        monthly_flows = cash_flows_df.groupby('year_month')['net_amount'].sum()
        metrics['monthly_flows'] = monthly_flows
    
    return metrics

def main():
    st.title("💰 Wealth Dashboard")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        
        # For development - simulate user
        user_id = st.text_input("User ID (for dev)", value="demo-user-123")
        
        # Data loading section
        st.subheader("Data Management")
        
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.success("Data refreshed!")
        
        uploaded_file = st.file_uploader(
            "Upload Platform File", 
            type=['xlsx'],
            help="Upload Excel file from crowdfunding platform"
        )
        
        platform = st.selectbox(
            "Select Platform",
            ["LBP", "PretUp", "BienPreter", "Homunity"]
        )
        
        if uploaded_file and st.button("Load Data"):
            try:
                # Save uploaded file temporarily
                with open(f"temp_{uploaded_file.name}", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Load data
                loader = DataLoader()
                success = loader.load_platform_data(
                    f"temp_{uploaded_file.name}", 
                    platform.lower(), 
                    user_id
                )
                
                if success:
                    st.success(f"✅ Data loaded from {platform}!")
                    st.cache_data.clear()  # Clear cache to reload data
                    os.remove(f"temp_{uploaded_file.name}")  # Cleanup
                else:
                    st.error("❌ Failed to load data")
                    
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Main content
    try:
        # Load data
        investments_df, cash_flows_df = load_user_data(user_id)
        
        if investments_df.empty and cash_flows_df.empty:
            st.warning("No data found. Please upload some files using the sidebar.")
            st.info("""
            **To get started:**
            1. Select a platform (LBP, PretUp, BienPreter, Homunity)
            2. Upload your Excel file from that platform
            3. Click 'Load Data'
            """)
            return
        
        # Calculate metrics
        metrics = calculate_metrics(investments_df, cash_flows_df)
        
        # Key Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_invested = metrics.get('total_invested', 0)
            st.metric(
                "💸 Total Invested",
                f"€{total_invested:,.0f}",
                help="Total amount invested across all platforms"
            )
        
        with col2:
            total_inflows = metrics.get('total_inflows', 0)
            st.metric(
                "💰 Total Returns",
                f"€{total_inflows:,.0f}",
                help="Total returns received"
            )
        
        with col3:
            net_cash_flow = metrics.get('net_cash_flow', 0)
            delta_color = "normal" if net_cash_flow >= 0 else "inverse"
            st.metric(
                "📊 Net Performance",
                f"€{net_cash_flow:,.0f}",
                f"{(net_cash_flow/total_invested)*100:.1f}%" if total_invested > 0 else "0%",
                delta_color=delta_color
            )
        
        with col4:
            active_projects = len(investments_df[investments_df['status'] == 'active']) if not investments_df.empty else 0
            st.metric(
                "🏗️ Active Projects",
                active_projects
            )
        
        st.markdown("---")
        
        # Charts Row 1
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Investment by Platform")
            if 'platform_breakdown' in metrics:
                fig = px.pie(
                    values=metrics['platform_breakdown'].values,
                    names=metrics['platform_breakdown'].index,
                    title="Platform Allocation"
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No investment data available")
        
        with col2:
            st.subheader("🎯 Project Status")
            if 'status_breakdown' in metrics:
                status_colors = {
                    'active': '#2ca02c',
                    'completed': '#1f77b4', 
                    'delayed': '#ff7f0e',
                    'defaulted': '#d62728',
                    'in_procedure': '#9467bd'
                }
                
                fig = px.bar(
                    x=metrics['status_breakdown'].index,
                    y=metrics['status_breakdown'].values,
                    title="Projects by Status",
                    color=metrics['status_breakdown'].index,
                    color_discrete_map=status_colors
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No status data available")
        
        # Charts Row 2
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Monthly Cash Flows")
            if 'monthly_flows' in metrics and not metrics['monthly_flows'].empty:
                monthly_flows = metrics['monthly_flows']
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=[str(period) for period in monthly_flows.index],
                    y=monthly_flows.values,
                    marker_color=['green' if x > 0 else 'red' for x in monthly_flows.values],
                    name="Monthly Flow"
                ))
                
                fig.update_layout(
                    title="Monthly Cash Flow Trend",
                    xaxis_title="Month",
                    yaxis_title="Amount (€)",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No cash flow data available")
        
        with col2:
            st.subheader("🏠 Asset Class Distribution")
            if 'asset_breakdown' in metrics:
                fig = px.donut(
                    values=metrics['asset_breakdown'].values,
                    names=metrics['asset_breakdown'].index,
                    title="Asset Class Allocation"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No asset class data available")
        
        # Data Tables
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["📈 Investments", "💸 Cash Flows"])
        
        with tab1:
            st.subheader("Investment Portfolio")
            if not investments_df.empty:
                # Format the dataframe for display
                display_df = investments_df[[
                    'platform', 'project_name', 'invested_amount', 
                    'annual_rate', 'investment_date', 'status'
                ]].copy()
                
                display_df['invested_amount'] = display_df['invested_amount'].apply(lambda x: f"€{x:,.0f}")
                display_df['annual_rate'] = display_df['annual_rate'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No investment data to display")
        
        with tab2:
            st.subheader("Recent Cash Flows")
            if not cash_flows_df.empty:
                # Show recent transactions
                recent_flows = cash_flows_df.sort_values('transaction_date', ascending=False).head(20)
                
                display_flows = recent_flows[[
                    'transaction_date', 'flow_type', 'gross_amount', 
                    'flow_direction', 'description'
                ]].copy()
                
                display_flows['gross_amount'] = display_flows['gross_amount'].apply(lambda x: f"€{x:,.2f}")
                
                st.dataframe(
                    display_flows,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No cash flow data to display")
        
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")
        st.info("Please check your database connection and data.")

if __name__ == "__main__":
    main()