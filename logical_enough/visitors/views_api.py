from flask_restful import Resource, reqparse

from logical_enough import logic, db
from logical_enough.models import Question, UserChallenge, Challenge, Answer


def make_error(msg, arg, code=400):
    return {'message': {arg: msg}}, code


def normalize(tokens, sep=' '):
    return sep.join(str(t.value) for t in tokens)


class CheckMatch(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()

        self.parser.add_argument('search_expression', type=str, required=True)
        self.parser.add_argument('document', type=str, required=True)

    def get(self):
        args = self.parser.parse_args()

        doc = args.get('document')
        normalized_doc = logic.analyze(doc)

        try:
            expression = logic.parse(args.get('search_expression'))
        except logic.ParserException as e:
            return make_error({'position': e.token.position, 'error': e.message}, 'search_expression')

        return {
            'document': doc,
            'normalized_document': normalize(normalized_doc),
            'matched': expression.match(normalized_doc)
        }


class CheckMatchMany(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()

        self.parser.add_argument('search_expression', type=str, required=True)
        self.parser.add_argument('documents', required=True, action='append')

    def get(self):
        args = self.parser.parse_args()

        try:
            expression = logic.parse(args.get('search_expression'))
        except logic.ParserException as e:
            return make_error({'position': e.token.position, 'error': e.message}, 'search_expression')

        documents = []
        for d in args.get('documents'):
            normalized_doc = logic.analyze(d)

            documents.append({
                'document': d,
                'normalized_document': normalize(normalized_doc),
                'matched': expression.match(normalized_doc)
            })

        return {'documents': documents}


class CheckQuestion(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()

        self.parser.add_argument('search_expression', type=str, required=True)
        self.parser.add_argument('challenge', required=True, type=int)
        self.parser.add_argument('question', required=True, type=int)
        self.parser.add_argument('user', required=True, type=int)

    def post(self):
        args = self.parser.parse_args()

        try:
            expression = logic.parse(args.get('search_expression', ''))
        except logic.ParserException as e:
            return make_error({'position': e.token.position, 'error': e.message}, 'search_expression')

        user_challenge = UserChallenge.query \
            .filter(UserChallenge.user.is_(args.get('user'))) \
            .filter(UserChallenge.challenge.is_(args.get('challenge'))) \
            .first()

        if user_challenge is None:
            return make_error('no such user_challenge?!?', 'user')

        if args.get('question') != user_challenge.current_question:
            return make_error('not the right question?!?', 'question')

        if user_challenge.is_done:
            return make_error('challenge done!', 'challenge')

        question = Question.query.get(user_challenge.current_question)
        documents = question.get_documents()

        good_documents = question.get_good_documents()
        wrong_documents = question.get_wrong_documents()

        good_docs = []
        wrong_docs = []
        for d in documents:
            if expression.match(logic.analyze(d)):
                good_docs.append(d)
            else:
                wrong_docs.append(d)

        end = good_docs == good_documents and wrong_docs == wrong_documents
        challenge_end = False

        if end:
            challenge = Challenge.query.get(user_challenge.challenge)
            questions = challenge.get_questions()
            index = [q.id for q in questions].index(question.id)

            if index < 0:
                return make_error('say what? question is not part of the challenge?!?', 'question')
            if index == len(questions) - 1:
                user_challenge.is_done = True
                challenge_end = True
            else:
                user_challenge.current_question = questions[index + 1].id

            db.session.add(user_challenge)
            db.session.add(Answer(args.get('user'), question.id, args.get('search_expression')))
            db.session.commit()

        return {
            'good_documents': [(d, d in good_documents) for d in good_docs],
            'wrong_documents': [(d, d in good_documents) for d in wrong_docs],
            'question_end': end,
            'challenge_end': challenge_end
        }
