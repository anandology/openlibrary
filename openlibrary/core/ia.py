"""Library for interacting wih archive.org.
"""
import urllib2
from xml.dom import minidom
import simplejson
import web
import urllib
import time
import hmac
import logging

from infogami.utils import stats
from infogami import config
from openlibrary.core import helpers as h

import cache

logger = logging.getLogger("openlibrary.ia")

def get_meta_xml(itemid):
    """Returns the contents of meta_xml as JSON.
    """
    itemid = web.safestr(itemid.strip())
    url = 'http://www.archive.org/download/%s/%s_meta.xml' % (itemid, itemid)
    try:
        stats.begin("archive.org", url=url)
        metaxml = urllib2.urlopen(url).read()
        stats.end()
    except IOError:
        stats.end()
        return web.storage()
        
    # archive.org returns html on internal errors. 
    # Checking for valid xml before trying to parse it.
    if not metaxml.strip().startswith("<?xml"):
        return web.storage()
    
    try:
        defaults = {"collection": [], "external-identifier": []}
        return web.storage(xml2dict(metaxml, **defaults))
    except Exception, e:
        print >> web.debug, "Failed to parse metaxml for %s: %s" % (itemid, str(e)) 
        return web.storage()
        
get_meta_xml = cache.memcache_memoize(get_meta_xml, key_prefix="ia.get_meta_xml", timeout=5*60)
        
def xml2dict(xml, **defaults):
    """Converts xml to python dictionary assuming that the xml is not nested.
    
    To get some tag as a list/set, pass a keyword argument with list/set as value.
    
        >>> xml2dict('<doc><x>1</x><x>2</x></doc>')
        {'x': 2}
        >>> xml2dict('<doc><x>1</x><x>2</x></doc>', x=[])
        {'x': [1, 2]}
    """
    d = defaults
    dom = minidom.parseString(xml)
    
    for node in dom.documentElement.childNodes:
        if node.nodeType == node.TEXT_NODE or len(node.childNodes) == 0:
            continue
        else:
            key = node.tagName
            value = node.childNodes[0].data
            
            if key in d and isinstance(d[key], list):
                d[key].append(value)
            elif key in d and isinstance(d[key], set):
                d[key].add(value)
            else:
                d[key] = value
                
    return d
    
def _get_metadata(itemid):
    """Returns metadata by querying the archive.org metadata API.
    """
    print >> web.debug, "_get_metadata", itemid
    url = "http://www.archive.org/metadata/%s" % itemid
    try:
        stats.begin("archive.org", url=url)        
        text = urllib2.urlopen(url).read()
        stats.end()
        return simplejson.loads(text)
    except (IOError, ValueError):
        return None

# cache the results in memcache for a minute
_get_metadata = web.memoize(_get_metadata, expires=60)
        
def locate_item(itemid):
    """Returns (hostname, path) for the item. 
    """
    d = _get_metadata(itemid)
    return d.get('server'), d.get('dir')


def get_ia_host():
    return config.get("ia_host", "archive.org")

def make_ia_url(path, **kwargs):
    url = "http://" + get_ia_host() + path
    if kwargs:
        url += "?" + urllib.urlencode(kwargs)
    return url

def _get_ia_secret():
    try:
        return config.ia_access_secret
    except AttributeError:
        raise Exception("config value config.ia_access_secret is not present -- check your config")

def make_token(name, expiry_seconds):
    """Cryptographically signs the name using a secret key shared betwen openlibrary and archvie.org.

    The expiry_seconds parameters specifies how long the token is valid.

    The secret key is specified in the openlibrary config as ``ia_access_secret``.
    """
    timestamp = int(time.time() + expiry_seconds)
    return _sign_token(name, timestamp)

def _sign_token(data, timestamp):
    token_data = '%s-%d' % (data, timestamp)
    
    secret = _get_ia_secret()
    token = '%d-%s' % (timestamp, hmac.new(secret, token_data).hexdigest())
    return token

def verify_token(name, token):
    """Cryptographically verifies that the token is the given name signed by
    the secret key shared between archive.org and openlibrary.
    """
    try:
        access_key = config.ia_access_secret
    except AttributeError:
        raise Exception("config value config.ia_access_secret is not present -- check your config")
    
    # split token
    try:
        token_timestamp, token_hmac = token.split('-')
    except ValueError:
        return False
        
    # token expired?
    if int(token_timestamp) < time.time():
        return False

    # token matched?
    return token == _sign_token(name, int(token_timestamp))

def _internal_api(method, **kw):
    # take values in the sorted order of keys to compute token
    values = [kv[1] for kv in sorted(kw.items())]
    token = make_token("".join(values), 10)
    kw['method'] = method
    kw['token'] = token

    url = make_ia_url("/account/api.php", **kw)
    logger.info("API call: %s", url)

    # TODO: handle errors
    try:
        stats.begin("archive.org", url=url)
        jsontext = urllib.urlopen(url).read()
        return simplejson.loads(jsontext)
    finally:
        stats.end()

@cache.memoize(engine="memcache", key=lambda identifier: "user-loans-%s" % identifier, expires=60)
def get_loans(username):
    """Returns loans of the archive.org user identified bu the username.

    This uses the archive.org internal API to get this info.
    """
    data = _internal_api(method="get_loans", username=username)
    
    # create loan objects
    loans = [Loan(d) for d in data["loans"]]

    # consider only the ones which have a valid OL key
    # This can happen when the book is not loaded to openlibrary
    loans = [loan for loan in loans if loan.book]
    return loans

@cache.memoize(engine="memcache", key=lambda identifier: "book-loans-%s" % identifier, expires=60)
def get_loans_of_book(identifier):
    data = _internal_api(
        method="loan_status", 
        identifier=identifier)
    return data['loans']

def borrow(username, identifier, resource_type):
    """Borrows a book via archive.org internal API.    
    """
    data = _internal_api(
        method="borrow", 
        username=username, 
        identifier=identifier, 
        resource_type=resource_type)
    return data

def return_bookreader_loan(username, identifier):
    return _internal_api(
        method="return_bookreader_loan", 
        username=username,
        identifier=identifier)

def get_account_details(username):
    return _internal_api(
        method="get_account", 
        username=username)

class Loan(web.storage):
    def __init__(self, data):
        self.update(data)

        self.book = self._find_ol_key(self.identifier)
        self.ocaid = self.identifier
        self.loan_link = ""
        self.resource_type = self.format
        self.loaned_at = self.datetime_to_float(h.parse_datetime(self.created))
        if self.fulfilled:
            self.expiry = self.until
        else:
            self.expiry = None

        self.key = "loan-" + self.identifier
        self._key = self.key

    def datetime_to_float(self, d):
        return float(d.strftime("%s.%f"))

    def _find_ol_key(self, itemid):
        keys = web.ctx.site.things({"type": "/type/edition", "ocaid": itemid})
        return keys and keys[0] or None
