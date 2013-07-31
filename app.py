import datetime

import pytz
import bottle

import session
import db

app = bottle.Bottle()

APPLICATION_NAME = 'testapp'

def session_cookie_init(fn):
	def wrapper(*args, **kwargs):
		db_session = db.db_session()

		# session class should handle integrityerror exceptions, etc
		# starting here
		s = session.Session(
			session_name=APPLICATION_NAME,
			server_session=session.ServerSession(db_session, db),
			bottle=bottle)
		if s.is_valid():
			session_id = s.update()
		else:
			session_id = s.create()
			bottle.request.environ['bottle.request']['session'] = \
				session_id
		# ending here

		try:
			fn(*args, **kwargs)
		except:
			db_session.rollback()
			raise
		db_session.close()
	return wrapper

@app.get('/', apply=[session_cookie_init,])
def index():
	return 'index'

bottle.run(app, host='localhost', server='gunicorn', port=8080, debug=True)
