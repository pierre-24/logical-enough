import functools

import flask
from flask.views import MethodView

from logical_enough.models import User, Challenge, Question, UserChallenge, Answer
from logical_enough.forms import LoginForm, UserForm, ChallengeForm, QuestionForm
from logical_enough import logic, db


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


@PageContextMixin.login_required
def logout():
    del flask.session[PageContextMixin.LOGIN_VAR]
    return flask.redirect(flask.url_for('login'))


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


class IndexPage(PageContextMixin, RenderTemplateView):
    template_name = 'index.html'
    decorators = [PageContextMixin.login_required]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context['challenges'] = Challenge.query.filter(Challenge.is_public.is_(True)).all()
        context['user_challenges'] = dict(
            (c.challenge, c) for c in UserChallenge.query.filter(UserChallenge.user.is_(self.get_user().id)).all())
        return context


class ChallengePage(PageContextMixin, GetObjectMixin, RenderTemplateView):

    decorators = [PageContextMixin.login_required]
    template_name = 'challenge.html'
    model = Challenge
    context_object_name = 'challenge'

    current_question = None
    challenge_done = False

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if not obj.is_public:
            flask.abort(404)

        user_challenge = UserChallenge.query\
            .filter(UserChallenge.user.is_(self.get_user().id))\
            .filter(UserChallenge.challenge.is_(obj.id))\
            .first()

        if user_challenge is None:  # never did the challenge, starts it
            self.current_question = Question.query.filter(Question.challenge.is_(obj.id)).first()
            user_challenge = UserChallenge(self.get_user().id, obj.id, self.current_question.id)
            db.session.add(user_challenge)
            db.session.commit()
        else:
            self.challenge_done = user_challenge.is_done
            if not self.challenge_done:
                self.current_question = Question.query.get(user_challenge.current_question)

        return obj

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['question'] = self.current_question
        context['challenge_done'] = self.challenge_done

        questions = self.object.get_questions()
        if self.challenge_done:
            context['progression'] = (len(questions), len(questions))
        else:
            context['progression'] = ([q.id for q in questions].index(self.current_question.id) + 1, len(questions))

        return context


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

        if User.query.filter(User.name.is_(form.login.data)).count() > 0:
            flask.flash("Impossible d'ajouter 2 fois la même personne", 'error')
            return super().form_invalid(form)

        user = User(form.login.data, is_admin=form.is_admin.data)
        db.session.add(user)
        db.session.commit()

        flask.flash('Personne ajoutée', 'success')
        self.success_url = flask.url_for('admin-users')

        return super().form_valid(form)


class AdminUsersDelete(DeleteView):
    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    model = User

    def pre_deletion(self, obj, *args, **kwargs):
        if obj.is_admin:
            flask.flash('Impossible de supprimer un admin !!', 'error')
            return False

        return True

    def delete(self, *args, **kwargs):
        self.success_url = flask.url_for('admin-users')
        flask.flash('Utilisateur supprimé', 'success')
        return super().delete(*args, **kwargs)


class AdminChallengesPage(PageContextMixin, FormView):
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
        db.session.add(challenge)
        db.session.commit()

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
            db.session.add(challenge)
            db.session.commit()
        else:
            flask.flash("Ce challenge n'existe pas")

        return flask.redirect(flask.url_for('admin-challenges'))


class AdminChallengePage(PageContextMixin, GetObjectMixin, RenderTemplateView):

    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    template_name = 'admin/challenge.html'
    model = Challenge
    context_object_name = 'challenge'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['questions'] = Question.query.filter(Question.challenge.is_(self.object.id))

        return context


class AdminCreateQuestionPage(PageContextMixin, GetObjectMixin, FormView):
    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    template_name = 'admin/question-create.html'
    model = Challenge
    context_object_name = 'challenge'

    form_class = QuestionForm

    def post(self, *args, **kwargs):
        self.get_object(*args, **kwargs)
        return super().post(*args, **kwargs)

    def form_valid(self, form):
        q = AdminQuestionPage.treat_form(form, self.object)
        if q is None:
            return self.form_invalid(form)

        db.session.add(q)
        db.session.commit()

        self.success_url = flask.url_for('admin-challenge', id=self.object.id)
        return super().form_valid(form)


class AdminQuestionPage(PageContextMixin, GetObjectMixin, FormView):

    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    model = Question
    context_object_name = 'question'
    template_name = 'admin/question-edit.html'
    form_class = QuestionForm

    challenge = None

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)

        if obj.challenge != kwargs.get('challenge_id', -1):
            flask.abort(404)

        self.challenge = Challenge.query.filter(Challenge.id.is_(obj.challenge)).first()
        if self.challenge is None:
            flask.abort(404)

        return obj

    def get(self, *args, **kwargs):
        self.get_object(*args, **kwargs)
        return super().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.get_object(*args, **kwargs)
        return super().post(*args, **kwargs)

    def get_form_kwargs(self):
        return {
            'hint_expr': self.object.hint_expr,
            'hint': self.object.hint,
            'documents': ';'.join(self.object.get_documents())
        }

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['challenge'] = self.challenge
        return context

    @staticmethod
    def treat_form(form, challenge, obj=None):
        try:
            search_expression = logic.parse(form.data.get('hint_expr'))
        except logic.ParserException as e:
            flask.flash('Erreur du parser: "{}"'.format(e), 'error')
            return None

        documents = form.data.get('documents').split(';')
        good_docs = []
        wrong_docs = []

        for d in documents:
            if search_expression.match(d):
                good_docs.append(d)
            else:
                wrong_docs.append(d)

        if len(good_docs) == 0:
            flask.flash('Il doit y avoir au moins un bon document', 'error')
            return None

        if obj is None:
            obj = Question(
                challenge=challenge.id,
                position=Challenge.query.count(),
                wrong_docs=wrong_docs,
                good_docs=good_docs,
                hint=form.data.get('hint'),
                hint_expr=str(search_expression)
            )

            flask.flash('Question ajoutée', 'success')
        else:
            obj.wrong_documents = ';'.join(wrong_docs)
            obj.good_documents = ';'.join(good_docs)
            obj.hint = form.data.get('hint')
            obj.hint_expr = str(search_expression)

            flask.flash('Question modifiée', 'success')

        return obj

    def form_valid(self, form):
        q = AdminQuestionPage.treat_form(form, self.challenge, self.object)
        if q is None:
            return self.form_invalid(form)

        db.session.add(q)
        db.session.commit()
        self.success_url = flask.url_for('admin-challenge', id=self.challenge.id)

        return super().form_valid(form)


class AdminQuestionDelete(DeleteView):
    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    model = Question

    def pre_deletion(self, obj, *args, **kwargs):
        if obj.challenge != kwargs.get('challenge_id', -1):
            flask.abort(404)

        self.success_url = flask.url_for('admin-challenge', id=self.object.challenge)
        return True

    def delete(self, *args, **kwargs):
        flask.flash('Question supprimée', 'success')
        return super().delete(*args, **kwargs)


class AdminViewAnswerPage(PageContextMixin, GetObjectMixin, RenderTemplateView):

    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]
    model = Question
    context_object_name = 'question'
    template_name = 'admin/answers.html'

    challenge = None

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)

        if obj.challenge != kwargs.get('challenge_id', -1):
            flask.abort(404)

        self.challenge = Challenge.query.filter(Challenge.id.is_(obj.challenge)).first()
        if self.challenge is None:
            flask.abort(404)

        return obj

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['challenge'] = self.challenge
        context['answers'] = Answer.query.filter(Answer.question.is_(self.object.id)).all()
        context['users'] = dict((u.id, u) for u in User.query.all())

        return context
