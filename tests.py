from unittest import TestCase
import json

import logic
import app


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


class TestAPI(TestCase):

    def setUp(self):
        self.app = app.app.test_client()

    def test_match(self):

        def make_request(expr, doc):
            response = self.app.get(
                '/api/check', data={'search_expression': expr, 'document': doc})
            j = json.loads(response.get_data().decode())
            return j

        # correct behavior
        self.assertTrue(make_request('a', 'a')['matched'])

        self.assertFalse(make_request('-a', 'a')['matched'])
        self.assertFalse(make_request('', 'a')['matched'])
        self.assertFalse(make_request('a', '')['matched'])

        # error behavior
        self.assertIn('message', make_request('a b OR c', 'a'))  # OR in a AND expression
