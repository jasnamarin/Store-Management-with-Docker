from flask_sqlalchemy import SQLAlchemy

database = SQLAlchemy()


class ProductCategory(database.Model):
    __tablename__ = 'product_category'
    id = database.Column(database.Integer, primary_key=True)

    productId = database.Column(database.Integer, database.ForeignKey('products.id'), nullable=False)
    categoryId = database.Column(database.Integer, database.ForeignKey('categories.id'), nullable=False)


class OrderProduct(database.Model):
    __tablename__ = 'order_product'
    id = database.Column(database.Integer, primary_key=True)

    orderId = database.Column(database.Integer, database.ForeignKey('orders.id'), nullable=False)
    productId = database.Column(database.Integer, database.ForeignKey('products.id'), nullable=False)

    price = database.Column(database.Float, nullable=False)
    requestedQuantity = database.Column(database.Integer, nullable=False)
    receivedQuantity = database.Column(database.Integer, nullable=False)


class Category(database.Model):
    __tablename__ = 'categories'
    id = database.Column(database.Integer, primary_key=True)

    name = database.Column(database.String(256), nullable=False)

    products = database.relationship('Product', secondary=ProductCategory.__table__,
                                     back_populates='categories')


class Product(database.Model):
    __tablename__ = 'products'
    id = database.Column(database.Integer, primary_key=True)

    name = database.Column(database.String(256), nullable=False)
    price = database.Column(database.Float, nullable=False)
    quantity = database.Column(database.Integer, nullable=False)

    categories = database.relationship('Category', secondary=ProductCategory.__table__,
                                       back_populates='products')
    orders = database.relationship('Order', secondary=OrderProduct.__table__,
                                   back_populates='products')


class Order(database.Model):
    __tablename__ = 'orders'
    id = database.Column(database.Integer, primary_key=True)

    totalPrice = database.Column(database.Float, nullable=False)
    buyerEmail = database.Column(database.String(256), nullable=False)
    status = database.Column(database.String(256), nullable=False)
    timestamp = database.Column(database.DateTime, nullable=False)

    products = database.relationship('Product', secondary=OrderProduct.__table__,
                                     back_populates='orders')
