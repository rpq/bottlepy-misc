import datetime

import pytz
import bottle

import session
import db

app = bottle.Bottle()

APPLICATION_NAME = 'testapp'

def session_cookie_init(fn):
	def wrapper(*args, **kwargs):
		s = session.ServerSession(APPLICATION_NAME, db.db_session, db,
			bottle.request, bottle.response)
		print 'bottle.request=%s' % [(k, v,) for k, v in bottle.request.headers.iteritems()]
		if s.is_valid_session():
			s.update_last_access_at(s.get_client_cookie())
		else:
			s.create_user_session()
		bottle.request.environ['bottle.request']['session'] = \
			s.user_session.session_id
		return fn(*args, **kwargs)
	return wrapper

@app.get('/', apply=session_cookie_init)
def index():
	return 'got the bottle request environ...'

bottle.run(app, host='localhost', port=8080, debug=True)
