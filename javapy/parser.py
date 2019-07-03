import javapy.tree as tree
from javapy.util import *
from javapy.tokenize import *

class JavaSyntaxError(SyntaxError):
    def __init__(self, msg='', at=None, token=None, got=None):
        if got is None:
            typecheck(token, (NoneType, TokenInfo), function='JavaSyntaxError')
        else:
            if token is not None:
                raise ValueError("JavaSyntaxError() arguments 'token' and 'got' are mutually exclusive")
            typecheck(got, TokenInfo, function='JavaSyntaxError')

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
                raise TypeError(f"JavaSyntaxError() argument 'at' must be string or (filename: str, line#: int, column#: int, line: str) tuple, not {typename(at)!r}")
            # msg = msg.strip() + ' '
            # if not added_open_bracket:
            #     msg += '['
            #     added_open_bracket = True
            # msg += f"in file \"{repr(at[0])[1:-1]}\" on line {at[1]}, column {at[2]} ({at[3].strip()})"
        
        if at is not None:
            super().__init__(msg, at)
        else:
            super().__init__(msg)

class Parser:
    def __init__(self, tokens, filename='<unknown source>'):
        typecheck(filename, str, function="Parser")
        self.tokens = LookAheadListIterator(tokens)
        self._scope = [False]
        self.filename = filename
        assert self.token.type == ENCODING
        self.next() # skip past the encoding token

    @property
    def token(self) -> TokenInfo:
        return self.tokens.look()

    def next(self):
        next(self.tokens)
        while self.token.type == COMMENT:
            last = self.token
            next(self.tokens)
            if self.token.type == NEWLINE:
                idx = last.line.index(last.string)
                sub = last.line[0:idx]
                if sub == "" or sub.isspace():
                    next(self.tokens)

    @property
    def doc(self):
        lookback = -1
        last = self.tokens.look(lookback)
        while last.type == NEWLINE:
            lookback -= 1
            last = self.tokens.look(lookback)
        if last.type == COMMENT and last.string != '/**/' and last.string[0:3] == '/**':
            return last.string

    def tok_match(self, token, test):
        if isinstance(test, (tuple, set)):
            for subtest in test:
                if self.tok_match(token, subtest):
                    return True
            return False
        elif isinstance(test, str):
            return token.string == test
        elif isinstance(test, int):
            return token.exact_type == test #or test == NEWLINE and token.string == ';' # or test in (NEWLINE, DEDENT) and token.type == ENDMARKER
        else:
            typecheck(test, (str, tuple), name=1)

    def accept(self, *tests):
        self.tokens.push_marker()
        last = None
        for test in tests:
            if not self.tok_match(self.token, test):
                # if self.token.type == DEDENT and (test == NEWLINE or isinstance(test, (set, tuple)) and NEWLINE in test):
                #     continue
                self.tokens.pop_marker(reset=True)
                return None
            last = self.token.string
            self.next()
    
        if last == '': last = True
        self.tokens.pop_marker(reset=False)
        return last

    def would_accept(self, *tests):
        look = 0
        for test in tests:
            token = self.tokens.look(look)
            
            # while token.type == COMMENT \
            #         or scope > 0 and token.type in (INDENT, DEDENT, NEWLINE):
            #     look += 1
            #     token = self.tokens.look(look)
            # if token.string in '([{':
            #     scope += 1
            # elif token.string in ')]}':
            #     scope -= 1

            if not self.tok_match(token, test):
                # if self.token.type == DEDENT and (test == NEWLINE or isinstance(test, (set, tuple)) and NEWLINE in test):
                #     continue
                return False

            look += 1

        return True

    def test_str(self, test):
        if isinstance(test, (tuple, set)):
            return join_natural((self.test_str(x) for x in test), word='or')
        elif isinstance(test, int):
            return tok_name[test]
        elif isinstance(test, str):
            return repr(test)
        else:
            raise TypeError(f'invalid test: {test!r}')

    def require(self, *tests):
        result = self.accept(*tests)
        if not result:
            raise JavaSyntaxError(f'expected {" ".join(self.test_str(x) for x in tests)}', got=self.token, at=self.position())
        return result
    
    def position(self):
        """ Returns a tuple of (filename, line#, column#, line) """
        return (self.filename, *self.token.start, self.token.line)

    def parse_ident(self):
        return self.require(NAME)

    def parse_name(self):
        return tree.Name(self.parse_ident())

    def parse_class_name(self):
        token = self.token
        name = self.parse_name()
        if name == 'var':
            raise JavaSyntaxError("'var' cannot be used as a type name", at=self.position())
        return name

    def parse_qual_name(self):
        result = self.parse_ident()
        while self.would_accept('.', NAME):
            self.next()
            result += '.' + self.parse_ident()
        return tree.Name(result)

# ---------------------------------------------

# ----- Compilation Unit -----

    def parse_compilation_unit(self):
        doc = self.doc
        modifiers, annotations = self.parse_mods_and_annotations(newlines=True)
        
        if not modifiers and self.would_accept('package'):
            package = self.parse_package_declaration(doc, annotations)
            doc = self.doc
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)
        else:
            package = None

        imports = []

        if not modifiers and not annotations:
            doc = None
            while True:
                if self.would_accept('import'):
                    imports.extend(self.parse_import_declarations())
                elif self.would_accept('from'):
                    imports.extend(self.parse_from_import_declarations())
                else:
                    break
            # while self.would_accept('import'):
            #     imports.extend(self.parse_import_declarations())

        # re-parse modifiers and annotations if the were used up
        if not modifiers and not annotations:
            doc = self.doc
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)

        while self.accept(';'):
            self.accept(NEWLINE)

        if package is None and not modifiers and self.would_accept(('open', 'module')):
            return self.parse_module_declaration(imports, annotations, doc)

        if self.token.type != ENDMARKER or modifiers or annotations:
            types = [self.parse_type_declaration(doc, modifiers, annotations)]
            while self.token.type != ENDMARKER:
                if self.accept(';'):
                    self.accept(NEWLINE)
                else:
                    types.append(self.parse_type_declaration())
        else:
            types = []

        if self.token.type != ENDMARKER:
            raise JavaSyntaxError(f"unexpected token {simple_token_str(self.token)}", at=self.position())

        return tree.CompilationUnit(package=package, imports=imports, types=types)

    def parse_module_declaration(self, imports, annotations, doc):
        isopen = bool(self.accept('open'))
        self.require('module')
        name = self.parse_qual_name()
        self.require(':')
        members = []
        if self.would_accept(';'):
            self.accept(NEWLINE)
        else:
            self.require(NEWLINE, INDENT)
            if self.accept(';'):
                self.accept(NEWLINE)
            else:
                while not self.would_accept(DEDENT):
                    members.append(self.parse_directive())
            self.require(DEDENT)

        return tree.ModuleCompilationUnit(name=name, open=isopen, imports=imports, annotations=annotations, doc=doc, members=members)

# ----- Declarations -----

    def parse_package_declaration(self, doc=None, annotations=None):
        if doc is None and self.token.type == STRING:
            doc = self.token.string
            self.next()
        if annotations is None:
            annotations = self.parse_annotations(newlines=True)
        
        self.require('package')
        name = self.parse_qual_name()
        self.require(NEWLINE)

        return tree.Package(name=name, doc=doc, annotations=annotations)

    def parse_import_declarations(self):
        self.require('import')
        static = bool(self.accept('static'))
        imports = []

        parens = self.accept('(')

        name, wildcard = self.parse_import_name()
        imports.append(tree.Import(name=name, static=static, wildcard=wildcard))
        # for (name, wildcard) in self.parse_import_names():
        #     imports.append(tree.Import(name=name, static=static, wildcard=wildcard))

        while self.accept(','):
            name, wildcard = self.parse_import_name()
            imports.append(tree.Import(name=name, static=static, wildcard=wildcard))
            # for (name, wildcard) in self.parse_import_names():
            #     imports.append(tree.Import(name=name, static=static, wildcard=wildcard))

        if parens:
            self.require(')')

        self.require(NEWLINE)

        return imports

    def parse_import_name(self):
        name = self.parse_qual_name()
        wildcard = bool(self.accept('.', '*'))
        return name, wildcard

    def parse_from_import_declarations(self):
        self.require('from')
        base = self.parse_qual_name()
        self.require('import')
        static = bool(self.accept('static'))
        imports = []
        parens = self.accept('(')

        name, wildcard = self.parse_from_import_name(base)
        imports.append(tree.Import(name=name, static=static, wildcard=wildcard))

        while self.accept(','):
            name, wildcard = self.parse_from_import_name(base)
            imports.append(tree.Import(name=name, static=static, wildcard=wildcard))

        if parens:
            self.require(')')

        self.require(NEWLINE)

        return imports

    def parse_from_import_name(self, base_name):
        if self.accept('*'):
            return base_name, True
        else:
            base_name += self.parse_qual_name()
            wildcard = bool(self.accept('.', '*'))
            return base_name, wildcard

    def parse_directive(self):
        doc = self.doc
        if self.would_accept('requires'):
            return self.parse_requires_directive(doc)
        elif self.would_accept('exports'):
            return self.parse_exports_directive(doc)
        elif self.would_accept('opens'):
            return self.parse_opens_directive(doc)
        elif self.would_accept('uses'):
            return self.parse_uses_directive(doc)
        elif self.would_accept('provides'):
            return self.parse_provides_directive(doc)
        else:
            raise JavaSyntaxError("expected 'requires', 'exports', 'opens', 'uses', or 'provides'", got=self.token, at=self.position())

    def parse_requires_directive(self, doc):
        self.require('requires')
        modifiers = []
        while self.would_accept(('transitive', 'static')):
            modifiers.append(tree.Modifier(self.token.string))
            self.next()
        name = self.parse_qual_name()
        self.require(NEWLINE)
        return tree.RequiresDirective(name=name, modifiers=modifiers, doc=doc)

    def parse_exports_directive(self, doc):
        self.require('exports')
        name = self.parse_qual_name()
        to = []
        if self.accept('to'):
            parens = self.accept('(')
            to.append(self.parse_qual_name())
            while self.accept(','):
                to.append(self.parse_qual_name())
            if parens:
                self.require(')')
        self.require(NEWLINE)
        return tree.ExportsDirective(name=name, to=to, doc=doc)

    def parse_opens_directive(self, doc):
        self.require('opens')
        name = self.parse_qual_name()
        to = []
        if self.accept('to'):
            parens = self.accept('(')
            to.append(self.parse_qual_name())
            while self.accept(','):
                to.append(self.parse_qual_name())
            if parens:
                self.require(')')
        self.require(NEWLINE)
        return tree.OpensDirective(name=name, to=to, doc=doc)

    def parse_uses_directive(self, doc):
        self.require('uses')
        name = self.parse_qual_name()
        if str(name) == 'var' or str(name).endswith('.var'):
            last = self.tokens.last()
            raise JavaSyntaxError("'var' cannot be used as a type name", at=(self.filename, *last.start, last.line))
        self.require(NEWLINE)
        return tree.UsesDirective(name=name, doc=doc)

    def parse_provides_directive(self, doc):
        self.require('provides')
        name = self.parse_qual_name()
        if str(name) == 'var' or str(name).endswith('.var'):
            last = self.tokens.last()
            raise JavaSyntaxError("'var' cannot be used as a type name", at=(self.filename, *last.start, last.line))
        provides = []
        if self.accept('with'):
            parens = self.accept('(')
            provides.append(self.parse_qual_name())
            while self.accept(','):
                provides.append(self.parse_qual_name())
            if parens:
                self.require(')')
        self.require(NEWLINE)
        return tree.ProvidesDirective(name=name, provides=provides, doc=doc)

    def parse_type_declaration(self, doc=None, modifiers=None, annotations=None):
        if doc is None and self.token.type == STRING:
            doc = self.token.string
            self.next()
        if modifiers is None and annotations is None:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)
        
        if self.would_accept('class'):
            return self.parse_class_declaration(doc, modifiers, annotations)
        elif self.would_accept('interface'):
            return self.parse_interface_declaration(doc, modifiers, annotations)
        elif self.would_accept('enum'):
            return self.parse_enum_declaration(doc, modifiers, annotations)
        elif self.would_accept('@', 'interface'):
            return self.parse_annotation_declaration(doc, modifiers, annotations)
        else:
            raise JavaSyntaxError(f"expected 'class', 'interface', 'enum', or '@interface' here", got=self.token, at=self.position())
        
    def parse_mods_and_annotations(self, newlines):
        modifiers = []
        annotations = []
        while True:
            if self.would_accept('@') and not self.would_accept('@', 'interface'):
                annotations.append(self.parse_annotation())
                if newlines:
                    self.accept(NEWLINE)
            elif self.would_accept(tree.Modifier.VALUES):
                modifiers.append(tree.Modifier(self.token.string))
                self.next()
            else:
                return modifiers, annotations

    def parse_class_declaration(self, doc=None, modifiers=None, annotations=None):
        if doc is None and self.token.type == STRING:
            doc = self.token.string
            self.next()
        if modifiers is None and annotations is None:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)

        self.require('class')

        name = self.parse_class_name()
        typeparams = self.parse_type_parameters_opt() or []
        superclass = self.accept('extends') and self.parse_generic_type()
        interfaces = self.parse_generic_type_list() if self.accept('implements') else []

        members = self.parse_class_body(self.parse_class_member)

        return tree.ClassDeclaration(name=name, typeparams=typeparams, superclass=superclass, interfaces=interfaces, members=members, doc=doc, modifiers=modifiers, annotations=annotations)

    def parse_interface_declaration(self, doc=None, modifiers=None, annotations=None):
        if doc is None and self.token.type == STRING:
            doc = self.token.string
            self.next()
        if modifiers is None and annotations is None:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)

        self.require('interface')

        name = self.parse_class_name()
        typeparams = self.parse_type_parameters_opt() or []
        interfaces = self.parse_generic_type_list() if self.accept('extends') else []

        members = self.parse_class_body(self.parse_interface_member)

        return tree.InterfaceDeclaration(name=name, typeparams=typeparams, interfaces=interfaces, members=members, doc=doc, modifiers=modifiers, annotations=annotations)

    def parse_enum_declaration(self, doc=None, modifiers=None, annotations=None):
        if doc is None and self.token.type == STRING:
            doc = self.token.string
            self.next()
        if modifiers is None and annotations is None:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)

        self.require('enum')

        name = self.parse_class_name()
        interfaces = self.parse_generic_type_list() if self.accept('implements') else []

        fields, members = self.parse_enum_body()

        return tree.EnumDeclaration(name=name, interfaces=interfaces, fields=fields, members=members, doc=doc, modifiers=modifiers, annotations=annotations)

    def parse_annotation_declaration(self, doc=None, modifiers=None, annotations=None):
        if doc is None and self.token.type == STRING:
            doc = self.token.string
            self.next()
        if modifiers is None and annotations is None:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)

        self.require('@', 'interface')

        name = self.parse_class_name()
        members = self.parse_class_body(self.parse_annotation_member)

        return tree.AnnotationDeclaration(name=name, members=members, doc=doc, modifiers=modifiers, annotations=annotations)

    def parse_method_or_field_declaration(self, doc=None, modifiers=None, annotations=None, interface=False):
        if doc is None and self.token.type == STRING:
            doc = self.token.string
            self.next()
        if modifiers is None and annotations is None:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)

        typeparams = self.parse_type_parameters_opt()

        if typeparams:
            if self.would_accept(NAME, '('):
                name=self.parse_name()
                return self.parse_constructor_rest(name=name, typeparams=typeparams, doc=doc, modifiers=modifiers, annotations=annotations)
            else:
                typ = tree.VoidType() if self.accept('void') else self.parse_type(annotations=[])
                return self.parse_method_rest(return_type=typ, name=self.parse_name(), typeparams=typeparams, doc=doc, modifiers=modifiers, annotations=annotations)
        elif self.accept('void'):
            return self.parse_method_rest(return_type=tree.VoidType(), name=self.parse_name(), doc=doc, modifiers=modifiers, annotations=annotations)
        else:
            if not interface and self.would_accept(NAME, '('):
                name = self.parse_name()
                return self.parse_constructor_rest(name=name, typeparams=typeparams, doc=doc, modifiers=modifiers, annotations=annotations)
            else:
                typ = self.parse_type(annotations=[])
                name = self.parse_name()
                if self.would_accept('('):
                    return self.parse_method_rest(return_type=typ, name=name, doc=doc, modifiers=modifiers, annotations=annotations)
                else:
                    return self.parse_field_rest(var_type=typ, name=name, doc=doc, modifiers=modifiers, annotations=annotations, require_init=interface)

    def parse_annotation_method_or_field_declaration(self, doc=None, modifiers=None, annotations=None):
        if doc is None and self.token.type == STRING:
            doc = self.token.string
            self.next()
        if modifiers is None and annotations is None:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)

        if 'static' in modifiers:
            typeparams = self.parse_type_parameters_opt()
            if typeparams:
                typ = tree.VoidType() if self.accept('void') else self.parse_type(annotations=[])
                return self.parse_method_rest(return_type=typ, name=self.parse_name(), typeparams=typeparams, doc=doc, modifiers=modifiers, annotations=annotations)
            elif self.accept('void'):
                return self.parse_method_rest(return_type=tree.VoidType(), name=self.parse_name(), doc=doc, modifiers=modifiers, annotations=annotations)
            else:
                typ = self.parse_type(annotations=[])
                name = self.parse_name()
                if self.would_accept('('):
                    return self.parse_method_rest(return_type=typ, name=name, doc=doc, modifiers=modifiers, annotations=annotations)
                else:
                    return self.parse_field_rest(var_type=typ, name=name, doc=doc, modifiers=modifiers, annotations=annotations)
        
        else:
            typ = self.parse_type(annotations=[])
            name = self.parse_name()
            if self.would_accept('('):
                return self.parse_annotation_property_rest(prop_type=typ, name=name, doc=doc, modifiers=modifiers, annotations=annotations)
            else:
                return self.parse_field_rest(var_type=typ, name=name, doc=doc, modifiers=modifiers, annotations=annotations)
            
    def parse_method_rest(self, *, return_type, name, typeparams=None, doc=None, modifiers=[], annotations=[]):
        params = self.parse_parameters()
        if self.would_accept('[') or self.would_accept('@'):
            dimensions = self.parse_dimensions()
            if isinstance(return_type, tree.ArrayType):
                return_type.dimensions += dimensions
            else:
                return_type = tree.ArrayType(return_type, dimensions)
        throws = self.parse_generic_type_list() if self.accept('throws') else []
        if self.would_accept(':'):
            body = self.parse_function_body()
        else:
            self.require(NEWLINE)
            body = None

        return tree.FunctionDeclaration(name=name, return_type=return_type, params=params, throws=throws, body=body, doc=doc, modifiers=modifiers, annotations=annotations)

    def parse_constructor_rest(self, *, name, typeparams=None, doc=None, modifiers=[], annotations=[]):
        params = self.parse_parameters()
        throws = self.parse_generic_type_list() if self.accept('throws') else []
        body = self.parse_function_body()
        return tree.ConstructorDeclaration(name=name, params=params, throws=throws, body=body, doc=doc, modifiers=modifiers, annotations=annotations)

    def parse_function_body(self):
        body = self.parse_block()
        if not isinstance(body, tree.Block):
            body = tree.Block(stmts=[body])
        return body

    def parse_annotation_property_rest(self, *, prop_type, name, doc=None, modifiers=[], annotations=[]):
        self.require('(', ')')
        dimensions = self.parse_dimensions_opt()
        default = self.accept('default') and self.parse_annotation_value()
        self.require(NEWLINE)
        return tree.AnnotationProperty(type=prop_type, name=name, default=default, doc=doc, modifiers=modifiers, annotations=annotations, dimensions=dimensions)

    def parse_field_rest(self, *, var_type, name, doc=None, modifiers=[], annotations=[], require_init=False):
        declarators = [self.parse_declarator_rest(name, require_init)]
        while self.accept(','):
            declarators.append(self.parse_declarator(require_init))
        self.require(NEWLINE)
        return tree.FieldDeclaration(type=var_type, declarators=declarators, doc=doc, modifiers=modifiers, annotations=annotations)

    def parse_declarator(self, require_init=False):
        return self.parse_declarator_rest(self.parse_name(), require_init)

    def parse_declarator_rest(self, name, require_init=False):
        dimensions = self.parse_dimensions_opt()
        accept = self.require if require_init else self.accept
        init = accept('=') and self.parse_initializer()
        return tree.VariableDeclarator(name=name, init=init, dimensions=dimensions)

    def parse_parameters(self, allow_this=True):
        self.require('(')
        if self.would_accept(')'):
            params = []
        else:
            params = [self.parse_parameter_opt_this() if allow_this else self.parse_parameter()]
            while self.accept(','):
                params.append(self.parse_parameter())
        self.require(')')
        return params

    def parse_parameter_opt_this(self):
        modifiers, annotations = self.parse_mods_and_annotations(newlines=False)
        typ = self.parse_type(annotations=[])
        if not modifiers and self.accept('this'):
            return tree.ThisParameter(type=typ, annotations=annotations)
        else:
            name = self.parse_name()
            if not modifiers and self.accept('.', 'this'):
                return tree.ThisParameter(type=typ, annotations=annotations, qualifier=name)
            dimensions = self.parse_dimensions_opt()
            return tree.FormalParameter(type=typ, name=name, modifiers=modifiers, annotations=annotations, dimensions=dimensions)

    def parse_parameter(self):
        modifiers, annotations = self.parse_mods_and_annotations(newlines=False)
        typ = self.parse_type(annotations=[])
        name = self.parse_name()
        dimensions = self.parse_dimensions_opt()
        return tree.FormalParameter(type=typ, name=name, modifiers=modifiers, annotations=annotations, dimensions=dimensions)

    def parse_class_body(self, parse_member):
        self.require(':')
        if self.accept(';'):
            members = []
            self.accept(NEWLINE)
        else:
            self.require(NEWLINE, INDENT)
            members = []
            while not self.would_accept(DEDENT):
                if self.accept(';'):
                    self.accept(NEWLINE)
                else:
                    members.append(parse_member())
            self.require(DEDENT)

        return members
                    
    def parse_enum_body(self):
        self.require(':')
        if self.accept(';'):
            fields = []
            members = []
            self.accept(NEWLINE)
        else:
            self.require(NEWLINE, INDENT)
            fields = []
            members = []

            while self.would_accept(NAME, (NEWLINE, '(', ':')) or self.would_accept('@'):
                if self.would_accept('@'):
                    try:
                        with self.tokens:
                            doc = self.doc
                            annotations = self.parse_annotations(newlines=True)
                            if not self.would_accept(NAME, (NEWLINE, '(', ':')):
                                raise JavaSyntaxError('')
                    except JavaSyntaxError:
                        break
                    field = self.parse_enum_field(doc, annotations)
                else:
                    field = self.parse_enum_field()
                fields.append(field)
                    
            while not self.would_accept(DEDENT):
                if self.accept(';'):
                    self.accept(NEWLINE)
                else:
                    members.append(self.parse_class_member())

            # while not self.would_accept((';', DEDENT)):
            #     fields.append(self.parse_enum_field())
                
            # if self.accept(';'):
            #     self.accept(NEWLINE)
            #     while not self.would_accept(DEDENT):
            #         if self.accept(';'):
            #             self.accept(NEWLINE)
            #         else:
            #             members.append(self.parse_class_member())
                
            self.require(DEDENT)

        return fields, members

    def parse_class_member(self):
        doc = self.doc
        if self.would_accept('static', ':'):
            self.next() # skip past the 'static' token
            body = self.parse_block()
            return tree.InitializerBlock(body=body, static=True)
        elif self.would_accept('this', ':'):
            self.next() # skip past the 'this' token
            body = self.parse_block()
            return tree.InitializerBlock(body=body, static=False)
        else:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)
            if self.would_accept(('class', 'interface', '@', 'enum')):
                return self.parse_type_declaration(doc, modifiers, annotations)
            else:
                return self.parse_method_or_field_declaration(doc, modifiers, annotations)

    def parse_interface_member(self):
        doc = self.doc
        modifiers, annotations = self.parse_mods_and_annotations(newlines=True)
        if self.would_accept(('class', 'interface', '@', 'enum')):
            return self.parse_type_declaration(doc, modifiers, annotations)
        else:
            return self.parse_method_or_field_declaration(doc, modifiers, annotations, interface=True)

    def parse_enum_field(self, doc=None, annotations=None):
        if doc is None:
            doc = self.doc
        if annotations is None:
            annotations = self.parse_annotations(newlines=True)
        name = self.parse_name()
        if self.would_accept('('):
            args = self.parse_args()
        else:
            args = None
        if self.would_accept(':'):
            members = self.parse_class_body(self.parse_class_member)
        else:
            members = None
            self.require(NEWLINE)

        return tree.EnumField(name=name, args=args, members=members, doc=doc, annotations=annotations)

    def parse_annotation_member(self):
        doc = self.doc
        if self.would_accept('static', ':'):
            self.next() # skips past the 'static' token
            body = self.parse_block()
            return tree.InitializerBlock(body=body, static=True)
        elif self.would_accept('dynamic', ':'):
            body = self.parse_block()
            return tree.InitializerBlock(body=body, static=False)
        else:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=True)
            if self.would_accept(('class', 'interface', '@', 'enum')):
                return self.parse_type_declaration(doc, modifiers, annotations)
            else:
                return self.parse_annotation_method_or_field_declaration(doc, modifiers, annotations)

# ----- Statements -----

    def parse_statement(self):
        if self.would_accept('if'):
            return self.parse_if()
        elif self.would_accept('for'):
            return self.parse_for()
        elif self.would_accept('while'):
            return self.parse_while()
        elif self.would_accept('do'):
            return self.parse_do()
        elif self.would_accept('try'):
            return self.parse_try()
        elif self.would_accept('break'):
            return self.parse_break()
        elif self.would_accept('continue'):
            return self.parse_continue()
        elif self.would_accept('yield'):
            return self.parse_yield()
        elif self.would_accept('throw'):
            return self.parse_throw()
        elif self.would_accept('return'):
            return self.parse_return()
        elif self.would_accept('switch'):
            return self.parse_switch()
        elif self.would_accept('synchronized'):
            return self.parse_synchronized()
        elif self.would_accept('assert'):
            return self.parse_assert()
        elif self.accept(';'):
            self.require(NEWLINE)
            return tree.EmptyStatement()
        elif self.would_accept('else'):
            raise JavaSyntaxError("'else' without 'if'", at=self.position())
        elif self.would_accept(('case', 'default')):
            raise JavaSyntaxError(f"'{self.token.string}' outside 'switch'", at=self.position())
        else:
            expr = self.parse_expr()
            self.require(NEWLINE)
            return tree.ExpressionStatement(expr)

    def parse_block_statement(self):
        if self.would_accept(NAME, ':', (NEWLINE, 'if', 'while', 'for', 'do', 'switch', 'synchronized', 'try')):
            label = self.parse_name()
            if self.would_accept(':', NEWLINE):
                return tree.LabeledStatement(label=label, stmt=self.parse_block())
            else:
                self.next() # skips past the ':' token
                return tree.LabeledStatement(label=label, stmt=self.parse_statement())

        if self.would_accept('final') or self.would_accept('@') and not self.would_accept('@', 'interface'):
            return self.parse_class_or_variable_decl()
        if self.would_accept(('class', 'abstract')):
            return self.parse_class_declaration(doc=self.doc)

        if self.would_accept((NAME, tree.PrimitiveType.VALUES)):
            try:
                with self.tokens:
                    return self.parse_variable_decl()
            except JavaSyntaxError as e1:
                try:
                    return self.parse_statement()
                except JavaSyntaxError as e2:
                    raise e2 from e1

        return self.parse_statement()

    def parse_class_or_variable_decl(self):
        doc = self.doc
        modifiers, annotations = self.parse_mods_and_annotations(newlines=True)
        if self.would_accept('class'):
            return self.parse_class_declaration(doc, modifiers, annotations)
        else:
            return self.parse_variable_decl(doc, modifiers, annotations)

    def parse_variable_decl(self, doc=None, modifiers=None, annotations=None, end=NEWLINE):
        if doc is None:
            doc = self.doc
        if modifiers is None and annotations is None:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=(end == NEWLINE))
        if self.accept('var'):
            typ = tree.GenericType(name=tree.Name('var'))
        else:
            typ = self.parse_type()
        declarators = [self.parse_declarator()]
        while self.accept(','):
            declarators.append(self.parse_declarator())
        self.require(end)
        return tree.VariableDeclaration(type=typ, declarators=declarators, doc=doc, modifiers=modifiers, annotations=annotations)

    def parse_block(self):
        self.require(':')

        if self.accept(';'):
            self.require(NEWLINE)
            return tree.Block(stmts=[])
        elif self.accept(NEWLINE):
            self.require(INDENT)
            stmts = [self.parse_block_statement()]
            while not self.would_accept(DEDENT):
                stmts.append(self.parse_block_statement())
            self.require(DEDENT)

            if len(stmts) == 1 and isinstance(stmts[0], tree.EmptyStatement):
                del stmts[0]
                
            return tree.Block(stmts)
        else:
            return self.parse_statement()

    def parse_if(self):
        self.require('if')
        condition = self.parse_expr()
        body = self.parse_block()
        if self.accept('else'):
            if self.would_accept('if'):
                elsebody = self.parse_if()
            else:
                elsebody = self.parse_block()
        else:
            elsebody = None
        return tree.IfStatement(condition=condition, body=body, elsebody=elsebody)

    def parse_for(self):
        self.require('for')
        control = self.parse_for_control()
        body = self.parse_block()
        return tree.ForLoop(control=control, body=body)

    def parse_for_control(self):
        try:
            with self.tokens:
                return self.parse_enhanced_for_control()
        except JavaSyntaxError:
            pass

        if self.accept(';'):
            init = None
        else:
            eat_semi = False
            try:
                with self.tokens:
                    parens = self.accept('(')
                    init = self.parse_variable_decl(end=')' if parens else ';')
                    eat_semi = parens
            except JavaSyntaxError:
                init = tree.ExpressionStatement(self.parse_expr())
                eat_semi = True

            if eat_semi:
                self.require(';')

        if self.accept(';'):
            condition = None
        else:
            condition = self.parse_expr()
            self.require(';')

        update = []

        if not self.would_accept(':'):
            if self.would_accept('('):
                try:
                    with self.tokens:
                        parens = self.accept('(')
                        update.append(self.parse_expr())
                        if not self.would_accept((',', ':')):
                            raise JavaSyntaxError('')
                        while self.accept(','):
                            update.append(self.parse_expr())
                except JavaSyntaxError as e:
                    if str(e) == '':
                        parens = False
                        update.append(self.parse_expr())
                        while self.accept(','):
                            update.append(self.parse_expr())
                    else:
                        raise
            else:
                parens = False
                update.append(self.parse_expr())
                while self.accept(','):
                    update.append(self.parse_expr())

            if parens:
                self.require(')')

        return tree.ForControl(init=init, condition=condition, update=update)

    def parse_enhanced_for_control(self):
        var = self.parse_enhanced_for_var()
        self.require(':')
        iterable = self.parse_expr()
        return tree.EnhancedForControl(var=var, iterable=iterable)

    def parse_enhanced_for_var(self):
        parens = self.accept('(')
        modifiers, annotations = self.parse_mods_and_annotations(newlines=parens)
        typ = self.parse_type(annotations=[])
        name = self.parse_name()
        dimensions = self.parse_dimensions_opt()
        if parens:
            self.require(')')
        return tree.VariableDeclaration(type=typ, declarators=[tree.VariableDeclarator(name=name, dimensions=dimensions)], modifiers=modifiers, annotations=annotations)

    def parse_while(self):
        self.require('while')
        condition = self.parse_expr()
        body = self.parse_block()
        return tree.WhileLoop(condition=condition, body=body)

    def parse_synchronized(self):
        self.require('synchronized')
        lock = self.parse_expr()
        body = self.parse_block()
        return tree.SynchronizedBlock(lock=lock, body=body)

    def parse_do(self):
        self.require('do')
        body = self.parse_block()
        self.require('while')
        condition = self.parse_expr()
        self.require(NEWLINE)
        return tree.DoWhileLoop(condition=condition, body=body)

    def parse_try(self):
        self.require('try')
        if self.would_accept(':'):
            resources = None
        else:
            parens = self.accept('(')
            resources = [self.parse_try_resource()]
            while self.accept(';'):
                if parens and self.would_accept(')'):
                    break
                resources.append(self.parse_try_resource())
        body = self.parse_block()
        catches = []
        while self.would_accept('catch'):
            catches.append(self.parse_catch())

        finallybody = self.accept('finally') and self.parse_block()

        return tree.TryStatement(resources=resources, catches=catches, body=body, finallybody=finallybody)

    def parse_catch(self):
        self.require('catch')
        parens = self.accept('(')
        
        modifiers, annotations = self.parse_mods_and_annotations(newlines=False)
        typ = self.parse_type_intersection()

        if parens and self.accept(')'):
            parens = False

        name = self.parse_name()
        catchvar = tree.CatchVar(type=typ, name=name, modifiers=modifiers, annotations=annotations)

        if parens:
            self.require(')')

        body = self.parse_block()

        return tree.CatchClause(var=catchvar, body=body)                

    def parse_try_resource(self):
        try:
            with self.tokens:
                modifiers, annotations = self.parse_mods_and_annotations(newlines=False)
                typ = self.parse_generic_type()
                name = self.parse_name()
                self.require('=')
                init = self.parse_expr()
                return tree.TryResource(name=name, type=typ, init=init, modifiers=modifiers, annotations=annotations)
        except JavaSyntaxError:
            return self.parse_expr()

    def parse_switch(self):
        self.require('switch')
        condition = self.parse_expr()
        self.require(':', NEWLINE, INDENT)
        cases = [self.parse_case()]
        while not self.would_accept(DEDENT):
            cases.append(self.parse_case())
        self.require(DEDENT)
        return tree.Switch(condition=condition, cases=cases)

    def parse_case(self):
        if self.accept('default'):
            labels = None
        else:
            self.require('case')
            parens = self.accept('(')
            labels = [self.parse_case_label()]
            while self.accept(','):
                labels.append(self.parse_case_label())
            if parens:
                self.require(')')
        if self.accept('->'):
            if self.would_accept('throw'):
                stmts = [self.parse_throw()]
            elif self.accept('{'):
                self.require(NEWLINE, INDENT)
                stmts = []
                while not self.would_accept(DEDENT):
                    stmts.append(self.parse_block_statement())
                self.require(DEDENT, '}')
                self.accept(NEWLINE)
                stmts = [tree.Block(stmts)]
            elif self.accept(NEWLINE, INDENT):
                stmts = []
                while not self.would_accept(DEDENT):
                    stmts.append(self.parse_block_statement())
                self.require(DEDENT)
                stmts = [tree.Block(stmts)]
            else:
                stmts = [tree.ExpressionStatement(self.parse_expr())]
                self.require(NEWLINE)
            return tree.SwitchCase(labels=labels, stmts=stmts, arrow=True)
        elif self.would_accept(':', NEWLINE, ('case', 'default')):
            self.next() # skip past the ':' token
            self.next() # skip past the NEWLINE token
            return tree.SwitchCase(labels=labels, stmts=[], arrow=False)
        else:
            return tree.SwitchCase(labels=labels, stmts=self.parse_block().stmts, arrow=False)

    def parse_case_label(self):
        if self.would_accept(NAME, ('->', ':')) or self.would_accept('(', NAME, ')', ('->', ':')):
            return self.parse_primary()
        else:
            return self.parse_expr()

    def parse_return(self):
        self.require('return')
        if self.accept(NEWLINE):
            return tree.ReturnStatement()
        else:
            result = tree.ReturnStatement(self.parse_expr())
            self.require(NEWLINE)
            return result

    def parse_throw(self):
        self.require('throw')
        result = tree.ThrowStatement(self.parse_expr())
        self.require(NEWLINE)
        return result

    def parse_break(self):
        self.require('break')
        if self.accept(NEWLINE):
            return tree.BreakStatement()
        else:
            result = tree.BreakStatement(self.parse_name())
            self.require(NEWLINE)
            return result

    def parse_continue(self):
        self.require('continue')
        if self.accept(NEWLINE):
            return tree.ContinueStatement()
        else:
            result = tree.ContinueStatement(self.parse_name())
            self.require(NEWLINE)
            return result

    def parse_yield(self):
        self.require('yield')
        result = tree.YieldStatement(self.parse_expr())
        self.require(NEWLINE)
        return result

    def parse_assert(self):
        self.require('assert')
        condition = self.parse_expr()
        message = self.accept(':') and self.parse_expr()
        self.require(NEWLINE)
        return tree.AssertStatement(condition=condition, message=message)

# ----- Type Stuff -----

    def parse_type_parameters_opt(self):
        if self.would_accept('<'):
            return self.parse_type_parameters()

    def parse_type_parameters(self):
        self.require('<')
        parens = self.accept('(')
        params = [self.parse_type_parameter()]
        while self.accept(','):
            params.append(self.parse_type_parameter())
        if parens:
            self.require(')')
        self.require('>')
        return params

    def parse_type_parameter(self, annotations=None):
        if annotations is None:
            annotations = self.parse_annotations(newlines=False)

        name = self.parse_name()
        bound = self.accept('extends') and self.parse_type_union()

        return tree.TypeParameter(name=name, bound=bound, annotations=annotations)

    def parse_annotations(self, newlines):
        annotations = []
        while self.would_accept('@') and not self.would_accept('@', 'interface'):
            annotations.append(self.parse_annotation())
            if newlines:
                self.accept(NEWLINE)
        return annotations

    def parse_annotation(self):
        self.require('@')
        typ = tree.GenericType(name=self.parse_qual_name())

        if self.accept('('):
            if self.would_accept(NAME, '='):
                args = [self.parse_annotation_arg()]
                while self.accept(','):
                    args.append(self.parse_annotation_arg())
            elif not self.would_accept(')'):
                args = self.parse_annotation_value()
            self.require(')')
        else:
            args = None

        return tree.Annotation(type=typ, args=args)

    def parse_annotation_arg(self):
        name = self.parse_name()
        self.require('=')
        value = self.parse_annotation_value()
        return tree.AnnotationArgument(name, value)

    def parse_annotation_value(self):
        if self.would_accept('@'):
            return self.parse_annotation()
        elif self.would_accept('{'):
            return self.parse_annotation_array()
        else:
            return self.parse_expr()

    def parse_annotation_array(self):
        self.require('{')
        values = []
        if not self.would_accept('}'):
            if not self.accept(','):
                while True:
                    values.append(self.parse_annotation_value())
                    if not self.accept(',') or self.would_accept('}'):
                        break

        self.require('}')

        return tree.ArrayInitializer(values)

    def parse_type_args_opt(self):
        if self.would_accept('<'):
            return self.parse_type_args()

    def parse_type_args(self):
        self.require('<')
        parens = self.accept('(')
        args = []
        if not self.would_accept('>'):
            args.append(self.parse_type_arg())
            while self.accept(','):
                args.append(self.parse_type_arg())
        if parens:
            self.require(')')
        self.require('>')
        return args

    def parse_type_arg(self, annotations=None):
        if annotations is None:
            annotations = self.parse_annotations(newlines=False)

        if self.accept('?'):
            bound = self.accept(('extends', 'super'))
            base = bound and self.parse_type_union(annotations=[])
            return tree.TypeArgument(base=base, bound=bound, annotations=annotations)
        
        else:
            return self.parse_generic_type_or_array(annotations)

    def parse_type(self, annotations=None):
        if annotations is None:
            annotations = self.parse_annotations(newlines=False)

        typ = self.parse_base_type(annotations=[])
        if self.would_accept('[') or self.would_accept('@'):
            dimensions = self.parse_dimensions()
            typ = tree.ArrayType(typ, dimensions, annotations=annotations)
        else:
            typ.annotations += annotations
        
        return typ

    def parse_cast_type(self, annotations=None):
        if annotations is None:
            annotations = self.parse_annotations(newlines=False)

        typ = self.parse_base_type(annotations=[])
        if self.would_accept('[') or self.would_accept('@'):
            dimensions = self.parse_dimensions()
            typ = tree.ArrayType(typ, dimensions, annotations=annotations)
        else:
            typ.annotations += annotations

        if isinstance(typ, tree.GenericType) and self.accept('&'):
            types = [typ, self.parse_generic_type()]
            while self.accept('&'):
                types.append(self.parse_generic_type())
            typ = tree.TypeUnion(types)
        
        return typ

    def parse_base_type(self, annotations=None):
        if annotations is None:
            annotations = self.parse_annotations(newlines=False)

        if self.would_accept(tree.PrimitiveType.VALUES):
            name = self.token.string
            self.next()
            return tree.PrimitiveType(name, annotations=annotations)

        else:
            return self.parse_generic_type(annotations)

    def parse_generic_type(self, annotations=None):
        if annotations is None:
            annotations = self.parse_annotations(newlines=False)

        name = self.parse_qual_name()
        if str(name) == 'var' or str(name).endswith('.var'):
            last = self.tokens.last()
            raise JavaSyntaxError("'var' cannot be used as a type name", at=(self.filename, *last.start, last.line))
        typeargs = self.parse_type_args_opt()

        typ = tree.GenericType(name, typeargs=typeargs)

        while self.would_accept('.', NAME):
            self.next() # skips past the '.' token
            name = self.parse_name()
            if str(name) == 'var':
                last = self.tokens.last()
                raise JavaSyntaxError("'var' cannot be used as a type name", at=(self.filename, *last.start, last.line))
            typeargs = self.parse_type_args_opt()

            typ = tree.GenericType(name, typeargs=typeargs, container=typ)

        return typ

    def parse_generic_type_or_array(self, annotations=None):
        if annotations is None:
            annotations = self.parse_annotations(newlines=False)

        if self.would_accept(tree.PrimitiveType.VALUES):
            name = self.token.string
            next(self.token)
            dimensions = self.parse_dimensions()
            return tree.ArrayType(tree.PrimitiveType(name), dimensions, annotations=annotations)

        else:
            typ = self.parse_generic_type(annotations)
            if self.would_accept('[') or self.would_accept('@'):
                typ.annotations = []
                dimensions = self.parse_dimensions()
                typ = tree.ArrayType(typ, dimensions, annotations=annotations)
            return typ

    def parse_type_union(self, annotations=None):
        parens = self.accept('(')
        if annotations is None:
            annotations = self.parse_annotations(newlines=False)

        typ = self.parse_generic_type(annotations=[])

        if self.accept('&'):
            types = [typ, self.parse_generic_type()]
            while self.accept('&'):
                types.append(self.parse_generic_type())
            typ = tree.TypeUnion(types)

        else:
            typ.annotations = annotations

        if parens:
            self.require(')')

        return typ

    def parse_type_intersection(self, annotations=None):
        parens = self.accept('(')
        if annotations is None:
            annotations = self.parse_annotations(newlines=False)

        typ = self.parse_generic_type(annotations=[])

        if self.accept('|'):
            types = [typ, self.parse_generic_type()]
            while self.accept('|'):
                types.append(self.parse_generic_type())
            typ = tree.TypeIntersection(types)

        else:
            typ.annotations = annotations

        if parens:
            self.require(')')

        return typ

    def parse_generic_type_list(self):
        parens = self.accept('(')
        types = [self.parse_generic_type()]
        while self.accept(','):
            types.append(self.parse_generic_type())
        if parens:
            self.require(')')
        return types

    def parse_dimensions(self):
        dimensions = [self.parse_dimension()]
        while self.would_accept('[') or self.would_accept('@'):
            dimensions.append(self.parse_dimension())
        return dimensions

    def parse_dimensions_opt(self):
        if self.would_accept('[') or self.would_accept('@'):
            return self.parse_dimensions()
        else:
            return []

    def parse_dimension(self):
        if self.would_accept('@'):
            result = self.parse_annotations(newlines=False)
        else:
            result = None
        self.require('[', ']')
        return result

# ----- Expressions -----

    def parse_expr(self):
        return self.parse_assignment()

    def parse_initializer(self):
        if self.would_accept('{'):
            return self.parse_array_init()
        else:
            return self.parse_expr()

    def parse_array_init(self):
        self.require('{')
        elements = []
        if not self.would_accept('}'):
            if not self.accept(','):
                elements.append(self.parse_initializer())
                while self.accept(','):
                    if self.would_accept('}'):
                        break
                    elements.append(self.parse_initializer())
        self.require('}')
        return tree.ArrayInitializer(elements)

    def parse_assignment(self):
        result = self.parse_conditional()
        if self.token.string in tree.Assignment.OPS:
            op = self.token.string
            self.next()
            result = tree.Assignment(op=op, lhs=result, rhs=self.parse_assignment())
        return result

    def parse_binary_expr(self, base_func, operators):
        result = base_func()
        while True:
            for key in operators:
                if self.accept(key):
                    result = tree.BinaryExpression(op=key, lhs=result, rhs=base_func())
                    break
            else:
                return result

    def has_switch_last(self):
        look = -1
        token = self.tokens.look(look)
        while token.type in (COMMENT, NEWLINE, INDENT, DEDENT, NL):
            token = self.tokens.look(look)
            look -= 1

        return token.type == KEYWORD and token.string == 'switch'

    def parse_conditional(self):
        if not self.has_switch_last() and self.would_accept(NAME, '->') or self.would_accept('('):
            try:
                with self.tokens:
                    result = self.parse_lambda()
            except JavaSyntaxError:
                result = self.parse_logic_or_expr()
        else:
            result = self.parse_logic_or_expr()            
        if self.accept('?'):
            truepart = self.parse_assignment()
            falsepart = self.parse_conditional()
            result = tree.ConditionalExpression(condition=result, truepart=truepart, falsepart=falsepart)
        return result

    def parse_logic_or_expr(self):
        result = self.parse_logic_and_expr()
        while self.accept('||'):
            result = tree.BinaryExpression(op='||', lhs=result, rhs=self.parse_logic_and_expr())
        return result

    def parse_logic_and_expr(self):
        result = self.parse_bitwise_or_expr()
        while self.accept('&&'):
            result = tree.BinaryExpression(op='&&', lhs=result, rhs=self.parse_bitwise_or_expr())
        return result

    def parse_bitwise_or_expr(self):
        result = self.parse_bitwise_xor_expr()
        while self.accept('|'):
            result = tree.BinaryExpression(op='|', lhs=result, rhs=self.parse_bitwise_xor_expr())
        return result

    def parse_bitwise_xor_expr(self):
        result = self.parse_bitwise_and_expr()
        while self.accept('^'):
            result = tree.BinaryExpression(op='^', lhs=result, rhs=self.parse_bitwise_and_expr())
        return result

    def parse_bitwise_and_expr(self):
        result = self.parse_equality()
        while self.accept('&'):
            result = tree.BinaryExpression(op='&', lhs=result, rhs=self.parse_equality())
        return result

    def parse_equality(self):
        return self.parse_binary_expr(self.parse_comp, ('==', '!='))

    def parse_comp(self):
        result = self.parse_shift()
        while True:
            if self.would_accept(('<=', '>=', '<', '>')):
                op = self.token.string
                self.next()
                result = tree.BinaryExpression(op=op, lhs=result, rhs=self.parse_shift())
            elif self.accept('instanceof'):
                typ = self.parse_generic_type_or_array()
                result = tree.TypeTest(type=typ, expr=result)
            else:
                return result

    def parse_shift(self):
        result = self.parse_add()
        while True:
            if self.accept('<<'):
                result = tree.BinaryExpression(op='<<', lhs=result, rhs=self.parse_add())
            else:
                token1 = self.token
                if token1.string == '>':
                    token2 = self.tokens.look(1)
                    if token2.string == '>' and token2.start == token1.end:
                        token3 = self.tokens.look(2)
                        if token3.string == '>' and token3.start == token2.end:
                            self.next()
                            self.next()
                            self.next()
                            result = tree.BinaryExpression(op='>>>', lhs=result, rhs=self.parse_add())
                        else:
                            result = tree.BinaryExpression(op='>>', lhs=result, rhs=self.parse_add())
                    else:
                        return result
                else:
                    return result

    def parse_add(self):
        return self.parse_binary_expr(self.parse_mul, ('+', '-'))

    def parse_mul(self):
        return self.parse_binary_expr(self.parse_unary, ('*', '/', '%'))

    def parse_unary(self):
        if self.would_accept(tree.UnaryExpression.OPS):
            op = self.token.string
            self.next()
            return tree.UnaryExpression(op=op, expr=self.parse_unary())

        elif self.would_accept(('++', '--')):
            op = self.token.string
            self.next()
            return tree.IncrementExpression(op=op, prefix=True, expr=self.parse_postfix())

        else:
            if self.would_accept('('):
                try:
                    with self.tokens:
                        self.next() # skip past the '(' token
                        typ = self.parse_cast_type()
                        self.require(')')
                        if self.would_accept('(') or self.would_accept(NAME, '->'):
                            try:
                                with self.tokens:
                                    expr = self.parse_lambda()
                            except JavaSyntaxError:
                                expr = self.parse_postfix()
                        else:
                            expr = self.parse_postfix()
                        return tree.CastExpression(type=typ, expr=expr)
                except JavaSyntaxError:
                    pass
            result = self.parse_postfix()
            if self.would_accept(('++', '--')):
                op = self.token.string
                self.next()
                result = tree.IncrementExpression(op=op, prefix=False, expr=result)
            return result

    def parse_postfix(self):
        result = self.parse_primary()
        while True:
            if self.would_accept('.'):
                result = self.parse_dot_expr(result)

            elif self.accept('['):
                index = self.parse_expr()
                self.require(']')
                result = tree.IndexExpression(indexed=result, index=index)

            elif self.would_accept('::'):
                result = self.parse_ref_expr(result)

            else:
                return result

    def parse_ref_expr(self, object):
        self.require('::')
        if self.accept('new'):
            return tree.MethodReference(name='new', object=object)
        else:
            return tree.MethodReference(name=self.parse_name(), object=object)

    def parse_dot_expr(self, object):
        self.require('.')
        if self.would_accept('new'):
            creator: tree.ClassCreator = self.parse_creator(allow_array=False)
            creator.object = object
            return creator

        elif self.accept('this'):
            if self.would_accept('('):
                args = self.parse_args()
                if not self.would_accept(NEWLINE):
                    self.require(NEWLINE) # raises error
                return tree.ThisCall(object=object, args=args)
            return tree.This(object=object)

        elif self.accept('super'):
            if self.would_accept('('):
                args = self.parse_args()
                if not self.would_accept(NEWLINE):
                    self.require(NEWLINE) # raises error
                return tree.SuperCall(object=object, args=args)
            return tree.Super(object=object)

        elif self.would_accept(NAME):
            name = self.parse_name()
            if self.would_accept('('):
                args = self.parse_args()
                return tree.FunctionCall(object=object, name=name, args=args)

            else:
                return tree.MemberAccess(object=object, name=name)

        elif self.would_accept('<'):
            typeargs = self.parse_type_args()
            if self.accept('this'):
                args = self.parse_args()
                if not self.would_accept(NEWLINE):
                    self.require(NEWLINE) # raises error
                return tree.ThisCall(object=object, args=args, typeargs=typeargs)
            elif self.accept('super'):
                args = self.parse_args()
                if not self.would_accept(NEWLINE):
                    self.require(NEWLINE) # raises error
                return tree.SuperCall(object=object, args=args, typeargs=typeargs)
            name = self.parse_name()
            args = self.parse_args()
            return tree.FunctionCall(object=object, name=name, args=args, typeargs=typeargs)

        else:
            raise JavaSyntaxError(f"expected NAME, 'this', 'super', 'new', or '<' here", got=self.token, at=self.position())
        
    def parse_args(self):
        self.require('(')
        args = []
        if not self.would_accept(')'):
            args.append(self.parse_expr())
            while self.accept(','):
                args.append(self.parse_expr())
        self.require(')')

        return args

    def parse_primary(self):
        if self.would_accept(NUMBER):
            result = tree.Literal(self.token.string)
            self.next()
        elif self.would_accept(STRING):
            # string = eval(self.token.string)
            # if self.token.string[0] == "'" and len(string) != 1:
            #     ends = '"'
            # else:
            #     ends = self.token.string[0]
            # result = tree.Literal(ends + repr(string)[1:-1].replace('"', R'\"') + ends)
            result = tree.Literal(self.token.string)
            self.next()

        elif self.accept('true'):
            result = tree.Literal('true')

        elif self.accept('false'):
            result = tree.Literal('false')

        elif self.accept('null'):
            result = tree.NullLiteral()

        elif self.accept('this'):
            if self.would_accept('('):
                args = self.parse_args()
                if not self.would_accept(NEWLINE):
                    self.require(NEWLINE) # raises error
                result = tree.ThisCall(args=args)
            else:
                result = tree.This()

        elif self.accept('super'):
            if self.would_accept('('):
                args = self.parse_args()
                if not self.would_accept(NEWLINE):
                    self.require(NEWLINE) # raises error
                result = tree.SuperCall(args=args)
            else:
                result = tree.Super()

        elif self.would_accept('switch'):
            result = self.parse_switch_expr()

        elif self.accept('void'):
            self.require('.', 'class')
            result = tree.TypeLiteral(type=tree.VoidType())

        elif self.would_accept(tree.PrimitiveType.VALUES):
            typ = tree.PrimitiveType(name=self.token.string)
            self.next()
            if self.would_accept('[') or self.would_accept('@'):
                dimensions = self.parse_dimensions()
                typ = tree.ArrayType(base=typ, dimensions=dimensions)
            self.require('.', 'class')
            result = tree.TypeLiteral(type=typ)

        elif self.accept('('):
            result = tree.Parenthesis(self.parse_expr())
            self.require(')')

        elif self.would_accept('['):
            result = self.parse_list_literal()

        elif self.would_accept('<'):
            typeargs = self.parse_type_args()
            name = self.parse_name()
            args = self.parse_args()
            result = tree.FunctionCall(name=name, args=args, typeargs=typeargs)

        elif self.would_accept('new'):
            result = self.parse_creator()

        elif self.would_accept(NAME):
            try:
                with self.tokens:
                    typ = self.parse_type()
                    if self.accept('.', 'class'):
                        result = tree.TypeLiteral(typ)
                    elif not isinstance(typ, tree.PrimitiveType) and (not isinstance(typ, tree.GenericType) or not typ.issimple) and self.would_accept('::'):
                        result = typ
                    else:
                        raise JavaSyntaxError('')
            except JavaSyntaxError:
                    name = self.parse_name()
                    
                    if self.would_accept('('):
                        args = self.parse_args()

                        result = tree.FunctionCall(name=name, args=args)
                    
                    else:
                        result = tree.MemberAccess(name=name)

        else:
            if self.token.type == NEWLINE:
                raise JavaSyntaxError("unexpected token", token=self.token, at=self.position())
            elif self.token.type == ENDMARKER:
                raise JavaSyntaxError("reached end of file while parsing", at=self.position())
            elif self.token.type in (INDENT, DEDENT):
                raise JavaSyntaxError(f"unexpected {tok_name[self.token.type].lower()}", at=self.position())
            else:
                raise JavaSyntaxError("illegal start of expression", token=self.token, at=self.position())

        return result
        
    def parse_creator(self, allow_array=True):
        self.require('new')
        typeargs = self.parse_type_args_opt()
        annotations = self.parse_annotations(newlines=False)
        if not typeargs and allow_array and self.would_accept(tree.PrimitiveType.VALUES):
            typ = tree.PrimitiveType(name=self.token.string, annotations=annotations)
            self.next()
            dimensions = []
            annotations = self.parse_annotations(newlines=False)
            self.require('[')
            if self.accept(']'):
                dimensions.append(tree.DimensionExpression(annotations=annotations))
                while self.would_accept(('@', '[')):
                    annotations = self.parse_annotations(newlines=False) if self.would_accept('@') else []
                    self.require('[', ']')
                    dimensions.append(tree.DimensionExpression(annotations=annotations))
                init = self.parse_array_init()
                result = tree.ArrayCreator(type=typ, dimensions=dimensions, initializer=init)

            else:
                dimensions.append(tree.DimensionExpression(size=self.parse_expr(), annotations=annotations))
                self.require(']')
                while self.would_accept(('@', '[')):
                    annotations = self.parse_annotations(newlines=False) if self.would_accept('@') else []
                    self.require('[')
                    if self.accept(']'):
                        dimensions.append(tree.DimensionExpression(annotations=annotations))
                        break
                    dimensions.append(tree.DimensionExpression(annotations=annotations, size=self.parse_expr()))
                    self.require(']')
                while self.would_accept(('@', '[')):
                    annotations = self.parse_annotations(newlines=False) if self.would_accept('@') else []
                    self.require('[', ']')
                    dimensions.append(tree.DimensionExpression(annotations=annotations))
                result = tree.ArrayCreator(type=typ, dimensions=dimensions)

        else:
            typ = self.parse_generic_type()
            typ.annotations = annotations
            if not typeargs and allow_array and self.would_accept(('[', '@')):
                dimensions = []
                annotations = self.parse_annotations(newlines=False)
                self.require('[')
                if self.accept(']'):
                    dimensions.append(tree.DimensionExpression(annotations=annotations))
                    while self.would_accept(('@', '[')):
                        annotations = self.parse_annotations(newlines=False) if self.would_accept('@') else []
                        self.require('[', ']')
                        dimensions.append(tree.DimensionExpression(annotations=annotations))
                    init = self.parse_array_init()
                    result = tree.ArrayCreator(type=typ, dimensions=dimensions, initializer=init)
                    
                else:
                    dimensions.append(tree.DimensionExpression(size=self.parse_expr(), annotations=annotations))
                    self.require(']')
                    while self.would_accept(('@', '[')):
                        annotations = self.parse_annotations(newlines=False) if self.would_accept('@') else []
                        self.require('[')
                        if self.accept(']'):
                            dimensions.append(tree.DimensionExpression(annotations=annotations))
                            break
                        dimensions.append(tree.DimensionExpression(annotations=annotations, size=self.parse_expr()))
                        self.require(']')
                    while self.would_accept(('@', '[')):
                        annotations = self.parse_annotations(newlines=False) if self.would_accept('@') else []
                        self.require('[', ']')
                        dimensions.append(tree.DimensionExpression(annotations=annotations))
                    result = tree.ArrayCreator(type=typ, dimensions=dimensions)

            else:
                args = self.parse_args()
                if self.accept('{'):
                    members = []
                    if not self.accept('}'):
                        self.require(NEWLINE)
                        if not self.accept('}'):
                            self.require(INDENT)
                            while not self.would_accept(DEDENT):
                                if self.accept(';'):
                                    self.accept(NEWLINE)
                                else:
                                    members.append(self.parse_class_member())
                            self.require(DEDENT, '}')
                else:
                    members = None
                if typeargs is None:
                    typeargs = []
                result = tree.ClassCreator(type=typ, args=args, typeargs=typeargs, members=members)
        
        return result

    def parse_lambda(self):
        if self.would_accept(NAME):
            args = [self.parse_name()]
        else:
            if self.would_accept('(', NAME, (')', ',')):
                self.next() # skips past the '(' token
                args = [self.parse_name()]
                while self.accept(','):
                    args.append(self.parse_name())
                self.require(')')
            else:
                args = self.parse_parameters(allow_this=False)

        self.require('->')

        if self.accept('{'):
            self.require(NEWLINE, INDENT)
            stmts = []
            while not self.would_accept(DEDENT):
                stmts.append(self.parse_block_statement())
            self.require(DEDENT, '}')
            body = tree.Block(stmts)
        else:
            body = self.parse_expr()

        return tree.Lambda(params=args, body=body)

    def parse_switch_expr(self):
        self.require('switch')
        condition = self.parse_expr()
        self.require('{', NEWLINE, INDENT)
        cases = []
        while not self.would_accept(DEDENT):
            cases.append(self.parse_case())
        self.require(DEDENT, '}')
        return tree.Switch(condition=condition, cases=cases)

    def parse_list_literal(self):
        self.require('[')
        elements = []
        if not self.would_accept(']'):
            if not self.accept(','):
                elements.append(self.parse_expr())
                while self.accept(','):
                    if self.would_accept(']'):
                        break
                    elements.append(self.parse_expr())
        self.require(']')

        return tree.FunctionCall(args=elements, name=tree.Name('of'), object=tree.MemberAccess(name=tree.Name('List'), object=tree.MemberAccess(name=tree.Name('util'), object=tree.MemberAccess(name=tree.Name('java')))))

def parse_file(file: open) -> tree.CompilationUnit:
    return Parser(tokenize(file.readline)).parse_compilation_unit()

def parse_str(s: str, encoding='utf-8') -> tree.CompilationUnit:
    import io
    return Parser(tokenize(io.BytesIO(bytes(s, encoding)).readline)).parse_compilation_unit()