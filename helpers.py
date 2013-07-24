import datetime
import unittest

import pytz

def to_utc(dt):
	utc = pytz.utc
	utc_dt = dt.astimezone(utc)
	return utc_dt

def naive_to_aware(dt, tz=pytz.utc):
	return dt.replace(tzinfo=tz)

def to_strftime(dt):
	return dt.strftime('%Y%m%d%H%M%S')

if __name__ == '__main__':
	import unittest

	class TestToUtc(unittest.TestCase):

		def test_to_utc_conversion(self):
			utc = pytz.timezone('UTC')
			eastern = pytz.timezone('US/Eastern')
			utc_now = datetime.datetime.now().replace(tzinfo=utc)
			eastern_now = utc_now.astimezone(eastern)
			self.assertEqual(to_utc(eastern_now), utc_now)

	unittest.main()
