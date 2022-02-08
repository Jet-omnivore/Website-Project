from flask import current_app
from flaskr.db import get_db, g
from flask_apscheduler import APScheduler

scheduler = APScheduler()

def close_scheduler(e=None):
    if scheduler and scheduler.running:
        scheduler.shutdown()

def init_scheduler(app):
    app.teardown_appcontext(close_scheduler)
    scheduler.init_app(app)
    scheduler.start()

def task(**kwargs):
    def wrapper(f):
        scheduler.add_job(func=f, id=f.__name__, **kwargs)
    return wrapper

@task(hour="00", minute="00", trigger='cron')
def update_users_data():
    with scheduler.app.app_context():
        db = get_db()
        try:
            # updating lased days
            db.execute("UPDATE lease SET leased_days = leased_days + 1")
            # updating balance of user
            db.execute("UPDATE user_data SET balance = balance + (SELECT SUM(daily_income) FROM lease WHERE lease.user_id = user_data.id)")
            db.commit()
        except db.IntegrityError:
            raise Exception("error in updating users data")
                
