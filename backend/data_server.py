"""Python 数据服务器。

推荐、识图发单、识图寻商品和成交价参考由这个进程提供。
用户、商品、购物车、订单和管理仍由业务服务提供，再由 Java Spring Boot 统一对外。
"""

from app import create_app

app = create_app(role="data")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
