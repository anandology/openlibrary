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
        i = web.input(next=None, redirect="true")
        return self.redirect(i.next, i.redirect)

    def redirect(self, next=None, redirect="true"):
        referer = next or web.ctx.env.get('HTTP_REFERER', '/')
        callback = web.ctx.home + "/account/ia-auth-callback?" + urllib.urlencode(dict(next=referer))
        url = ia.make_ia_url("/account/auth.php", next=callback, redirect=redirect)
        raise web.seeother(url)

class ia_logout(delegate.page):
    path = "/account/ia-logout"
    def POST(self):
        web.setcookie("ia_auth", "", expires=5*60)
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        url = ia.make_ia_url("/account/logout.php", next=referer)
        raise web.seeother(url)

class ia_auth_callback(delegate.page):
    path = "/account/ia-auth-callback"
    
    def GET(self):
        i = web.input(token="", username="", next="/")
        if ia.verify_token(i.username, i.token):
            cookie = i.username + "$" + ia.make_token(i.username, 365*24*3600)
            # cookie is valid for 5 minutes. After that it will again check
            # for login.
            web.setcookie("ia_auth", cookie, expires=5*60)
        raise web.seeother(i.next)

def check_ia_auth():
    """Contacts archive.org to get the latest info of the currently logged-in 
    user, if not already logged in.
    """
    if "ia_auth" not in web.cookies():
        # when /books/OL1M/foo/borrow?x=1 is accessed:
        #   web.ctx.fullpath = "/books/OL1M/borrow?x=1"
        #   web.ctx.readable_fullpath = "/books/OL1M/foo/borrow?x=1"
        next = web.ctx.get("readable_fullpath") or web.ctx.fullpath
        return ia_auth().redirect(next=next, redirect="false")

def get_current_username():
    cookie = web.cookies(ia_auth=None).ia_auth
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
        loans = [self._prepare_loan(loan) for loan in self._fetch_loans(self.username)]
        return [loan for loan in loans if loan]

    def _fetch_loans(self, username):
        token = ia.make_token(username, 10)
        url = ia.make_ia_url("/account/loans.php", format="json", username=username, token=token)
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

        if loan.book is None:
            return None
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
