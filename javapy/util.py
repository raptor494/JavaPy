import re
import inspect
import math
from enum import Enum
from collections import OrderedDict
from numbers import Number
from typing import _GenericAlias, Optional, Tuple
from Lib.tokenize import TokenInfo
from typeguard import check_type, check_argument_types
from javapy.tokenize import simple_token_str
from functools import wraps

class JavaSyntaxError(SyntaxError):
    def __init__(self, msg: str='', at: Optional[Tuple[str, int, int, str]]=None, token: Optional[TokenInfo]=None, got: Optional[TokenInfo]=None):
        """        
        Args:
            msg (str, optional): The error message. Defaults to ''.
            at (Tuple[str, int, int, str], optional): A tuple of (filename, line, column, line string). Defaults to None.
            token (TokenInfo, optional): The error token. Defaults to None.
            got (TokenInfo, optional): The token which was gotten (adjusts the error message slightly). Defaults to None.
        """
        if got is None:
            check_type('token', token, Optional[TokenInfo])
        else:
            if token is not None:
                raise ValueError("arguments 'token' and 'got' are mutually exclusive")
            check_type('got', got, TokenInfo)

        msg = str(msg).strip()

        if token is not None:
            msg += ' (token ' + simple_token_str(token) + ')'
        elif got is not None:
            msg += ', got ' + simple_token_str(got)

        if at is not None:
            if not isinstance(at, tuple) or len(at) != 4 \
                    or not isinstance(at[0], str) \
                    or not isinstance(at[1], int) \
                    or not isinstance(at[2], int) \
                    or not isinstance(at[3], str):
                raise TypeError(f"argument 'at' must be string or (filename: str, line#: int, column#: int, line: str) tuple, not {typename(at)!r}")
            # msg = msg.strip() + ' '
            # if not added_open_bracket:
            #     msg += '['
            #     added_open_bracket = True
            # msg += f"in file \"{repr(at[0])[1:-1]}\" on line {at[1]}, column {at[2]} ({at[3].strip()})"
            lineno = at[1]
            at = (at[0], 1, at[2]+1, at[3])
        
        if at is not None:
            super().__init__(msg, at)
            self.lineno = lineno
        else:
            super().__init__(msg)

class EmptyLineHandling(Enum):
    NOT_SPECIAL = 0
    REPLACE_WITH_EMPTY = 1
    REMOVE = 2

def lstrip_multiline(string: str, empty_line_handling: EmptyLineHandling=EmptyLineHandling.REPLACE_WITH_EMPTY, ignore_first: bool=False) -> str:
    assert check_argument_types()

    lines = string.splitlines()

    if len(lines) == 1:
        return lines[0].lstrip()

    def get_indent(line):
        i = 0
        for i, c in enumerate(line):
            if not c.isspace():
                break
        return line[0:i]

    def get_common_indent(indent1, indent2):
        if indent1.startswith(indent2):
            return indent2
        elif indent2.startswith(indent1):
            return indent1

        i = 0
        for i, (c1, c2) in enumerate(zip(indent1, indent2)):
            if c1 != c2:
                break
        return indent1[0:i]

    if empty_line_handling is EmptyLineHandling.REMOVE:
        for i in reversed(range(len(lines))):
            if not ignore_first or i > 0:
                line = lines[i]
                if line == "" or line.isspace():
                    del lines[i]
        if len(lines) == 0:
            return ""
        empty_line_handling = EmptyLineHandling.NOT_SPECIAL

    common_indent = None
    for i, line in enumerate(lines):
        if (not ignore_first or i > 0) and (empty_line_handling is EmptyLineHandling.NOT_SPECIAL or not line.isspace() and len(line) != 0):
            indent = get_indent(line)
            if common_indent is None:
                common_indent = indent
            else:
                common_indent = get_common_indent(common_indent, indent)
    
    if common_indent is not None and common_indent != "":
        index = slice(len(common_indent), None)
        for i, line in enumerate(lines):
            if not ignore_first or i > 0:
                if empty_line_handling is not EmptyLineHandling.NOT_SPECIAL and (line.isspace() or len(line) == 0):
                    if empty_line_handling is EmptyLineHandling.REPLACE_WITH_EMPTY:
                        lines[i] = ""
                else:
                    lines[i] = line[index]
        
    return '\n'.join(lines)

NAME_REGEX = re.compile(r"[a-zA-Z_][a-zA-Z_0-9]*")
NAME_BYTES_REGEX = re.compile(rb"[a-zA-Z_][a-zA-Z_0-9]*")

def isname(value):
    if isinstance(value, bytes):
        return bool(NAME_BYTES_REGEX.match(value))
    else:
        return bool(NAME_REGEX.match(value))

def get_calling_function_name():
    stack = inspect.stack()
    try:
        element = stack[2]
    except IndexError:
        element = stack[1]
    return element.function

def typename(value_or_type):
    if isinstance(value_or_type, type):
        return value_or_type.__name__
    else:
        return type(value_or_type).__name__

def join_natural(iterable, separator=', ', word='and', oxford_comma=True, add_spaces=True):
    if add_spaces:
        if len(word) != 0 and not word[-1].isspace():
            word += ' '
        if len(separator) != 0 and len(word) != 0 and not separator[-1].isspace() and not word[0].isspace():
            word = ' ' + word

    last2 = None
    set_last2 = False
    last1 = None
    set_last1 = False

    result = ""
    for i, item in enumerate(iterable):
        if set_last2:
            if i == 2:
                result += str(last2)
            else:
                result += separator + str(last2)
        last2 = last1
        set_last2 = set_last1
        last1 = item
        set_last1 = True

    if set_last2:
        if result:
            if oxford_comma:
                result += separator + str(last2) + separator + word + str(last1)
            else:
                if add_spaces and not word[0].isspace():
                    word = ' ' + word

                result += separator + str(last2) + word + str(last1)
                
        else:
            if add_spaces and not word[0].isspace():
                word = ' ' + word

            result = str(last2) + word + str(last1)

    elif set_last1:
        result = str(last1)

    return result

_TYPECHECK_CALL_REGEX = re.compile(r"^\s*typecheck\(\s*(.*?)(?:\s*,.*\)$)", re.ASCII)
_ITERTYPECHECK_CALL_REGEX = re.compile(r"^\s*itertypecheck\(\s*(.*?)(?:\s*,.*\)$)", re.ASCII)
_LISTTYPECHECK_CALL_REGEX = re.compile(r"^\s*listtypecheck\(\s*(.*?)(?:\s*,.*\)$)", re.ASCII)

# def typecheck(value, test, *, name=None, function=None, include_argument=True):
    # if isinstance(value, test): 
    #     return

    # if name is None or function is None:
    #     try:
    #         frameinfo = inspect.stack()[1]
        
    #         if function is None:
    #             function = frameinfo.function
    #             if function[0].isalpha() or function[0] == '_':
    #                 function += '()'
    #         elif not isinstance(function, str):
    #             raise TypeError(f"typecheck(0 argument 'function' must be string, not '{typename(function)}'")
    #         elif isname(function):
    #             function += '()'

    #         if name is None:
    #             # import uncompyle6, io
    #             # strio = io.StringIO()
    #             # code = inspect.currentframe().f_back.f_code
    #             # uncompyle6.code_deparse(code, out=strio)
    #             # source = strio.getvalue()
    #             source = frameinfo.code_context[frameinfo.index]
    #             print(source)
    #             match = _TYPECHECK_CALL_REGEX.match(source)
    #             if match:
    #                 name = match.group(1)
    #         elif not isinstance(name, (str, int)):
    #             raise TypeError(f"typecheck() argument 'name' must be string or int, not '{typename(name)}'")
    #         else:
    #             if include_argument and (not isinstance(name, str) or not re.match(r"argument\s+.+", name)):
    #                 name = f"argument {name!r}"
    #             else:
    #                 name = repr(name)

    #     finally:
    #         del frameinfo

    # else:
    #     if not isinstance(name, (str, int)):
    #         raise TypeError(f"typecheck() argument 'name' must be string or int, not '{typename(name)}'")
    #     if not isinstance(function, str):
    #         raise TypeError(f"typecheck(0 argument 'function' must be string, not '{typename(function)}'")
    #     if isname(function):
    #         function += '()'
    #     if include_argument and (not isinstance(name, str) or not re.match(r"argument\s+.+", name)):
    #         name = f"argument {name!r}"
    #     else:
    #         name = repr(name)

    # if isinstance(test, tuple):
    #     options = join_natural(('string' if typ is str else typ.__name__ for typ in test), word='or')
    # else:
    #     options = test.__name__

    # if name is None:
    #     msg = f"{function} argument must be {options}, not '{typename(value)}'"
    # else:
    #     msg = f"{function} {name} must be {options}, not '{typename(value)}'"

    # raise TypeError(msg)

# class FormatIndexMode(Enum):
    # NO_FORMAT = 0
    # FORMAT = 1
    # OLD_FORMAT = 2

# def itertypecheck(iterable, test, *, name=None, function=None, include_argument=True, index_format=FormatIndexMode.NO_FORMAT):
    # typecheck(index_format, FormatIndexMode)
    # for index, value in enumerate(iterable):
    #     if not isinstance(value, test):
    #         if name is None or function is None:
    #             try:
    #                 frameinfo = inspect.stack()[1]
                
    #                 if function is None:
    #                     function = frameinfo.function
    #                     if function[0].isalpha() or function[0] == '_':
    #                         function += '()'
    #                 elif not isinstance(function, str):
    #                     raise TypeError(f"typecheck(0 argument 'function' must be string, not '{typename(function)}'")
    #                 elif isname(function):
    #                     function += '()'

    #                 if name is None:
    #                     # import uncompyle6, io
    #                     # strio = io.StringIO()
    #                     # code = inspect.currentframe().f_back.f_code
    #                     # uncompyle6.code_deparse(code, out=strio)
    #                     # source = strio.getvalue()
    #                     source = frameinfo.code_context[frameinfo.index]
    #                     print(source)
    #                     match = _TYPECHECK_CALL_REGEX.match(source)
    #                     if match:
    #                         name = match.group(1)
    #                 elif not isinstance(name, (str, int)):
    #                     raise TypeError(f"typecheck() argument 'name' must be string or int, not '{typename(name)}'")
    #                 else:
    #                     if include_argument and (not isinstance(name, str) or not re.match(r"argument\s+.+", name)):
    #                         name = f"argument {name!r}"
    #                     else:
    #                         name = repr(name)

    #             finally:
    #                 del frameinfo

    #         else:
    #             if not isinstance(name, (str, int)):
    #                 raise TypeError(f"typecheck() argument 'name' must be string or int, not '{typename(name)}'")
    #             if not isinstance(function, str):
    #                 raise TypeError(f"typecheck() argument 'function' must be string, not '{typename(function)}'")
    #             if isname(function):
    #                 function += '()'
    #             if include_argument and (not isinstance(name, str) or not re.match(r"argument\s+.+", name)):
    #                 name = f"argument {name!r}"
    #             else:
    #                 name = repr(name)

    #         if isinstance(test, tuple):
    #             options = join_natural(('string' if typ is str else typ.__name__ for typ in test), word='or')
    #         else:
    #             options = test.__name__

    #         if name is None:
    #             msg = f"{function} argument value at index {index} must be {options}, not '{typename(value)}'"
    #         else:
    #             if index_format is FormatIndexMode.NO_FORMAT: 
    #                 msg = f"{function} {name}[{index}] must be {options}, not '{typename(value)}'"
    #             elif index_format is FormatIndexMode.FORMAT:
    #                 msg = f"{function} {name.format(index)} must be {options}, not '{typename(value)}'"
    #             elif index_format is FormatIndexMode.OLD_FORMAT:
    #                 msg = f"{function} {name % index} must be {options}, not '{typename(value)}'"

    #         raise TypeError(msg)

# def listtypecheck(iterable, itertypetest, test, *, name=None, function=None, include_argument=True, index_format=FormatIndexMode.NO_FORMAT):
    # typecheck(index_format, FormatIndexMode)
    # if not isinstance(iterable, itertypetest):
    #     if name is None or function is None:
    #         try:
    #             frameinfo = inspect.stack()[1]
            
    #             if function is None:
    #                 function = frameinfo.function
    #                 if function[0].isalpha() or function[0] == '_':
    #                     function += '()'
    #             elif not isinstance(function, str):
    #                 raise TypeError(f"typecheck(0 argument 'function' must be string, not '{typename(function)}'")
    #             elif isname(function):
    #                 function += '()'

    #             if name is None:
    #                 # import uncompyle6, io
    #                 # strio = io.StringIO()
    #                 # code = inspect.currentframe().f_back.f_code
    #                 # uncompyle6.code_deparse(code, out=strio)
    #                 # source = strio.getvalue()
    #                 source = frameinfo.code_context[frameinfo.index]
    #                 match = _LISTTYPECHECK_CALL_REGEX.match(source)
    #                 if match:
    #                     name = match.group(1)
    #             elif not isinstance(name, (str, int)):
    #                 raise TypeError(f"typecheck() argument 'name' must be string or int, not '{typename(name)}'")
    #             else:
    #                 if include_argument and (not isinstance(name, str) or not re.match(r"argument\s+.+", name)):
    #                     name = f"argument {name!r}"
    #                 else:
    #                     name = repr(name)

    #         finally:
    #             del frameinfo

    #     else:
    #         if not isinstance(name, (str, int)):
    #             raise TypeError(f"typecheck() argument 'name' must be string or int, not '{typename(name)}'")
    #         if not isinstance(function, str):
    #             raise TypeError(f"typecheck(0 argument 'function' must be string, not '{typename(function)}'")
    #         if isname(function):
    #             function += '()'
    #         if include_argument and (not isinstance(name, str) or not re.match(r"argument\s+.+", name)):
    #             name = f"argument {name!r}"
    #         else:
    #             name = repr(name)

    #     if isinstance(test, tuple):
    #         options = join_natural(('string' if typ is str else typ.__name__ for typ in test), word='or')
    #     else:
    #         options = test.__name__

    #     if name is None:
    #         error = TypeError(f"{function} argument must be {options}, not '{typename(iterable)}'")
    #     else:
    #         error = TypeError(f"{function} {name} must be {options}, not '{typename(iterable)}'")

    #     raise error

    # if iterable is None:
    #     return

    # try:
    #     for index, value in enumerate(iterable):
    #         if not isinstance(value, test):
    #             if name is None or function is None:
    #                 try:
    #                     frameinfo = inspect.stack()[1]
                    
    #                     if function is None:
    #                         function = frameinfo.function
    #                         if function[0].isalpha() or function[0] == '_':
    #                             function += '()'
    #                     elif not isinstance(function, str):
    #                         raise TypeError(f"typecheck(0 argument 'function' must be string, not '{typename(function)}'")
    #                     elif isname(function):
    #                         function += '()'

    #                     if name is None:
    #                         # import uncompyle6, io
    #                         # strio = io.StringIO()
    #                         # code = inspect.currentframe().f_back.f_code
    #                         # uncompyle6.code_deparse(code, out=strio)
    #                         # source = strio.getvalue()
    #                         source = frameinfo.code_context[frameinfo.index]
    #                         print(source)
    #                         match = _LISTTYPECHECK_CALL_REGEX.match(source)
    #                         if match:
    #                             name = match.group(1)
    #                     elif not isinstance(name, (str, int)):
    #                         raise TypeError(f"typecheck() argument 'name' must be string or int, not '{typename(name)}'")
    #                     else:
    #                         if include_argument and (not isinstance(name, str) or not re.match(r"argument\s+.+", name)):
    #                             name = f"argument {name!r}"
    #                         else:
    #                             name = repr(name)

    #                 finally:
    #                     del frameinfo

    #             else:
    #                 if not isinstance(name, (str, int)):
    #                     raise TypeError(f"typecheck() argument 'name' must be string or int, not '{typename(name)}'")
    #                 if not isinstance(function, str):
    #                     raise TypeError(f"typecheck(0 argument 'function' must be string, not '{typename(function)}'")
    #                 if isname(function):
    #                     function += '()'
    #                 if include_argument and (not isinstance(name, str) or not re.match(r"argument\s+.+", name)):
    #                     name = f"argument {name!r}"
    #                 else:
    #                     name = repr(name)

    #             if isinstance(test, tuple):
    #                 options = join_natural(('string' if typ is str else typ.__name__ for typ in test), word='or')
    #             else:
    #                 options = test.__name__

    #             if name is None:
    #                 msg = f"{function} argument value at index {index} must be {options}, not '{typename(value)}'"
    #             else:
    #                 if index_format is FormatIndexMode.NO_FORMAT: 
    #                     msg = f"{function} {name}[{index}] must be {options}, not '{typename(value)}'"
    #                 elif index_format is FormatIndexMode.FORMAT:
    #                     msg = f"{function} {name.format(index)} must be {options}, not '{typename(value)}'"
    #                 elif index_format is FormatIndexMode.OLD_FORMAT:
    #                     msg = f"{function} {name % index} must be {options}, not '{typename(value)}'"

    #             raise TypeError(msg)

    # except TypeError as e:
    #     if str(e) == f"'{type(iterable).__name__}' object is not iterable":
    #         return
    #     else:
    #         raise

class LookAheadListIterator(object):
    def __init__(self, iterable):
        self.list = list(iterable)

        self.marker = 0
        self.saved_markers = []

        self.default = None
        self.value = None

    def __iter__(self):
        return self

    def set_default(self, value):
        self.default = value

    def next(self):
        return self.__next__()

    def previous(self):
        try:
            self.value = self.list[self.marker-1]
            self.marker -= 1
        except IndexError:
            pass
        return self.value

    def __next__(self):
        try:
            self.value = self.list[self.marker]
            self.marker += 1
        except IndexError:
            raise StopIteration()

        return self.value

    def look(self, i=0):
        """ Look ahead of the iterable by some number of values with advancing
        past them.

        If the requested look ahead is past the end of the iterable then None is
        returned.

        """

        try:
            self.value = self.list[self.marker + i]
        except IndexError:
            return self.default

        return self.value

    def last(self):
        return self.value

    def __enter__(self):
        self.push_marker()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Reset the iterator if there was an error
        if exc_type or exc_val or exc_tb:
            self.pop_marker(True)
        else:
            self.pop_marker(False)

    def push_marker(self):
        """ Push a marker on to the marker stack """
        # print('push marker, stack =', self.saved_markers)
        self.saved_markers.append(self.marker)

    def pop_marker(self, reset):
        """ Pop a marker off of the marker stack. If reset is True then the
        iterator will be returned to the state it was in before the
        corresponding call to push_marker().

        """

        saved = self.saved_markers.pop()
        if reset:
            # print(f'reset {saved}, stack =', self.saved_markers)
            self.marker = saved
        # elif self.saved_markers:
        #     print(f'pop marker {saved}, no reset, stack =', self.saved_markers)
            # self.saved_markers[-1] = saved