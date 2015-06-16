# -*- coding: utf-8 -*-
import re
import posixpath

import requests
from requests.auth import HTTPBasicAuth

class eActivitiesException(Exception):
    pass

IPv4_RE = r'(25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})(\.(25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})){3}'
IPv6_RE = r'([0-9a-f]){1,4}(:([0-9a-f]){1,4}){7}'

class Banned(eActivitiesException):
    BANNED_MSG_RE = r'^IP address (?P<banned_ip>' + IPv4_RE + r'|' + IPv6_RE + r') has been banned until (?P<banned_until>[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2})$'

    def __init__(self, banned_until=None, banned_ip=None):
        self.banned_until = banned_until
        self.banned_ip = banned_ip

    @classmethod
    def from_json(cls, obj):
        if not obj.get('message'):
            return cls()
        msg = obj.get('message')
        msgm = re.match(cls.BANNED_MSG_RE, msg)
        if not msgm:
            return cls()
        return cls(datetime.datetime.strptime(msgm.group('banned_until'), '%d/%m/%Y %H:%M:%S'), msgm.group('banned_ip'))

class HTTPError(requests.HTTPError, eActivitiesException):
    pass

class eActivities(object):
    def __init__(self, api_key, endpoint='https://eactivities.union.ic.ac.uk/api/'):
        self.c = requests.Session()
        self.c.auth = HTTPBasicAuth('', api_key)
        self.endpoint = endpoint

    def get(self, path, *args, **kwargs):
        resp = self.c.get(posixpath.join(self.endpoint, path), *args, **kwargs)

        self._raise_for_status(resp)

        return resp

    def _raise_for_status(self, resp):
        if resp.status_code == 403:
            msg = resp.json().get('message', None)
            if msg and 'IP address' in msg and 'has been banned' in msg:
                 raise Banned.from_json(resp.json())

        if not resp:
            raise HTTPError('%s: %s' % (resp.status_code, resp.reason))

    def csp_details(self):
        return self.get('').json()

    def products(self):
        return eActivitiesProducts(self)

    def reports(self):
        return eActivitiesReports(self)

class eActivitiesReports(object):
    def __init__(self, eactivities):
        self.eactivities = eactivities

    def members_list(self, year=None):
        opt_params = {'year': year} if year else {}
        return self.eactivities.get('reports/members', params=opt_params).json()

    def sales_list(self, year=None):
        opt_params = {'year': year} if year else {}
        return self.eactivities.get('reports/onlinesales', params=opt_params).json()

class eActivitiesProducts(object):
    def __init__(self, eactivities):
        self.eactivities = eactivities

    def list(self):
        return self.eactivities.get('products').json()

    def details(self, id_):
        return self.eactivities.get(posixpath.join('products', id_)).json()

    def sales(self, id_):
        return self.eactivities.get(posixpath.join('products', id_, 'sales')).json()
