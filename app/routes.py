from app import app, db, auth
from passlib.hash import pbkdf2_sha256
from app.models import *

import datetime, string, random

from flask import jsonify, request
import re

@auth.verify_password
def verify_password(login, password):
    user = db.session.query(User).filter_by(login=login).first()
    if not user:
        return None
    if pbkdf2_sha256.verify(password, user.password_hash):
        return user

@app.route('/api/v1/user/getMe')
@auth.login_required
def getMe():
    user = auth.current_user()
    
    return jsonify({
            'user_id': user.id,
            'user_name': user.name,
            'wallet_id': db.session.query(Wallet).filter_by(user_id=user.id).first().id
        }), 200

@app.route('/api/v1/user/signUp', methods=['POST'])
def signUp():
    name = request.args['name']
    login = request.args['login']
    password = request.args['password']

    # check if username exists
    if User.query.filter_by(login=login).scalar() != None:
        return jsonify({'message': 'Username already exists.'}), 403

    # check if login is appropriate
    if re.fullmatch(r'[a-zA-Z0-9_]{5,20}', login) == None:
        return jsonify({
            'message': 'Invalid username format. Username must be 5-20 characters long. \
Latin letters, digits and _ are allowed.'
        }), 422

    # check if password is appropriate
    if len(password) < 8:
        return jsonify({
            'message': 'Invalid password format. Password must be at least 8 characters long.'
        }), 422

    # register the new user
    new_user = User(name=name, login=login, password_hash=pbkdf2_sha256.hash(password))
    db.session.add(new_user)

    db.session.commit()

    new_wallet = Wallet(user_id=new_user.id)
    db.session.add(new_wallet)

    db.session.commit()

    return jsonify({'message': 'User succesfully created.'}), 201

@app.route('/api/v1/wallet/<walletId>/addExpense', methods=['POST'])
@auth.login_required
def addExpense(walletId):
    name = request.args['name']
    amount = request.args['amount']

    # Check walletId
    try:
        walletId = int(walletId)
        if db.session.query(Wallet).get(walletId) == None:
            return jsonify({'message': 'Wallet not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Wallet id must be integer.'}), 400

    if auth.current_user().id != db.session.query(Wallet).get(walletId).user_id:
        return jsonify({'message': 'Access denied.'}), 403

    try:
        amount = int(amount)
        assert amount != 0
        new_expense = Expense(name=name, amount=amount, wallet_id=walletId)
        db.session.add(new_expense)
        db.session.commit()
        return jsonify({'message': 'Expense succesfully created.'}), 201
    except AssertionError:
        return jsonify({'message': 'Amount must be non-zero.'}), 422
    except ValueError:
        return jsonify({'message': 'Amount must be integer.'}), 400

@app.route('/api/v1/wallet/<walletId>')
def getWallet(walletId):
    # Check walletId
    try:
        walletId = int(walletId)
        wallet = db.session.query(Wallet).get(walletId)
        if wallet == None:
            return jsonify({'message': 'Wallet not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Wallet id must be integer.'}), 400
    
    user = db.session.query(User).get(wallet.user_id);
    if user == None:
        return jsonify({'message': 'Wallet not found.'}), 404

    expenses = [{
        'id': expense.id,
        'amount': expense.amount,
        'name': expense.name,
        'budget_name': '' if expense.item_id == None else db.session.query(Budget).get(db.session.query(Item).get(expense.item_id).budget_id).name
    } for expense in db.session.query(Expense).filter_by(wallet_id=wallet.id).all()]

    balance = sum([expense['amount'] for expense in expenses])

    return jsonify(
        {
            'user_name': user.name,
            'balance': balance,
            'expenses': expenses,
        }
    ), 200

@app.route('/api/v1/expense/<expenseId>', methods=['PUT', 'DELETE'])
@auth.login_required
def editExpense(expenseId):
    try:
        expenseId = int(expenseId)
        expense = db.session.query(Expense).get(expenseId)
        if expense == None:
            return jsonify({'message': 'Expense not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Expense id must be integer.'}), 400

    if auth.current_user().id != db.session.query(Wallet).get(expense.wallet_id).user_id:
        return jsonify({'message': 'Access denied.'}), 403


    if request.method == 'PUT':
        try:
            name = request.args['name']
            assert name != None
            expense.name = name
        except:
            pass

        try:
            amount = int(request.args.get('amount'))
            assert amount != 0
            expense.amount = amount
        except:
            pass


        db.session.commit()
        
        return jsonify({'message': 'Expense updated.'}), 200
    
    else: # DELETE
        db.session.delete(expense)
        db.session.commit()
        return jsonify({'message': 'Expense deleted.'}), 200

@app.route('/api/v1/budget/resolveInvite/<invite>')
def resolveInvite(invite):
    try:
        budget = db.session.query(Budget).filter_by(invite=invite).first()
        assert budget != None
        assert budget.invite_expires > datetime.datetime.now()
        return jsonify({'id': budget.id}), 200
    except AssertionError:
        return jsonify({'message': 'Invalid budget invite.'}), 404

@app.route('/api/v1/budget/<budgetId>/getExpenses')
def getBudgetExpenses(budgetId):
    # Check budgetId
    try:
        budgetId = int(budgetId)
        budget = db.session.query(Budget).get(budgetId)
        if budget == None:
            return jsonify({'message': 'Budget not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Budget id must be integer.'}), 400
    
    item_ids = [item.id for item in db.session.query(Item).filter_by(budget_id=budget.id)]

    matches = []
    wallet_ids = set()
    for expense in db.session.query(Expense).all():
        if expense.wallet_id in wallet_ids:
            matches.append(expense)
        else:
            if expense.item_id in item_ids:
                wallet_ids.add(expense.wallet_id)
                matches.append(expense)

    expenses = [
        {
            'amount': expense.amount,
            'name': expense.name,
            'user_name': db.session.query(User).get(db.session.query(Wallet).get(expense.wallet_id).user_id).name,
            'wallet_id': expense.wallet_id,
        }
        for expense in matches
    ]

    return jsonify(expenses), 200

@app.route('/api/v1/budget/<budgetId>')
def getBudget(budgetId):
    # Check budgetId
    try:
        budgetId = int(budgetId)
        budget = db.session.query(Budget).get(budgetId)
        if budget == None:
            return jsonify({'message': 'Budget not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Budget id must be integer.'}), 400

    items = [
        {
            'id': item.id,
            'name': item.name,
            'amount': item.amount,
            'avaliable_amount': sum([-expense.amount for expense in db.session.query(Expense).filter_by(item_id=item.id)])
        }
        for item in db.session.query(Item).filter_by(budget_id=budget.id)
    ]

    return jsonify(
        {
            'name': budget.name,
            'invite': budget.invite,
            'invite_expires': budget.invite_expires,
            'items': items,
        }
    ), 200

@app.route('/api/v1/item/<itemId>/putMoney', methods=['POST'])
@auth.login_required
def putMoney(itemId):
    # Check itemId
    try:
        itemId = int(itemId)
        item = db.session.query(Item).get(itemId)
        if item == None:
            return jsonify({'message': 'Item not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Item id must be integer.'}), 400
    
    # Check wallet_id
    try:
        wallet_id = int(request.args['wallet_id'])
        wallet = db.session.query(Wallet).get(wallet_id)
        if wallet == None:
            return jsonify({'message': 'Wallet not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Wallet id is either not specified or not an integer.'}), 400

    if auth.current_user().id != wallet.user_id:
        return jsonify({'message': 'Access denied.'}), 403

    try:
        amount = int(request.args.get('amount'))
        assert amount != 0
    
        db.session.add(Expense(name='Budget item ' + item.name + ' transfer', amount=amount, wallet_id=wallet_id, item_id=item.id))
        db.session.commit()

        return jsonify({'message': 'Money put.'}), 201

    except AssertionError:
        return jsonify({'message': 'Amount must be non-zero.'}), 422
    except ValueError:
        return jsonify({'message': 'Amount must be integer.'}), 400

@app.route('/api/v1/budget', methods=['POST'])
def createBudget():
    def generateInvite():
        return ''.join(random.choices(string.ascii_lowercase, k=5))

    invite = generateInvite()
    while db.session.query(Budget).filter_by(invite=invite).scalar() != None:
        generateInvite()

    invite_expires = datetime.datetime.now() + datetime.timedelta(days=7)

    budget = Budget(name=request.args['name'], invite=invite, invite_expires=invite_expires)
    
    db.session.add(budget)
    db.session.commit()

    return jsonify({'id': budget.id}), 201

@app.route('/api/v1/budget/<budgetId>', methods=['PUT', 'DELETE'])
def editBudget(budgetId):
    # Check budgetId
    try:
        budgetId = int(budgetId)
        budget = db.session.query(Budget).get(budgetId)
        if budget == None:
            return jsonify({'message': 'Budget not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Budget id must be integer.'}), 400

    if request.method == 'PUT':
        budget.name = request.args['name']
        db.session.commit()
        return jsonify({'message': 'Budget updated.'}), 200
    else: # DELETE
        db.session.delete(budget)
        db.session.commit()
        return jsonify({'message': 'Budget deleted.'}), 200

@app.route('/api/v1/budget/<budgetId>/addItem', methods=['POST'])
def addItem(budgetId):
    # Check budgetId
    try:
        budgetId = int(budgetId)
        budget = db.session.query(Budget).get(budgetId)
        if budget == None:
            return jsonify({'message': 'Budget not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Budget id must be integer.'}), 400

    # Verify amount
    try:
        amount = int(request.args['amount'])
        assert amount > 0
    except AssertionError:
        return jsonify({'message': 'Amount must be positive.'}), 422
    except ValueError:
        return jsonify({'message': 'Amount must be integer.'}), 400
    
    item = Item(name=request.args['name'], amount=amount, budget_id = budget.id)

    db.session.add(item)
    db.session.commit()

    return jsonify({'id': item.id}), 201

@app.route('/api/v1/item/<itemId>', methods=['PUT', 'DELETE'])
def editItem(itemId):
    # Check itemId
    try:
        itemId = int(itemId)
        item = db.session.query(Item).get(itemId)
        if item == None:
            return jsonify({'message': 'Item not found.'}), 404
    except ValueError:
        return jsonify({'message': 'Item id must be integer.'}), 400

    if request.method == 'PUT':

        try:
            name = request.args['name']
            assert name != None
            item.name = name
        except:
            pass

        try:
            amount = int(request.args.get('amount'))
            assert amount > 0
            item.amount = amount
        except:
            pass

        db.session.commit()
        return jsonify({'message': 'Item updated.'}), 200
    else: # DELETE
        db.session.delete(item)
        db.session.commit()
        return jsonify({'message': 'Item deleted.'}), 200
