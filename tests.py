from unittest import TestCase
import json
import tempfile
import shutil
import os

import flask

import logic
import app
import settings
from commons import db
from models import User, Challenge
from views import PageContextMixin


class TestLogic(TestCase):

    def test_parser(self):

        exprs = [
            'a',
            '-a',
            'a b',
            'a OR b',
            '(a OR b) c',
        ]

        for e in exprs:
            p = logic.Parser(logic.Lexer(e))
            s = p.search_expr()

            self.assertEqual(str(s), e)

    def test_match(self):
        exprs_match = [
            ('a', ['a', 'a b', 'b a'], ['b', '']),
            ('-a', ['b', ''], ['a']),
            ('a OR b', ['a', 'a b', 'b', 'a c'], ['c', '']),
            ('(a OR b) c', ['a c', 'b c'], ['a', 'b', 'c', '']),
            ('a OR -a', ['a', 'b', ''], [])
        ]

        for e, st, nst in exprs_match:
            p = logic.Parser(logic.Lexer(e))
            s = p.search_expr()

            for x in st:
                self.assertTrue(s.match(x), msg=e + ' is not matching ' + x)
            for x in nst:
                self.assertFalse(s.match(x), msg=e + ' is matching ' + x)


class TestFlask(TestCase):

    def setUp(self):
        self.app = app.app

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

        self.admin = User.query.filter(User.eid.is_('admin')).first()
        self.assertIsNotNone(self.admin)
        self.user = User.query.filter(User.eid.is_('user')).first()
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


class TestViews(TestFlask):

    def test_login_logout(self):
        """Test the behavior of the login and logout pages"""

        # good credentials:
        self.assertTrue(self.login(self.user.eid))

        with self.client.session_transaction() as session:
            self.assertIn(PageContextMixin.LOGIN_VAR, session)
            self.assertEqual(session[PageContextMixin.LOGIN_VAR], self.user.id)
            self.assertFalse(session['is_admin'])

        self.assertTrue(self.logout())

        with self.client.session_transaction() as session:
            self.assertNotIn(PageContextMixin.LOGIN_VAR, session)

        # wrong credentials:
        self.assertFalse(self.login(self.user.eid + 'x'))

        # if already connected, get redirect
        self.assertTrue(self.login(self.user.eid))

        response = self.client.get(flask.url_for('login'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(b'Redirecting' in response.data)

        response = self.client.post(flask.url_for('login'))
        self.assertEqual(response.status_code, 302)  # redirected in post as well !
        self.assertTrue(b'Redirecting' in response.data)

        # check admin
        self.assertTrue(self.logout())
        self.assertTrue(self.login(self.admin.eid))

        with self.client.session_transaction() as session:
            self.assertIn(PageContextMixin.LOGIN_VAR, session)
            self.assertEqual(session[PageContextMixin.LOGIN_VAR], self.admin.id)
            self.assertTrue(session['is_admin'])

    def test_admin_users_management(self):
        self.assertTrue(self.login(self.admin.eid))

        # add normal user
        eid = 'xxx'

        user_count = User.query.count()

        response = self.client.post(flask.url_for('admin-users'), data={
            'eid': eid
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(User.query.count(), user_count + 1)

        last_user = User.query.order_by(User.id.desc()).first()
        self.assertEqual(last_user.eid, eid)
        self.assertFalse(last_user.is_admin)

        # delete user
        response = self.client.delete(flask.url_for('admin-users-delete', id=last_user.id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.query.count(), user_count)

        # add admin
        response = self.client.post(flask.url_for('admin-users'), data={
            'eid': eid,
            'is_admin': True
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(User.query.count(), user_count + 1)

        last_user = User.query.order_by(User.id.desc()).first()
        self.assertEqual(last_user.eid, eid)
        self.assertTrue(last_user.is_admin)

        # cannot delete admin
        response = self.client.delete(flask.url_for('admin-users-delete', id=last_user.id))
        self.assertEqual(response.status_code, 403)

        self.assertEqual(User.query.count(), user_count + 1)

        # cannot delete unknown user
        response = self.client.delete(flask.url_for('admin-users-delete', id=last_user.id + 1))
        self.assertEqual(response.status_code, 404)

        # cannot add twice the same person
        response = self.client.post(flask.url_for('admin-users'), data={
            'eid': eid
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(User.query.count(), user_count + 1)

        # normal user cannot add user
        self.logout()
        self.assertTrue(self.login(self.user.eid))

        eid += 'x'

        response = self.client.post(flask.url_for('admin-users'), data={
            'eid': eid,
            'is_admin': True
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 403)

        self.assertEqual(User.query.count(), user_count + 1)

        # normal user cannot delete
        response = self.client.delete(flask.url_for('admin-users-delete', id=last_user.id))
        self.assertEqual(response.status_code, 403)

        self.assertEqual(User.query.count(), user_count + 1)

    def test_admin_challenges_management(self):
        self.assertTrue(self.login(self.admin.eid))

        # add challenge
        name = 'xxx'

        challenges_count = Challenge.query.count()

        response = self.client.post(flask.url_for('admin-challenges'), data={
            'name': name
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Challenge.query.count(), challenges_count + 1)

        last_challenge = Challenge.query.order_by(Challenge.id.desc()).first()
        self.assertEqual(last_challenge.name, name)
        self.assertFalse(last_challenge.is_public)

        # change challenge state
        self.client.get(flask.url_for('admin-challenge-toggle', id=last_challenge.id))
        last_challenge = Challenge.query.get(last_challenge.id)
        self.assertTrue(last_challenge.is_public)

        self.client.get(flask.url_for('admin-challenge-toggle', id=last_challenge.id))
        last_challenge = Challenge.query.get(last_challenge.id)
        self.assertFalse(last_challenge.is_public)

        # delete challenge
        response = self.client.delete(flask.url_for('admin-challenge-delete', id=last_challenge.id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Challenge.query.count(), challenges_count)

        # normal user can't do anything
        response = self.client.post(flask.url_for('admin-challenges'), data={
            'name': name
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Challenge.query.count(), challenges_count + 1)  # add challenge
        self.logout()
        self.assertTrue(self.login(self.user.eid))

        name += 'x'

        response = self.client.post(flask.url_for('admin-challenges'), data={
            'name': name
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Challenge.query.count(), challenges_count + 1)  # cannot add

        response = self.client.get(flask.url_for('admin-challenge-toggle', id=last_challenge.id))
        self.assertEqual(response.status_code, 403)
        last_challenge = Challenge.query.get(last_challenge.id)
        self.assertFalse(last_challenge.is_public)  # cannot change state

        response = self.client.delete(flask.url_for('admin-challenge-delete', id=last_challenge.id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Challenge.query.count(), challenges_count + 1)  # cannot delete
