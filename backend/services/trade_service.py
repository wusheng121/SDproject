"""购物车、订单、模拟支付与评价。"""

from sqlalchemy import and_

from extensions import db
from models import Cart, Order, OrderItem, Product, Review, User, UserBehavior
from services.cache_store import invalidate_product


class TradeError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _fail(code: str, message: str, status: int = 400):
    db.session.rollback()
    raise TradeError(code, message, status)


def _product(product_id: int) -> Product:
    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        _fail("VALIDATION_ERROR", "商品无效", 422)
    product = db.session.get(Product, product_id)
    if not product:
        _fail("NOT_FOUND", "商品不存在", 404)
    return product


def _pending_hold(product_id: int) -> bool:
    return (
        db.session.query(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(OrderItem.product_id == product_id, Order.status == "pending")
        .first()
        is not None
    )


def _assert_purchasable(user: User, product: Product):
    if product.seller_id == user.id:
        _fail("TRADE_OWN_PRODUCT", "不能购买自己发布的商品", 403)
    if product.status != "approved":
        _fail("TRADE_UNAVAILABLE", "商品未上架或已售出", 409)
    if _pending_hold(product.id):
        _fail("TRADE_UNAVAILABLE", "该商品已有待支付订单", 409)


def _record_once(user_id: int, product_id: int, behavior_type: str, value: int | None = None):
    existing = UserBehavior.query.filter_by(
        user_id=user_id, product_id=product_id, behavior_type=behavior_type
    ).first()
    if existing:
        return
    db.session.add(
        UserBehavior(
            user_id=user_id,
            product_id=product_id,
            behavior_type=behavior_type,
            value=value,
        )
    )


def _cart_item(cart: Cart) -> dict:
    product = db.session.get(Product, cart.product_id)
    price = float(product.price) if product else 0
    quantity = cart.quantity or 1
    seller = None
    if product and product.seller:
        seller = {"id": product.seller.id, "username": product.seller.username}
    return {
        "id": cart.id,
        "product_id": cart.product_id,
        "name": product.name if product else "商品已删除",
        "price": price,
        "condition": product.condition if product else None,
        "image_url": product.image_url if product else None,
        "status": product.status if product else None,
        "quantity": quantity,
        "line_amount": round(price * quantity, 2),
        "seller": seller,
    }


def list_cart(user: User) -> dict:
    carts = Cart.query.filter_by(user_id=user.id).order_by(Cart.created_at.desc()).all()
    items = [_cart_item(cart) for cart in carts]
    total = round(sum(item["line_amount"] for item in items), 2)
    return {"items": items, "total_amount": total}


def add_to_cart(user: User, product_id: int) -> tuple[dict, bool]:
    product = _product(product_id)
    _assert_purchasable(user, product)
    existing = Cart.query.filter_by(user_id=user.id, product_id=product.id).first()
    if existing:
        return _cart_item(existing), False
    cart = Cart(user_id=user.id, product_id=product.id, quantity=1)
    db.session.add(cart)
    _record_once(user.id, product.id, "add_cart", value=1)
    db.session.commit()
    return _cart_item(cart), True


def remove_from_cart(user: User, product_id: int) -> None:
    product = _product(product_id)
    cart = Cart.query.filter_by(user_id=user.id, product_id=product.id).first()
    if not cart:
        _fail("NOT_FOUND", "购物车中没有该商品", 404)
    db.session.delete(cart)
    db.session.commit()


def _own_order(user: User, order_id: int) -> Order:
    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        _fail("VALIDATION_ERROR", "订单无效", 422)
    order = db.session.get(Order, order_id)
    if not order or order.buyer_id != user.id:
        _fail("NOT_FOUND", "订单不存在", 404)
    return order


def _order_public(order: Order) -> dict:
    items = OrderItem.query.filter_by(order_id=order.id).all()
    product_ids = [item.product_id for item in items]
    products = {}
    if product_ids:
        products = {
            product.id: product
            for product in Product.query.filter(Product.id.in_(product_ids)).all()
        }
    reviews = {
        review.product_id: review
        for review in Review.query.filter_by(order_id=order.id, user_id=order.buyer_id).all()
    }
    item_rows = []
    for item in items:
        product = products.get(item.product_id)
        review = reviews.get(item.product_id)
        item_rows.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": product.name if product else "商品已删除",
                "image_url": product.image_url if product else None,
                "quantity": item.quantity,
                "price": item.price,
                "line_amount": round(float(item.price) * item.quantity, 2),
                "reviewed": review is not None,
                "review": (
                    {"id": review.id, "score": review.score, "comment": review.comment}
                    if review
                    else None
                ),
            }
        )
    return {
        "id": order.id,
        "status": order.status,
        "total_amount": order.total_amount,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": item_rows,
    }


def list_orders(user: User) -> list[dict]:
    orders = (
        Order.query.filter_by(buyer_id=user.id).order_by(Order.created_at.desc()).all()
    )
    return [_order_public(order) for order in orders]


def create_order(user: User, product_ids: list | None = None) -> dict:
    carts = Cart.query.filter_by(user_id=user.id).all()
    if product_ids is not None:
        try:
            wanted = {int(product_id) for product_id in product_ids}
        except (TypeError, ValueError):
            _fail("VALIDATION_ERROR", "商品无效", 422)
        if not wanted:
            _fail("VALIDATION_ERROR", "请选择要结算的商品", 422)
        carts = [cart for cart in carts if cart.product_id in wanted]
        if len(carts) != len(wanted):
            _fail("VALIDATION_ERROR", "购物车中没有选中的商品", 422)
    if not carts:
        _fail("VALIDATION_ERROR", "购物车是空的", 422)

    lines = []
    for cart in carts:
        product = db.session.get(Product, cart.product_id)
        if not product:
            _fail("NOT_FOUND", "商品不存在", 404)
        _assert_purchasable(user, product)
        lines.append((cart, product))

    total = round(sum(float(product.price) * (cart.quantity or 1) for cart, product in lines), 2)
    order = Order(buyer_id=user.id, status="pending", total_amount=total)
    db.session.add(order)
    db.session.flush()
    for cart, product in lines:
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=cart.quantity or 1,
                price=float(product.price),
            )
        )
        db.session.delete(cart)
    db.session.commit()
    return _order_public(order)


def pay_order(user: User, order_id: int) -> dict:
    order = _own_order(user, order_id)
    if order.status != "pending":
        _fail("ORDER_STATE", "只有待支付订单可以支付", 409)
    items = OrderItem.query.filter_by(order_id=order.id).all()
    if not items:
        _fail("VALIDATION_ERROR", "订单没有商品", 422)
    products = []
    for item in items:
        product = db.session.get(Product, item.product_id)
        if not product or product.status != "approved":
            _fail("TRADE_UNAVAILABLE", "有商品已售出或已下架，请取消订单", 409)
        products.append(product)
    order.status = "paid"
    category_names = []
    for product in products:
        product.status = "sold"
        category_names.extend(link.category.name for link in product.categories if link.category)
        Cart.query.filter_by(product_id=product.id).delete(synchronize_session=False)
        _record_once(user.id, product.id, "order", value=1)
    db.session.commit()
    for product in products:
        invalidate_product(product.id, category_names)
    return _order_public(order)


def cancel_order(user: User, order_id: int) -> dict:
    order = _own_order(user, order_id)
    if order.status != "pending":
        _fail("ORDER_STATE", "只有待支付订单可以取消", 409)
    items = OrderItem.query.filter_by(order_id=order.id).all()
    order.status = "cancelled"
    for item in items:
        product = db.session.get(Product, item.product_id)
        if not product or product.status != "approved":
            continue
        if Cart.query.filter_by(user_id=user.id, product_id=product.id).first():
            continue
        db.session.add(
            Cart(user_id=user.id, product_id=product.id, quantity=item.quantity or 1)
        )
    db.session.commit()
    return _order_public(order)


def _parse_score(score) -> int:
    if isinstance(score, bool) or not isinstance(score, int):
        _fail("VALIDATION_ERROR", "评分必须是 1 到 5 的整数", 422)
    if not 1 <= score <= 5:
        _fail("VALIDATION_ERROR", "评分必须是 1 到 5 的整数", 422)
    return score


def review_public(review: Review) -> dict:
    author = db.session.get(User, review.user_id)
    return {
        "id": review.id,
        "order_id": review.order_id,
        "product_id": review.product_id,
        "score": review.score,
        "comment": review.comment or "",
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "user": {"id": author.id, "username": author.username} if author else None,
    }


def create_review(user: User, order_id: int, product_id: int, score, comment) -> dict:
    order = _own_order(user, order_id)
    if order.status != "paid":
        _fail("ORDER_STATE", "支付完成后才能评价", 409)
    product = _product(product_id)
    item = OrderItem.query.filter_by(order_id=order.id, product_id=product.id).first()
    if not item:
        _fail("NOT_FOUND", "订单中没有该商品", 404)
    score = _parse_score(score)
    text = (comment or "").strip()
    if len(text) > 500:
        _fail("VALIDATION_ERROR", "评价不能超过 500 字", 422)
    existing = Review.query.filter_by(
        user_id=user.id, product_id=product.id, order_id=order.id
    ).first()
    if existing:
        _fail("REVIEW_EXISTS", "该商品已经评价过", 409)
    review = Review(
        user_id=user.id,
        product_id=product.id,
        order_id=order.id,
        score=score,
        comment=text or None,
    )
    db.session.add(review)
    _record_once(user.id, product.id, "review", value=score)
    db.session.commit()
    return review_public(review)


def find_reviewable_order_id(user: User, product_id: int) -> int:
    product = _product(product_id)
    row = (
        db.session.query(Order.id)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .outerjoin(
            Review,
            and_(
                Review.order_id == Order.id,
                Review.product_id == product.id,
                Review.user_id == user.id,
            ),
        )
        .filter(
            Order.buyer_id == user.id,
            Order.status == "paid",
            OrderItem.product_id == product.id,
            Review.id.is_(None),
        )
        .order_by(Order.id.desc())
        .first()
    )
    if not row:
        _fail("ORDER_STATE", "没有可评价的已支付订单", 409)
    return row[0]


def list_my_reviews(user: User) -> list[dict]:
    reviews = (
        Review.query.filter_by(user_id=user.id).order_by(Review.created_at.desc()).all()
    )
    return [review_public(review) for review in reviews]


def list_product_reviews(product_id: int) -> list[dict]:
    product = _product(product_id)
    reviews = (
        Review.query.filter_by(product_id=product.id).order_by(Review.created_at.desc()).all()
    )
    return [review_public(review) for review in reviews]
