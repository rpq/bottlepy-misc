import datetime

import pytz
import bottle

import session
import db

app = bottle.Bottle()

APPLICATION_NAME = 'testapp'

@app.get('/')
def index():
	s = session.ServerSession(APPLICATION_NAME, db.db_session, db,
		bottle.request, bottle.response)
	print '!!!!bottle request headers=%s' % bottle.request.environ
	print bottle.request.cookies.items()
	if s.is_valid_session():
		print 'is valid!'
		s.update_last_access_at(s.get_client_cookie())
		print s.get_client_cookie()
	else:
		print s.create_user_session()
	session_id = s.get_client_cookie()
	return 'got the bottle request environ...'

bottle.run(app, host='winscores.com', port=8080, debug=True)
