import re

from typing import Iterator, Union, List
from logical_enough.stopwords import FRENCH_STOPWORDS, ENGLISH_STOPWORDS

EOF = 'EOF'
MINUS = '-'
QUOTE = '"'
LPAR = '('
RPAR = ')'
SPACE = 'SPACE'

SYMBOL_TR = {
    ' ': SPACE,
    '-': MINUS,
    '"': QUOTE,
    '(': LPAR,
    ')': RPAR
}

ALL_SYMBOLS = ''.join(SYMBOL_TR.keys())

WORD = 'WORD'

AND = 'AND'
OR = 'OR'
NOT = 'NOT'

ALL_OPERATORS = [AND, OR, NOT]


# Token
class Token:
    """Token class"""
    def __init__(self, type_: str, value: Union[str, None], position: int = -1):
        self.type = type_
        self.value = value
        self.position = position

    def __repr__(self) -> str:
        return 'Token({}, {}{})'.format(
            self.type, repr(self.value), ', {}'.format(self.position) if self.position > -1 else '')


# Lexer
class Lexer:
    def __init__(self, input_: str):
        self.input = input_
        self.pos = 0

    @staticmethod
    def find_next_symbol(w: Union[str, List], s: str, start: int = 0) -> int:
        """Find the next element of ``w`` in ``s``, starting at ``start``.
        Returns -1 if nothing found.

        :param w: symbols
        :param s: string
        :param start: starting search position
        """
        for i, c in enumerate(s[start:]):
            if c in w:
                return start + i

        return -1

    def tokenize(self) -> Iterator[Token]:
        """Get the next token"""

        while self.pos < len(self.input):
            pos = self.pos
            if self.input[pos] in SYMBOL_TR:
                if self.input[pos] != ' ':  # skip space
                    yield Token(SYMBOL_TR[self.input[pos]], self.input[pos], pos)
                self.pos += 1
            else:
                next_space = Lexer.find_next_symbol(ALL_SYMBOLS, self.input, self.pos)

                if next_space < 0:
                    word = self.input[pos:]
                    self.pos = len(self.input)
                else:
                    word = self.input[pos:next_space]
                    self.pos = next_space

                if word in ALL_OPERATORS:
                    yield Token(word, word, pos)
                else:
                    yield Token(WORD, word.lower(), pos)

        yield Token(EOF, None, self.pos)

    def tokenize_all(self) -> Iterator[Token]:
        """Tokenize all the input"""

        for t in self.tokenize():
            yield t

            if t.type == EOF:
                break


# Ast
class AST:
    def __init__(self):
        self.parent = None

    def match(self, s: List[Token]) -> bool:
        raise NotImplementedError()


class SearchExpr(AST):
    def __init__(self, expr: Union['AndExpr', 'OrExpr', None] = None):
        super().__init__()

        self.expr = expr
        if expr is not None:
            expr.parent = self

    def match(self, s: List[Token]) -> bool:
        if self.expr is not None:
            return self.expr.match(s)
        else:
            return False

    def __str__(self):
        if self.expr is not None:
            return str(self.expr)
        else:
            return ''


class SeqExpr(AST):
    def __init__(self, values: List):
        super().__init__()
        self.values = values
        for v in values:
            v.parent = self


class AndExpr(SeqExpr):
    def __init__(self, values: List['OrExpr']):
        super().__init__(values)

    def match(self, s: List[Token]) -> bool:
        return all(v.match(s) for v in self.values)

    def __str__(self):
        return ' '.join(str(v) for v in self.values)


class OrExpr(SeqExpr):
    def __init__(self, values: List['Term']):
        super().__init__(values)

    def match(self, s: List[Token]) -> bool:
        return any(v.match(s) for v in self.values)

    def __str__(self):
        return ' OR '.join(str(v) for v in self.values)


class Term(AST):
    def __init__(self, expr: Union['NotExpr', 'SingleTerm', 'Group', 'SubExpr']):
        super().__init__()
        self.expr = expr
        expr.parent = self

    def match(self, s: List[Token]) -> bool:
        return self.expr.match(s)

    def __str__(self):
        return str(self.expr)


class NotExpr(AST):
    def __init__(self, expr: Term):
        super().__init__()
        self.expr = expr
        expr.parent = self

    def match(self, s: List[Token]) -> bool:
        return not self.expr.match(s)

    def __str__(self):
        return '-' + str(self.expr)


class SingleTerm(AST):
    def __init__(self, word: str):
        super().__init__()
        self.word = word
        self.has_wildcard = '*' in self.word
        self.reg = None
        if self.has_wildcard:
            self.reg = re.compile(self.word.replace('*', '.*'))

    def __str__(self):
        return self.word

    def match(self, s: List[Token]) -> bool:
        for t in s:
            if not self.has_wildcard and t.value == self.word:
                return True
            elif self.has_wildcard and self.reg.match(t.value):
                return True

        return False


class Group(AST):
    C = '+'

    def __init__(self, words: List[str]):
        super().__init__()
        self.words = words
        self.w_all = self.C.join(words)

    def __str__(self):
        return '"{}"'.format(' '.join(self.words))

    def match(self, s: List[Token]) -> bool:
        s_all = self.C.join(t.value for t in s)
        return self.w_all in s_all


class SubExpr(AST):
    def __init__(self, expr: AndExpr):
        super().__init__()
        self.expr = expr
        expr.parent = self

    def __str__(self):
        return '({})'.format(str(self.expr))

    def match(self, s: List[Token]) -> bool:
        return self.expr.match(s)


# Parser
class ParserException(Exception):
    def __init__(self, token, msg):
        super().__init__('parser error at position {} [{}]: {}'.format(token.position, repr(token), msg))
        self.token = token
        self.message = msg


class Parser:
    """
    A more or less LL(1) parser which use the following rules:

    .. code-block:: text

        searchExpr := andExpr EOF
        andExpr := orExpr (AND? orExpr)*
        orExpr := term (OR term)*
        term := notExpr | singleTerm | group | subExpr
        notExpr := (NOT | MINUS) term
        singleTerm := WORD
        group := QUOTE singleTerm* QUOTE
        subExpr := LPAR andExpr RPAR

    """

    firsts_of_term = [MINUS, WORD, QUOTE, LPAR]

    def __init__(self, lexer):
        self.lexer = lexer
        self.tokenizer = lexer.tokenize()
        self.current_token = None
        self.next_token = None

        self.next()
        self.next()  # twice so that `current_token` is set

    def next(self) -> None:
        """Get next token"""

        self.current_token = self.next_token

        try:
            self.next_token = next(self.tokenizer)
        except StopIteration:
            self.next_token = Token(EOF, None)

    def peek(self) -> Token:
        """Check the next token"""

        return self.next_token

    def eat(self, token_type: str) -> None:
        """Consume the token if of the right type

        :param token_type: the token type
        :raise ParserException: if not of the correct type
        """
        if self.current_token.type == token_type:
            self.next()
        else:
            raise ParserException(self.current_token, 'token must be {}'.format(token_type))

    def search_expr(self) -> SearchExpr:
        """
        searchExpr := andExpr EOF
        """

        node = None
        if self.current_token.type != EOF:
            node = self.andExpr()

        self.eat(EOF)

        return SearchExpr(node)

    def andExpr(self) -> AndExpr:
        """
        andExpr := orExpr (AND? orExpr)*
        """

        total_next = self.firsts_of_term.copy()
        total_next.append(AND)

        node_list = [self.orExpr()]

        while self.current_token.type in total_next:
            if self.current_token.type == AND:
                self.eat(AND)
            node_list.append(self.orExpr())

        return AndExpr(node_list)

    def orExpr(self) -> OrExpr:
        """
        orExpr := term (OR term)*
        """

        node_list = [self.term()]

        while self.current_token.type == OR:
            self.eat(OR)
            node_list.append(self.term())

        return OrExpr(node_list)

    def term(self) -> Term:
        """
        term := notExpr | singleTerm | group | subExpr

        firsts:

        + notExpr: MINUS
        + singleTerm : WORD
        + group: QUOTE
        + subExpr: LPAR
        """

        next_tok = self.current_token.type

        if next_tok == MINUS:
            return Term(self.notExpr())
        elif next_tok == WORD:
            return Term(self.singleTerm())
        elif next_tok == QUOTE:
            return Term(self.group())
        elif next_tok == LPAR:
            return Term(self.subExpr())
        else:
            raise ParserException(self.current_token, 'expected term firsts')

    def notExpr(self) -> NotExpr:
        """
        notExpr := (NOT | MINUS) term
        """

        if self.current_token.type == MINUS:
            self.eat(MINUS)
        elif self.current_token.type == NOT:
            self.eat(NOT)
        else:
            raise ParserException(self.current_token, 'expected MINUS or NOT')

        return NotExpr(self.term())

    def singleTerm(self) -> SingleTerm:
        """
        singleTerm := WORD
        """

        w = self.current_token.value
        self.eat(WORD)

        return SingleTerm(w)

    def group(self) -> Group:
        """
        group := QUOTE singleTerm* QUOTE

        Note: this rule actually eats everything until the next quote
        """
        self.eat(QUOTE)

        word_list = []

        while self.current_token.type != QUOTE:  # eat everything until next quote
            word_list.append(self.current_token.value)
            self.next()

        self.eat(QUOTE)
        return Group(word_list)

    def subExpr(self) -> SubExpr:
        """
        subExpr := LPAR andExpr RPAR
        """
        self.eat(LPAR)
        s = SubExpr(self.andExpr())
        self.eat(RPAR)

        return s


def parse(expr):
    return Parser(Lexer(expr)).search_expr()


class Analyzer:
    """
    Input > tokenizer > Token filter
    """

    def __init__(self, input_: str):
        self.input = input_
        self.pos = 0
        self.len = len(input_)

    def tokenize(self) -> Iterator[Token]:
        """Stop after every non-alphanumeric character
        """

        while self.pos < self.len:
            pos = self.pos
            next_break = -1
            for i, l in enumerate(self.input[pos:]):
                if not l.isalnum():
                    next_break = self.pos + i
                    break
            if next_break == -1:
                next_break = self.len

            yield Token(WORD, self.input[pos:next_break])

            self.pos = next_break + 1  # skip break

    def filter(self) -> Iterator[Token]:
        """

        + Lowercase everything
        + Remove empty tokens
        + Remove french and english stopwords
        """
        for t in self.tokenize():
            if t.value == '':
                continue

            if t.value is not None:
                t.value = t.value.lower()
                if t.value in FRENCH_STOPWORDS:
                    continue
                if t.value in ENGLISH_STOPWORDS:
                    continue

            yield t


def analyze(inp: str):
    return list(Analyzer(inp).filter())
