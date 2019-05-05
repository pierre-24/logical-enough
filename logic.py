EOF = 'EOF'
MINUS = '-'
QUOTE = '"'
START_PAR = '('
END_PAR = ')'
SPACE = 'SPACE'
LOGIC_OR = '|'

SYMBOL_TR = {
    ' ': SPACE,
    '-': MINUS,
    '"': QUOTE,
    '(': START_PAR,
    ')': END_PAR,
    '|': LOGIC_OR
}

ALL_SYMBOLS = ''.join(SYMBOL_TR.keys())

WORD = 'WORD'


# Token
class Token:
    """Token class"""
    def __init__(self, type_, value, position=-1):
        self.type = type_
        self.value = value
        self.position = position

    def __repr__(self):
        return 'Token({}, {}{})'.format(
            self.type, repr(self.value), ', {}'.format(self.position) if self.position > -1 else '')


# Lexer
class Lexer:
    def __init__(self, input_):
        self.input = input_
        self.pos = 0

    @staticmethod
    def find_next_symbol(w, s, start=0):
        """Find the next element of ``w`` in ``s``, starting at ``start``.
        Returns -1 if nothing found.

        :param w: symbols
        :type w: str|list
        :param s: string
        :type s: str
        :param start: starting search position
        :type start: int
        :rtype: int
        """
        for i, c in enumerate(s[start:]):
            if c in w:
                return start + i

        return -1

    def tokenize(self):
        """Tokenize the input"""

        while self.pos < len(self.input):
            pos = self.pos
            if self.input[pos] in SYMBOL_TR:
                yield Token(SYMBOL_TR[self.input[pos]], self.input[pos], pos)
                self.pos += 1
            else:
                next_space = Lexer.find_next_symbol(ALL_SYMBOLS, self.input, self.pos)
                if next_space < 0:
                    yield Token(WORD, self.input[pos:len(self.input)], pos)
                    self.pos = len(self.input)
                else:
                    yield Token(WORD, self.input[pos:next_space], pos)
                    self.pos = next_space

        yield Token(EOF, None, self.pos)

    def tokenize_and_filter(self):
        """Filter tokens:

        + Lower words (that are not "AND" or "OR") ;
        """

        for t in self.tokenize():
            if t.type == WORD:
                if t.value not in ['AND', 'OR']:
                    t.value = t.value.lower()
            yield t


# Ast
class AST:
    def __init__(self):
        self.parent = None

    def match(self, s):
        raise NotImplementedError()


class SearchExpr(AST):
    def __init__(self, expr=None):
        super().__init__()

        self.expr = expr
        if expr is not None:
            expr.parent = self

    def match(self, s):
        if self.expr is not None:
            return self.expr.match(list(e.lower() for e in s.split(' ')))
        else:
            return False

    def __str__(self):
        if self.expr is not None:
            return str(self.expr)
        else:
            return ''


class AndExprs(AST):
    def __init__(self, values):
        super().__init__()
        self.values = values
        for v in values:
            v.parent = self

    def match(self, s):
        return all(v.match(s) for v in self.values)

    def __str__(self):
        return ' '.join(
            '({})'.format(str(v)) if isinstance(v, OrExprs) else str(v) for v in self.values)


class OrExprs(AST):
    def __init__(self, values):
        super().__init__()
        self.values = values
        for v in values:
            v.parent = self

    def match(self, s):
        return any(v.match(s) for v in self.values)

    def __str__(self):
        return ' OR '.join(
            '({})'.format(str(v)) if isinstance(v, AndExprs) else str(v) for v in self.values)


class NotExpr(AST):
    def __init__(self, expr):
        super().__init__()
        self.expr = expr
        expr.parent = self

    def match(self, s):
        return not self.expr.match(s)

    def __str__(self):
        return '-' + str(self.expr)


class SearchTerm(AST):
    def __init__(self, term):
        super().__init__()
        self.term = term
        self._spl = term.split(' ')

    def match(self, s):
        if ' ' in self.term:
            index = -1
            while True:
                try:
                    index = s.index(self._spl[0], index + 1 if index >= 0 else 0)
                    if index > len(s) - len(self._spl):
                        return False
                    else:
                        if all(self._spl[i] == s[index + i] for i in range(len(self._spl))):
                            return True
                except ValueError:
                    return False
        else:
            return self.term in s

    def __str__(self):
        if ' ' in self.term:
            return '"{}"'.format(self.term)
        else:
            return self.term


# Parser
class ParserException(Exception):
    def __init__(self, token, msg):
        super().__init__('parser error at position {} [{}]: {}'.format(token.position, repr(token), msg))
        self.token = token
        self.message = msg


class Parser:

    def __init__(self, lexer):
        self.lexer = lexer
        self.tokenizer = lexer.tokenize_and_filter()
        self.current_token = None

        self.next()

    def next(self):
        """Get next token"""

        try:
            self.current_token = next(self.tokenizer)
        except StopIteration:
            self.current_token = Token(EOF, None)

    def eat(self, token_type):
        """Consume the token if of the right type

        :param token_type: the token type
        :type token_type: str
        :raise ParserException: if not of the correct type
        """
        if self.current_token.type == token_type:
            self.next()
        else:
            raise ParserException(self.current_token, 'token must be {}'.format(token_type))

    def term(self):
        """

        :rtype: SearchTerm
        """

        term = ''

        if self.current_token.type == QUOTE:
            self.eat(QUOTE)
            while self.current_token.type != QUOTE:
                term += self.current_token.value
                self.next()

            self.eat(QUOTE)

        else:
            term = self.current_token.value
            self.eat(WORD)

        return SearchTerm(term)

    def not_expr(self):
        """

        :rtype: NotExpr
        """

        self.eat(MINUS)
        node = self.term()
        return NotExpr(node)

    def sequence(self):
        """

        :rtype: AST
        """

        seq = []
        seq_type = None

        while self.current_token.type in [START_PAR, QUOTE, SPACE, MINUS, WORD]:
            t = self.current_token.type
            v = self.current_token.value

            if t == WORD:
                if v in ['OR', 'AND']:
                    if seq_type is not None:
                        if v != seq_type:
                            raise ParserException(self.current_token, '{} in a {} expression'.format(v, seq_type))
                        else:
                            self.next()
                    else:
                        seq_type = v
                        self.next()
                else:
                    seq.append(self.term())
            elif t == QUOTE:
                seq.append(self.term())
            elif t == MINUS:
                seq.append(self.not_expr())
            elif t == START_PAR:
                self.eat(START_PAR)
                seq.append(self.sequence())
                self.eat(END_PAR)
            elif t == SPACE:
                self.eat(SPACE)
            else:
                raise ParserException(self.current_token, 'unhandled case ?!?')

            if seq_type is None and len(seq) == 2:
                seq_type = 'AND'

        if seq_type == 'AND':
            return AndExprs(seq)
        elif seq_type == 'OR':
            return OrExprs(seq)
        else:
            if len(seq) == 1:
                return seq[0]
            else:
                return AndExprs(seq)

    def search_expr(self):
        """

        :rtype: SearchExpr
        """

        node = None
        if self.current_token.type != EOF:
            node = self.sequence()

        self.eat(EOF)

        return SearchExpr(node)


def parse(expr):
    return Parser(Lexer(expr)).search_expr()
