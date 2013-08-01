import datetime

import pytz

from helpers import to_utc, naive_to_aware

class Session(object):

	def __init__(self, **kwargs):
		self.session_name = kwargs.pop('session_name')
		self.server_session = kwargs.pop('server_session')
		bottle = kwargs.pop('bottle', None)
		if bottle:
			self.cookie_request = CookieRequest(
				application_name=self.session_name,
				bottle_request=bottle.request)
			self.cookie_response = CookieResponse(
				application_name=self.session_name,
				bottle_response=bottle.response)

	def create(self, **kwargs):
		cookie_id = self.cookie_request.get()
		if cookie_id and self.server_session.get_session_entry(cookie_id):
			raise Exception('Session ID already set to: {0}'.format(
				self.session_id))
		session_id = self.server_session.create_new_session_id(
			anonymous=True,
			session_name=self.session_name)
		self.cookie_response.set(session_id, **kwargs)
		return session_id

	def update(self, **kwargs):
		session_id = self.cookie_request.get()
		if not session_id:
			raise Exception(
				'Unable to update because Session ID is not set')
		self.server_session.update(session_id)
		self.cookie_response.set(session_id, **kwargs)
		return session_id

	def expired(self):
		session_id = self.cookie_request.get()
		if not session_id:
			return True

		now = naive_to_aware(datetime.datetime.utcnow(),
			pytz.timezone('UTC'))
		expire = to_utc(self.server_session.get_session_entry(
			session_id).expires)
		if now > expire:
			return True
		else:
			return False

	def is_valid(self):
		return self.exists() and not self.expired()

	def exists(self):
		session_id = self.cookie_request.get()
		if session_id is None:
			return False

		user_session = self.server_session.get_session_entry(session_id)
		if not user_session:
			return False

		return True

class SessionCookie(object):

	def __init__(self, application_name):
		self.application_name = application_name

	def get_cookie_name(self):
		return 'cookie_{0}_session_id'.format(self.application_name)

class CookieRequest(SessionCookie):

	def __init__(self, **kwargs):
		self.bottle_request = kwargs.pop('bottle_request')
		super(CookieRequest, self).__init__(**kwargs)

	def get(self):
		return self.bottle_request.get_cookie(
			self.get_cookie_name(), None)

	def get_expiration(self):
		# FIXME: get expiration from cookie
		cookie = self.bottle_request.get_cookie(self.get_cookie_name())
		return 0

class CookieResponse(SessionCookie):

	def __init__(self, **kwargs):
		self.bottle_response = kwargs.pop('bottle_response')

		super(CookieResponse, self).__init__(**kwargs)

	def set(self, session_id, **kwargs):
		self.bottle_response.set_cookie(
			self.get_cookie_name(),
			session_id, **kwargs)

class ServerSession(object):
	SESSION_EXPIRES = datetime.timedelta(minutes=30)

	def __init__(self, db_session, sa_models):
		self.db_session = db_session
		self.sa_models = sa_models

	def get_new_expiration(self, _from=None, expires=None):
		'''
			1. _from must be datetime
			2. expires must be timedelta
		'''
		if not _from:
			_from = naive_to_aware(datetime.datetime.utcnow())
		if not expires:
			expires = self.SESSION_EXPIRES

		return _from + expires

	def get_session_entry(self, session_id):
		return self.db_session.query(
			self.sa_models.UserSession).filter_by(
				session_id=unicode(session_id)).first()

	def create_new_session_id(self, **kwargs):
		session_id = self.sa_models.UserSession.create_id()
		user_session = self.sa_models.UserSession(
			anonymous=kwargs.pop('anonymous'),
			session_name=kwargs.pop('session_name'),
			session_id=session_id,
			expires=self.get_new_expiration(),
			last_access_at=naive_to_aware(datetime.datetime.utcnow()))
		self.db_session.add(user_session)
		self.db_session.commit()
		return user_session.session_id

	def update(self, session_id):
		user_session = self.get_session_entry(session_id)
		user_session.expires = self.get_new_expiration()
		user_session.last_access_at = naive_to_aware(
			datetime.datetime.utcnow())
		self.db_session.add(user_session)
		self.db_session.commit()
		return user_session.session_id

if __name__ == '__main__':
	import unittest
	import urllib2

	import db

	SERVER_HOST = 'localhost:8080'

	class TestSession(unittest.TestCase):

		def _setup_sqlalchemy(self):
			self.sa_session = db.db_session()
			self.sa_models = db

		def setUp(self):
			self.application_name = 'testapp'
			self.cookie_session_name = 'cookie_{0}_session_id'.format(
				self.application_name)
			self._setup_sqlalchemy()

		def _extract_cookies(self, response):
			import Cookie as cookie
			cookies = [v for k, v in response.headers.items() if k.lower() == 'set-cookie']

			header_keys = map(lambda x: x.lower(), response.headers.keys())
			self.assertIn('set-cookie', header_keys)
			simple_cookies = [cookie.SimpleCookie(r) for r in cookies]
			self.assertTrue(len(simple_cookies) > 0)
			return simple_cookies

		def _simple_cookies_to_headers(self, sc):
			a = []
			for s in sc:
				d = {}
				d['Cookie'] = s.output(header='').strip()
				a.append(d)
			return a

		def test_cookie_name(self):
			import bottle
			ss = Session(session_name=self.cookie_session_name,
				server_session=ServerSession(
					db_session=self.sa_session,
					sa_models=self.sa_models),
					bottle=bottle)
			self.assertIn(self.cookie_session_name,
				ss.cookie_request.get_cookie_name())
			self.assertIn(self.cookie_session_name,
				ss.cookie_response.get_cookie_name())

		def test_create_cookie(self):
			req = urllib2.Request(url='http://localhost:8080')
			response = urllib2.urlopen(req)
			simple_cookies = self._extract_cookies(response)
			self.assertTrue(response is not None)
			cookie_headers = self._simple_cookies_to_headers(simple_cookies)
			self.assertTrue(
				'Cookie' not in [
					c.values() for c in cookie_headers])
			self.assertRegexpMatches(simple_cookies[0].output(header=''),
				r'[a-z_]*=[a-z0-9]*')
			return simple_cookies, cookie_headers

		def test_get_existing_cookie(self):
			simple_cookies, cookie_headers = self.test_create_cookie()
			prev_cookie_id = simple_cookies[0][
				self.cookie_session_name].value
			req = urllib2.Request(
				url='http://localhost:8080',
				headers=cookie_headers[0])
			response = urllib2.urlopen(req)
			simple_cookies = self._extract_cookies(response)
			self.assertEqual(prev_cookie_id,
				simple_cookies[0][self.cookie_session_name].value)

	unittest.main()
