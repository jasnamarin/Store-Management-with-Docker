from flask import Flask, request, jsonify, Response
from applications.configuration import Configuration
from flask_jwt_extended import JWTManager
from applications.utils import role_check
from sqlalchemy import func

from applications.models import database, Product, OrderProduct, Category, ProductCategory

application = Flask(__name__)
application.config.from_object(Configuration)

jwt = JWTManager(application)


@application.route('/productStatistics', methods=['GET'])
@role_check('administrator')
def product_statistics():
    statistics = []

    products = Product.query.all()
    application.logger.debug(f'products queried: {products}')
    for product in products:
        product_orders = OrderProduct.query.filter(OrderProduct.productId == product.id).all()
        sold = 0
        waiting = 0
        application.logger.debug(f'orders which contain this product: {product_orders}')
        if product_orders:
            for order in product_orders:
                waiting += order.requestedQuantity - order.receivedQuantity
                sold += order.requestedQuantity

        statistics += {
            'name': product.name,
            'sold': sold,
            'waiting': waiting
        }
        application.logger.debug(f'stats to return: {statistics}')

    return jsonify(statistics=statistics), 200


@application.route('/categoryStatistics', methods=['GET'])
@role_check('administrator')
def category_statistics():
    categories = Category.query.outerjoin(ProductCategory).outerjoin(Product).outerjoin(OrderProduct) \
        .group_by(Category.id).order_by(func.sum(OrderProduct.requestedQuantity).desc()).order_by(Category.name)

    application.logger.debug(f'categories queried: {categories}')
    statistics = [category.name for category in categories]
    application.logger.debug(f'stats about these categories: {statistics}')
    return jsonify(statistics=statistics), 200


if __name__ == '__main__':
    database.init_app(application)
    application.run(debug=True, host='0.0.0.0', port=5003)
