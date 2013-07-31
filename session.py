import datetime

import pytz

from helpers import to_utc, naive_to_aware

# in seconds
EXPIRATION_DEFAULT = 60*24*1

class ServerSession(object):
	# in seconds
	EXPIRATION_DEFAULT = EXPIRATION_DEFAULT

	def __init__(self,
		application_name,
		sqlalchemy_session,
		sqlalchemy_models,
		bottle_request=None,
		bottle_response=None):

		self.application_name = application_name
		self.sqlalchemy_session = sqlalchemy_session
		self.sqlalchemy_models = sqlalchemy_models
		self.bottle_request = bottle_request
		self.bottle_response = bottle_response
		self.user_session = None

	def get_cookie_name(self):
		return 'cookie_{0}_session_id'.format(self.application_name)

	def get_client_cookie(self):
		client_cookie_id = self.bottle_request.get_cookie(
			self.get_cookie_name(), None)
		return client_cookie_id

	def get_server_cookie(self, client_cookie_id):
		print 'server cookies=%s' % [s.session_id for s in self.sqlalchemy_session.query(
			self.sqlalchemy_models.UserSession).filter_by(
				session_id=client_cookie_id).all()]
		self.user_session = self.sqlalchemy_session.query(
			self.sqlalchemy_models.UserSession).filter_by(
				session_id=unicode(client_cookie_id)).first()
		return self.user_session

	def get_client_cookie_expiration(self):
		cookie = self.bottle_request.get_cookie(self.get_cookie_name())
		#print 'found cookie: %s' % cookie
		#if cookie:
		#	print cookie.__class__.__name__
		#	print dir(cookie)
		#	return cookie.get('max_age', None) or \
		#		cookie.get('expires', None)
		#else:
		return 0

	def compute_expiration(self, _from=None, _add_on=None):
		if not _from:
			_from = naive_to_aware(datetime.datetime.utcnow())
		if not _add_on:
			_add_on =  datetime.timedelta(seconds=EXPIRATION_DEFAULT)

		cookie_expiration = self.get_client_cookie_expiration()
		if cookie_expiration:
			return _from + datetime.timedelta(seconds=cookie_expiration)
		else:
			return _from + _add_on

	def update_last_access_at(self, client_cookie_id):
		self.get_server_cookie(client_cookie_id)
		self.user_session.expires = self.compute_expiration()
		self.user_session.last_access_at = naive_to_aware(
			datetime.datetime.utcnow())
		self.sqlalchemy_session.add(self.user_session)
		self.sqlalchemy_session.commit()
		self.set_client_cookie(client_cookie_id)

	def set_client_cookie(self, client_cookie_id):
		self.bottle_response.set_cookie(
			self.get_cookie_name(),
			client_cookie_id)

	def create_user_session(self, anonymous=True):
		client_cookie_id = self.sqlalchemy_models.UserSession.create_id()
		self.user_session = self.sqlalchemy_models.UserSession(
			anonymous=anonymous,
			session_name=self.get_cookie_name(),
			session_id=client_cookie_id,
			expires=self.compute_expiration(),
			last_access_at=naive_to_aware(datetime.datetime.utcnow()))
		self.sqlalchemy_session.add(self.user_session)
		self.sqlalchemy_session.commit()
		self.set_client_cookie(client_cookie_id)
		return self.user_session

	def cookie_expired(self):
		now = naive_to_aware(datetime.datetime.utcnow(),
			pytz.timezone('UTC'))
		expire = to_utc(self.user_session.expires)
		print now
		print expire
		if now > expire:
			print 'expired'
			return True
		else:
			return False

	def is_valid_session(self):
		client_cookie_id = self.get_client_cookie()
		print 'found client cookie %s' % client_cookie_id
		print 'found server cookie = %s' % self.get_server_cookie(
			client_cookie_id)
		if client_cookie_id and self.get_server_cookie(
			client_cookie_id) and not self.cookie_expired():
			print 'valid cookie!!!'
			return True
		else:
			return False

if __name__ == '__main__':
	import unittest
	import urllib2

	import db

	SERVER_HOST = 'localhost:8080'

	class TestSession(unittest.TestCase):

		def _setup_sqlalchemy(self):
			self.sa_session = db.db_session
			self.sa_models = db

		def setUp(self):
			self.application_name = 'blahblah'
			self._setup_sqlalchemy()

		def _extract_cookies(self, response):
			import Cookie as cookie
			cookies = [v for k, v in response.headers.items() if k.lower() == 'set-cookie']

			print 'returned headers.. %s' % map(
					lambda x: x.lower(), response.headers.keys())
			self.assertTrue(
				'set-cookie' in map(
					lambda x: x.lower(), response.headers.keys()))
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
			ss = ServerSession(self.application_name,
				self.sa_session,
				self.sa_models)
			self.assertIn(self.application_name, ss.get_cookie_name())

		def test_create_and_existing_new_cookie(self):
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
			simple_cookies, cookie_headers = \
				self.test_create_and_existing_new_cookie()
			prev_cookie_id = simple_cookies[0].values()[0].value
			print 'sending headers... %s' % cookie_headers[0]
			req = urllib2.Request(
				url='http://localhost:8080',
				headers=cookie_headers[0])
			response = urllib2.urlopen(req)
			simple_cookies = self._extract_cookies(response)
			self.assertEqual(prev_cookie_id,
				simple_cookies[0].values()[0].value)

	unittest.main()
