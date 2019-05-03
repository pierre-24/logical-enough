import functools

import flask
from flask.views import MethodView

from models import User
from forms import LoginForm


class RenderTemplateView(MethodView):

    template_name = None

    def get_context_data(self, *args, **kwargs):
        return {}

    def get(self, *args, **kwargs):
        if not self.template_name:
            raise ValueError('template_name')

        context_data = self.get_context_data(*args, **kwargs)
        return flask.render_template(self.template_name, **context_data)


class FormView(RenderTemplateView):

    form_class = None
    success_url = '/'
    failure_url = '/'
    modal_form = False

    def get_form_kwargs(self):
        return {}

    def get_form(self):
        """Return an instance of the form"""
        return self.form_class(**self.get_form_kwargs())

    def get_context_data(self, *args, **kwargs):
        """Insert form in context data"""

        context = super().get_context_data(*args, **kwargs)

        if 'form' not in context:
            context['form'] = kwargs.pop('form', self.get_form())

        return context

    def post(self, *args, **kwargs):
        """Handle POST: validate form."""

        if not self.form_class:
            raise ValueError('form_class')

        form = self.get_form()

        if form.validate_on_submit():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        """If the form is valid, go to the success url"""

        return flask.redirect(self.success_url)

    def form_invalid(self, form):
        """If the form is invalid, go back to the same page with an error"""

        if not self.modal_form:
            return self.get(form=form)
        else:
            return flask.redirect(self.failure_url)


class PageContextMixin:
    """Maintain the logged_in information in context"""

    LOGIN_VAR = 'logged_user'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['user'] = self.get_user()

        return context

    @staticmethod
    def get_user():
        """Get logged in user"""

        if PageContextMixin.LOGIN_VAR in flask.session:
            return User.query\
                .filter(User.id.is_(flask.session[PageContextMixin.LOGIN_VAR]))\
                .first()

        return None

    @staticmethod
    def login_user(eid):
        user = User.query.filter(User.eid.is_(eid)).first()

        if user is None:
            flask.flash("Tu n'existes pas, va t'en !", 'error')
            return None

        flask.session[PageContextMixin.LOGIN_VAR] = user.id
        if user.is_admin:
            flask.session['is_admin'] = True
        else:
            flask.session['is_admin'] = False

        return user

    @staticmethod
    def login_required(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if PageContextMixin.LOGIN_VAR not in flask.session:
                return flask.redirect(flask.url_for('login', next=flask.request.url))
            return f(*args, **kwargs)
        return decorated_function

    @staticmethod
    def admin_required(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'is_admin' not in flask.session:
                return flask.abort(403)
            return f(*args, **kwargs)
        return decorated_function


@PageContextMixin.login_required
def logout():
    del flask.session[PageContextMixin.LOGIN_VAR]
    return flask.redirect(flask.url_for('login'))


class IndexPage(PageContextMixin, RenderTemplateView):
    template_name = 'index.html'
    decorators = [PageContextMixin.login_required]


class LoginPage(FormView):
    form_class = LoginForm
    template_name = 'login.html'

    def dispatch_request(self, *args, **kwargs):

        if PageContextMixin.get_user() is not None:
            flask.flash('Vous êtes déjà entré!', category='error')
            return flask.redirect(flask.url_for('index'))

        return super().dispatch_request(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context['next'] = flask.request.args.get('next', '')

        return context

    def form_valid(self, form):

        login = form.login.data
        user = PageContextMixin.login_user(login)

        if user is not None:
            flask.flash('Bienvenue !', 'success')

            self.success_url = flask.url_for('index')
            if 'next' in flask.request.args and flask.request.args['next'] != '':
                self.success_url = flask.request.args['next']

            return super().form_valid(form)

        else:
            return self.form_invalid(form)
