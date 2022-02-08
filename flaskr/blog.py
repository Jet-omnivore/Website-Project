import uuid
import sys
import requests
import logging

from flask import (
        Blueprint, flash, redirect, render_template, request, url_for, session, current_app
    )

from werkzeug.exceptions import abort
from flaskr.paytm_checksum import generate_checksum, verify_checksum
from datetime import datetime
from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('user', __name__, url_prefix="/user") 
logging.basicConfig(level=logging.DEBUG)

@bp.route('/my')
@login_required
def my():
    db = get_db()
    user_data = db.execute(
            'SELECT availabe_coins, balance, daily_income, total_income FROM user_data WHERE id = ?;'
            ,(session['user_id'], )).fetchone()
    return render_template('blog/my.html', user_data=user_data)


@bp.route('/withdraw', methods=['POST', 'GET'])
@login_required
def withdraw():
    db = get_db()
    withdraw_data = db.execute(
                    'SELECT withdrawable_amount, withdrawn_amount FROM user_data WHERE id = ?;'
                    ,(session['user_id'], )).fetchone()

    if request.method == 'POST':
        error = None

        try:
            account_number = int(request.form['account-number'])
            amount_entered = int(request.form['amount'])
        except:
            error = 'You entered wrong data.'
            amount_entered = 0
        holder_name = request.form['holder-name']
        ifsc_code = request.form['ifsc-code']
        upi_id = request.form['holder-name']

        if amount_entered < 100:
            error = 'Withdraw amount should be greater 100 INR'
        elif amount_entered > withdraw_data[0]:
            error = 'Insufficient Balance'

        if error is None:
            message = 'Successful' 
            flash(message)

            time = datetime.now()
            db.execute("INSERT INTO withdrawal_record (user_id, amount, bought_date, status) VALUES (?, ?, ? , ?)",
                        (session['user_id'], amount_entered, time, 'Processing')
                    )
            db.execute(
                    "UPDATE user_data SET withdrawn_amount = withdrawn_amount + ?", (amount_entered, )
                    )
            db.commit()

        flash(error)
        return render_template('blog/withdraw.html', withrawable_amount=withdraw_data[0], withdrawn_cash=withdraw_data[1])
    return render_template('blog/withdraw.html', withrawable_amount=withdraw_data[0], withdrawn_cash=withdraw_data[1])


@bp.route('/buy/<equipment_index>')
@login_required
def buy_equipment(equipment_index):
    equipment_index = int(equipment_index)
    equipment = current_app.config['equipments_data'][equipment_index]
    amount = equipment[3]
    cust_id = session['user_id']

    return redirect(url_for('user.checkout', cust_id=cust_id, amount=amount, equipment=equipment))

    '''time = datetime.utcnow()
    db.execute(
        'INSERT INTO lease (user_id, daily_income, total_income, leased_days, accumulated_income, bought_date, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (session['user_id'], 1, 1, 2, 1, time, 'idk')
        )
    db.commit()

    return redirect(url_for('main'))'''


@bp.route('my_leasing/')
@login_required
def my_leasing():
    db = get_db()
    all_leases = db.execute( 'SELECT daily_income, total_income, leased_days, accumulated_income FROM lease WHERE user_id = ?' , 
            (session['user_id'],)).fetchall()
    return render_template('blog/my_leasing.html', all_leases=all_leases)


@bp.route('withdrawal-record/')
@login_required
def withdrawal_record():
    db = get_db()
    all_records = db.execute("SELECT amount, bought_date, status FROM withdrawal_record WHERE user_id = ?",
                                (session['user_id'], )
                            )
    return render_template('blog/withdrawal_record.html', all_records=all_records)

@bp.route('/buy-page', methods=['GET', 'POST'])
@login_required
def checkout():
    customer_id = request.args.get('cust_id') 
    amount = request.args.get('amount')
    equipment = request.args.get('equipment')
    order_id = uuid.uuid4()

    transaction_data = {
        "MID": current_app.config.get('MERCHANT_ID'),
        "WEBSITE": current_app.config.get('WEBSITE_NAME'),
        "INDUSTRY_TYPE_ID": current_app.config.get('INDUSTRY_TYPE_ID'),
        "ORDER_ID": str(order_id),
        "CUST_ID": '00' + str(customer_id),
        "TXN_AMOUNT": str(amount),
        "CHANNEL_ID": "WEB",
        "MOBILE_NO": "7777777777",
        "EMAIL": "singhjatan56@gmail.com",
        "CALLBACK_URL": request.url_root + 'user/callback'
    }

    session['current_equipment'] = equipment
    # Generate checksum hash
    transaction_data["CHECKSUMHASH"] = generate_checksum(transaction_data, current_app.config['MERCHANT_KEY'])

    url = current_app.config.get('BASE_URL') + '/theia/processTransaction'

    logging.info("Request params: {transaction_data}".format(transaction_data=transaction_data))
    return render_template("blog/buy_page.html", transaction_data=transaction_data, url=url)

@bp.route('/callback', methods=['GET', 'POST'])
def callback():
    # log the callback response payload returned:
    callback_response = request.form.to_dict()
    logging.info("Transaction response: {callback_response}".format(callback_response=callback_response))

    # verify callback response checksum:
    checksum_verification_status = verify_checksum(callback_response, current_app.config.get('MERCHANT_KEY'),
                                                   callback_response.get("CHECKSUMHASH"))
    logging.info("checksum_verification_status: {check_status}".format(check_status=checksum_verification_status))

    # verify transaction status:
    transaction_verify_payload = {
        "MID": callback_response.get("MID"),
        "ORDERID": callback_response.get("ORDERID"),
        "CHECKSUMHASH": callback_response.get("CHECKSUMHASH")
    }
    url = current_app.config.get('BASE_URL') + '/order/status'
    verification_response = requests.post(url=url, json=transaction_verify_payload)
    logging.info("Verification response: {verification_response}".format(
        verification_response=verification_response.json()))

    verification_response_data = verification_response.json()
    v = verification_response_data

    db = get_db()
    try:
        db.execute("INSERT INTO user_order (user_id, amount, order_id, respcode, order_date) VALUES (?, ?, ?, ?, ?)"
                , (session.get('user_id'), v['TXNAMOUNT'], v['ORDERID'], v['RESPCODE'], v['TXNDATE'])
                )
        db.commit()
    except db.IntegrityError as err:
        raise err
    
    if checksum_verification_status:
        if verification_response_data.get('RESPCODE') == '01':
            add_equipment(session['current_equipment'])
            del session['current_equipment']

    return render_template("callback.html",
                       callback_response=callback_response,
                       checksum_verification_status=checksum_verification_status,
                       verification_response=verification_response.json())


def add_equipment(equipment):
    db = get_db()

    try:
        time = datetime.utcnow()
        db.execute(
            'INSERT INTO lease (user_id, daily_income, total_income, leased_days, accumulated_income, bought_date, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (session['user_id'], 1, 1, 2, 1, time, 'Ongoing')
            )
        db.commit()
    except db.IntegrityError:
        raise Exception('LEASE INSERT ERROR ....')
