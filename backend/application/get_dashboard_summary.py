from datetime import date, timedelta

from domain.ports.sale_repository import SaleRepository


async def get_dashboard_summary(sale_repo: SaleRepository) -> dict:
    today = date.today()
    start = today - timedelta(days=6)
    start_str = start.isoformat()
    today_str = today.isoformat()

    raw_days = await sale_repo.summary_by_day(start_str, today_str)
    by_date = {d["date"]: d for d in raw_days}

    last_7_days = []
    for i in range(7):
        day = start + timedelta(days=i)
        key = day.isoformat()
        entry = by_date.get(key)
        last_7_days.append(
            {
                "date": key,
                "total_mxn": entry["total_mxn"] if entry else 0.0,
                "total_sats": entry["total_sats"] if entry else 0,
                "count": entry["count"] if entry else 0,
            }
        )

    today_entry = by_date.get(today_str)
    today_summary = {
        "total_mxn": today_entry["total_mxn"] if today_entry else 0.0,
        "total_sats": today_entry["total_sats"] if today_entry else 0,
        "count": today_entry["count"] if today_entry else 0,
    }

    top_products = await sale_repo.top_products(start_str, today_str, limit=3)

    return {
        "today": today_summary,
        "last_7_days": last_7_days,
        "top_products": top_products,
    }
