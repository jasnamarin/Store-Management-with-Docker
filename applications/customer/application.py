from datetime import datetime

from flask import Flask, request, jsonify
from applications.configuration import Configuration
from flask_jwt_extended import JWTManager, get_jwt
from sqlalchemy import and_
from applications.utils import role_check

from applications.models import database, Product, Category, ProductCategory, Order, OrderProduct


application = Flask(__name__)
application.config.from_object(Configuration)

jwt = JWTManager(application)


@application.route('/search', methods=['GET'])
@role_check('customer')
def search_products():
    name = request.args.get('name', None)
    category = request.args.get('category', None)

    if name and category:
        # can't use column data directly in and_ call - instead make a list, then unpack it
        categories = Category.query.join(ProductCategory).join(Product).filter(
            and_(*[Category.name.like(f'%{category}%'), Product.name.like(f'%{name}%')])
        ).group_by(Category.id).with_entities(Category.name).all()

        products = Product.query.join(ProductCategory).join(Category).filter(
            and_(*[Category.name.like(f'%{category}%'), Product.name.like(f'%{name}%')])
        ).group_by(Product.id).all()
    elif name:
        categories = Category.query.join(ProductCategory).join(Product).filter(
            *[Product.name.like(f'%{name}%')]
        ).group_by(Category.id).with_entities(Category.name).all()

        products = database.session.query(Product).filter(Product.name.like(f'%{name}%')).all()
    elif category:
        categories = database.session.query(Category).filter(Category.name.like(f'%{category}%')).all()

        products = Product.query.join(ProductCategory).join(Category).filter(
            *[Category.name.like(f'%{category}%')]
        ).group_by(Product.id).all()
    else:
        application.logger.debug('debug log info')
        products = database.session.query(Product).all()
        categories = database.session.query(Category).all()

    product_info = []
    for product in products:
        product_categories = [c.name for c in product.categories]
        product_info.append({
            'categories': product_categories,
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'quantity': product.quantity
        })

    category_info = [c.name for c in categories]

    return jsonify(categories=category_info, products=product_info), 200


@application.route('/order', methods=['POST'])
@role_check('customer')
def place_order():
    requests = request.json.get('requests', [])  # list of product ids and quantities

    if requests is None or len(requests) == 0:
        return jsonify(message='Field requests is missing.'), 400

    additional_claims = get_jwt()
    email = additional_claims['email']

    products = []
    quantities = []
    prices = []
    total_price = 0
    for i in range(len(requests)):
        product_id = requests[i].get('id', '')
        if product_id is None or product_id == '':
            return jsonify(message=f'Product id is missing for request number {i}.'), 400
        product_quantity = requests[i].get('quantity', '')
        if product_quantity is None or product_quantity == '':
            return jsonify(message=f'Product quantity is missing for request number {i}.'), 400
        try:
            if int(product_id) <= 0:
                return jsonify(message=f'Invalid product id for request number {i}.'), 400
        except ValueError:
            return jsonify(message=f'Invalid product id for request number {i}.'), 400
        try:
            if int(product_quantity) <= 0:
                return jsonify(message=f'Invalid product quantity for request number {i}.'), 400
        except ValueError:
            return jsonify(message=f'Invalid product quantity for request number {i}.'), 400

        # check if product with this id exists in database
        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            return jsonify(message=f'Invalid product for request number {i}.'), 400

        products.append(product_id)
        quantities.append(product_quantity)
        price = product.price * product_quantity
        prices.append(price)
        total_price += price

    order = Order(totalPrice=total_price, buyerEmail=email, status='PENDING', timestamp=datetime.today())
    database.session.add(order)
    database.session.commit()

    pending_order = False
    for i in range(len(products)):
        product = Product.query.filter(Product.id == products[i]).first()
        if product.quantity >= quantities[i]:
            product.quantity -= quantities[i]
            order_product = OrderProduct(productId=product.id, orderId=order.id, price=prices[i],
                                         requestedQuantity=quantities[i], receivedQuantity=quantities[i])
        else:
            pending_order = True
            order_product = OrderProduct(productId=product.id, orderId=order.id, price=prices[i],
                                         requestedQuantity=quantities[i], receivedQuantity=product.quantity)
            product.quantity = 0
        database.session.add(order_product)
        database.session.commit()

    if not pending_order:
        order.status = 'COMPLETE'
        database.session.commit()

    return jsonify(id=order.id), 200


@application.route('/status', methods=['GET'])
@role_check('customer')
def order_status():
    additional_claims = get_jwt()
    email = additional_claims['email']

    return_orders = []  # list of dictionaries
    orders = Order.query.filter(Order.buyerEmail == email).all()
    for order in orders:
        product_list = OrderProduct.query.filter(OrderProduct.orderId == order.id).all()
        return_products = []
        for product in product_list:
            product_name = Product.query.filter(Product.id == product.productId).first().name
            product_categories = ProductCategory.query.filter(ProductCategory.productId == product.productId).all()
            return_categories = [Category.query.filter(Category.id == category.categoryId).first().name for category in product_categories]

            return_products.append({
                'categories': return_categories,
                'name': product_name,
                'price': product.price,
                'received': product.receivedQuantity,
                'requested': product.requestedQuantity
            })

        return_orders.append({
            'products': return_products,
            'price': order.totalPrice,
            'status': order.status,
            'timestamp': order.timestamp
        })

    return jsonify(orders=return_orders), 200


if __name__ == '__main__':
    database.init_app(application)
    application.run(debug=True, host='0.0.0.0', port=5000)
