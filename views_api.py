from flask_restful import Resource, reqparse

import logic


def make_error(msg, arg, code=400):
    return {'message': {arg: msg}}, code


class CheckMatch(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()

        self.parser.add_argument('search_expression', type=str, required=True)
        self.parser.add_argument('document', type=str, required=True)

    def get(self):

        args = self.parser.parse_args()
        parser = logic.Parser(logic.Lexer(args.get('search_expression', '')))

        try:
            expression = parser.search_expr()
        except logic.ParserException as e:
            return make_error({'position': e.token.position, 'error': e.message}, 'search_expression')

        return {'matched': expression.match(args.get('document'))}
