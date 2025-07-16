# backend/api.py

"""
Main API file for the Wealth Dashboard project.
This file initializes the FastAPI application and defines the API endpoints.
"""

import os
from fastapi import FastAPI, Depends, HTTPException, Security, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd

# Import the calculator and models
# Robust import for different execution contexts
try:
    from backend.analytics.patrimoine_calculator import PatrimoineCalculator
    from backend.models.models import InvestmentInDB, CashFlowInDB
except ImportError:
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    from backend.analytics.patrimoine_calculator import PatrimoineCalculator
    from backend.models.models import InvestmentInDB, CashFlowInDB


# --- Configuration and Security ---

# For local dev, you might need to load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("SUPABASE_KEY")
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    """Dependency to validate the API key."""
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured on server.")
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=403,
            detail="Could not validate credentials",
        )

# --- Pydantic Models for API Responses ---

class GlobalKpisResponse(BaseModel):
    patrimoine_total: float
    plus_value_nette: float
    total_apports: float
    tri_global_brut: float
    tri_global_net: float
    herfindahl_index: float

class PlatformKpisResponse(BaseModel):
    capital_investi_encours: Tuple[float, float]
    plus_value_realisee_nette: float
    tri_brut: float
    tri_net: float
    interets_bruts_recus: float
    impots_et_frais: float
    nombre_projets: int
    total_invested_platform: float
    total_repaid_platform: float
    repayment_rate_platform: float
    projected_liquidity_6m: float
    projected_liquidity_12m: float
    projected_liquidity_24m: float
    weighted_average_duration: float
    duration_distribution: Dict[str, float]
    reinvestment_rate: float
    unrealized_gain_loss: float
    total_gain_net_platform: float
    maturity_indicator: float

class EvolutionData(BaseModel):
    apports_cumules: Dict[str, Optional[float]]
    patrimoine_total_evolution: Dict[str, Optional[float]]
    benchmark: Dict[str, Optional[float]]

class ChartsResponse(BaseModel):
    repartition_data: Dict[str, float]
    evolution_data: EvolutionData

# --- FastAPI Application Initialization ---

app = FastAPI(
    title="Expert Patrimoine API",
    description="API for the advanced wealth management dashboard.",
    version="1.0.0",
)

# --- API Endpoints ---

@app.get("/api/v1/status", tags=["Health"])
def get_status():
    """
    Check the status of the API.
    Returns a simple message to confirm the API is running.
    """
    return {"status": "ok", "message": "Expert Patrimoine API is running!"}

@app.get("/api/v1/kpis/global", response_model=GlobalKpisResponse, tags=["KPIs"])
def get_global_kpis_endpoint(user_id: str, api_key: str = Depends(get_api_key)):
    """
    Get global Key Performance Indicators (KPIs) for a user.
    """
    try:
        calculator = PatrimoineCalculator(user_id=user_id)
        kpis = calculator.get_global_kpis()
        return kpis
    except Exception as e:
        # Log the exception for debugging
        print(f"Error in get_global_kpis_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/kpis/platform/{platform_name}", response_model=PlatformKpisResponse, tags=["KPIs"])
def get_platform_kpis_endpoint(platform_name: str, user_id: str, api_key: str = Depends(get_api_key)):
    """
    Get Key Performance Indicators (KPIs) for a specific platform.
    """
    try:
        calculator = PatrimoineCalculator(user_id=user_id)
        platform_details = calculator.get_platform_details()
        if platform_name in platform_details:
            return platform_details[platform_name]
        else:
            raise HTTPException(status_code=404, detail="Platform not found")
    except Exception as e:
        print(f"Error in get_platform_kpis_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/investments", response_model=List[InvestmentInDB], tags=["Data"])
def get_investments_endpoint(
    user_id: str,
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    api_key: str = Depends(get_api_key)
):
    """
    Get a list of investments, with optional filtering.
    """
    try:
        calculator = PatrimoineCalculator(user_id=user_id)
        # Make a copy to avoid modifying the original dataframe
        investments_df = calculator.investments_df.copy()

        if platform:
            investments_df = investments_df[investments_df['platform'] == platform]

        if status:
            investments_df = investments_df[investments_df['status'] == status]

        # Handle NaN values before converting to dict, as they are not valid JSON
        investments_df.fillna(value="", inplace=True)
        return investments_df.to_dict(orient='records')
    except Exception as e:
        print(f"Error in get_investments_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/cashflows", response_model=List[CashFlowInDB], tags=["Data"])
def get_cashflows_endpoint(
    user_id: str,
    platform: Optional[str] = Query(None),
    api_key: str = Depends(get_api_key)
):
    """
    Get a list of cash flows, with optional filtering.
    """
    try:
        calculator = PatrimoineCalculator(user_id=user_id)
        cash_flows_df = calculator.cash_flows_df.copy()

        if platform:
            cash_flows_df = cash_flows_df[cash_flows_df['platform'] == platform]
        
        cash_flows_df.fillna(value="", inplace=True)
        return cash_flows_df.to_dict(orient='records')
    except Exception as e:
        print(f"Error in get_cashflows_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/charts", response_model=ChartsResponse, tags=["Charts"])
def get_charts_endpoint(
    user_id: str,
    api_key: str = Depends(get_api_key)
):
    """
    Get data for performance and concentration charts.
    """
    try:
        calculator = PatrimoineCalculator(user_id=user_id)
        charts_data = calculator.get_charts_data()

        # Convert pandas Series to dictionary with proper date formatting
        def series_to_dict(s: pd.Series) -> Dict[str, Optional[float]]:
            if s.empty:
                return {}
            # Convert timestamp index to string 'YYYY-MM-DD'
            s.index = s.index.strftime('%Y-%m-%d')
            # Replace NaN with None for JSON compatibility
            return s.where(pd.notna(s), None).to_dict()

        charts_data['evolution_data']['apports_cumules'] = series_to_dict(charts_data['evolution_data']['apports_cumules'])
        charts_data['evolution_data']['patrimoine_total_evolution'] = series_to_dict(charts_data['evolution_data']['patrimoine_total_evolution'])
        
        # Benchmark can be a DataFrame, handle it
        benchmark_series = charts_data['evolution_data']['benchmark']
        if isinstance(benchmark_series, pd.DataFrame) and not benchmark_series.empty:
             # Assuming the first column is the one we want
            benchmark_series = benchmark_series.iloc[:, 0]

        charts_data['evolution_data']['benchmark'] = series_to_dict(benchmark_series)

        return charts_data
    except Exception as e:
        print(f"Error in get_charts_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# To run this API locally:
# uvicorn backend.api:app --reload