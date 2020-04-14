from unittest import TestCase
import json
import tempfile
import shutil
import os

import flask

from logical_enough import db, settings, create_app, logic
from logical_enough.models import User, Challenge, Question, UserChallenge, Answer
from logical_enough.base_views import PageContextMixin


class TestLogic(TestCase):

    def test_lexer(self):

        exprs = [
            ('a', ['a', None]),
            ('-a', ['-', 'a', None]),
            ('a OR b', ['a', 'OR', 'b', None]),
            ('(a* OR b) c', ['(', 'a*', 'OR', 'b', ')', 'c', None])
        ]

        for e, toks in exprs:
            p = logic.Lexer(e)
            self.assertEqual(list(t.value for t in p.tokenize_all()), toks)

    def test_parser(self):

        exprs = [
            'a',
            '-a',
            'a b',
            'a OR b',
            '(a OR b) c',
            'a OR b c'
        ]

        for e in exprs:
            p = logic.Parser(logic.Lexer(e))
            s = p.search_expr()

            self.assertEqual(str(s), e)

    def test_analyzer(self):
        m = ['a', 'b', 'x', 'z']
        mx = list(t.value for t in logic.Analyzer('a b c x y z').filter())
        self.assertEqual(m, mx)

    def test_match(self):
        exprs_match = [
            ('x', ['x', 'x z', 'z x'], ['z', '']),
            ('-a', ['b', ''], ['a']),
            ('a OR b', ['a', 'a b', 'b', 'a x'], ['x', '']),
            ('(a OR b) x', ['a x', 'b x'], ['a', 'b', 'x', '']),
            ('a OR -a', ['a', 'b', ''], []),
            ('a*', ['a', 'ab', 'x a', 'ax az'], ['b', 'x', 'xa', 'xax']),
            ('"a b"', ['a b', 'a b x', 'x a b x'], ['a', 'b', 'a x b', 'b a', 'ab'])
        ]

        for e, st, nst in exprs_match:
            p = logic.Parser(logic.Lexer(e))
            s = p.search_expr()

            for x in st:
                x_toks = logic.analyze(x)
                self.assertTrue(s.match(x_toks), msg=e + ' is not matching ' + x)
            for x in nst:
                x_toks = logic.analyze(x)
                self.assertFalse(s.match(x_toks), msg=e + ' is matching ' + x)


class TestFlask(TestCase):

    def setUp(self):
        self.app = create_app()

        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SERVER_NAME'] = 'localhost'

        # use temp directory
        self.data_files_directory = tempfile.mkdtemp()
        settings.DATA_FILES_DIRECTORY = self.data_files_directory

        # push context
        self.app_context = self.app.app_context()
        self.app_context.push()

        # use temporary database
        self.db_file = 'temp.db'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = \
            'sqlite:///' + os.path.join(self.data_files_directory, self.db_file)

        db.create_all()
        self.db_session = db.session

        # add admin and user
        self.admin = User('admin', is_admin=True)
        self.db_session.add(self.admin)

        self.user = User('user', is_admin=False)
        self.db_session.add(self.user)

        self.db_session.commit()

        self.admin = User.query.filter(User.name.is_('admin')).first()
        self.assertIsNotNone(self.admin)
        self.user = User.query.filter(User.name.is_('user')).first()
        self.assertIsNotNone(self.user)

        # create client
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        shutil.rmtree(self.data_files_directory)
        self.app_context.pop()

    def login(self, username):
        """Login client."""

        self.client.post(flask.url_for('login'), data={
            'login': username,
        }, follow_redirects=False)

        with self.client.session_transaction() as session:
            return PageContextMixin.LOGIN_VAR in session

    def logout(self):
        """Logout client"""
        self.client.get(flask.url_for('logout'), follow_redirects=False)

        with self.client.session_transaction() as session:
            return PageContextMixin.LOGIN_VAR not in session


class TestAPI(TestFlask):
    def test_checks(self):

        def make_request(expr, doc, status=200):
            response = self.client.get(
                '/api/checks', data={'search_expression': expr, 'document': doc})
            self.assertEqual(response.status_code, status)
            j = json.loads(response.get_data().decode())
            return j

        # correct behavior
        self.assertTrue(make_request('a', 'a')['matched'])

        self.assertFalse(make_request('-a', 'a')['matched'])
        self.assertFalse(make_request('', 'a')['matched'])
        self.assertFalse(make_request('a', '')['matched'])

        self.assertTrue(make_request('"a b"', 'a b')['matched'])

        # error behavior
        self.assertIn('message', make_request('a b OR c', 'a', status=400))  # OR in a AND expression

    def test_checks_many(self):

        def make_request(expr, docs, status=200):
            response = self.client.get(
                '/api/checks_many', data={'search_expression': expr, 'documents': docs})
            self.assertEqual(response.status_code, status)
            j = json.loads(response.get_data().decode())
            return j

        self.assertEqual(make_request('a OR b', ['a', 'b', 'c'])['matched'], [True, True, False])

    def test_check_question(self):

        def make_request(search_expr, user_id, challenge_id, question_id, status=200):
            response = self.client.post('/api/check_question', data={
                'search_expression': search_expr,
                'user': user_id,
                'challenge': challenge_id,
                'question': question_id
            })

            self.assertEqual(response.status_code, status)
            return json.loads(response.get_data().decode())

        # add a challenge and a question
        challenge_name = 'xxx'
        self.assertTrue(self.login(self.admin.name))

        response = self.client.post(flask.url_for('admin.challenges'), data={
            'name': challenge_name
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        challenge = Challenge.query.order_by(Challenge.id.desc()).first()

        # add 2 question
        question_count = Question.query.count()
        documents = ['a', 'b', 'c']

        search_expression_1 = logic.parse('a OR b')
        response = self.client.post(flask.url_for('admin.question-create', id=challenge.id), data={
            'hint_expr': str(search_expression_1),
            'hint': '',
            'documents': ';'.join(documents)
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Question.query.count(), question_count + 1)
        question_1 = Question.query.order_by(Question.id.desc()).first()

        search_expression_2 = logic.parse('a OR -b')
        response = self.client.post(flask.url_for('admin.question-create', id=challenge.id), data={
            'hint_expr': str(search_expression_2),
            'hint': '',
            'documents': ';'.join(documents)
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Question.query.count(), question_count + 2)
        question_2 = Question.query.order_by(Question.id.desc()).first()

        # start to play
        user_challenge_count = UserChallenge.query.count()
        response = self.client.get(flask.url_for('challenge', id=challenge.id))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(UserChallenge.query.count(), user_challenge_count)  # cannot play if challenge is not public

        self.client.get(flask.url_for('admin.challenge-toggle', id=challenge.id))

        user_challenge_count = UserChallenge.query.count()
        response = self.client.get(flask.url_for('challenge', id=challenge.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserChallenge.query.count(), user_challenge_count + 1)

        user_challenge = UserChallenge.query.order_by(UserChallenge.id.desc()).first()

        self.assertEqual(user_challenge.user, self.admin.id)
        self.assertEqual(user_challenge.challenge, challenge.id)
        self.assertEqual(user_challenge.current_question, question_1.id)
        self.assertFalse(user_challenge.is_done)

        # wrong answer to first question
        answer_count = Answer.query.count()

        test_expr = logic.parse('a')
        j = make_request(str(test_expr), self.admin.id, challenge.id, question_1.id)
        self.assertFalse(j['question_end'])
        self.assertFalse(j['challenge_end'])

        for d, is_good in j['good_documents']:
            if is_good:
                self.assertIn(d, question_1.get_good_documents())
            else:
                self.assertIn(d, question_1.get_wrong_documents())
            self.assertTrue(test_expr.match(d))

        for d, is_good in j['wrong_documents']:
            if is_good:
                self.assertIn(d, question_1.get_good_documents())
            else:
                self.assertIn(d, question_1.get_wrong_documents())
            self.assertFalse(test_expr.match(d), msg=d)

        # good answer to first question
        j = make_request(str(search_expression_1), self.admin.id, challenge.id, question_1.id)
        self.assertTrue(j['question_end'])
        self.assertFalse(j['challenge_end'])

        user_challenge = UserChallenge.query.get(user_challenge.id)
        self.assertFalse(user_challenge.is_done)
        self.assertEqual(user_challenge.current_question, question_2.id)

        self.assertEqual(Answer.query.count(), answer_count + 1)
        last_answer = Answer.query.order_by(Answer.id.desc()).first()
        self.assertEqual(last_answer.answer, str(search_expression_1))

        # if we try the same question, we get error
        make_request(str(search_expression_1), self.admin.id, challenge.id, question_1.id, status=400)

        # good answer to second question
        j = make_request(str(search_expression_2), self.admin.id, challenge.id, question_2.id)
        self.assertTrue(j['question_end'])
        self.assertTrue(j['challenge_end'])

        user_challenge = UserChallenge.query.get(user_challenge.id)
        self.assertTrue(user_challenge.is_done)  # ok, we're good

        self.assertEqual(Answer.query.count(), answer_count + 2)
        last_answer = Answer.query.order_by(Answer.id.desc()).first()
        self.assertEqual(last_answer.answer, str(search_expression_2))

        # if we try the same question, we get error (challenge is done!)
        make_request(str(search_expression_2), self.admin.id, challenge.id, question_2.id, status=400)


class TestViews(TestFlask):

    def test_login_logout(self):
        """Test the behavior of the login and logout pages"""

        # good credentials:
        self.assertTrue(self.login(self.user.name))

        with self.client.session_transaction() as session:
            self.assertIn(PageContextMixin.LOGIN_VAR, session)
            self.assertEqual(session[PageContextMixin.LOGIN_VAR], self.user.id)
            self.assertFalse(session['is_admin'])

        self.assertTrue(self.logout())

        with self.client.session_transaction() as session:
            self.assertNotIn(PageContextMixin.LOGIN_VAR, session)

        # wrong credentials:
        self.assertFalse(self.login(self.user.name + 'x'))

        # if already connected, get redirect
        self.assertTrue(self.login(self.user.name))

        response = self.client.get(flask.url_for('login'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(b'Redirecting' in response.data)

        response = self.client.post(flask.url_for('login'))
        self.assertEqual(response.status_code, 302)  # redirected in post as well !
        self.assertTrue(b'Redirecting' in response.data)

        # check admin
        self.assertTrue(self.logout())
        self.assertTrue(self.login(self.admin.name))

        with self.client.session_transaction() as session:
            self.assertIn(PageContextMixin.LOGIN_VAR, session)
            self.assertEqual(session[PageContextMixin.LOGIN_VAR], self.admin.id)
            self.assertTrue(session['is_admin'])

    def test_admin_users_management(self):
        self.assertTrue(self.login(self.admin.name))

        # add normal user
        eid = 'xxx'

        user_count = User.query.count()

        response = self.client.post(flask.url_for('admin.users'), data={
            'login': eid
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(User.query.count(), user_count + 1)

        last_user = User.query.order_by(User.id.desc()).first()
        self.assertEqual(last_user.name, eid)
        self.assertFalse(last_user.is_admin)

        # delete user
        response = self.client.delete(flask.url_for('admin.user-delete', id=last_user.id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.query.count(), user_count)

        # add admin
        response = self.client.post(flask.url_for('admin.users'), data={
            'login': eid,
            'is_admin': True
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(User.query.count(), user_count + 1)

        last_user = User.query.order_by(User.id.desc()).first()
        self.assertEqual(last_user.name, eid)
        self.assertTrue(last_user.is_admin)

        # cannot delete admin
        response = self.client.delete(flask.url_for('admin.user-delete', id=last_user.id))
        self.assertEqual(response.status_code, 403)

        self.assertEqual(User.query.count(), user_count + 1)

        # cannot delete unknown user
        response = self.client.delete(flask.url_for('admin.user-delete', id=last_user.id + 1))
        self.assertEqual(response.status_code, 404)

        # cannot add twice the same person
        response = self.client.post(flask.url_for('admin.users'), data={
            'login': eid
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(User.query.count(), user_count + 1)

        # normal user cannot add user
        self.logout()
        self.assertTrue(self.login(self.user.name))

        eid += 'x'

        response = self.client.post(flask.url_for('admin.users'), data={
            'login': eid,
            'is_admin': True
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 403)

        self.assertEqual(User.query.count(), user_count + 1)

        # normal user cannot delete
        response = self.client.delete(flask.url_for('admin.user-delete', id=last_user.id))
        self.assertEqual(response.status_code, 403)

        self.assertEqual(User.query.count(), user_count + 1)

    def test_admin_challenges_management(self):
        self.assertTrue(self.login(self.admin.name))

        # add challenge
        name = 'xxx'

        challenges_count = Challenge.query.count()

        response = self.client.post(flask.url_for('admin.challenges'), data={
            'name': name
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Challenge.query.count(), challenges_count + 1)

        last_challenge = Challenge.query.order_by(Challenge.id.desc()).first()
        self.assertEqual(last_challenge.name, name)
        self.assertFalse(last_challenge.is_public)

        # change challenge state
        self.client.get(flask.url_for('admin.challenge-toggle', id=last_challenge.id))
        last_challenge = Challenge.query.get(last_challenge.id)
        self.assertTrue(last_challenge.is_public)

        self.client.get(flask.url_for('admin.challenge-toggle', id=last_challenge.id))
        last_challenge = Challenge.query.get(last_challenge.id)
        self.assertFalse(last_challenge.is_public)

        # delete challenge
        response = self.client.delete(flask.url_for('admin.challenge-delete', id=last_challenge.id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Challenge.query.count(), challenges_count)

        # normal user can't do anything
        response = self.client.post(flask.url_for('admin.challenges'), data={
            'name': name
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Challenge.query.count(), challenges_count + 1)  # add challenge
        self.logout()
        self.assertTrue(self.login(self.user.name))

        name += 'x'

        response = self.client.post(flask.url_for('admin.challenges'), data={
            'name': name
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Challenge.query.count(), challenges_count + 1)  # cannot add

        response = self.client.get(flask.url_for('admin.challenge-toggle', id=last_challenge.id))
        self.assertEqual(response.status_code, 403)
        last_challenge = Challenge.query.get(last_challenge.id)
        self.assertFalse(last_challenge.is_public)  # cannot change state

        response = self.client.delete(flask.url_for('admin.challenge-delete', id=last_challenge.id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Challenge.query.count(), challenges_count + 1)  # cannot delete

    def test_admin_questions_management(self):
        challenge_name = 'xxx'
        self.assertTrue(self.login(self.admin.name))

        response = self.client.post(flask.url_for('admin.challenges'), data={
            'name': challenge_name
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        challenge = Challenge.query.order_by(Challenge.id.desc()).first()

        # add question
        question_count = Question.query.count()

        search_expression = logic.parse('a OR b')
        documents = ['a', 'b', 'c']

        hint = 'yyyy'

        response = self.client.post(flask.url_for('admin.question-create', id=challenge.id), data={
            'hint_expr': str(search_expression),
            'hint': hint,
            'documents': ';'.join(documents)
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Question.query.count(), question_count + 1)

        last_question = Question.query.order_by(Question.id.desc()).first()
        self.assertEqual(last_question.hint_expr, str(search_expression))
        self.assertEqual(last_question.hint, hint)

        good_docs = last_question.get_good_documents()
        wrong_docs = last_question.get_wrong_documents()

        for d in documents:
            if search_expression.match(d):
                self.assertIn(d, good_docs)
            else:
                self.assertIn(d, wrong_docs)

        # modify question: add documents
        documents.append('d')

        response = self.client.post(
            flask.url_for('admin.question', id=last_question.id, challenge_id=challenge.id),
            data={
                'hint_expr': str(search_expression),
                'hint': hint + 'x',
                'documents': ';'.join(documents)
            },
            follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        last_question = Question.query.get(last_question.id)
        self.assertEqual(last_question.hint_expr, str(search_expression))
        self.assertEqual(last_question.hint, hint + 'x')

        good_docs = last_question.get_good_documents()
        wrong_docs = last_question.get_wrong_documents()

        for d in documents:
            if search_expression.match(d):
                self.assertIn(d, good_docs)
            else:
                self.assertIn(d, wrong_docs)

        # modify question: change search expr
        search_expression = logic.parse('a OR -b')

        response = self.client.post(
            flask.url_for('admin.question', id=last_question.id, challenge_id=challenge.id),
            data={
                'hint_expr': str(search_expression),
                'hint': hint,
                'documents': ';'.join(documents)
            },
            follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        last_question = Question.query.get(last_question.id)
        self.assertEqual(last_question.hint_expr, str(search_expression))
        self.assertEqual(last_question.hint, hint)

        good_docs = last_question.get_good_documents()
        wrong_docs = last_question.get_wrong_documents()

        for d in documents:
            if search_expression.match(d):
                self.assertIn(d, good_docs)
            else:
                self.assertIn(d, wrong_docs)

        # delete question
        response = self.client.post(
            flask.url_for('admin.question-delete', id=last_question.id, challenge_id=challenge.id),
            follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Question.query.count(), question_count)

        # delete challenge also delete question(s)
        response = self.client.post(flask.url_for('admin.question-create', id=challenge.id), data={
            'hint_expr': str(search_expression),
            'hint': hint,
            'documents': ';'.join(documents)
        }, follow_redirects=False)  # re add a question
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Question.query.count(), question_count + 1)

        response = self.client.delete(flask.url_for('admin.challenge-delete', id=challenge.id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Question.query.count(), question_count)

        # user can't!
        response = self.client.post(flask.url_for('admin.challenges'), data={
            'name': challenge_name
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)  # re-add challenge

        challenge = Challenge.query.order_by(Challenge.id.desc()).first()

        response = self.client.post(flask.url_for('admin.question-create', id=challenge.id), data={
            'hint_expr': str(search_expression),
            'hint': hint,
            'documents': ';'.join(documents)
        }, follow_redirects=False)  # re add a question
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Question.query.count(), question_count + 1)

        self.assertTrue(self.logout())
        self.assertTrue(self.login(self.user.name))

        # user cannot add question
        response = self.client.post(flask.url_for('admin.question-create', id=challenge.id), data={
            'hint_expr': 'a',
            'hint': hint,
            'documents': ';'.join(documents)
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Question.query.count(), question_count + 1)

        # user cannot modify question
        response = self.client.post(
            flask.url_for('admin.question', id=last_question.id, challenge_id=challenge.id),
            data={
                'hint_expr': 'a',
                'hint': hint,
                'documents': ';'.join(documents)
            },
            follow_redirects=False)
        self.assertEqual(response.status_code, 403)

        last_question = Question.query.get(last_question.id)
        self.assertEqual(last_question.hint_expr, str(search_expression))

        # user cannot delete question
        response = self.client.post(
            flask.url_for('admin.question-delete', id=last_question.id, challenge_id=challenge.id),
            follow_redirects=False)
        self.assertEqual(response.status_code, 403)

        self.assertEqual(Question.query.count(), question_count + 1)
