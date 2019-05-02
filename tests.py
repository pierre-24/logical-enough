from unittest import TestCase

import logic


class TestLogic(TestCase):

    def test_parser(self):

        expr = '(Lapin OR vache OR "animal de la ferme") cri -video AND test'

        p = logic.Parser(logic.Lexer(expr))
        s = p.search_expr()
        print(str(s))
