from app import db

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    login = db.Column(db.String(256))
    password_hash = db.Column(db.String(256))


class Wallet(db.Model):
    __tablename__ = 'wallet'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Expense(db.Model):
    __tablename__ = 'expense'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    name = db.Column(db.String(256))


class Item(db.Model):
    __tablename__ = 'item'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    amount = db.Column(db.Integer)
    budget_id = db.Column(db.Integer, db.ForeignKey('budget.id'))


class Budget(db.Model):
    __tablename__ = 'budget'

    id = db.Column(db.Integer, primary_key=True)
    invite = db.Column(db.String(256))
    name = db.Column(db.String(256))
    invite_expires = db.Column(db.DateTime)
