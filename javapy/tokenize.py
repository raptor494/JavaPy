""" This is a customized version of python's default tokenizer,
from the tokenize module.
"""

from Lib.tokenize import (
    EXACT_TOKEN_TYPES,
    detect_encoding,
    TokenInfo,
    TokenError,
    group,
    maybe,
    any,
    tabsize,
    single_quoted,
    triple_quoted,
    endpats,
    untokenize
)
from token import *
from enum import Enum, auto

#region custom token types
next_index = 59
custom_token_names = set()
def add_custom_token(name, symbol=None) -> int:
    global next_index
    index = next_index
    next_index += 1
    tok_name[index] = name
    if symbol is not None:
        EXACT_TOKEN_TYPES[symbol] = index
    custom_token_names.add(name)
    return index

TRIPLESHIFTEQUAL = add_custom_token('TRIPLESHIFTEQUAL', '>>>=')
KEYWORD = add_custom_token('KEYWORD')
DOUBLECOLON = add_custom_token('DOUBLECOLON', '::')
DOUBLEPLUS = add_custom_token('DOUBLEPLUS', '++')
DOUBLEMINUS = add_custom_token('DOUBLEMINUS', '--')
DOUBLEAMPER = add_custom_token('DOUBLEAMPER', '&&')
DOUBLEVBAR = add_custom_token('DOUBLEVBAR', '||')
FSTRING_BEGIN = add_custom_token('FSTRING_BEGIN')
FSTRING_MIDDLE = add_custom_token('FSTRING_MIDDLE')
FSTRING_END = add_custom_token('FSTRING_END')
#endregion custom token types

import Lib.tokenize as Lib_tokenize
__all__ = Lib_tokenize.__all__ + [*custom_token_names,
            'print_token', 'print_token_simple', 'token_str',
            'simple_token_str', 'all_token_strs', 'print_tokens']
del Lib_tokenize, next_index, custom_token_names, add_custom_token

RESERVED_WORDS = {
    'if', 'else', 'for', 'while', 'do', 'try', 'catch', 'finally', 'synchronized', 'throw', 'return', 'switch', 'case', 'default', 'assert', 'break', 'continue',
    'void', 'boolean', 'byte', 'short', 'char', 'int', 'long', 'float', 'double',
    'class', 'interface', 'enum', 'package',
    'public', 'private', 'protected', 'static', 'final', 'transient', 'volatile', 'strictfp', 'native',
    'true', 'false', 'null', 'this', 'super', 'new', 
}

#region print methods
def print_token(token):
    print(token_str(token))

def print_token_simple(token):
    if token.type in (INDENT, DEDENT, ENDMARKER):
        print(tok_name[token.type])
    elif token.type in (NEWLINE, NL):
        print(repr(token.string)[1:-1])
    elif token.type == ENCODING:
        print('ENCODING', repr(token.string))
    elif token.type == STRING and token.string[0]*3 == token.string[0:3]:
        print(token.string[0]*3 + repr(eval(token.string))[1:-1] + token.string[0]*3)
    elif token.type == COMMENT:
        print(token.string.replace('\n', R'\n'))
    else:
        print(token.string)

def token_str(token):
    return f"{tok_name[token.exact_type]:15} {f'{token.start!r} -> {token.end!r}':30} {token.string!r}"

def simple_token_str(token):
    if token.type in (INDENT, DEDENT, ENDMARKER):
        return tok_name[token.type]
    elif token.type in (NEWLINE, NL):
        return repr(token.string)[1:-1] or R'\n'
    elif token.type == ENCODING:
        return f"ENCODING {token.string!r}"
    elif token.type == STRING and token.string[0]*3 == token.string[0:3]:
        return token.string[0]*3 + repr(eval(token.string))[1:-1] + token.string[0]*3
    elif token.type == STRING:
        return token.string
    elif token.type == COMMENT:
        return token.string.replace('\n', R'\n')
    else:
        return repr(token.string)

def all_token_strs(tokens, exact=True):
    tokens = list(tokens)
    names = [None]*len(tokens)
    stpos = [None]*len(tokens)
    enpos = [None]*len(tokens)
    strs  = [None]*len(tokens)
    longest_name = 0
    longest_spos = 0
    longest_epos = 0

    for i, token in enumerate(tokens):
        name = tok_name[token.exact_type if exact else token.type]
        spos = repr(token.start)
        epos = repr(token.end)
        if longest_name < len(name):
            longest_name = len(name)
        if longest_spos < len(spos):
            longest_spos = len(spos)
        if longest_epos < len(epos):
            longest_epos = len(epos)
        if token.type == ENDMARKER:
            string = ''
        elif token.type == INDENT:
            string = R'\t'
        elif token.type == DEDENT:
            string = R'\b'
        elif token.type in (NEWLINE, NL):
            string = R'\n'
        else:
            string = repr(token.string)

        names[i] = name
        stpos[i] = spos
        enpos[i] = epos
        strs[i]  = string

    return [f"{names[i]:{longest_name}} {stpos[i]:{longest_spos}} -> {enpos[i]:{longest_epos}}  {strs[i]}" for i in range(len(names))]

def print_tokens(tokens, exact=True):
    print(*all_token_strs(tokens, exact), sep='\n')
#endregion print methods


#region regexes
# Note: we use unicode matching for names ("\w") but ascii matching for
# number literals.
Whitespace = r'[ \f\t]*'
SingleLineComment = r'//[^\r\n]*'
MultiLineComment = r'/\*(?:[^*]|\*(?!/))*'
Comment = group(SingleLineComment, MultiLineComment)
Ignore = Whitespace + any(r'\\\r?\n' + Whitespace) + maybe(Comment)
Name = r'(?:\w|\$)+'

FloatSuffix = r'[fFdD]'
IntSuffix = r'[lL]'

Hexnumber = r'0[xX][0-9a-fA-F]+(?:_+[0-9a-fA-F]+)*' + maybe(IntSuffix)
Binnumber = r'0[bB][01]+(?:_+[01]+)*' + maybe(IntSuffix)
Octnumber = r'0_*[0-7]+(?:_+[0-7]+)*' + maybe(IntSuffix)
Decnumber = r'(?:0|[1-9][0-9]*(?:_+[0-9]+)*)' + r'[fFdDlL]?'
Intnumber = group(Hexnumber, Binnumber, Octnumber, Decnumber)
ExponentSuffix = r'[-+]?[0-9]+(?:_+[0-9]+)*'
Exponent = r'[eE]' + ExponentSuffix
Pointfloat = group(r'[0-9]+(?:_+[0-9]+)*\.(?:[0-9]+(?:_+[0-9]+)*)?',
                   r'\.[0-9]+(?:_+[0-9]+)*') + maybe(Exponent)
Expfloat = r'[0-9](?:_?[0-9])*' + Exponent
HexExponent = r'[pP]' + ExponentSuffix
Hexfloat = r'0[xX]' + group(r'[0-9a-fA-F]+(?:_+[0-9a-fA-F]+)*\.(?:[0-9a-fA-F]+(?:_+[0-9a-fA-F]+)*)?',
                            r'\.[0-9a-fA-F]+(?:_+[0-9a-fA-F]+)*') + HexExponent
Floatnumber = group(Hexfloat, Pointfloat, Expfloat) + maybe(FloatSuffix)
Number = group(Floatnumber, Intnumber)

# Return the empty string, plus all of the valid string prefixes.
def combinations(*options: str) -> set:
    def combine(options: set) -> set:
        if len(options) == 0:
            return options
        elif len(options) == 1:
            elem = options.pop()
            return {elem, elem.upper()}
        else:
            result = set()
            for elem in options:
                combinations = combine(options - {elem})
                result.update(combinations)
                lower = elem
                upper = elem.upper()
                for elem in combinations:
                    result.add(lower + elem)
                    result.add(upper + elem)
            return result

    options_set = set()
    for elem in options:
        assert isinstance(elem, str) and len(elem) == 1
        elem = elem.lower()
        assert elem not in options_set
        options_set.add(elem)
    return combine(options_set)

all_string_prefixes = combinations('r', 'f') + combinations('r', 'b') + {""}

# Note that since _all_string_prefixes includes the empty string,
#  StringPrefix can be the empty string (making it optional).
StringPrefix = group(*all_string_prefixes)

# Tail end of ' string.
Single = r"[^'\\]*(?:\\.[^'\\]*)*'"
# Tail end of " string.
Double = r'[^"\\]*(?:\\.[^"\\]*)*"'
# Tail end of ''' string.
Single3 = r"[^'\\]*(?:(?:\\.|'(?!''))[^'\\]*)*'''"
# Tail end of """ string.
Double3 = r'[^"\\]*(?:(?:\\.|"(?!""))[^"\\]*)*"""'
# Tail end of f' string.
FSingle = r"[^'\\%]*(?:(?:\\.|%(?:%|n(?![\w$])))[^'\\]*)*(?:%\{?|')"
# Tail end of f" string.
FDouble = r'[^"\\%]*(?:(?:\\.|%(?:%|n(?![\w$])))[^"\\]*)*(?:%\{?|")'
# Tail end of f''' string.
FSingle3 = r"[^'\\%]*(?:(?:\\.|'(?!'')|%(?:%|n(?![\w$])))[^'\\]*)*(?:%\{?|''')"
# Tail end of f""" string.
FDouble3 = r'[^"\\%]*(?:(?:\\.|"(?!"")|%(?:%|n(?![\w$])))[^"\\]*)*(?:%\{?|""")'

Triple = group(StringPrefix + "'''", StringPrefix + '"""')
# Single-line ' or " string.
String = group(StringPrefix + r"'[^\n'\\]*(?:\\.[^\n'\\]*)*'",
               StringPrefix + r'"[^\n"\\]*(?:\\.[^\n"\\]*)*"')
MultiLineCommentEnd = r'(?:[^*]|\*(?!/))*(?:\*/)'
LambdaNewline = r'\s*' + group(
                    SingleLineComment,
                    r'(?:/\*(?:[^*]|\*(?!/))*\*/\s*)+(?:/\*(?:[^*]|\*(?!/))*|' + SingleLineComment + r')?'
                ) + r'?\r?\n'
ClassCreatorNewline = r'\s*\{' + group(
                    SingleLineComment,
                    r'(?:/\*(?:[^*]|\*(?!/))*\*/\s*)+(?:/\*(?:[^*]|\*(?!/))*|' + SingleLineComment + r')?'
                ) + r'?\r?\n'

# Because of leftmost-then-longest match semantics, be sure to put the
# longest operators first (e.g., if = came before ==, == would get
# recognized as two instances of =).
Operator = group(r">>>?=", r"<<=?",
                 r"->", r"::", r"&&", r"\|\|",
                 r"\+\+", r"--",
                 r"[-+*/%&|^=<>!]=?",
                 r"~", r"\?")

Bracket = r'[][(){}]'
Special = group(r'\r?\n', r'\.\.\.', r'[:;.,@]')
Funny = group(Operator, Bracket, Special)

PlainToken = group(Number, Funny, String, Name)
Token = Ignore + PlainToken

# First (or only) line of ' or " string.
NormalStringPrefix = group("", *combinations('r', 'b'))
FStringPrefix = group(*combinations('r', 'f') - {'r', 'R'})
ContStr = group(FStringPrefix + r"'[^\n'\\%]*(?:(?:\\.|%(?:%|n(?![\w$])))[^\n'\\%]*)*" +
                group("%", "'", r'\\\r?\n'),
                FStringPrefix + r'"[^\n"\\%]*(?:(?:\\.|%(?:%|n(?![\w$])))[^\n"\\%]*)*' +
                group("%", '"', r'\\\r?\n'),
                NormalStringPrefix + r"'[^\n'\\]*(?:\\.[^\n'\\]*)*" +
                group("'", r'\\\r?\n'),
                NormalStringPrefix + r'"[^\n"\\]*(?:\\.[^\n"\\]*)*' +
                group('"', r'\\\r?\n'))
PseudoExtras = group(r'\\\r?\n|\Z', Comment, Triple)
PseudoToken = Whitespace + group(PseudoExtras, Number, Funny, ContStr, Name)
FunnyNoBracket = group(Operator, r'[][(){]', Special)
FStringSingleCont = r"\}" + FSingle[:-1] + r"|\\\r?\n)"
FStringSinglePseudoToken = Whitespace + group(PseudoExtras, Number, FStringSingleCont, FunnyNoBracket, ContStr, Name)
FStringDoubleCont = r'\}' + FDouble[:-1] + r"|\\\r?\n)"
FStringDoublePseudoToken = Whitespace + group(PseudoExtras, Number, FStringDoubleCont, FunnyNoBracket, ContStr, Name)
FStringSingle3Cont = r"\}" + FSingle3
FStringSingle3PseudoToken = Whitespace + group(PseudoExtras, Number, FStringSingle3Cont, FunnyNoBracket, ContStr, Name)
FStringDouble3Cont = r'\}' + FDouble3
FStringDouble3PseudoToken = Whitespace + group(PseudoExtras, Number, FStringDouble3Cont, FunnyNoBracket, ContStr, Name)

# For a given string prefix plus quotes, endpats maps it to a regex
#  to match the remainder of that string. _prefix can be empty, for
#  a normal single or triple quoted string (with no prefix).
endpats = {}
for _prefix in all_string_prefixes:
    if 'f' in _prefix or 'F' in _prefix:
        endpats[_prefix + "'"] = FSingle
        endpats[_prefix + '"'] = FDouble
        endpats[_prefix + "'''"] = FSingle3
        endpats[_prefix + '"""'] = FDouble3
    else:
        endpats[_prefix + "'"] = Single
        endpats[_prefix + '"'] = Double
        endpats[_prefix + "'''"] = Single3
        endpats[_prefix + '"""'] = Double3

# A set of all of the single and triple quoted string prefixes,
#  including the opening quotes.
single_quoted = set()
triple_quoted = set()
for t in all_string_prefixes:
    for u in (t + '"', t + "'"):
        single_quoted.add(u)
    for u in (t + '"""', t + "'''"):
        triple_quoted.add(u)

#endregion regexes

tabsize = 8

class Scope(Enum):
    NONE    = '\n'
    PAREN   = '('
    SQBRACK = '['
    CBRACK  = '{'
    LAMBDA  = '->'
    NEW     = 'new'
    SWITCH  = 'switch'
    STRING  = '""'
    FSTRING_SINGLE = "f'"
    FSTRING_DOUBLE = 'f"'
    FSTRING_SINGLE3 = "f'''"
    FSTRING_DOUBLE3 = 'f"""'
    FSTRING_SINGLE_BRACK = "f'{"
    FSTRING_DOUBLE_BRACK = 'f"{'
    FSTRING_SINGLE3_BRACK = "f'''{"
    FSTRING_DOUBLE3_BRACK = 'f"""{'

Scope.FSTRINGS = (Scope.FSTRING_SINGLE, Scope.FSTRING_DOUBLE, Scope.FSTRING_SINGLE3, Scope.FSTRING_DOUBLE3, Scope.FSTRING_SINGLE_BRACK, Scope.FSTRING_DOUBLE_BRACK, Scope.FSTRING_SINGLE3_BRACK, Scope.FSTRING_DOUBLE3_BRACK)

def tokenize(readline):
    """
    The tokenize() generator requires one argument, readline, which
    must be a callable object which provides the same interface as the
    readline() method of built-in file objects.  Each call to the function
    should return one line of input as bytes.  Alternatively, readline
    can be a callable function terminating with StopIteration:
        readline = open(myfile, 'rb').__next__  # Example of alternate readline

    The generator produces 5-tuples with these members: the token type; the
    token string; a 2-tuple (srow, scol) of ints specifying the row and
    column where the token begins in the source; a 2-tuple (erow, ecol) of
    ints specifying the row and column where the token ends in the source;
    and the line on which the token was found.  The line passed is the
    logical line; continuation lines are included.

    The first token sequence will always be an ENCODING token
    which tells you which encoding was used to decode the bytes stream.
    """
    # This import is here to avoid problems when the itertools module is not
    # built yet and tokenize is imported.
    from itertools import chain, repeat
    encoding, consumed = detect_encoding(readline)
    rl_gen = iter(readline, b"")
    empty = repeat(b"")
    return _tokenize(chain(consumed, rl_gen, empty).__next__, encoding)

def _tokenize(readline, encoding):
    import re

    def get_fstring_scope(token: str, brackets: bool) -> Scope:
        if token[1] == '"':
            if token[1:4] == '"""':
                return Scope.FSTRING_DOUBLE3_BRACK if brackets else Scope.FSTRING_DOUBLE3
            else:
                return Scope.FSTRING_DOUBLE_BRACK if brackets else Scope.FSTRING_DOUBLE
        elif token[1] == "'":
            if token[1:4] == "'''":
                return Scope.FSTRING_SINGLE3_BRACK if brackets else Scope.FSTRING_SINGLE3
            else:
                return Scope.FSTRING_SINGLE_BRACK if brackets else Scope.FSTRING_SINGLE
        elif token[2] == '"':
            if token[2:5] == '"""':
                return Scope.FSTRING_DOUBLE3_BRACK if brackets else Scope.FSTRING_DOUBLE3
            else:
                return Scope.FSTRING_DOUBLE_BRACK if brackets else Scope.FSTRING_DOUBLE
        elif token[2] == "'":
            if token[2:5] == "'''":
                return Scope.FSTRING_SINGLE3_BRACK if brackets else Scope.FSTRING_SINGLE3
            else:
                return Scope.FSTRING_SINGLE_BRACK if brackets else Scope.FSTRING_SINGLE
        else:
            assert False

    def get_str_token_type(token: str) -> int:
        if token.startswith("}"):
            if token.endswith("%"):
                return FSTRING_MIDDLE
            else:
                return FSTRING_END
        elif token.endswith("%"):
            if token.endswith("%"):
                return FSTRING_MIDDLE
            else:
                return FSTRING_BEGIN
        else:
            return STRING

    def choose_pseudotoken_based_on_scope():
        if scope[-1] is Scope.FSTRING_SINGLE_BRACK:
            return FStringSinglePseudoToken
        elif scope[-1] is Scope.FSTRING_SINGLE3_BRACK:
            return FStringSingle3PseudoToken
        elif scope[-1] is Scope.FSTRING_DOUBLE_BRACK:
            return FStringDoublePseudoToken
        elif scope[-1] is Scope.FSTRING_DOUBLE3_BRACK:
            return FStringDouble3PseudoToken
        else:
            return PseudoToken

    lnum = continued = 0
    scope = [Scope.NONE]
    opposites = {')': '(', ']': '[', '}': '{'}
    numchars = '0123456789'
    contstr, needcont = '', 0
    contline = endprog = strstart = None
    contcomm, commstart = '', None
    indents = [0]
    last = TokenInfo(ENDMARKER, '', (0, 0), (0, 0), '')

    if encoding is not None:
        if encoding == "utf-8-sig":
            # BOM will already have been stripped.
            encoding = "utf-8"
        last = TokenInfo(ENCODING, encoding, (0, 0), (0, 0), '')
        yield last

    last_line = b''
    line = b''
    while True:                                # loop over lines in stream
        try:
            # We capture the value of the line variable here because
            # readline uses the empty string '' to signal end of input,
            # hence `line` itself will always be overwritten at the end
            # of this loop.
            last_line = line
            line = readline()
        except StopIteration:
            line = b''

        if encoding is not None:
            line = line.decode(encoding)
        lnum += 1
        pos = 0
        maxpos = len(line)

        if contstr:                            # continued string
            if not line:
                raise TokenError("EOF in multi-line string", strstart)
            endmatch = endprog.match(line)
            if endmatch:
                pos = end = endmatch.end(0)
                token = contstr + line[:end]
                last = TokenInfo(get_str_token_type(token), token,
                            strstart, (lnum, end), contline + line)
                yield last
                if not token.startswith("}"):
                    if token.endswith("%{"):
                        scope.append(get_fstring_scope(token, brackets=True))
                    elif token.endswith("%"):
                        scope.append(get_fstring_scope(token, brackets=False))
                elif not token.endswith("%{") and not token.endswith("%"):
                    assert scope[-1] in Scope.FSTRINGS
                    del scope[-1]
                contstr, needcont = '', 0
                contline = None
            elif needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
                last = TokenInfo(ERRORTOKEN, contstr + line,
                            strstart, (lnum, len(line)), contline)
                yield last
                contstr = ''
                contline = None
                continue
            else:
                contstr += line
                contline += line
                continue

        elif contcomm:                            # continued multi-line comment
            if not line:
                raise TokenError("EOF in multi-line comment", commstart)
            endmatch = endprog.match(line)
            if endmatch:
                pos = end = endmatch.end(0)
                yield TokenInfo(COMMENT, contcomm + line[:end],
                            commstart, (lnum, end), contline + line)
                contcomm = ''
                contline = None
            else:
                contcomm += line
                contline += line
                continue

        elif scope[-1] is Scope.NONE and not continued:  # new statement
            if not line: break
            column = 0
            while pos < maxpos:                   # measure leading whitespace
                if line[pos] == ' ':
                    column += 1
                elif line[pos] == '\t':
                    column = (column//tabsize + 1)*tabsize
                elif line[pos] == '\f':
                    column = 0
                else:
                    break
                pos += 1
            if pos == maxpos:
                break

            if line[pos] in '\r\n' or line[pos:pos+2] == '//':           # skip comments or blank lines
                if line[pos] == '/':
                    comment_token = line[pos:].rstrip('\r\n')
                    yield TokenInfo(COMMENT, comment_token,
                                (lnum, pos), (lnum, pos + len(comment_token)), line)
                    pos += len(comment_token)

                # yield TokenInfo(NL, line[pos:],
                #            (lnum, pos), (lnum, len(line)), line)
                continue

            if column > indents[-1]:           # count indents or dedents
                indents.append(column)
                last = TokenInfo(INDENT, line[:pos], (lnum, 0), (lnum, pos), line)
                yield last
            while column < indents[-1]:
                if column not in indents:
                    if len(scope) > 1 and line[pos] == '}':
                        indents = indents[:-1]
                        last = TokenInfo(DEDENT, '', (lnum, pos), (lnum, pos), line)
                        yield last
                        while column < indents[-1] and column not in indents:
                            indents = indents[:-1]
                            last = TokenInfo(DEDENT, '', (lnum, pos), (lnum, pos), line)
                            yield last
                        break
                    raise IndentationError(
                        "unindent does not match any outer indentation level",
                        ("<tokenize>", lnum, pos, line))
                indents = indents[:-1]

                last = TokenInfo(DEDENT, '', (lnum, pos), (lnum, pos), line)
                yield last

        else:                                  # continued statement
            if not line:
                raise TokenError("EOF in multi-line statement", (lnum, 0))
            continued = 0

        while pos < maxpos:
            pseudomatch = re.compile(choose_pseudotoken_based_on_scope(), re.UNICODE).match(line, pos)
            if pseudomatch:                                # scan for tokens
                start, end = pseudomatch.span(1)
                spos, epos, pos = (lnum, start), (lnum, end), end
                if start == end:
                    continue
                token, initial = line[start:end], line[start]

                
                if (initial in numchars or                  # ordinary number
                    (initial == '.' and token != '.' and token != '...')):
                    last = TokenInfo(NUMBER, token, spos, epos, line)
                    yield last
                elif initial in '\r\n':
                    if scope[-1] is Scope.NONE:
                        last = TokenInfo(NEWLINE, token, spos, epos, line)
                        yield last
                        if len(scope) > 1 and scope[-2] in (Scope.NEW, Scope.SWITCH):
                            # print('leaving new|switch [0]')
                            del scope[-2]
                            # print('scope =', scope)
                    # else:
                    #     yield TokenInfo(NL, token, spos, epos, line)

                elif line[start:start+2] == '//':
                    assert not token.endswith("\n")
                    yield TokenInfo(COMMENT, token, spos, epos, line)

                elif line[start:start+2] == '/*':
                    endprog = re.compile(MultiLineCommentEnd, re.UNICODE)
                    endmatch = endprog.match(line, pos)
                    if endmatch:                           # all on one line
                        pos = endmatch.end(0)
                        token = line[start:pos]
                        yield TokenInfo(COMMENT, token, spos, (lnum, pos), line)
                    else:
                        commstart = (lnum, start)          # multiple lines
                        contcomm = line[start:]
                        contline = line
                        break

                elif token in triple_quoted:
                    endprog = re.compile(endpats[token], re.UNICODE)
                    endmatch = endprog.match(line, pos)
                    if endmatch:                           # all on one line
                        pos = endmatch.end(0)
                        token = line[start:pos]
                        last = TokenInfo(STRING, token, spos, (lnum, pos), line)
                        yield last
                    else:
                        strstart = (lnum, start)           # multiple lines
                        contstr = line[start:]
                        contline = line
                        break

                # Check up to the first 3 chars of the token to see if
                #  they're in the single_quoted set. If so, they start
                #  a string.
                # We're using the first 3, because we're looking for
                #  "rb'" (for example) at the start of the token. If
                #  we switch to longer prefixes, this needs to be
                #  adjusted.
                # Note that initial == token[:1].
                # Also note that single quote checking must come after
                #  triple quote checking (above).
                elif (initial in single_quoted or
                      token[:2] in single_quoted or
                      token[:3] in single_quoted):
                    if token[-1] == '\n':                  # continued string
                        strstart = (lnum, start)
                        # Again, using the first 3 chars of the
                        #  token. This is looking for the matching end
                        #  regex for the correct type of quote
                        #  character. So it's really looking for
                        #  endpats["'"] or endpats['"'], by trying to
                        #  skip string prefix characters, if any.
                        endprog = re.compile(endpats.get(initial) or
                                           endpats.get(token[1]) or
                                           endpats.get(token[2]),
                                           re.UNICODE)
                        contstr, needcont = line[start:], 1
                        contline = line
                        break
                    else:                                  # ordinary string
                        last = TokenInfo(STRING, token, spos, epos, line)
                        yield last

                elif initial.isidentifier() or initial == '$':               # ordinary name
                    if token == 'switch':
                        scope.append(Scope.SWITCH)
                        # print('entering switch')
                        # print('scope =', scope)
                    elif token == 'new':
                        if last.exact_type != DOUBLECOLON:
                            scope.append(Scope.NEW)
                        # print('entering new')
                        # print('scope =', scope)
                    last = TokenInfo(KEYWORD if token in RESERVED_WORDS else NAME, token, spos, epos, line)
                    yield last
                    
                elif initial == '\\':                      # continued stmt
                    continued = 1
                else:
                    if initial in '([{':
                        scope.append(Scope(initial))
                        if initial == '{' and (last.string == '->' or len(scope) > 1 and scope[-2] in (Scope.NEW, Scope.SWITCH)):
                            if re.match(LambdaNewline, line[pos:]):
                                scope.append(Scope.NONE)
                                # print('entering inline block')
                        elif initial == '[' and len(scope) > 1 and scope[-2] is Scope.NEW:
                            del scope[-2]
                        # print('scope =', scope)
                    elif initial in ')]}':
                        if initial == '}' and scope[-1] is Scope.NONE and len(scope) > 1 and scope[-2] is Scope.CBRACK:
                            if len(scope) > 2 and scope[-3] in (Scope.NEW, Scope.SWITCH):
                                # print('leaving inline block and new|switch')
                                del scope[-3:]
                                # print('scope =', scope)
                            else:
                                # print('leaving inline block')
                                del scope[-2:]
                                # print('scope =', scope)
                        # elif initial == '}' and scope[-1] is Scope.BLOCK and len(scope) > 2 and scope[-2] is Scope.NONE and scope[-3] is Scope.CBRACK:
                        #     print('leaving inline block and new|switch')
                        #     del scope[-3:]
                        #     print('scope =', scope)
                        elif scope[-1] in (Scope.NEW, Scope.SWITCH) and len(scope) > 1 and scope[-2].value == opposites[initial]:
                            # print('leaving new|switch [1]')
                            del scope[-2:]
                            # print('scope =', scope)
                        elif scope[-1].value == opposites[initial]:
                            del scope[-1]
                            if initial == ')' and scope[-1] is Scope.NEW and not re.match(ClassCreatorNewline, line[pos:]):
                                # print('leaving new')
                                del scope[-1]
                            # print('scope =', scope)
                        else:
                            raise TokenError(f"Unbalanced '{initial}' (scope={scope})", (lnum, pos))
                    elif initial == ':':
                        if scope[-1] in (Scope.NEW, Scope.SWITCH):
                            # print('leaving new|switch [2]')
                            del scope[-1]
                            # print('scope =', scope)
                        
                    last = TokenInfo(OP, token, spos, epos, line)
                    yield last
            else:
                last = TokenInfo(ERRORTOKEN, line[pos],
                           (lnum, pos), (lnum, pos+1), line)
                yield last
                pos += 1

    # Add an implicit NEWLINE if the input doesn't end in one
    if last_line and last_line[-1] not in '\r\n':
        yield TokenInfo(NEWLINE, '', (lnum - 1, len(last_line)), (lnum - 1, len(last_line) + 1), '')
    for _ in indents[1:]:                 # pop remaining indent levels
        yield TokenInfo(DEDENT, '', (lnum, 0), (lnum, 0), '')
    yield TokenInfo(ENDMARKER, '', (lnum, 0), (lnum, 0), '')

    if len(scope) != 1:
        raise TokenError(f"scope error: {scope}", (lnum, 0))

def main(args=None):
    import sys, argparse

    # Helper error handling routines
    def perror(message):
        print(message, file=sys.stderr)

    def error(message, filename=None, location=None):
        if location:
            args = (filename,) + location + (message,)
            perror("%s:%d:%d: error: %s" % args)
        elif filename:
            perror("%s: error: %s" % (filename, message))
        else:
            perror("error: %s" % message)
        exit(1)

    # Parse the arguments and options
    parser = argparse.ArgumentParser(prog='python -m tokenize')
    parser.add_argument(dest='filename', nargs='?',
                        metavar='filename.py',
                        help='the file to tokenize; defaults to stdin')
    parser.add_argument('-e', '--exact', dest='exact', action='store_true',
                        help='display token names using the exact type')
    parser.add_argument('-sl', '--start-line', dest='start_line', type=int, default=0,
                        help='Only print tokens starting on or after this line')
    parser.add_argument('-el', '--end-line', dest='end_line', type=int, default=-1,
                        help='Only print tokens ending on or before this line')
    args = parser.parse_args(args)

    try:
        # Tokenize the input
        if args.filename:
            filename = args.filename
            with open(filename, 'rb') as f:
                tokens = list(tokenize(f.readline))
        else:
            filename = "<stdin>"
            tokens = _tokenize(sys.stdin.readline, None)

        if args.start_line != 0 or args.end_line != -1:
                tokens = filter(lambda token: token.start[0] >= args.start_line and token.end[0] <= args.end_line, tokens)

        # Output the tokenization
        print_tokens(tokens, args.exact)
    except IndentationError as err:
        line, column = err.args[1][1:3]
        error(err.args[0], filename, (line, column))
    except TokenError as err:
        line, column = err.args[1]
        error(err.args[0], filename, (line, column))
    except SyntaxError as err:
        error(err, filename)
    except OSError as err:
        error(err)
    except KeyboardInterrupt:
        print("interrupted\n")
    except Exception as err:
        perror("unexpected error: %s" % err)
        raise

if __name__ == "__main__":
    main()