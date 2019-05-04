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

        try:
            expression = logic.parse(args.get('search_expression', ''))
        except logic.ParserException as e:
            return make_error({'position': e.token.position, 'error': e.message}, 'search_expression')

        return {
            'document': args.get('document'),
            'matched': expression.match(args.get('document'))
        }


class CheckMatchMany(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()

        self.parser.add_argument('search_expression', type=str, required=True)
        self.parser.add_argument('documents', required=True, action='append')

    def get(self):

        args = self.parser.parse_args()

        try:
            expression = logic.parse(args.get('search_expression', ''))
        except logic.ParserException as e:
            return make_error({'position': e.token.position, 'error': e.message}, 'search_expression')

        return {'matched': [expression.match(d) for d in args.get('documents')]}
