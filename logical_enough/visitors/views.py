import flask

from logical_enough import db
from logical_enough.visitors.forms import LoginForm
from logical_enough.models import Challenge, UserChallenge, Question
from logical_enough.base_views import RenderTemplateView, FormView, GetObjectMixin, PageContextMixin


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
