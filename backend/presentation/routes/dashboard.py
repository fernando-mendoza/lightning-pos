from fastapi import APIRouter
from pydantic import BaseModel

from application.get_dashboard_summary import get_dashboard_summary
from infrastructure.db.sale_repo_sqlite import SaleRepoSQLite

router = APIRouter()
sale_repo = SaleRepoSQLite()


class DaySummary(BaseModel):
    total_mxn: float
    total_sats: int
    count: int


class DailyEntry(DaySummary):
    date: str


class TopProduct(BaseModel):
    name: str
    quantity: int
    total_mxn: float


class DashboardSummaryResponse(BaseModel):
    today: DaySummary
    last_7_days: list[DailyEntry]
    top_products: list[TopProduct]


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_summary():
    data = await get_dashboard_summary(sale_repo)
    return DashboardSummaryResponse(**data)
