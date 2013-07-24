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
		self.user_session.last_access_at = naive_to_aware(datetime.datetime.utcnow())
		self.sqlalchemy_session.add(self.user_session)
		self.sqlalchemy_session.commit()

	def set_client_cookie(self, client_cookie_id):
		self.bottle_response.set_cookie(
			self.get_cookie_name(),
			client_cookie_id)

	def create_user_session(self, anonymous=True):
		client_cookie_id = self.sqlalchemy_models.UserSession.create_id()
		self.set_client_cookie(client_cookie_id)
		self.user_session = self.sqlalchemy_models.UserSession(
			anonymous=anonymous,
			session_name=self.get_cookie_name(),
			session_id=client_cookie_id,
			expires=self.compute_expiration(),
			last_access_at=naive_to_aware(datetime.datetime.utcnow()))
		self.sqlalchemy_session.add(self.user_session)
		self.sqlalchemy_session.commit()
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

	class TestSession(unittest.TestCase):

		def _setup_sqlalchemy(self):
			self.sa_session = db.db_session
			self.sa_models = db

		def setUp(self):
			self.application_name = 'blahblah'
			self._setup_sqlalchemy()

		def test_cookie_name(self):
			ss = ServerSession(self.application_name,
				self.sa_session,
				self.sa_models)
			self.assertIn(self.application_name, ss.get_cookie_name())

		def test_create_and_existing_new_cookie(self):
			import Cookie as cookie

			req = urllib2.Request(url='http://www.winscores.com:8080')
			response = urllib2.urlopen(req)
			print response.headers.items()
			cookies = [v for k, v in response.headers.items() if k.lower() == 'set-cookie']
			print 'cookies fetched from first response header: %s' % \
				cookies
			simple_cookies = [cookie.SimpleCookie(r) for r in cookies]
			print simple_cookies
			cookie_headers = dict([('Cookie', s.output(header='').strip()) for s in simple_cookies])
			print cookie_headers

			req = urllib2.Request(
				url='http://www.winscores.com:8080',
				headers=cookie_headers)
			print 'second request\'s header items=%s' % req.header_items()
			response = urllib2.urlopen(req)
			print 'second requests\'s response\'s headers %s' % response.headers

		def test_get_existing_cookie(self):
			pass

	unittest.main()
