import datetime

import pytz
import bottle

import session
import db

app = bottle.Bottle()
app.config['session.keyword'] = 'session'
app.config['db.keyword'] = 'db_'
app.config['db_models.keyword'] = 'models'

APPLICATION_NAME = 'testapp'

def session_cookie_init(fn):
    def wrapper(*args, **kwargs):
        db_session = db.db_session()

        session_ = session.Session(
            session_name=APPLICATION_NAME,
            server_session=session.ServerSession(db_session, db),
            bottle=bottle)
        if session_.is_valid():
            session_id = session_.update(secure=False)
            bottle.request.session = session_id
        else:
            session_id = session_.create(secure=False)
            bottle.request.session = session_id
            id(bottle.request)

        try:
            kwargs[app.config['session.keyword']] = session_id
            return fn(*args, **kwargs)
        except:
            db_session.rollback()
            raise
        db_session.close()
    return wrapper

def db_init(fn):
    def wrapper(*args, **kwargs):
        db_session = db.db_session()
        kwargs[app.config['db.keyword']] = db_session
        kwargs[app.config['db_models.keyword']] = db
        return fn(*args, **kwargs)
    return wrapper

@app.get('/', apply=[session_cookie_init, db_init])
def index(session, db_, models):
    import simplejson
    u = db_.query(models.UserSession).filter_by(session_id=session).first()
    if u.session_data:
        loaded = simplejson.loads(u.session_data)
    else:
        loaded = {}

    load = simplejson.dumps({'count': loaded.get('count',0) + 1})

    u.session_data = load
    db_.add(u)
    db_.commit()
    print u.session_data
    return 'hello world, click count=%s' % u.session_data

bottle.run(app, host='localhost', port=8080)
