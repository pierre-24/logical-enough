from unittest import TestCase

import logic


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
            ('a', ['a', 'a b'], ['b', '']),
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
