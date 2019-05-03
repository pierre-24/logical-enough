import functools

import flask
from flask.views import MethodView

from models import User, Challenge
from forms import LoginForm, UserForm, ChallengeForm
import commons


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


class DeleteView(MethodView):

    success_url = '/'
    model = None
    url_parameter = 'id'

    def get_object(self, *args, **kwargs):

        obj = self.model.query.get(kwargs.get(self.url_parameter))

        if obj is None:
            flask.abort(404)

        return obj

    def pre_deletion(self, obj):
        """
        Performs an action before deletion from database (checks something, for example)
        Note: if return `False`, deletion is not performed
        """
        return True

    def post_deletion(self, obj):
        """Performs an action after deletion from database"""
        pass

    def post(self, *args, **kwargs):
        return self.delete(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Handle delete"""

        obj = self.get_object(*args, **kwargs)

        if not self.pre_deletion(obj):
            return flask.abort(403)

        commons.db.session.delete(obj)
        commons.db.session.commit()

        self.post_deletion(obj)

        return flask.redirect(self.success_url)


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
            if 'is_admin' not in flask.session or not flask.session['is_admin']:
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


# ADMIN
class AdminUsersPage(PageContextMixin, FormView):
    form_class = UserForm
    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    template_name = 'admin/users.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context['users'] = User.query.all()
        return context

    def form_valid(self, form):

        if User.query.filter(User.eid.is_(form.eid.data)).count() > 0:
            flask.flash("Impossible d'ajouter 2 fois la même personne", 'error')
            return super().form_invalid(form)

        user = User(form.eid.data, is_admin=form.is_admin.data)
        commons.db.session.add(user)
        commons.db.session.commit()

        flask.flash('Personne ajoutée', 'success')
        self.success_url = flask.url_for('admin-users')

        return super().form_valid(form)


class AdminUsersDelete(DeleteView):
    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    model = User

    def pre_deletion(self, obj):
        if obj.is_admin:
            flask.flash('Impossible de supprimer un admin !!', 'error')
            return False

        return True

    def delete(self, *args, **kwargs):
        self.success_url = flask.url_for('admin-users')
        flask.flash('Utilisateur supprimé', 'success')
        return super().delete(*args, **kwargs)


class AdminChallengePage(PageContextMixin, FormView):
    form_class = ChallengeForm
    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    template_name = 'admin/challenges.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context['challenges'] = Challenge.query.all()
        return context

    def form_valid(self, form):

        if Challenge.query.filter(Challenge.name.is_(form.name.data)).count() > 0:
            flask.flash("Impossible d'ajouter 2 fois le même challenge", 'error')
            return super().form_invalid(form)

        challenge = Challenge(form.name.data)
        commons.db.session.add(challenge)
        commons.db.session.commit()

        flask.flash('Challenge créé', 'success')
        self.success_url = flask.url_for('admin-challenges')

        return super().form_valid(form)


class AdminChallengesDelete(DeleteView):
    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    model = Challenge

    def delete(self, *args, **kwargs):
        self.success_url = flask.url_for('admin-challenges')
        flask.flash('Challenge supprimé', 'success')
        return super().delete(*args, **kwargs)


class AdminChallengesToggle(PageContextMixin, MethodView):
    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]

    def get(self, *args, **kwargs):
        id = kwargs.get('id', -1)
        challenge = Challenge.query.get(id)

        if challenge is not None:
            challenge.is_public = not challenge.is_public
            commons.db.session.add(challenge)
            commons.db.session.commit()
        else:
            flask.flash("Ce challenge n'existe pas")

        return flask.redirect(flask.url_for('admin-challenges'))
