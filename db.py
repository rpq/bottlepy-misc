import datetime
import hashlib

import sqlalchemy

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker

import helpers

engine = create_engine('postgresql://nginx@/scrap_test',
	echo=True)
Base = declarative_base()

class User(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key=True)
	username = Column(String)

class UserSession(Base):
	__tablename__ = 'user_session'

	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
	anonymous = Column(Boolean, nullable=True)

	session_name = Column(String)
	session_id = Column(String, unique=True)
	expires = Column(DateTime(timezone=True))
	last_access_at = Column(DateTime(timezone=True))

	@classmethod
	def create_id(cls):
		SALT = '09123kasdc012409asd8fi0a9s'
		h = hashlib.new('sha256')
		string_ = '{0}{1}'.format(
			helpers.to_strftime(datetime.datetime.utcnow()), SALT)
		print 'here is the string to generate_=%s' % string_
		h.update(string_)
		print 'generated brand new digest=%s' % h.hexdigest()
		return h.hexdigest()

db_session = sessionmaker(bind=engine)
db_session = db_session()

if __name__ == '__main__':
	Base.metadata.create_all(engine)