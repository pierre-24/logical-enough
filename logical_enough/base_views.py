import functools

import flask
from flask.views import MethodView

from logical_enough import db
from logical_enough.models import User


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

    url_args = []
    url_kwargs = {}

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

        self.url_args = args
        self.url_kwargs = kwargs

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
            return self.get(form=form, *self.url_args, **self.url_kwargs)
        else:
            return flask.redirect(self.failure_url)


class GetObjectMixin:
    model = None
    context_object_name = 'object'
    url_parameter = 'id'

    object = None

    def get_object(self, *args, **kwargs):

        if self.object is None:
            obj = self.model.query.get(kwargs.get(self.url_parameter))

            if obj is None:
                flask.abort(404)

            self.object = obj
        return self.object

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context[self.context_object_name] = self.get_object(*args, **kwargs)
        return context


class DeleteView(GetObjectMixin, MethodView):

    success_url = '/'

    def pre_deletion(self, obj, *args, **kwargs):
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

        if not self.pre_deletion(obj, *args, **kwargs):
            return flask.abort(403)

        db.session.delete(obj)
        db.session.commit()

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
        user = User.query.filter(User.name.is_(eid)).first()

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