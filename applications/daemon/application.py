import time

from flask import Flask
from applications.configuration import Configuration
from redis import Redis
import json

from applications.models import database, Category, ProductCategory, OrderProduct, Product, Order

application = Flask(__name__)
application.config.from_object(Configuration)

# checks if data sent by warehouse is valid

with application.app_context() as context:
    database.init_app(application)
    with Redis(host=Configuration.REDIS_HOST) as redis:
        channel = redis.pubsub()
        channel.subscribe(Configuration.REDIS_MESSAGE_CHANNEL)
        application.logger.debug('subscribed to redis message channel')
        #start_time = time.time()
        #while (time.time() - start_time) < 180:  # 3 min
        while True:
            message = channel.get_message()
            application.logger.debug(f'received message: {message}')
            if message is not None and message['data'] != 1:
                batch = json.loads(message['data'].decode("utf-8"))
                application.logger.debug(f'batch = {batch}')
                products = []
                for product in batch.get('products'):
                    name = product.get('name')
                    categories_string = product.get('categories')
                    categories = categories_string.split('|')
                    application.logger.debug(f'categories: {categories}')  # should be a list of category names
                    delivery_quantity = int(product.get('quantity'))
                    delivery_price = float(product.get('price'))

                    old_product = Product.query.filter(Product.name == name).first()
                    if old_product is None:
                        # product doesn't already exist in database
                        # add product + all new product categories to DB
                        new_product = Product(name=name, quantity=delivery_quantity, price=delivery_price)
                        database.session.add(new_product)
                        database.session.commit()
                        for c_name in categories:
                            existing_category = Category.query.filter(Category.name == c_name).first()
                            if existing_category is None:
                                category = Category(name=c_name)
                                database.session.add(category)
                                database.session.commit()
                                product_category = ProductCategory(productId=new_product.id, categoryId=category.id)
                            else:
                                product_category = ProductCategory(productId=new_product.id, categoryId=existing_category.id)

                            database.session.add(product_category)
                            database.session.commit()
                    elif set(categories) == set(old_product.categories):
                        # product already present in database and all categories correct
                        # update price and quantity
                        old_quantity = old_product.quantity
                        old_price = old_product.price
                        new_price = (old_quantity * old_price + delivery_quantity * delivery_price) \
                                    / (old_quantity + delivery_quantity)

                        # database.session.query(Product).filter(Product.id == old_product.id).update(
                        #     {'quantity': old_quantity + delivery_quantity, 'price': new_price},
                        #     synchronize_session='fetch')
                        old_product.quantity += delivery_quantity
                        old_product.price = new_price
                        database.session.commit()
                    else:
                        # if there are missing or redundant categories for an existing product
                        # ignore new info
                        continue

                    application.logger.debug('products updated')
                    orders = Order.query.filter(Order.status == 'PENDING').join(OrderProduct).join(Product) \
                        .filter(Product.name == name).group_by(Order.id).order_by(Order.timestamp)
                    for order in orders:
                        application.logger.debug(f'order: {order}')
                        existing_product = Product.query.filter(Product.name == name)
                        order_product = OrderProduct.query.and_(filter(OrderProduct.orderId == order.id),
                                                                filter(OrderProduct.productId == existing_product.id)).first()
                        required = order_product.requested_quantity - order_product.received_quantity

                        if existing_product.quantity >= required:
                            existing_product.quantity -= required
                            order_product.received_quantity += required

                        if order_product.requested_quantity == order_product.received_quantity:
                            # check if order is still pending
                            pending_products = OrderProduct.query.and_(
                                filter(OrderProduct.orderId == order.id),
                                filter(OrderProduct.requestedQuantity > OrderProduct.receivedQuantity)).all()
                            if not pending_products or len(pending_products) == 0:
                                order.status = 'COMPLETE'
                                database.session.commit()
                        else:
                            # the order requires more of the new product
                            # but there is none left - so break
                            break
                    application.logger.debug('orders updated')
