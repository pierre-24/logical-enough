import flask
from flask import Blueprint
from flask.views import MethodView

from logical_enough import db, logic
from logical_enough.admin.forms import UserForm, ChallengeForm, QuestionForm
from logical_enough.models import User, Challenge, Question, Answer
from logical_enough.base_views import RenderTemplateView, FormView, GetObjectMixin, DeleteView, PageContextMixin


admin_blueprint = Blueprint('admin', __name__, url_prefix='/admin')


class AdminContextMixin(PageContextMixin):
    decorators = [PageContextMixin.login_required, PageContextMixin.admin_required]


# --- Users
class AdminUsersPage(AdminContextMixin, FormView):
    form_class = UserForm
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
        self.success_url = flask.url_for('admin.users')

        return super().form_valid(form)


admin_blueprint.add_url_rule('/utilisateurs.html', view_func=AdminUsersPage.as_view('users'))


class AdminUsersDelete(AdminContextMixin, DeleteView):
    model = User

    def pre_deletion(self, obj, *args, **kwargs):
        if obj.is_admin:
            flask.flash('Impossible de supprimer un admin !!', 'error')
            return False

        return True

    def delete(self, *args, **kwargs):
        self.success_url = flask.url_for('admin.users')
        flask.flash('Utilisateur supprimé', 'success')
        return super().delete(*args, **kwargs)


admin_blueprint.add_url_rule('/utilisateur-del-<int:id>.html', view_func=AdminUsersDelete.as_view('user-delete'))


# -- Challenge
class AdminChallengesPage(AdminContextMixin, FormView):
    form_class = ChallengeForm
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
        self.success_url = flask.url_for('admin.challenges')

        return super().form_valid(form)


admin_blueprint.add_url_rule('/challenges.html', view_func=AdminChallengesPage.as_view('challenges'))


class AdminChallengeDelete(AdminContextMixin, DeleteView):
    model = Challenge

    def delete(self, *args, **kwargs):
        self.success_url = flask.url_for('admin.challenges')
        flask.flash('Challenge supprimé', 'success')
        return super().delete(*args, **kwargs)


admin_blueprint.add_url_rule(
    '/challenge-del-<int:id>.html', view_func=AdminChallengeDelete.as_view('challenge-delete'))


class AdminChallengeToggle(AdminContextMixin, MethodView):

    def get(self, *args, **kwargs):
        id = kwargs.get('id', -1)
        challenge = Challenge.query.get(id)

        if challenge is not None:
            challenge.is_public = not challenge.is_public
            db.session.add(challenge)
            db.session.commit()
        else:
            flask.flash("Ce challenge n'existe pas")

        return flask.redirect(flask.url_for('admin.challenges'))


admin_blueprint.add_url_rule(
    '/challenge-vue-<int:id>.html', view_func=AdminChallengeToggle.as_view('challenge-toggle'))


class AdminChallengePage(AdminContextMixin, GetObjectMixin, RenderTemplateView):

    template_name = 'admin/challenge.html'
    model = Challenge
    context_object_name = 'challenge'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['questions'] = Question.query.filter(Question.challenge.is_(self.object.id))

        return context


admin_blueprint.add_url_rule('/challenge-<int:id>.html', view_func=AdminChallengePage.as_view('challenge'))


# -- Questions
class AdminCreateQuestionPage(AdminContextMixin, GetObjectMixin, FormView):
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

        self.success_url = flask.url_for('admin.challenge', id=self.object.id)
        return super().form_valid(form)


admin_blueprint.add_url_rule(
    '/challenge-<int:id>/nouvelle-question.html', view_func=AdminCreateQuestionPage.as_view('question-create'))


class AdminQuestionPage(AdminContextMixin, GetObjectMixin, FormView):

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
            if search_expression.match(logic.analyze(d)):
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
        self.success_url = flask.url_for('admin.challenge', id=self.challenge.id)

        return super().form_valid(form)


admin_blueprint.add_url_rule(
    '/challenge-<int:challenge_id>/question-<int:id>.html', view_func=AdminQuestionPage.as_view('question'))


class AdminQuestionDelete(AdminContextMixin, DeleteView):
    model = Question

    def pre_deletion(self, obj, *args, **kwargs):
        if obj.challenge != kwargs.get('challenge_id', -1):
            flask.abort(404)

        self.success_url = flask.url_for('admin.challenge', id=self.object.challenge)
        return True

    def delete(self, *args, **kwargs):
        flask.flash('Question supprimée', 'success')
        return super().delete(*args, **kwargs)


admin_blueprint.add_url_rule(
    '/challenge-<int:challenge_id>/question-del-<int:id>.html',
    view_func=AdminQuestionDelete.as_view('question-delete'))


class AdminViewAnswersPage(AdminContextMixin, GetObjectMixin, RenderTemplateView):
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


admin_blueprint.add_url_rule(
    '/challenge-<int:challenge_id>/question-<int:id>-réponses.html',
    view_func=AdminViewAnswersPage.as_view('question-answers'))
