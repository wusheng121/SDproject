from flask import Blueprint, request

from auth import login_required
from services.trade_service import (
    TradeError,
    add_to_cart,
    cancel_order,
    create_order,
    create_review,
    list_cart,
    list_orders,
    list_product_reviews,
    pay_order,
    remove_from_cart,
)
from utils.response import api_error, api_ok

trade_bp = Blueprint("trade_bp", __name__, url_prefix="/api/v1")


def _trade_call(fn):
    try:
        return fn()
    except TradeError as exc:
        return api_error(exc.code, exc.message, exc.status)


@trade_bp.get("/cart")
@login_required
def get_cart(user):
    return _trade_call(lambda: api_ok(list_cart(user)))


@trade_bp.post("/cart")
@login_required
def post_cart(user):
    payload = request.get_json(silent=True) or {}

    def action():
        item, created = add_to_cart(user, payload.get("product_id"))
        return api_ok({"item": item, "created": created}, status=201 if created else 200)

    return _trade_call(action)


@trade_bp.delete("/cart/<int:product_id>")
@login_required
def delete_cart_item(user, product_id):
    return _trade_call(lambda: (remove_from_cart(user, product_id), api_ok({"removed": True}))[1])


@trade_bp.get("/orders")
@login_required
def get_orders(user):
    return _trade_call(lambda: api_ok({"items": list_orders(user)}))


@trade_bp.post("/orders")
@login_required
def post_order(user):
    payload = request.get_json(silent=True) or {}
    product_ids = payload.get("product_ids")
    return _trade_call(lambda: api_ok(create_order(user, product_ids), status=201))


@trade_bp.post("/orders/<int:order_id>/pay")
@login_required
def post_pay(user, order_id):
    return _trade_call(lambda: api_ok(pay_order(user, order_id)))


@trade_bp.post("/orders/<int:order_id>/cancel")
@login_required
def post_cancel(user, order_id):
    return _trade_call(lambda: api_ok(cancel_order(user, order_id)))


@trade_bp.post("/orders/<int:order_id>/reviews")
@login_required
def post_review(user, order_id):
    payload = request.get_json(silent=True) or {}
    return _trade_call(
        lambda: api_ok(
            create_review(
                user,
                order_id,
                payload.get("product_id"),
                payload.get("score"),
                payload.get("comment"),
            ),
            status=201,
        )
    )


@trade_bp.get("/products/<int:product_id>/reviews")
def get_product_reviews(product_id):
    return _trade_call(lambda: api_ok({"items": list_product_reviews(product_id)}))
