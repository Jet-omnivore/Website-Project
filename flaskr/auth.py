import functools
import sys
import re

from flask import (
        Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
        )

from random import randrange
from werkzeug.security import check_password_hash, generate_password_hash
from flaskr.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')
gmail_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

@bp.route('/otp-verification', methods=('GET', 'POST'))
def otp_verification():
    db = get_db()
    if request.method == 'POST':
        otp = request.form['otp']
        
        error = None
        if len(str(otp)) != 6:
            error = 'Invalid OTP' 
        elif int(otp) != session['otp']:
            error = "Incorrect otp"

        if error is None:
            try:
                db.execute(
                        "INSERT INTO user (gmail, password) VALUES (?, ?)",
                        (session['gmail'], generate_password_hash(session['password']))
                    )
                
                user = db.execute('SELECT * FROM user WHERE gmail = ?', (session['gmail'],)).fetchone()

                db.execute(
                       "INSERT INTO user_data (id, availabe_coins, balance, daily_income, total_income, withdrawable_amount, withdrawn_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (user['id'], 0, 0, 0, 0, 0, 0)
                    )

                db.commit()
                session.clear()
                session['user_id'] = user['id']
            except db.IntegrityError:
                error = f'Gmail {session["gmail"]} is already registered.'
            else:
                return redirect(url_for('user.my'))
        flash(error)

    if not session['otp-sent']:
        mail = current_app.config['mail']
        session['otp'] = randrange(100000, 999999)
        mail.send_message(
                subject= 'OTP VERIFICATION',
                body = f"Welcome! Thanks for Signing Up.\n Your OTP is {session['otp']} \nDon't share OTP with anyone.",
                recipients = [session['gmail']],
                sender = current_app.config['MAIL_USERNAME']
                )
        session['otp-sent'] = True
    return render_template('auth/otp.html')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        gmail = request.form['gmail']
        password = request.form['password']
        confirm_passowrd = request.form['confirm-password']
        db = get_db()
        error = None

        if not gmail:
            error = 'Gmail is required.'
        elif not re.fullmatch(gmail_regex, gmail):
            error = 'Invalid gmail'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_passowrd:
            error = 'Password and confirm password must be same'
        elif len(password) < 8:
            error = 'Password is too short.'

        if error is None:
            try: 
                session.clear()
                session['gmail'] = gmail
                session['password'] = password
                session['otp-sent'] = False
                pass
            except db.IntegrityError:
                error = f'Gmail {gmail} is already registered.'
            else:
                return redirect(url_for('auth.otp_verification'))

        flash(error)
    return render_template('auth/register.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
                'SELECT * FROM user WHERE id = ?', (user_id,)
            ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main'))

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == "POST":
        gmail = request.form['gmail']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
                'SELECT * FROM user WHERE gmail = ?', (gmail,)).fetchone()
        
        if not re.fullmatch(gmail_regex, gmail):
            error = 'Invalid gmail'

        if user is None:
            error = 'Incorrect gmail'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('user.my'))
        
        flash(error)
    return render_template('auth/login.html')

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view
