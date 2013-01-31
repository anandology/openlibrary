import web
import hmac
import logging
import random
import urllib
import uuid
import datetime, time

from infogami.utils import delegate
from infogami import config
from infogami.utils.view import require_login, render, render_template, add_flash_message
from infogami.infobase.client import ClientException
from infogami.utils.context import context
import infogami.core.code as core

from openlibrary.i18n import gettext as _
from openlibrary.core import helpers as h
from openlibrary.core import support
from openlibrary import accounts
from openlibrary.core import ia

import forms
import utils
import borrow

from openlibrary.plugins.recaptcha import recaptcha

logger = logging.getLogger("openlibrary.account")

# XXX: These need to be cleaned up
Account = accounts.Account
send_verification_email = accounts.send_verification_email
create_link_doc = accounts.create_link_doc
sendmail = accounts.sendmail

class account(delegate.page):
    """Account preferences.
    """
    @require_login
    def GET(self):
        user = accounts.get_current_user()
        return render.account(user)

class account_create(delegate.page):
    """New account creation.

    Account will in the pending state until the email is activated.
    """
    path = "/account/create"

    def GET(self):
        # redirect to archive.org sign up page
        raise web.redirect(ia.make_ia_url("/account/login.createaccount.php", source=openlibrary))

del delegate.pages['/account/register']

class account_login(delegate.page):
    """Account login.

    Login can fail because of the following reasons:

    * account_not_found: Error message is displayed.
    * account_bad_password: Error message is displayed with a link to reset password.
    * account_not_verified: Error page is dispalyed with button to "resend verification email".
    """
    path = "/account/login"

    def GET(self):
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        i = web.input(redirect=referer)
        return self.redirect(next=i.redirect)

        f = forms.Login()
        f['redirect'].value = i.redirect
        return render.login(f)

    def POST(self):
        i = web.input(remember=False, redirect='/', action="login")

        if i.action == "resend_verification_email":
            return self.POST_resend_verification_email(i)
        else:
            return self.POST_login(i)

    def error(self, name, i):
        f = forms.Login()
        f.fill(i)
        f.note = utils.get_error(name)
        return render.login(f)

    def POST_login(self, i):
        # make sure the username is valid
        if not forms.vlogin.valid(i.username):
            return self.error("account_user_notfound", i)

        # Try to find account with exact username, failing which try for case variations.
        account = accounts.find(username=i.username) or accounts.find(lusername=i.username)

        if not account:
            return self.error("account_user_notfound", i)

        if i.redirect == "/account/login" or i.redirect == "":
            i.redirect = "/"

        status = account.login(i.password)
        if status == 'ok':
            expires = (i.remember and 3600*24*7) or ""
            web.setcookie(config.login_cookie_name, web.ctx.conn.get_auth_token(), expires=expires)
            raise web.seeother(i.redirect)
        elif status == "account_not_verified":
            return render_template("account/not_verified", username=account.username, password=i.password, email=account.email)
        elif status == "account_not_found":
            return self.error("account_user_notfound", i)
        elif status == "account_blocked":
            return self.error("account_blocked", i)
        else:
            return self.error("account_incorrect_password", i)

    def POST_resend_verification_email(self, i):
        try:
            accounts.login(i.username, i.password)
        except ClientException, e:
            code = e.get_data().get("code")
            if code != "account_not_verified":
                return self.error("account_incorrect_password", i)

        account = accounts.find(username=i.username)
        account.send_verification_email()

        title = _("Hi %(user)s", user=account.displayname)
        message = _("We've sent the verification email to %(email)s. You'll need to read that and click on the verification link to verify your email.", email=account.email)
        return render.message(title, message)

    def redirect(self, next=None, redirect="true"):
        referer = next or web.ctx.env.get('HTTP_REFERER', '/')
        callback = web.ctx.home + "/account/ia-auth-callback?" + urllib.urlencode(dict(next=referer))
        url = ia.make_ia_url("/account/auth.php", next=callback, redirect=redirect)
        raise web.seeother(url)

class account_logout(delegate.page):
    path = "/account/logout"

    def POST(self):
        referer = web.ctx.env.get('HTTP_REFERER', web.ctx.home + "/")
        web.setcookie(config.login_cookie_name, "", expires=-1)
        url = ia.make_ia_url("/account/logout.php", next=referer)
        return web.seeother(url)

class account_verify(delegate.page):
    """Verify user account.
    """
    path = "/account/verify/([0-9a-f]*)"

    def GET(self, code):
        docs = web.ctx.site.store.values(type="account-link", name="code", value=code)
        if docs:
            doc = docs[0]

            account = accounts.find(username = doc['username'])
            if account:
                if account['status'] != "pending":
                    return render['account/verify/activated'](account)
            account.activate()
            user = web.ctx.site.get("/people/" + doc['username']) #TBD
            return render['account/verify/success'](account)
        else:
            return render['account/verify/failed']()

    def POST(self, code=None):
        """Called to regenerate account verification code.
        """
        i = web.input(email=None)
        account = accounts.find(email=i.email)
        if not account:
            return render_template("account/verify/failed", email=i.email)
        elif account['status'] != "pending":
            return render['account/verify/activated'](account)
        else:
            account.send_verification_email()
            title = _("Hi %(user)s", user=account.displayname)
            message = _("We've sent the verification email to %(email)s. You'll need to read that and click on the verification link to verify your email.", email=account.email)
            return render.message(title, message)

class account_verify_old(account_verify):
    """Old account verification code.

    This takes username, email and code as url parameters. The new one takes just the code as part of the url.
    """
    path = "/account/verify"
    def GET(self):
        # It is too long since we switched to the new account verification links.
        # All old links must be expired by now.
        # Show failed message without thinking.
        return render['account/verify/failed']()

class account_email(delegate.page):
    """Change email.
    """
    path = "/account/email"

    def get_email(self):
        user = accounts.get_current_user()
        return user.get_account()['email']

    @require_login
    def GET(self):
        f = forms.ChangeEmail()
        return render['account/email'](self.get_email(), f)

    @require_login
    def POST(self):
        f = forms.ChangeEmail()
        i = web.input()

        if not f.validates(i):
            return render['account/email'](self.get_email(), f)
        else:
            user = accounts.get_current_user()
            username = user.key.split('/')[-1]

            displayname = user.displayname or username

            send_email_change_email(username, i.email)

            title = _("Hi %(user)s", user=user.displayname or username)
            message = _("We've sent an email to %(email)s. You'll need to read that and click on the verification link to update your email.", email=i.email)
            return render.message(title, message)

class account_email_verify(delegate.page):
    path = "/account/email/verify/([0-9a-f]*)"

    def GET(self, code):
        link = accounts.get_link(code)
        if link:
            username = link['username']
            email = link['email']
            link.delete()
            return self.update_email(username, email)
        else:
            return self.bad_link()

    def update_email(self, username, email):
        if accounts.find(email=email):
            title = _("Email address is already used.")
            message = _("Your email address couldn't be updated. The specified email address is already used.")
        else:
            logger.info("updated email of %s to %s", username, email)
            accounts.update_account(username=username, email=email, status="active")
            title = _("Email verification successful.")
            message = _('Your email address has been successfully verified and updated in your account.')
        return render.message(title, message)

    def bad_link(self):
        title = _("Email address couldn't be verified.")
        message = _("Your email address couldn't be verified. The verification link seems invalid.")
        return render.message(title, message)

class account_email_verify_old(account_email_verify):
    path = "/account/email/verify"

    def GET(self):
        # It is too long since we switched to the new email verification links.
        # All old links must be expired by now.
        # Show failed message without thinking.
        return self.bad_link()

class account_password(delegate.page):
    path = "/account/password"

    @require_login
    def GET(self):
        f = forms.ChangePassword()
        return render['account/password'](f)

    @require_login
    def POST(self):
        f = forms.ChangePassword()
        i = web.input()

        if not f.validates(i):
            return render['account/password'](f)

        user = accounts.get_current_user()
        username = user.key.split("/")[-1]

        if self.try_login(username, i.password):
            accounts.update_account(username, password=i.new_password)
            add_flash_message('note', _('Your password has been updated successfully.'))
            raise web.seeother('/account')
        else:
            f.note = "Invalid password"
            return render['account/password'](f)

    def try_login(self, username, password):
        account = accounts.find(username=username)
        return account and account.verify_password(password)

class account_password_forgot(delegate.page):
    path = "/account/password/forgot"

    def GET(self):
        f = forms.ForgotPassword()
        return render['account/password/forgot'](f)

    def POST(self):
        i = web.input(email='')

        f = forms.ForgotPassword()

        if not f.validates(i):
            return render['account/password/forgot'](f)

        account = accounts.find(email=i.email)

        if account.is_blocked():
            f.note = utils.get_error("account_blocked")
            return render_template('account/password/forgot', f)

        send_forgot_password_email(account.username, i.email)
        return render['account/password/sent'](i.email)

class account_password_reset(delegate.page):

    path = "/account/password/reset/([0-9a-f]*)"

    def GET(self, code):
        docs = web.ctx.site.store.values(type="account-link", name="code", value=code)
        if not docs:
            title = _("Password reset failed.")
            message = "Your password reset link seems invalid or expired."
            return render.message(title, message)

        f = forms.ResetPassword()
        return render['account/password/reset'](f)

    def POST(self, code):
        link = accounts.get_link(code)
        if not link:
            title = _("Password reset failed.")
            message = "The password reset link seems invalid or expired."
            return render.message(title, message)

        username = link['username']
        i = web.input()

        accounts.update_account(username, password=i.password)
        link.delete()
        return render_template("account/password/reset_success", username=username)

class account_notifications(delegate.page):
    path = "/account/notifications"

    @require_login
    def GET(self):
        user = accounts.get_current_user()
        prefs = web.ctx.site.get(user.key + "/preferences")
        d = (prefs and prefs.get('notifications')) or {}
        email = accounts.get_current_user().email
        return render['account/notifications'](d, email)

    @require_login
    def POST(self):
        user = accounts.get_current_user()
        key = user.key + '/preferences'
        prefs = web.ctx.site.get(key)

        d = (prefs and prefs.dict()) or {'key': key, 'type': {'key': '/type/object'}}

        d['notifications'] = web.input()

        web.ctx.site.save(d, 'save notifications')

        add_flash_message('note', _("Notification preferences have been updated successfully."))
        web.seeother("/account")

class account_loans(delegate.page):
    path = "/account/loans"

    @require_login
    def GET(self):
        user = accounts.get_current_user()
        loans = user.get_loans(_cache="update")
        return render['account/borrow'](user, loans)

class account_ia_auth_callback(delegate.page):
    path = "/account/ia-auth-callback"

    def GET(self):
        i = web.input(token="", ia_username="", next="/", remember="")
        self.process_input(i)

        f = forms.Login()
        return self.render(i.ia_username, f, forms.NewAccount())

    def render(self, ia_email, login_form, newaccount_form):
        # generate a new token as the token came from archive.org is short-lived
        token = ia.make_token(ia_email, 3600*12)
        return render["account/link"](login_form, newaccount_form, ia_email, token)

    def POST(self):
        i = web.input(token="", ia_username="", next="/", remember="", action=None, ia_email=None, _method="POST")
        self.process_input(i)

        if i.get("action") == "link":
            return self.POST_link(i)
        elif i.get("action") == "new-account":
            return self.POST_new_account(i)
        else:
            return self.render(i.ia_email, forms.Login(), forms.NewAccount())

    def POST_link(self, i):
        f = forms.Login()
        if f.validates(i):
            account = accounts.find(i.username)
            account.link(i.ia_email)
            self.setcookie(account, i.remember)
            raise web.seeother(i.next)
        else:
            return self.render(f, i.ia_email)

    def POST_new_account(self, i):
        displayname = ia.get_account_details(i.ia_email).get('screenname') or i.username

        f = forms.NewAccount()
        if not f.validates(i):
            return self.render(i.ia_email, forms.Login(), f)

        accounts.register(username=i.username,
                  email="%s@example.com" % uuid.uuid4(),
                  password="",
                  displayname=displayname)
        account = accounts.find(username=i.username)
        account.activate()
        account.link(i.ia_email)
        self.setcookie(account, i.remember)            
        raise web.seeother(i.next)

    def process_input(self, i):
        # for POST requests, we'll have ia_email
        # and for GET requests, we'll have username
        ia_email = i.get("ia_email") or i.get("ia_username")

        if not ia.verify_token(ia_email, i.token):
            # Invalid token. Try login again.
            return account_login().redirect(i.next)

        account = accounts.find(ia_email=ia_email)

        # If the token is valid and account is already linked, 
        # redirect to the next URL after setting the login cookie
        if account:
            self.setcookie(account, i.remember)
            raise web.seeother(i.next)

    def setcookie(self, account, remember=False):
        expires = (remember and 3600*24*7) or ""
        cookie = account.fake_login_cookie()
        web.setcookie(config.login_cookie_name, cookie, expires=expires)

class account_others(delegate.page):
    path = "(/account/.*)"

    def GET(self, path):
        return render.notfound(path, create=False)


####


def send_email_change_email(username, email):
    key = "account/%s/email" % username

    doc = create_link_doc(key, username, email)
    web.ctx.site.store[key] = doc

    link = web.ctx.home + "/account/email/verify/" + doc['code']
    msg = render_template("email/email/verify", username=username, email=email, link=link)
    sendmail(email, msg)

def send_forgot_password_email(username, email):
    key = "account/%s/password" % username

    doc = create_link_doc(key, username, email)
    web.ctx.site.store[key] = doc

    link = web.ctx.home + "/account/password/reset/" + doc['code']
    msg = render_template("email/password/reminder", username=username, link=link)
    sendmail(email, msg)




def as_admin(f):
    """Infobase allows some requests only from admin user. This decorator logs in as admin, executes the function and clears the admin credentials."""
    def g(*a, **kw):
        try:
            delegate.admin_login()
            return f(*a, **kw)
        finally:
            web.ctx.headers = []
    return g
