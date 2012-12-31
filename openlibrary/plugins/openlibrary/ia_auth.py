import web
import urllib
import simplejson

from infogami.utils import delegate
from infogami.utils.view import public
from openlibrary.core import ia
from openlibrary.core import helpers as h

def setup():
    pass

class ia_auth(delegate.page):
    path = "/account/ia-auth"
    def GET(self):
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        callback = web.ctx.home + "/account/ia-auth-callback?" + urllib.urlencode(dict(next=referer))
        url = ia.make_ia_url("/account/auth.php", next=callback)
        raise web.seeother(url)

class ia_logout(delegate.page):
    path = "/account/ia-logout"
    def POST(self):
        web.setcookie("ia_auth", "", expires=-1)
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        raise web.seeother(referer)

class ia_auth_callback(delegate.page):
    path = "/account/ia-auth-callback"
    
    def GET(self):
        i = web.input(token="", userid="", next="/")
        if ia.verify_token(i.userid, i.token):
            cookie = i.userid + "$" + ia.make_token(i.userid, 365*24*3600)
            web.setcookie("ia_auth", cookie)
        raise web.seeother(i.next)

def get_current_username():
    cookie = web.cookies(ia_auth="").ia_auth
    if cookie:
        try:
            username, token = cookie.split("$")
        except ValueError:
            return
        if ia.verify_token(username, token):
            return username

@public
def get_ia_user():
    username = get_current_username()
    return username and ArchiveUser(username)

class ArchiveUser:
    def __init__(self, username):
        self.username = username

    def get_loans(self):
        return [self._prepare_loan(loan) for loan in self._fetch_loans(self.username)]

    def _fetch_loans(self, username):
        token = ia.make_token(username, 10)
        url = ia.make_ia_url("/account/loans.php", format="json", userid=username, token=token)
        try:
            jsontext = urllib.urlopen(url).read()
            data = simplejson.loads(jsontext)
            return data['loans']
        except IOError:
            return []

    def _prepare_loan(self, loan):
        loan = web.storage(loan)
        loan.book = self._find_ol_key(loan.identifier)
        loan.ocaid = loan.identifier
        loan.loan_link = ""
        loan.resource_type = loan.format
        loan.return_url = ia.make_ia_url("/borrow.php", identifier=loan['identifier'])
        loan.read_url = ia.make_ia_url("/borrow.php", identifier=loan['identifier'])
        loan.loaned_at = self.datetime_to_float(h.parse_datetime(loan.created))
        if loan.fulfilled:
            loan.expiry = loan.until
        else:
            loan.expiry = None
        return loan

    def datetime_to_float(self, d):
        return float(d.strftime("%s.%f"))

    def _find_ol_key(self, itemid):
        keys = web.ctx.site.things({"type": "/type/edition", "ocaid": itemid})
        return keys and keys[0] or None
        
    def _get_doc(self, itemid):
        keys = web.ctx.site.things({"type": "/type/edition", "ocaid": itemid})
        if keys:
            return web.ctx.site.get(keys[0])
