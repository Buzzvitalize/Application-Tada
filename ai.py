from models import db, OrderItem
from sqlalchemy import func


def recommend_products(limit: int = 5):
    """Return top-selling product names as basic recommendations."""
    results = (
        db.session.query(OrderItem.product_name)
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )
    return [r[0] for r in results]
