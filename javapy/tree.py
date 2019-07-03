if __name__ == '__main__':
    from os.path import basename
    print('Error:', basename(__file__), 'is not a script')
    exit(1)    

from typing import List, Set, Tuple
from abc import ABC, abstractmethod
from javapy.util import *
from textwrap import indent, dedent
import re
import functools

@functools.total_ordering
class Position:
    """ Represents a position in source code.

    :ivar line: The line number (0-based)
    :vartype line: int

    :ivar column: The column number (0-based)
    :vartype column: int

    :ivar linestr: The entire line, as a string
    :vartype linestr: str

    """
    __slots__ = ('line', 'column', 'linestr')

    def __init__(self, line: int, column: int, linestr: str):
        typecheck(line, int, function='Position')
        typecheck(column, int, function='Position')
        typecheck(linestr, str, function='Position')
        super().__setattr__('line', line)
        super().__setattr__('column', column)
        super().__setattr__('linestr', linestr)
        self.line: int
        self.column: int
        self.linestr: str    

    def __iter__(self):
        return iter((self.line, self.column, self.linestr))

    def __getitem__(self, index):
        if index < 0:
            index += 3
            if index < 0:
                raise IndexError('tuple index out of range')
        elif index > 2:
            raise IndexError('tuple index out of range')

        if index == 0:
            return self.line
        elif index == 1:
            return self.column
        elif index == 2:
            return self.linestr

    def __repr__(self):
        if self is Position.NOPOS:
            return "Position.NOPOS"
        return f"{typename(self)}(line={self.line}, column={self.column}, linestr={self.linestr!r})"

    def __setattr__(self, name, value):
        if name in self.__slots__:
            raise AttributeError(f"cannot modify attribute {name!r} in {typename(self)!r} object")
        else:
            raise AttributeError(f"{typename(self)!r} object has no attribute {name!r}")

    def __eq__(self, other):
        if isinstance(other, tuple) and len(other) >= 2 and len(other) <= 3 and isinstance(other[0], int) and isinstance(other[1], int):
            if len(other) == 3:
                if isinstance(other[2], str):
                    return self.line == other[0] and self.column == other[1] and self.linestr == other[2]
            else:
                return self.line == other[0] and self.column == other[1]
        return isinstance(other, Position) and self.line == other.line and self.column == other.column and self.linestr == other.linestr

    def __lt__(self, other):
        if isinstance(other, tuple) and len(other) >= 2 and len(other) <= 3 and isinstance(other[0], int) and isinstance(other[1], int):
            if len(other) == 3:
                if isinstance(other[2], str):
                    return self.line < other[0] or self.line == other.line and self.column < other[1]
            else:
                return self.line < other[0] or self.line == other.line and self.column < other[1]
        if isinstance(other, Position):
            return self.line < other.line or self.line == other.line and self.column < other.column
        else:
            return NotImplemented

Position.NOPOS = Position(0, 0, '')

# def cplist(lst: list) -> list:
#     if lst is not None:
#         if isinstance(lst, NodeList):
#             return lst.copy()
#         else:
#             return list(lst)

def copy(node, parent=None):
    if node is None:
        return None
    elif isinstance(node, (Node, NodeList)):
        return node.copy(parent)
    elif isinstance(node, list):
        return [copy(elem, parent) for elem in node]
    else:
        return node

class Node(ABC):
    def __init__(self, parent=None):
        typecheck(parent, (NoneType, Node), function=typename(self))

        self.parent: Node = parent
        
        self.children: NodeList = NodeList()

    def copy(self, parent=None):
        elems = {'parent': parent}
        for key, value in self.__dict__.items():
            if key not in ('parent', 'children') and key[0] != '_':
                elems[key] = copy(value)
        return type(self)(**elems)

    @abstractmethod
    def __str__(self):
        return NotImplemented

    def accept(self, visitor, value):
        """ A NodeVisitor visits this Node.
            
            :type visitor: NodeVisitor

            :return: True if the visitor should also visit this Node's children, False if it should not.
        """
        return visitor.visit_node(self, value)

    def __repr__(self):
        return f"{typename(self)}({', '.join(f'{key}={value!r}' for key, value in self.__dict__.items() if key not in ('parent', 'children'))})"

    def __delattr__(self, name):
        if name == 'parent' or name == 'children':
            raise AttributeError(f"attribute {name!r} in {typename(self)} object cannot be deleted")
        if hasattr(self, name):
            oldval = getattr(self, name)
            if isinstance(oldval, Node):
                self.children.remove(oldval)
            elif isinstance(oldval, NodeList):
                for elem in oldval:
                    try:
                        self.children.remove(elem)
                    except ValueError:
                        pass
            elif isinstance(oldval, list):
                def remove(elements):
                    for elem in elements:
                        if isinstance(elem, (Node, NoneType)):
                            try:
                                self.children.remove(elem)
                            except ValueError:
                                pass
                        elif isinstance(elem, list):
                            remove(elem)
                remove(oldval)

        super().__delattr__(name)

    def __setattr__(self, name, value):
        if name != 'parent' and name != 'children':
            if isinstance(value, Node):
                if hasattr(self, name):
                    oldval = getattr(self, name)
                    if isinstance(oldval, Node):
                        self.children.remove(oldval)
                value.parent = self
                self.children.append(value)
            elif isinstance(value, list):
                if hasattr(self, name):
                    oldval = getattr(self, name)
                    if isinstance(oldval, Node):
                        if hasattr(oldval, 'parent'):
                            oldval.parent = None
                try:
                    value = NodeList(value, self)
                except TypeError as e:
                    if str(e).startswith('NodeList()'):
                        pass
                    else:
                        raise                
                
        super().__setattr__(name, value)

class NodeList(list):
    def __init__(self, value=[], parent=None):
        listtypecheck(value, list, (Node, NoneType, list), name=0, function='NodeList')
        typecheck(parent, (NoneType, Node), function='NodeList')
        self._list = [] if value is not None and len(value) == 0 else value
        for i, value in enumerate(self._list):
            if isinstance(value, list):
                self._list[i] = NodeList(value, parent)
        self._parent = parent

    def copy(self, parent=None):
        return [copy(elem, parent) for elem in self]

    def __iadd__(self, other):
        if not isinstance(other, list):
            return NotImplemented
        self.extend(other)
        return self

    def __bool__(self):
        return bool(self._list)

    def __setattr__(self, name, value):
        if name == '_list':
            if hasattr(self, name) and getattr(self, name) is not None:
                raise AttributeError(f'cannot change {name} attribute of NodeList object')
        elif name == 'parent':
            raise AttributeError("cannot change 'parent' attribute of NodeList object")
        super().__setattr__(name, value)
        
    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        if not isinstance(value, (Node, NoneType)):
            raise AttributeError(f'cannot change parent attribute of NodeList object to {typename(value)!r} instance')
        for elem in self._list:
            if elem is not None:
                elem.parent = value
        self._parent = value

    def __iter__(self):
        return iter(self._list)

    def __len__(self):
        return len(self._list)

    def __getitem__(self, index):
        return self._list[index]

    def __str__(self):
        return str(self._list)

    def __repr__(self):
        return f"NodeList({self._list!r})"

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            for elem in self._list[index]:
                elem.parent = None
            self._list[index] = value
            for elem in value:
                elem.parent = self.parent
        elif isinstance(index, tuple):
            for subindex in index:
                self.__setitem__(subindex, value)
        else:
            typecheck(value, (NoneType, Node))
            oldval = self._list[index]
            if hasattr(oldval, 'parent'):
                oldval.parent = None
            self._list[index] = value
            if value is not None:
                value.parent = self.parent

    def __delattr__(self, name):
        if name == '_list' or name == '_parent':
            raise AttributeError(f'cannot delete {name} attribute of NodeList object')
        super().__delattr__(name)

    def __delitem__(self, index):
        if isinstance(index, slice):
            for elem in self._list[index]:
                elem.parent = None
            del self._list[index]
        elif isinstance(index, tuple):
            for subindex in index:
                self.__delitem__(subindex)
        else:
            self._list[index].parent = None
            del self._list[index]

    def __eq__(self, other):
        if other is self:
            return True
        if isinstance(other, NodeList):
            return self._list == other._list
        else:
            return self._list == other

    def append(self, element):
        """ Append object to the end of the list. """
        self._list.append(element)
        if element is not None:
            element.parent = self.parent

    def extend(self, iterable):
        """ Extend list by appending elements from the iterable. """
        oldlen = len(self._list)
        self._list.extend(iterable)
        newlen = len(self._list)
        for i in range(oldlen, newlen):
            elem = self._list[i]
            if elem is not None:
                typecheck(elem, Node, name=f"iterable[{i}]")
                elem.parent = self.parent

    def clear(self):
        """ Remove all items from list. """
        for elem in self._list:
            if elem is not None:
                elem.parent = None

        self._list.clear()

    def remove(self, value, all=True, by_instance=True):
        """ Remove occurrences of value.

        Raises ValueError if the value is not present.
        """
        import operator
        equal = operator.is_ if by_instance else operator.eq

        for i in reversed(range(len(self._list))):
            elem = self[i]
            if equal(value, elem):
                if isinstance(elem, Node):
                    elem.parent = None
                del self._list[i]
                if not all:
                    return
        else:
            return

        raise ValueError

    def pop(self, index=-1):
        removed = self._list.pop(index)
        if removed is not None:
            removed.parent = None
        return removed

    def insert(self, index, item):
        """ Insert item before index. """
        if item is not None:
            item.parent = self.parent
        self._list.insert(index, item)

    def index(self, x, start=None, end=None):
        if start is None:
            if end is not None:
                raise ValueError("index() 'end' argument must be None when 'start' is None")
            return self._list.index(x)
        elif end is None:
            return self._list.index(x, start)
        else:
            return self._list.index(x, start, end)

    def count(self, x):
        return self._list.count(x)

    def sort(self, key=None, reverse=False):
        self._list.sort(key, reverse)

    def reverse(self):
        self._list.reverse()


class Name(Node):
    REGEX = re.compile(r"^[a-zA-Z_$][a-zA-Z_0-9$]*(?:\.[a-zA-Z_$][a-zA-Z_0-9$]*)*$")

    def __init__(self, value, parent=None):
        if isinstance(value, Name):
            value = str(value)
        else:
            typecheck(value, str, name=0, function='Name')
        if not Name.REGEX.match(value):
            raise ValueError(f"Name() argument is not a valid name")

        super().__init__(parent)

        self.__strval: str = value

    def copy(self, parent=None):
        return Name(self.__strval, parent=parent)

    def accept(self, visitor, value):
        return visitor.visit_name(self, value)
        
    def __str__(self):
        return self.__strval

    def __hash__(self):
        return hash(self.__strval)

    def __eq__(self, other):
        return isinstance(other, Name) and str(self) == str(other) or str(self) == other

    @property
    def isdotted(self):
        return '.' in str(self)

    def __add__(self, other):
        if isinstance(other, str):
            return Name(str(self) + '.' + other)
        else:
            typecheck(other, (Name, str))
            return Name(str(self) + '.' + str(other))

    def __getitem__(self, index):
        return str(self)[index]

class CompilationUnit(Node):
    def __init__(self, *, package=None, imports=[], types=[]):
        typecheck(package, (Package, NoneType), function='CompilationUnit')
        listtypecheck(imports, list, Import, function='CompilationUnit')
        listtypecheck(types, list, TypeDeclaration, function='CompilationUnit')

        super().__init__(None)

        self.package: Package = package
        self.imports: List[Import] = imports
        self.types: List[TypeDeclaration] = types

    def copy(self, parent=None):
        if parent is not None:
            raise ValueError('Cannot give a CompilationUnit a parent node')
        return super().copy()

    def accept(self, visitor, value):
        return visitor.visit_compilation_unit(self, value)

    def __str__(self):
        result = ""
        if self.package:
            result = str(self.package)

        if self.imports:
            if result:
                result += '\n\n'
            result += '\n'.join(str(import_) for import_ in self.imports)

        if self.types:
            if result:
                result += '\n\n'
            result += '\n\n'.join(str(type_) for type_ in self.types)

        return result

class Documented(ABC):
    DOCSTR_REGEX = re.compile(r"^/\*\*?((?:[^*]|\*(?!/))*)\*/$")
    STARLINE_REGEX = re.compile(r"^(\s*\*).*")

    @abstractmethod
    def __init__(self, doc):
        if doc is not None:
            # if isinstance(doc, list):
            #     itertypecheck(doc, str, function=typename(self))
            #     lines = doc
            # else:
                typecheck(doc, str, function=typename(self))
                if not Documented.DOCSTR_REGEX.match(doc):
                    raise ValueError(f"{typename(self)}() argument 'doc' is not a valid docstring")
                doc = lstrip_multiline(doc, ignore_first=True)
                lines = doc.splitlines()
                if len(lines) > 1:
                    for line in lines[1:]:
                        if line[0] != '*':
                            break
                    else:
                        for i in range(1, len(lines)):
                            lines[i] = ' ' + lines[i]
                        doc = '\n'.join(lines)
                        
                            
            #     match = Documented.DOCSTR_REGEX.match(doc)
            #     if match:
            #         print('content 0 =', repr(match.group(1)))
            #         content = lstrip_multiline(match.group(1), ignore_first=True)
            #     else:
            #         print('content 0 =', repr(doc))
            #         content = lstrip_multiline(doc)

            #     print('content 1 =', repr(content))

            #     lines = content.splitlines()
            #     print('lines 1 =', lines)
            #     if len(lines) > 1:
            #         match = Documented.STARLINE_REGEX.match(lines[1])
            #         if match:
            #             indent = match.group(1) + '*'
            #             for line in lines:
            #                 if not line.startswith(indent):
            #                     break
            #             else:
            #                 index = slice(len(indent))
            #                 for i in range(1, len(lines)):
            #                     lines[i] = lines[i][index]
            #                 print('lines 2 =', lines)
            #                 content = lstrip_multiline('\n'.join(lines))
            #                 lines = content.splitlines()
            #                 print('lines 3 =', lines)

            # doc = '/** ' + lines[0]
            # if len(lines) > 1:
            #     for i in range(1, len(lines)):
            #         doc += '\n *'
            #         line = lines[i]
            #         if i+1 == len(lines):
            #             if line.isspace():
            #                 doc += '/'
            #             else:
            #                 doc += ' ' + line + '\n */'
            #         else:
            #             doc += ' ' + line
            # else:
            #     doc = doc.strip() + ' */'
                            
        self.doc: str = doc

    def doc_str(self, newlines=True):
        if self.doc is not None:
            if newlines:
                return self.doc + '\n'
            else:
                return self.doc + ' '
        else:
            return ""
    
class Named(ABC):
    def __init__(self, name):
        typecheck(name, Name, function=typename(self))

        self.name: Name = name

class Annotated(ABC):
    def __init__(self, annotations):
        listtypecheck(annotations, list, Annotation, function=typename(self))

        self.annotations: List[Annotation] = annotations

    def anno_str(self, newlines=True):
        result = ""
        newline = '\n' if newlines else ' '
        for anno in self.annotations:
            result += str(anno) + newline

        return result

class Dimension(ABC):
    @abstractmethod
    def __init__(self, dimensions):
        typecheck(dimensions, list, function=typename(self))
        for i, value in enumerate(dimensions):
            listtypecheck(value, (NoneType, list), Annotation, function=typename(self), name=f"dimensions[{i}]")

        self.dimensions = dimensions

    def dim_str(self):
        if self.dimensions:
            return ' '.join('[]' if dim is None else ' '.join(str(anno) for anno in dim) + ' []' for dim in self.dimensions)
        else:
            return ""

class ModuleCompilationUnit(Named, Documented, Annotated, Node):
    def __init__(self, *, imports=[], open=False, name, members=[], doc=None, annotations=[]):
        listtypecheck(imports, list, Import, function='ModuleCompilationUnit')
        typecheck(open, bool, function='ModuleCompilationUnit')
        listtypecheck(members, list, Directive, function='ModuleCompilationUnit')
        
        Node.__init__(self, parent=None)
        Named.__init__(self, name)
        Documented.__init__(self, doc)
        Annotated.__init__(self, annotations)

        self.imports: List[Import] = imports
        self.open: bool = open
        self.members: List[Directive] = members

    def accept(self, visitor, value):
        return visitor.visit_module_compilation_unit(self, value)
        
    def __str__(self):
        result = '\n'.join(str(import_) for import_ in self.imports)
        if result:
            result += '\n\n'
        result += self.doc_str() + self.anno_str()
        if self.open:
            result += "open "
        result += f"module {self.name}"
        if self.members:
            result += ' {\n\t' + '\n'.join(indent(str(member), '\t') for member in self.members) + '\n}'
        else:
            result += r' {}'
        return result

class Declaration(Annotated):
    @abstractmethod
    def __init__(self, modifiers, annotations):
        listtypecheck(modifiers, list, Modifier, function=typename(self))

        Annotated.__init__(self, annotations)

        self.modifiers: List[Modifier] = modifiers

    def mod_str(self):
        result = ""
        for mod in self.modifiers:
            result += str(mod) + ' '
        return result

class Package(Node, Named, Documented, Annotated):
    def __init__(self, *, name, doc=None, annotations=[], parent=None):
        Node.__init__(self, parent)
        Named.__init__(self, name)
        Documented.__init__(self, doc)
        Annotated.__init__(self, annotations)

    def accept(self, visitor, value):
        return visitor.visit_package(self, value)

    def __str__(self):
        return f"{self.doc_str()}{self.anno_str()}package {self.name};"

class Import(Node, Named):
    def __init__(self, *, name, static=False, wildcard=False, parent=None):
        typecheck(static, bool, function='Import')
        typecheck(wildcard, bool, function='Import')

        Node.__init__(self, parent)
        Named.__init__(self, name)

        self.static: bool = static
        self.wildcard: bool = wildcard

    def accept(self, visitor, value):
        return visitor.visit_import(self, value)

    def __str__(self):
        result = "import "
        if self.static:
            result += "static "
        result += str(self.name)
        if self.wildcard:
            result += '.*'
        result += ';'
        return result

class Directive(Documented, Named, Node):
    def __init__(self, name, doc=None, parent=None):
        Node.__init__(self, parent)
        Named.__init__(self, name)
        Documented.__init__(self, doc)

class RequiresDirective(Directive):
    def __init__(self, *, modifiers=[], name, doc=None, parent=None):
        listtypecheck(modifiers, list, Modifier, function='RequiresDirective')

        super().__init__(name, doc, parent)

        self.modifiers: List[Modifier] = modifiers

    def accept(self, visitor, value):
        return visitor.visit_requires_directive(self, value)

    def __str__(self):
        return f"{self.doc_str()}requires {Declaration.mod_str(self)}{self.name};"

class ExportsDirective(Directive):
    def __init__(self, *, name, to=[], doc=None, parent=None):
        listtypecheck(to, list, Name, function='ExportsDirective')

        super().__init__(name, doc, parent)

        self.to: List[Name] = to

    def accept(self, visitor, value):
        return visitor.visit_exports_directive(self, value)

    def __str__(self):
        result = f"{self.doc_str()}exports {self.name}"
        if self.to:
            result += " to " + ', '.join(str(name) for name in self.to)
        result += ';'
        return result

class OpensDirective(Directive):
    def __init__(self, *, name, to=[], doc=None, parent=None):
        listtypecheck(to, list, Name, function='OpensDirective')

        super().__init__(name, doc, parent)

        self.to: List[Name] = to

    def accept(self, visitor, value):
        return visitor.visit_opens_directive(self, value)

    def __str__(self):
        result = f"{self.doc_str()}opens {self.name}"
        if self.to:
            result += " to " + ', '.join(str(name) for name in self.to)
        result += ';'
        return result

class UsesDirective(Directive):
    def accept(self, visitor, value):
        return visitor.visit_uses_directive(self, value)

    def __str__(self):
        return f"{self.doc_str()}uses {self.name};"

class ProvidesDirective(Directive):
    def __init__(self, *, name, provides=[], doc=None, parent=None):
        listtypecheck(provides, list, Name, function='ProvidesDirective')

        super().__init__(name, doc, parent)

        self.provides: List[Name] = provides

    def accept(self, visitor, value):
        return visitor.visit_provides_directive(self, value)

    def __str__(self):
        result = f"{self.doc_str()}provides {self.name}"
        if self.provides:
            result += " with " + ', '.join(str(name) for name in self.provides)
        result += ';'
        return result

class Member(Documented): pass

class TypeDeclaration(Named, Member, Declaration, Node):
    def __init__(self, *, name, members=[], doc=None, annotations=[], modifiers=[], parent=None):
        listtypecheck(members, list, Member, function=typename(self))

        Node.__init__(self, parent)
        Named.__init__(self, name)
        Member.__init__(self, doc)
        Declaration.__init__(self, modifiers, annotations)

        self.members: List[Member] = members

class GenericDeclaration(Declaration):
    def __init__(self, typeparams):
        listtypecheck(typeparams, list, TypeParameter, function=typename(self))

        self.typeparams: List[TypeParameter] = typeparams

    def typeparams_str(self):
        if self.typeparams:
            return '<' + ', '.join(str(param) for param in self.typeparams) + '>'
        else:
            return ""

class Statement(Node): pass

class ClassDeclaration(TypeDeclaration, GenericDeclaration, Statement):
    def __init__(self, *, name, typeparams=[], superclass=None, interfaces=[], members=[], doc=None, annotations=[], modifiers=[], parent=None):
        typecheck(superclass, (NoneType, GenericType), function='ClassDeclaration')
        listtypecheck(interfaces, list, GenericType, function='ClassDeclaration')

        TypeDeclaration.__init__(self, name=name, members=members, doc=doc, annotations=annotations, modifiers=modifiers, parent=parent)
        GenericDeclaration.__init__(self, typeparams)

        self.superclass: GenericType = superclass
        self.interfaces: List[GenericType] = interfaces

    def accept(self, visitor, value):
        return visitor.visit_class_declaration(self, value)

    def __str__(self):
        result = f"{self.doc_str()}{self.anno_str()}{self.mod_str()}class {self.name}{self.typeparams_str()}"
        if self.superclass:
            result += f" extends {self.superclass}"
        if self.interfaces:
            result += ' implements ' + ', '.join(str(interface) for interface in self.interfaces)
        if self.members:
            result += ' {\n' + '\n'.join(indent(str(member), '\t') for member in self.members) + '\n}'
        else:
            result += r' {}'
        return result

class InterfaceDeclaration(TypeDeclaration, GenericDeclaration):
    def __init__(self, *, name, typeparams=[], interfaces=[], members=[], doc=None, annotations=[], modifiers=[], parent=None):
        listtypecheck(interfaces, list, GenericType, function='InterfaceDeclaration')

        TypeDeclaration.__init__(self, name=name, members=members, doc=doc, annotations=annotations, modifiers=modifiers, parent=parent)
        GenericDeclaration.__init__(self, typeparams)

        self.interfaces: List[GenericType] = interfaces

    def accept(self, visitor, value):
        return visitor.visit_interface_declaration(self, value)

    def __str__(self):
        result = f"{self.doc_str()}{self.anno_str()}{self.mod_str()}interface {self.name}{self.typeparams_str()}"
        if self.interfaces:
            result += ' extends ' + ', '.join(str(interface) for interface in self.interfaces)
        if self.members:
            result += ' {\n' + '\n'.join(indent(str(member), '\t') for member in self.members) + '\n}'
        else:
            result += r' {}'
        return result

class AnnotationDeclaration(TypeDeclaration):
    def accept(self, visitor, value):
        return visitor.visit_annotation_declaration(self, value)

    def __str__(self):
        result = f"{self.doc_str()}{self.anno_str()}{self.mod_str()}@interface {self.name}"
        if self.members:
            result += ' {\n' + '\n'.join(indent(str(member), '\t') for member in self.members) + '\n}'
        else:
            result += r' {}'
        return result

class EnumDeclaration(TypeDeclaration):
    def __init__(self, *, name, interfaces=[], fields=[], members=[], doc=None, annotations=[], modifiers=[], parent=None):
        listtypecheck(interfaces, list, GenericType, function='EnumDeclaration')
        listtypecheck(fields, list, EnumField, function='EnumDeclaration')

        super().__init__(name=name, members=members, doc=doc, annotations=annotations, modifiers=modifiers, parent=parent)

        self.fields: List[EnumField] = fields
        self.interfaces: List[GenericType] = interfaces

    def accept(self, visitor, value):
        return visitor.visit_enum_declaration(self, value)

    def __str__(self):
        result = f"{self.doc_str()}{self.anno_str()}{self.mod_str()}enum {self.name}"
        if self.interfaces:
            result += ' implements ' + ', '.join(str(interface) for interface in self.interfaces)
        body = ""
        if self.fields:
            body += ',\n'.join(indent(str(field), '\t') for field in self.fields)
        if self.members:
            body += ';\n' + '\n'.join(indent(str(member), '\t') for member in self.members)
        if body:
            result += ' {\n' + body + '\n}'
        else:
            result += r' {}'
        return result

class Modifier(Node):
    VALUES = {'public', 'private', 'protected', 'static', 'native', 'final', 'abstract', 'synchronized', 'strictfp', 'transient', 'volatile', 'default'}

    def __init__(self, value, parent=None):
        typecheck(value, str, function='Modifier')
        if value not in Modifier.VALUES:
            raise ValueError(f'not a modifier: {value!r}')

        super().__init__(parent)

        self.__value: str = value

    def accept(self, visitor, value):
        return visitor.visit_modifier(self, value)

    def copy(self, parent=None):
        return Modifier(self.__value, parent)

    def __str__(self):
        return self.__value

    def __hash__(self):
        return hash(self.__value)

    def __eq__(self, other):
        return isinstance(other, Modifier) and str(self) == str(other) or str(self) == other

class EnumField(Node, Named, Member, Annotated):
    def __init__(self, name, args=None, members=None, doc=None, annotations=[], parent=None):
        listtypecheck(args, (NoneType, list), Expression, function='EnumField')
        listtypecheck(members, (NoneType, list), Member, function='EnumField')

        Node.__init__(self, parent)
        Named.__init__(self, name)
        Member.__init__(self, doc)
        Annotated.__init__(self, annotations)

        self.args: List[Expression] = args
        self.members: List[Member] = members

    def accept(self, visitor, value):
        return visitor.visit_enum_field(self, value)

    def __str__(self):
        result = f"{self.doc_str()}{self.anno_str()}{self.name}"
        if self.args is not None:
            result += '(' + ', '.join(str(arg) for arg in self.args) + ')'
        if self.members is not None:
            if self.members:
                result += ' {\n' + '\n'.join(indent(str(member), '\t') for member in self.members) + '\n}'
            else:
                result += r' {}'
        return result

class VariableDeclaration(Statement, Documented, Declaration):
    def __init__(self, *, type, declarators, doc=None, annotations=[], modifiers=[], parent=None):
        typecheck(type, Type, function=typename(self))
        listtypecheck(declarators, list, VariableDeclarator, function=typename(self))
        if len(declarators) == 0:
            raise ValueError(f"{typename(self)}() given empty declarator list")

        Statement.__init__(self, parent)
        Declaration.__init__(self, modifiers, annotations)
        Documented.__init__(self, doc)

        self.type: Type = type
        self.declarators: List[VariableDeclarator] = declarators

    def accept(self, visitor, value):
        return visitor.visit_variable_declaration(self, value)
    
    def __str__(self, newlines=True):
        if len(self.declarators) > 1 and isinstance(self.type, GenericType) and self.type.issimple and self.type.name == 'var':
            prefix = f"{self.doc_str(newlines)}{self.anno_str(newlines)}{self.mod_str()}{self.type}"
            return '; '.join(f"{prefix} {decl}" for decl in self.declarators) + ';'
        return f"{self.doc_str(newlines)}{self.anno_str(newlines)}{self.mod_str()}{self.type} {', '.join(str(decl) for decl in self.declarators)};"

class VariableDeclarator(Node, Named, Dimension):
    def __init__(self, *, name, dimensions=[], init=None, parent=None):
        typecheck(init, (NoneType, Initializer), function=typename(self))

        Node.__init__(self, parent)
        Named.__init__(self, name)
        Dimension.__init__(self, dimensions)

        self.init: Initializer = init

    def accept(self, visitor, value):
        return visitor.visit_variable_declarator(self, value)

    def __str__(self):
        result = str(self.name) + self.dim_str()
        if self.init:
            result += f" = {self.init}"
        return result

class FunctionDeclaration(Named, Member, GenericDeclaration, Node):
    def __init__(self, *, name, return_type, params, typeparams=[], throws=[], body, doc=None, modifiers=[], annotations=[], parent=None):
        typecheck(return_type, Type, function='FunctionDeclaration')
        typecheck(params, list, function='FunctionDeclaration')
        if len(params) > 0 and isinstance(params[0], ThisParameter):
            if len(params) > 1:
                itertypecheck(params[1:], FormalParameter, function='FunctionDeclaration')
        else:
            itertypecheck(params, FormalParameter, function='FunctionDeclaration')
        listtypecheck(throws, list, GenericType, function='FunctionDeclaration')
        typecheck(body, (NoneType, Block), function='FunctionDeclaration')
        
        Node.__init__(self, parent)
        Named.__init__(self, name)
        GenericDeclaration.__init__(self, typeparams)
        Declaration.__init__(self, modifiers, annotations)
        Member.__init__(self, doc)

        self.return_type: Type = return_type
        self.params: List[FormalParameter] = params
        self.body: Block = body
        self.throws: List[GenericType] = throws

    def accept(self, visitor, value):
        return visitor.visit_function_declaration(self, value)

    def __str__(self):
        result = f"{self.doc_str()}{self.anno_str()}{self.mod_str()}{self.typeparams_str()}{self.return_type} {self.name}" \
                 f"({', '.join(str(param) for param in self.params)})"
        if self.throws:
            result += " throws " + ', '.join(str(exception) for exception in self.throws)
        if self.body:
            result += f' {self.body}'
        else:
            result += ';'
        return result

class ConstructorDeclaration(Named, Member, GenericDeclaration, Node):
    def __init__(self, *, name, params, typeparams=[], throws=[], body, doc=None, modifiers=[], annotations=[], parent=None):
        typecheck(params, list, function='FunctionDeclaration')
        if len(params) > 0 and isinstance(params[0], ThisParameter):
            if len(params) > 1:
                itertypecheck(params[1:], FormalParameter, function='FunctionDeclaration')
        else:
            itertypecheck(params, FormalParameter, function='FunctionDeclaration')
        listtypecheck(throws, list, GenericType, function='FunctionDeclaration')
        typecheck(body, (NoneType, Block), function='FunctionDeclaration')
        
        Node.__init__(self, parent)
        Named.__init__(self, name)
        GenericDeclaration.__init__(self, typeparams)
        Declaration.__init__(self, modifiers, annotations)
        Member.__init__(self, doc)

        self.params: List[FormalParameter] = params
        self.body: Block = body
        self.throws: List[GenericType] = throws

    def accept(self, visitor, value):
        return visitor.visit_constructor_declaration(self, value)

    def __str__(self):
        result = f"{self.doc_str()}{self.anno_str()}{self.mod_str()}{self.typeparams_str()}{self.name}" \
                 f"({', '.join(str(param) for param in self.params)})"
        if self.throws:
            result += " throws " + ', '.join(str(exception) for exception in self.throws)
        if self.body:
            result += f' {self.body}'
        else:
            result += ';'
        return result

class AnnotationProperty(Named, Declaration, Member, Dimension, Node):
    def __init__(self, *, type, name, default=None, dimensions=[], doc=None, annotations=[], modifiers=[], parent=None):
        typecheck(type, Type, function='AnnotationProperty')
        typecheck(default, (AnnotationValue, NoneType), function='AnnotationProperty')

        Node.__init__(self, parent)
        Declaration.__init__(self, modifiers, annotations)
        Named.__init__(self, name)
        Member.__init__(self, doc)
        Dimension.__init__(self, dimensions)

        self.type: Type = type
        self.default: AnnotationValue = default

    def accept(self, visitor, value):
        return visitor.visit_annotation_property(self, value)

    def __str__(self):
        result = f"{self.doc_str()}{self.anno_str()}{self.mod_str()}{self.type} {self.name}(){self.dim_str()}"
        if self.default:
            result += f" default {self.default}"
        result += ';'
        return result

class FormalParameter(Named, Declaration, Dimension, Node):
    def __init__(self, *, name, type, dimensions=[], annotations=[], modifiers=[], parent=None):
        typecheck(type, Type, function=typename(self))

        Node.__init__(self, parent)
        Named.__init__(self, name)
        Declaration.__init__(self, modifiers, annotations)
        Dimension.__init__(self, dimensions)

        self.type: Type = type

    def accept(self, visitor, value):
        return visitor.visit_formal_parameter(self, value)

    def __str__(self):
        return f"{self.anno_str(newlines=False)}{self.mod_str()}{self.type} {self.name}{self.dim_str()}"

class ThisParameter(Annotated, Node):
    def __init__(self, *, type, qualifier=None, annotations=[], parent=None):
        typecheck(type, Type, function='ThisParameter')
        typecheck(qualifier, (NoneType, Name), function='ThisParameter')

        Node.__init__(self, parent)
        Annotated.__init__(self, annotations)

        self.type: Type = type
        self.qualifier: Name = qualifier

    def accept(self, visitor, value):
        return visitor.visit_this_parameter(self, value)

    def __str__(self):
        result = f"{self.anno_str(newlines=False)}{self.type} "
        if self.qualifier:
            result += f"{self.qualifier}."
        result += "this"
        return result

class InitializerBlock(Member, Node):
    def __init__(self, *, body, static, doc=None, parent=None):
        typecheck(body, Block, function='InitializerBlock')
        typecheck(static, bool, function='InitializerBlock')

        Node.__init__(self, parent)
        Member.__init__(self, doc)

        self.body: Block = body
        self.static: bool = static

    def accept(self, visitor, value):
        return visitor.visit_initializer_block(self, value)

    def __str__(self):
        if self.static:
            return f"{self.doc_str()}static {self.body}"
        else:
            return f"{self.doc_str()}{self.body}"

class FieldDeclaration(Declaration, Member, Node):
    def __init__(self, *, type, declarators, doc=None, annotations=[], modifiers=[], parent=None):
        typecheck(type, Type, function=typename(self))
        listtypecheck(declarators, list, VariableDeclarator, function=typename(self))
        if len(declarators) == 0:
            raise ValueError(f"{typename(self)}() given empty declarator list")

        Node.__init__(self, parent)
        Member.__init__(self, doc)
        Declaration.__init__(self, modifiers, annotations)

        self.type: Type = type
        self.declarators: List[VariableDeclarator] = declarators

    def accept(self, visitor, value):
        return visitor.visit_field_declaration(self, value)
    
    def __str__(self):
        return f"{self.doc_str()}{self.anno_str()}{self.mod_str()}{self.type} {', '.join(str(decl) for decl in self.declarators)};"

class TypeArgument(Node, Annotated):
    def __init__(self, *, base=None, bound=None, annotations=[], parent=None):
        typecheck(base, (NoneType, GenericType, ArrayType, TypeUnion), function='TypeArgument')
        if base:
            typecheck(bound, str, function='TypeArgument')
            if bound != 'extends' and bound != 'super':
                raise ValueError(f'TypeArgument() invalid bound')
        else:
            if bound is not None:
                raise ValueError(f"TypeArgument() bound may not be given if base is not given")
            
        Node.__init__(self, parent)
        Annotated.__init__(self, annotations)

        self.base: Type = base
        self.bound: str = bound

    def accept(self, visitor, value):
        return visitor.visit_type_argument(self, value)

    def __str__(self):
        result = f'{self.anno_str(newlines=False)}?'
        if self.base:
            result += f" {self.bound} {self.base}"
        return result

class TypeParameter(Node, Named, Annotated):
    def __init__(self, name, *, bound=None, annotations=[], parent=None):
        typecheck(bound, (NoneType, GenericType, ArrayType, TypeUnion), function='TypeParameter')

        Node.__init__(self, parent)
        Annotated.__init__(self, annotations)
        Named.__init__(self, name)

        self.bound: Type = bound

    def accept(self, visitor, value):
        return visitor.visit_type_parameter(self, value)

    def __str__(self):
        result = f"{self.anno_str(newlines=False)}{self.name}"
        if self.bound:
            result += f" extends {self.bound}"
        return result

class Type(Node, Annotated):
    def __init__(self, annotations=[], parent=None):
        Node.__init__(self, parent)
        Annotated.__init__(self, annotations)

    def __eq__(self, other):
        return isinstance(other, str) and str(self) == other or super().__eq__(other)

class PrimitiveType(Type):
    VALUES = {'boolean', 'byte', 'short', 'char', 'int', 'long', 'float', 'double'}

    def __init__(self, name, *, annotations=[], parent=None):
        typecheck(name, str, function='PrimitiveType')
        if name not in PrimitiveType.VALUES:
            raise ValueError(f'PrimitiveType() not a primitive type: {name!r}')

        super().__init__(annotations, parent)

        self.name: str = name

    def accept(self, visitor, value):
        return visitor.visit_primitive_type(self, value)

    def __str__(self):
        return self.anno_str(newlines=False) + self.name

class VoidType(Type):
    def __init__(self, annotations=[], parent=None):
        super().__init__(annotations, parent)
        self.name = 'void'

    def accept(self, visitor, value):
        return visitor.visit_void_type(self, value)

    def copy(self, parent=None):
        return VoidType(annotations=copy(self.annotations),
                        parent=parent)

    def __str__(self):
        return self.anno_str(newlines=False) + 'void'

class ArrayType(Type, Dimension):
    def __init__(self, base, dimensions=None, *, annotations=[], parent=None):
        typecheck(base, (PrimitiveType, GenericType), function=typename(self))

        Type.__init__(self, annotations, parent)
        Dimension.__init__(self, dimensions or [None])
        if len(self.dimensions) == 0:
            raise ValueError(f'{typename(self)}() invalid dimensions')

        self.base: Type = base

    def accept(self, visitor, value):
        return visitor.visit_array_type(self, value)

    @property
    def name(self):
        return self.base.name + '[]'*len(self.dimensions)

    def __str__(self):
        return f"{self.anno_str(newlines=False)}{self.base}{self.dim_str()}"

class GenericType(Type):
    def __init__(self, name, *, typeargs=None, container=None, annotations=[], parent=None):
        typecheck(name, Name, function='GenericType')
        listtypecheck(typeargs, (NoneType, list), (GenericType, ArrayType, TypeArgument), function='GenericType')
        typecheck(container, (NoneType, GenericType), function='GenericType')

        super().__init__(annotations, parent)

        self._name: Name = name
        self.typeargs: list = typeargs
        self.container: GenericType = container

    def accept(self, visitor, value):
        return visitor.visit_generic_type(self, value)

    @property
    def name(self):
        if self.container:
            return str(self.container) + '.' + str(self._name)
        else:
            return str(self._name)

    def copy(self, parent=None):
        return GenericType(name=copy(self._name),
                           typeargs=copy(self.typeargs),
                           container=copy(self.container),
                           annotations=copy(self.annotations),
                           parent=parent)
        
    @property
    def issimple(self):
        return self.typeargs is None and len(self.annotations) == 0 and (self.container is None or self.container.issimple)

    def __str__(self):
        result = self.anno_str(newlines=False) + self.name
        if self.typeargs is not None:
            result += '<' + ', '.join(str(arg) for arg in self.typeargs) + '>'
        return result

class TypeUnion(Type):
    def __init__(self, *types, parent=None):
        if len(types) == 1 and isinstance(types[0], list):
            types = types[0]
        else:
            types = list(types)
        if len(types) == 0:
            raise ValueError('TypeUnion() no types given')
        listtypecheck(types, list, (GenericType, ArrayType), function='TypeUnion')

        super().__init__(parent=parent)

        self.types: List[GenericType] = types

    def accept(self, visitor, value):
        return visitor.visit_type_union(self, value)

    @property
    def name(self):
        return ' & '.join(type_.name for type_ in self.types)

    def __str__(self):
        return ' & '.join(str(type_) for type_ in self.types)

class TypeIntersection(Type):
    def __init__(self, *types, parent=None):
        if len(types) == 1 and isinstance(types[0], list):
            types = types[0]
        else:
            types = list(types)
        if len(types) == 0:
            raise ValueError('TypeIntersection() no types given')
        listtypecheck(types, list, GenericType, function='TypeIntersection')

        super().__init__(parent=parent)

        self.types: List[GenericType] = types

    def accept(self, visitor, value):
        return visitor.visit_type_intersection(self, value)

    @property
    def name(self):
        return ' | '.join(type_.name for type_ in self.types)

    def __str__(self):
        return ' | '.join(str(type_) for type_ in self.types)

class AnnotationValue(Node): pass

class Annotation(AnnotationValue):
    def __init__(self, type, *, args=None, parent=None):
        typecheck(type, GenericType, function='Annotation')
        typecheck(args, (NoneType, AnnotationValue, list), function='Annotation')
        if isinstance(args, list):
            itertypecheck(args, AnnotationArgument, function='Annotation')

        super().__init__(parent)

        self.type: GenericType = type
        self.args: List[AnnotationValue] = args

    def accept(self, visitor, value):
        return visitor.visit_annotation(self, value)

    def __str__(self):
        result = f"@{self.type}"
        if self.args is not None:
            if isinstance(self.args, list):
                result += '(' + ', '.join(str(arg) for arg in self.args) + ')'
            else:
                result += f'({self.args})'
        return result

class AnnotationArgument(Node, Named):
    def __init__(self, name, value, *, parent=None):
        typecheck(value, AnnotationValue, function='AnnotationArgument')

        Node.__init__(self, parent)
        Named.__init__(self, name)

        self.value: AnnotationValue = value

    def accept(self, visitor, value):
        return visitor.visit_annotation_argument(self, value)

    def __str__(self):
        return f"{self.name} = {self.value}"

class Initializer(AnnotationValue): pass

class ArrayInitializer(Initializer):
    def __init__(self, values, *, parent=None):
        listtypecheck(values, list, AnnotationValue, function=typename(self))

        super().__init__(parent)

        self.values: List[Initializer] = values

    def accept(self, visitor, value):
        return visitor.visit_array_initializer(self, value)

    def __str__(self):
        return '{' + ', '.join(str(init) for init in self.values) + '}'

class Expression(Initializer): pass

class BinaryExpression(Expression):
    OPS = {'+', '-', '*', '/', '%', '^', '&', '|', '&&', '||', '<', '>', '==', '!=',
              '<=', '>=', '<<', '>>', '>>>'}

    def __init__(self, *, op, lhs, rhs, parent=None):
        typecheck(op, str, function='BinaryExpression')
        if op not in BinaryExpression.OPS:
            raise ValueError(f'BinaryExpression() invalid operator')
        typecheck(lhs, Expression, function='BinaryExpression')
        typecheck(rhs, Expression, function='BinaryExpression')

        super().__init__(parent)

        self.op: str = op
        self.lhs: Expression = lhs
        self.rhs: Expression = rhs

    def accept(self, visitor, value):
        return visitor.visit_binary_expression(self, value)

    def __str__(self):
        return f"{self.lhs} {self.op} {self.rhs}"

class UnaryExpression(Expression):
    OPS = {'!', '~', '+', '-'}

    def __init__(self, *, op, expr, parent=None):
        typecheck(op, str, function='UnaryExpression')
        if op not in UnaryExpression.OPS:
            raise ValueError("UnaryExpression() invalid operator")
        typecheck(expr, Expression, function='UnaryExpression')

        super().__init__(parent)

        self.op: str = op
        self.expr: Expression = expr

    def accept(self, visitor, value):
        return visitor.visit_unary_expression(self, value)

    def __str__(self):
        return f"{self.op}{self.expr}"

class ConditionalExpression(Expression):
    def __init__(self, *, condition, truepart, falsepart, parent=None):
        typecheck(condition, Expression, function='ConditionalExpression')
        typecheck(truepart, Expression, function='ConditionalExpression')
        typecheck(falsepart, Expression, function='ConditionalExpression')

        super().__init__(parent)

        self.condition: Expression = condition
        self.truepart: Expression = truepart
        self.falsepart: Expression = falsepart

    def accept(self, visitor, value):
        return visitor.visit_conditional_expression(self, value)

    def __str__(self):
        return f"{self.condition}? {self.truepart} : {self.falsepart}"

class IncrementExpression(Expression):
    def __init__(self, *, op, expr, prefix, parent=None):
        typecheck(op, str, function='IncrementExpression')
        if op != '++' and op != '--':
            raise ValueError('IncrementExpression() invalid operator')
        typecheck(expr, Expression, function='IncrementExpression')
        typecheck(prefix, bool, function='IncrementExpression')

        super().__init__(parent)

        self.op: str = op
        self.expr: Expression = expr
        self.prefix: bool = prefix

    def accept(self, visitor, value):
        return visitor.visit_increment_expression(self, value)

    def __str__(self):
        if self.prefix:
            return f"{self.op}{self.expr}"
        else:
            return f"{self.expr}{self.op}"

class IndexExpression(Expression):
    def __init__(self, *, indexed, index, parent=None):
        typecheck(indexed, Expression, function='IndexExpression')
        typecheck(index, Expression, function='IndexExpression')

        super().__init__(parent)

        self.indexed: Expression = indexed
        self.index: Expression = index

    def accept(self, visitor, value):
        return visitor.visit_index_expression(self, value)

    def __str__(self):
        return f"{self.indexed}[{self.index}]"

class CastExpression(Expression):
    def __init__(self, *, type, expr, parent=None):
        typecheck(type, Type, function='CastExpression')
        typecheck(expr, Expression, function='CastExpression')

        super().__init__(parent)

        self.type: Type = type
        self.expr: Expression = expr

    def accept(self, visitor, value):
        return visitor.visit_cast_expression(self, value)

    def __str__(self):
        return f"({self.type}){self.expr}"

class Assignment(Expression):
    OPS = {'=', '+=', '-=', '*=', '/=', '%=', '^=', '&=', '|=', '<<=', '>>=', '>>>='}

    def __init__(self, *, op, lhs, rhs, parent=None):
        typecheck(op, str, function='Assignment')
        if op not in Assignment.OPS:
            raise ValueError('Assignment() invalid operator')
        typecheck(lhs, Expression, function='Assignment')
        typecheck(rhs, Expression, function='Assignment')

        super().__init__(parent)

        self.op: str = op
        self.lhs: Expression = lhs
        self.rhs: Expression = rhs

    def accept(self, visitor, value):
        return visitor.visit_assignment(self, value)

    def __str__(self):
        return f"{self.lhs} {self.op} {self.rhs}"

class MemberAccess(Expression):
    def __init__(self, *, object=None, name, parent=None):
        typecheck(object, (NoneType, Expression), function='MemberAccess')
        typecheck(name, Name, function='MemberAccess')

        super().__init__(parent)

        self.name: Name = name
        self.object: Expression = object

    def accept(self, visitor, value):
        return visitor.visit_member_access(self, value)

    @property
    def isvariable(self):
        return self.object is None and not self.name.isdotted

    @property
    def isfield(self):
        return self.object is not None or self.name.isdotted

    def __str__(self):
        if self.object:
            return f"{self.object}.{self.name}"
        else:
            return str(self.name)

class FunctionCall(Expression):
    def __init__(self, *, object=None, name, args=[], typeargs=[], parent=None):
        typecheck(object, (NoneType, Expression), function='FunctionCall')
        typecheck(name, Name, function='FunctionCall')
        listtypecheck(args, list, Expression, function='FunctionCall')
        listtypecheck(typeargs, list, (GenericType, ArrayType, TypeArgument), function='FunctionCall')

        super().__init__(parent)

        self.object: Expression = object
        self.name: Name = name
        self.args: List[Expression] = args
        self.typeargs: List = typeargs

    def accept(self, visitor, value):
        return visitor.visit_function_call(self, value)

    @property
    def isfunction(self):
        return self.object is None and not self.name.isdotted

    @property
    def ismethod(self):
        return self.object is not None or self.name.isdotted

    def __str__(self):
        if self.typeargs:
            result = '<' + ', '.join(str(arg) for arg in self.typeargs) + '>'
        else:
            result = ""
        result += f"{self.name}({', '.join(str(arg) for arg in self.args)})"
        if self.object:
            result = f"{self.object}.{result}"
        return result

class ThisCall(Expression):
    def __init__(self, *, object=None, args=[], typeargs=[], parent=None):
        typecheck(object, (NoneType, Expression), function='FunctionCall')
        listtypecheck(args, list, Expression, function='FunctionCall')
        listtypecheck(typeargs, list, (GenericType, ArrayType, TypeArgument), function='FunctionCall')

        super().__init__(parent)

        self.object: Expression = object
        self.args: List[Expression] = args
        self.typeargs: List = typeargs

    def accept(self, visitor, value):
        return visitor.visit_this_call(self, value)

    @property
    def issimple(self):
        return self.object is None and not self.typeargs

    def __str__(self):
        if self.typeargs:
            result = '<' + ', '.join(str(arg) for arg in self.typeargs) + '>'
        else:
            result = ""
        result += f"this({', '.join(str(arg) for arg in self.args)})"
        if self.object:
            result = f"{self.object}.{result}"
        return result

class SuperCall(Expression):
    def __init__(self, *, object=None, args=[], typeargs=[], parent=None):
        typecheck(object, (NoneType, Expression), function='FunctionCall')
        listtypecheck(args, list, Expression, function='FunctionCall')
        listtypecheck(typeargs, list, (GenericType, ArrayType, TypeArgument), function='FunctionCall')

        super().__init__(parent)

        self.object: Expression = object
        self.args: List[Expression] = args
        self.typeargs: List = typeargs

    def accept(self, visitor, value):
        return visitor.visit_super_call(self, value)

    @property
    def issimple(self):
        return self.object is None and not self.typeargs

    def __str__(self):
        if self.typeargs:
            result = '<' + ', '.join(str(arg) for arg in self.typeargs) + '>'
        else:
            result = ""
        result += f"super({', '.join(str(arg) for arg in self.args)})"
        if self.object:
            result = f"{self.object}.{result}"
        return result

class Literal(Expression):
    def __init__(self, value, *, parent=None):
        typecheck(value, str, function='Literal')

        super().__init__(parent)

        self._str_value = value
        
        def parse_value():
            if self.isnumber:
                if len(value) > 1:
                    first = value[1]
                    if first in 'xX':
                        if 'p' in value or 'P' in value:
                            return float.fromhex(self._strip_num_value())
                        else:
                            return int(self._strip_num_value(), base=16)
                    elif first in 'bB':
                        return int(self._strip_num_value(), base=2)
                if value[-1] in 'fFdD':
                    return float(self._strip_num_value())
                return int(self._strip_num_value())
            elif self.isstring:
                from ast import literal_eval
                return literal_eval(value)
            elif value == 'true':
                return True
            elif value == 'false':
                return False
            else:
                raise ValueError(f'{value!r} is not a valid literal')

        self._value = parse_value()

    @property
    def value(self):
        return self._value

    def accept(self, visitor, value):
        return visitor.visit_literal(self, value)

    def _strip_num_value(self):
        value = self._str_value.replace('_', '')
        if value[-1] in "fFlLdD":
            value = value[:-1]
        return value

    @property
    def isstring(self):
        return self._str_value[0] in ('"', "'") or self._str_value[0] in "rR" and self._str_value[1] in ('"', "'")

    @property
    def isnumber(self):
        return self._str_value[0] in "0123456789."

    @property
    def isfloatingpoint(self):
        if not self.isnumber:
            return False
        value = self._str_value
        if len(value) > 1:
            if value[1] in "xX":
                return 'p' in value or 'P' in value
            elif 'e' in value or 'E' in value:
                return True
        return '.' in value

    @property
    def isintegral(self):
        return not self.isfloatingpoint

    @property
    def isboolean(self):
        return self._str_value in ('true', 'false')

    def __str__(self):
        if isinstance(self.value, str):
            if self._str_value[0] in "rR" and self._str_value[1:4] in ("'''", '"""') or self._str_value[0:3] in ("'''", '"""'):
                result = repr(dedent(self.value))
            else:
                result = repr(self.value)
            if result[0] == "'":
                result = '"' + result[1:-1].replace(r"\'", "'") + '"'
            
            return result
        else:
            return self._str_value

class NullLiteral(Expression):
    def accept(self, visitor, value):
        return visitor.visit_null_literal(self, value)

    def __str__(self):
        return 'null'

class TypeLiteral(Expression):
    def __init__(self, type, *, parent=None):
        typecheck(type, Type, function='TypeLiteral')

        super().__init__(parent)

        self.type: Type = type

    def accept(self, visitor, value):
        return visitor.visit_type_literal(self, value)

    def __str__(self):
        return f"{self.type}.class"

class ClassCreator(Expression):
    def __init__(self, *, type, object=None, args=[], typeargs=[], members=None, parent=None):
        typecheck(type, Type, function='ClassCreator')
        typecheck(object, (NoneType, Expression), function='ClassCreator')
        listtypecheck(args, list, Expression, function='ClassCreator')
        listtypecheck(typeargs, list, (GenericType, ArrayType, TypeArgument), function='ClassCreator')
        listtypecheck(members, (NoneType, list), Member, function='ClassCreator')
        
        super().__init__(parent)

        self.type: Type = type
        self.object: Expression = object
        self.args: List[Expression] = args
        self.typeargs: List = typeargs
        self.members: List[Member] = members

    def accept(self, visitor, value):
        return visitor.visit_class_creator(self, value)

    def __str__(self):
        result = "new "
        if self.typeargs:
            result += '<' + ', '.join(str(arg) for arg in self.typeargs) + '> '
        result += str(self.type) + '(' + ', '.join(str(arg) for arg in self.args) + ')'
        if self.members is not None:
            if self.members:
                result += ' {\n' + '\n'.join(indent(str(member), '\t') for member in self.members) + '\n}'
            else:
                result += r' {}'
        if self.object:
            result = f"{self.object}.{result}"
        return result

class ArrayCreator(Expression):
    def __init__(self, *, type, dimensions, initializer=None, parent=None):
        typecheck(type, Type, function='ArrayCreator')
        listtypecheck(dimensions, list, DimensionExpression, function='ArrayCreator')
        typecheck(initializer, (NoneType, ArrayInitializer), function='ArrayCreator')
        if len(dimensions) == 0:
            raise ValueError(f'ArrayCreator() invalid dimensions')

        super().__init__(parent)

        self.type: Type = type
        self.dimensions: List[Expression] = dimensions
        self.initializer: Expression = initializer

    def accept(self, visitor, value):
        return visitor.visit_array_creator(self, value)
    
    def __str__(self):
        result = f"new {self.type}" + ''.join(str(dim) for dim in self.dimensions)
        if self.initializer:
            result += f" {self.initializer}"
        return result

class DimensionExpression(Node, Annotated):
    def __init__(self, *, annotations=[], size=None, parent=None):
        typecheck(size, (NoneType, Expression), function='DimensionExpression')

        Node.__init__(self, parent)
        Annotated.__init__(self, annotations)

        self.size: Expression = size

    def accept(self, visitor, value):
        return visitor.visit_dimension_expression(self, value)

    def __str__(self):
        result = self.anno_str(newlines=False)
        if result:
            result = ' ' + result
        result += '['
        if self.size:
            result += str(self.size)
        result += ']'
        return result

class MethodReference(Expression):
    def __init__(self, *, name, object, parent=None):
        if isinstance(name, str):
            if name != 'new':
                raise ValueError('MethodReference() invalid name')
        else:
            typecheck(name, Name, function='MethodReference')
        typecheck(object, (Expression, GenericType, ArrayType), function='MethodReference')

        super().__init__(parent)

        self.name: Name = name
        self.object = object

    def accept(self, visitor, value):
        return visitor.visit_method_reference(self, value)

    def __str__(self):
        return f"{self.object}::{self.name}"

class TypeTest(Expression):
    def __init__(self, *, type, expr, parent=None):
        typecheck(type, Type, function='TypeTest')
        typecheck(expr, Expression, function='TypeTest')

        super().__init__(parent)

        self.type: Type = type
        self.expr: Expression = expr

    def accept(self, visitor, value):
        return visitor.visit_type_test(self, value)

    def __str__(self):
        return f"{self.expr} instanceof {self.type}"

class Parenthesis(Expression):
    def __init__(self, expr, *, parent=None):
        typecheck(expr, Expression, function='Parenthesis')

        super().__init__(parent)

        self.expr: Expression = expr

    def accept(self, visitor, value):
        return visitor.visit_parenthesis(self, value)

    def __str__(self):
        return f"({self.expr})"

class This(Expression):
    def __init__(self, *, object=None, parent=None):
        typecheck(object, (NoneType, Expression), function='This')

        super().__init__(parent)

        self.object: Expression = object

    def accept(self, visitor, value):
        return visitor.visit_this(self, value)

    def __str__(self):
        if self.object:
            return f"{self.object}.this"
        else:
            return 'this'

class Super(Expression):
    def __init__(self, *, object=None, parent=None):
        typecheck(object, (NoneType, Expression), function='Super')

        super().__init__(parent)

        self.object: Expression = object

    def accept(self, visitor, value):
        return visitor.visit_super(self, value)

    def __str__(self):
        if self.object:
            return f"{self.object}.super"
        else:
            return 'super'

class Lambda(Expression):
    def __init__(self, *, params, body, parent=None):
        typecheck(params, list, function='Lambda')
        if len(params) != 0:
            if isinstance(params[0], Name):
                itertypecheck(params, Name, function='Lambda')
            else:
                itertypecheck(params, FormalParameter, function='Lambda')
        typecheck(body, (Block, Expression), function='Lambda')

        super().__init__(parent)

        self.params: List = params
        self.body = body

    def accept(self, visitor, value):
        return visitor.visit_lambda(self, value)

    def __str__(self):
        if len(self.params) == 1 and isinstance(self.params[0], Name):
            result = str(self.params[0])
        else:
            result = '(' + ', '.join(str(param) for param in self.params) + ')'
        result += f" -> {self.body}"
        return result

class ExpressionStatement(Statement):
    def __init__(self, expr, *, parent=None):
        typecheck(expr, Expression, function='ExpressionStatement')

        super().__init__(parent)

        self.expr: Expression = expr

    def accept(self, visitor, value):
        return visitor.visit_expression_statement(self, value)
    
    def __str__(self):
        return f"{self.expr};"

class EmptyStatement(Statement):
    def accept(self, visitor, value):
        return visitor.visit_empty_statement(self, value)

    def __str__(self):
        return ';'

class LabeledStatement(Statement):
    def __init__(self, *, label, stmt, parent=None):
        typecheck(label, Name, function='LabeledStatement')
        typecheck(stmt, Statement, function='LabeledStatement')

        super().__init__(parent)

        self.label: Name = label
        self.stmt: Statement = stmt

    def accept(self, visitor, value):
        return visitor.visit_labeled_statement(self, value)

    def __str__(self):
        return f"{self.label}: {self.stmt}"

def format_body(body, newline_in_empty_body=False):
    if isinstance(body, Block):
        if newline_in_empty_body and len(body.stmts) == 0:
            return ' {\n}'
        else:
            return ' ' + str(body)
    else:
        return '\n' + indent(str(body), '\t')

class IfStatement(Statement):
    def __init__(self, *, condition, body, elsebody=None, parent=None):
        typecheck(condition, Expression, function='IfStatement')
        typecheck(body, Block, function='IfStatement')
        typecheck(elsebody, (NoneType, Block, IfStatement), function='IfStatement')

        super().__init__(parent)

        self.condition: Expression = condition
        self.body: Block = body
        self.elsebody: Block = elsebody

    def accept(self, visitor, value):
        return visitor.visit_if_statement(self, value)

    def __str__(self):
        result = f"if({self.condition}){format_body(self.body, newline_in_empty_body=self.elsebody or isinstance(self.parent, IfStatement))}"
        if self.elsebody:
            if isinstance(self.body, Block):
                result += " else"
            else:
                result += "\nelse"
            if isinstance(self.elsebody, IfStatement):
                result += f" {self.elsebody}"
            else:
                result += ' ' + format_body(self.elsebody, newline_in_empty_body=True)
        return result

class Block(Statement):
    def __init__(self, stmts=[], *, parent=None):
        listtypecheck(stmts, list, Statement, function='Block')

        super().__init__(parent)

        self.stmts: List[Statement] = stmts

    def accept(self, visitor, value):
        return visitor.visit_block(self, value)

    def __str__(self):
        if self.stmts:
            return '{\n' + '\n'.join(indent(str(stmt), '\t') for stmt in self.stmts) + '\n}'
        else:
            return r'{}'
        
class Switch(Statement, Expression):
    def __init__(self, *, condition, cases, parent=None):
        typecheck(condition, Expression, function='SwitchStatement')
        listtypecheck(cases, list, SwitchCase, function='SwitchStatement')

        super().__init__(parent)

        self.condition: Expression = condition
        self.cases: List[SwitchCase] = cases

    def accept(self, visitor, value):
        return visitor.visit_switch(self, value)

    def __str__(self):
        result = f"switch({self.condition}) {{"
        if self.cases:
            result += '\n' + '\n'.join(indent(str(case), '\t') for case in self.cases) + '\n}'
        else:
            result += '}'
        return result

class SwitchCase(Node):
    def __init__(self, *, labels=None, stmts, arrow=False, parent=None):
        listtypecheck(labels, (NoneType, list), (Name, Expression), function='SwitchCase')
        listtypecheck(stmts, list, Statement, function='SwitchCase')
        typecheck(arrow, bool, function='SwitchCase')

        if arrow:
            if len(stmts) != 1:
                raise ValueError('SwitchCase() arrow switch case can only have 1 body statement')
            typecheck(stmts[0], (ExpressionStatement, Block, ThrowStatement), function=typename(self))

        super().__init__(parent)

        self.labels: List[Expression] = labels
        self.stmts: List[Statement] = stmts
        self.arrow: bool = arrow

    def accept(self, visitor, value):
        return visitor.visit_switch_case(self, value)

    def __str__(self):
        if self.arrow:
            if self.labels:
                result = "case " + ', '.join(str(label) for label in self.labels) + ' -> '
            else:
                result = "default -> "
        else:
            if self.labels:
                result = "case " + ', '.join(str(label) for label in self.labels) + ':'
            else:
                result = "default:"

        if self.stmts:
            if self.arrow:
                stmt = self.stmts[0]
                if isinstance(stmt, Block) and len(stmt.stmts) == 0:
                    result += '{\n}'
                else:
                    result += str(stmt)
            elif len(self.stmts) == 1:
                result += format_body(self.stmts[0], newline_in_empty_body=True)
            else:
                result += '\n' + '\n'.join(indent(str(stmt), '\t') for stmt in self.stmts)
        
        return result

class ThrowStatement(Statement):
    def __init__(self, error, *, parent=None):
        typecheck(error, Expression, function='ThrowStatement')

        super().__init__(parent)

        self.error: Expression = error

    def accept(self, visitor, value):
        return visitor.visit_throw_statement(self, value)

    def __str__(self):
        return f"throw {self.error};"

class ReturnStatement(Statement):
    def __init__(self, value=None, *, parent=None):
        typecheck(value, (NoneType, Expression), function='ReturnStatement')

        super().__init__(parent)

        self.value: Expression = value

    def accept(self, visitor, value):
        return visitor.visit_return_statement(self, value)

    def __str__(self):
        if self.value:
            return f"return {self.value};"
        else:
            return 'return;'

class BreakStatement(Statement):
    def __init__(self, label=None, *, parent=None):
        typecheck(label, (NoneType, Name), function='BreakStatement')

        super().__init__(parent)

        self.label: Name = label

    def accept(self, visitor, value):
        return visitor.visit_break_statement(self, value)

    def __str__(self):
        if self.label:
            return f"break {self.label};"
        else:
            return 'break;'

class ContinueStatement(Statement):
    def __init__(self, label=None, *, parent=None):
        typecheck(label, (NoneType, Name), function='ContinueStatement')

        super().__init__(parent)

        self.label: Name = label

    def accept(self, visitor, value):
        return visitor.visit_continue_statement(self, value)

    def __str__(self):
        if self.label:
            return f"continue {self.label};"
        else:
            return 'continue;'

class YieldStatement(Statement):
    KEYWORD = 'break'

    def __init__(self, value, *, parent=None):
        typecheck(value, Expression, function='YieldStatement')

        super().__init__(parent)

        self.value: Expression = value

    def accept(self, visitor, value):
        return visitor.visit_yield_statement(self, value)

    def __str__(self):
        return f"{YieldStatement.KEYWORD} {self.value};"

class ForLoop(Statement):
    def __init__(self, *, control, body, parent=None):
        typecheck(control, (ForControl, EnhancedForControl), function='ForLoop')
        typecheck(body, Statement, function='ForLoop')

        super().__init__(parent)

        self.control = control
        self.body: Statement = body

    def accept(self, visitor, value):
        return visitor.visit_for_loop(self, value)

    def __str__(self):
        return f"for({self.control}){format_body(self.body)}"

class ForControl(Node):
    def __init__(self, *, init=None, condition=None, update=[], parent=None):
        typecheck(init, (NoneType, VariableDeclaration, ExpressionStatement), function=typename(self))
        typecheck(condition, (NoneType, Expression), function=typename(self))
        listtypecheck(update, list, Expression, function=typename(self))

        super().__init__(parent)

        self.init = init
        self.condition: Expression = condition
        self.update: List[Expression] = update

    def accept(self, visitor, value):
        return visitor.visit_for_control(self, value)

    def __str__(self):
        if self.init:
            if isinstance(self.init, VariableDeclaration):
                result = self.init.__str__(newlines=False)
            else:
                result = str(self.init)
        else:
            result = ';'

        if self.condition:
            result += f' {self.condition};'
        else:
            result += ';'

        if self.update:
            result += ' ' + ', '.join(str(update) for update in self.update)
        
        return result

class EnhancedForControl(Node):
    def __init__(self, *, var, iterable, parent=None):
        typecheck(var, VariableDeclaration, function=typename(self))
        if len(var.declarators) != 1:
            raise ValueError('EnhancedForControl() too many declarators given')
        if var.declarators[0].init:
            raise ValueError('EnhancedForControl() declarator may not have initializer')
        typecheck(iterable, Expression, function=typename(self))

        super().__init__(parent)

        self.var: VariableDeclaration = var
        self.iterable: Expression = iterable

    def accept(self, visitor, value):
        return visitor.visit_enhanced_for_control(self, value)

    def __str__(self):
        result = str(self.var)[0:-1]
        result += f" : {self.iterable}"
        return result

class WhileLoop(Statement):
    def __init__(self, *, condition, body, parent=None):
        typecheck(condition, Expression, function='WhileLoop')
        typecheck(body, Statement, function='WhileLoop')

        super().__init__(parent)

        self.condition: Expression = condition
        self.body: Statement = body

    def accept(self, visitor, value):
        return visitor.visit_while_loop(self, value)

    def __str__(self):
        return f"while({self.condition}){format_body(self.body)}"

class DoWhileLoop(Statement):
    def __init__(self, *, condition, body, parent=None):
        typecheck(condition, Expression, function='DoWhileLoop')
        typecheck(body, Statement, function='DoWhileLoop')

        super().__init__(parent)

        self.condition: Expression = condition
        self.body: Statement = body

    def accept(self, visitor, value):
        return visitor.visit_do_while_loop(self, value)

    def __str__(self):
        if isinstance(self.body, Block):
            return f"do{format_body(self.body, newline_in_empty_body=True)} while({self.condition});"
        else:
            return "do\n" + indent(str(self.body), '\t') + "\nwhile({self.condition});"

class SynchronizedBlock(Statement):
    def __init__(self, *, lock, body, parent=None):
        typecheck(lock, Expression, function='SynchronizedBlock')
        typecheck(body, Block, function='SynchronizedBlock')

        super().__init__(parent)

        self.lock: Expression = lock
        self.body: Block = body

    def accept(self, visitor, value):
        return visitor.visit_synchronized_block(self, value)

    def __str__(self):
        return f"synchronized({self.lock}) {self.body}"

class TryStatement(Statement):
    def __init__(self, *, resources=None, body, catches, finallybody=None, parent=None):
        listtypecheck(resources, (NoneType, list), (TryResource, Expression), function='TryStatement')
        typecheck(body, Block, function='TryStatement')
        listtypecheck(catches, list, CatchClause, function='TryStatement')
        typecheck(finallybody, (NoneType, Block), function='TryStatement')

        super().__init__(parent)

        self.resources: List[TryResource] = resources
        self.body: Block = body
        self.catches: List[CatchClause] = catches
        self.finallybody = finallybody

    def accept(self, visitor, value):
        return visitor.visit_try_statement(self, value)

    def __str__(self):
        result = "try"
        if self.resources is not None:
            result += '(' + '; '.join(str(resource) for resource in self.resources) + ')'
        result += format_body(self.body, newline_in_empty_body=self.catches or self.finallybody)
        if self.catches:
            result += ' ' + ' '.join(str(catch) for catch in self.catches)
        if self.finallybody:
            result += ' finally' + format_body(self.finallybody, newline_in_empty_body=True)
        return result

class TryResource(Node, Named, Documented, Dimension, Declaration):
    def __init__(self, *, type, name, dimensions=[], init, doc=None, modifiers=[], annotations=[], parent=None):
        typecheck(type, Type, function='TryResource')
        typecheck(init, Expression, function='TryResource')

        Node.__init__(self, parent)
        Declaration.__init__(self, modifiers, annotations)
        Named.__init__(self, name)
        Documented.__init__(self, doc)
        Dimension.__init__(self, dimensions)

        self.type: Type = type
        self.init: Expression = init

    def accept(self, visitor, value):
        return visitor.visit_try_resource(self, value)

    def __str__(self):
        return f"{self.doc_str(newlines=False)}{self.anno_str(newlines=False)}{self.mod_str()}{self.type} {self.name}{self.dim_str()} = {self.init}"

class CatchClause(Node):
    def __init__(self, *, var, body, parent=None):
        typecheck(var, CatchVar, function='CatchClause')
        typecheck(body, Block, function='CatchClause')

        super().__init__(parent)

        self.var: CatchVar = var   
        self.body: Block = body

    def accept(self, visitor, value):
        return visitor.visit_catch_clause(self, value)

    def __str__(self):
        return f"catch({self.var})" + format_body(self.body, newline_in_empty_body=True)
    
class CatchVar(Node, Named, Documented, Declaration):
    def __init__(self, *, name, type, doc=None, modifiers=[], annotations=[], parent=None):
        typecheck(type, (TypeIntersection, GenericType), function='CatchVar')

        Node.__init__(self, parent)
        Named.__init__(self, name)
        Declaration.__init__(self, modifiers, annotations)
        Documented.__init__(self, doc)

        self.type: Type = type

    def accept(self, visitor, value):
        return visitor.visit_catch_var(self, value)

    def __str__(self):
        return f"{self.doc_str(newlines=False)}{self.anno_str(newlines=False)}{self.mod_str()}{self.type} {self.name}"

class AssertStatement(Statement):
    def __init__(self, *, condition, message=None, parent=None):
        typecheck(condition, Expression, function='AssertStatement')
        typecheck(message, (NoneType, Expression), function='AssertStatement')

        super().__init__(parent)

        self.condition: Expression = condition
        self.message: Expression = message

    def accept(self, visitor, value):
        return visitor.visit_assert_statement(self, value)

    def __str__(self):
        result = f"assert {self.condition}"
        if self.message:
            result += f" : {self.message}"
        result += ';'
        return result


class NodeVisitor:
    def __call__(self, node: Node, value=None):
        typecheck(node, Node)
        proceed = node.accept(self, value)
        if not isinstance(proceed, bool):
            raise TypeError('Node.accept(NodeVisitor) did not return True or False')
        if proceed:
            for child in node.children:
                self(child, value)
        return value

    def visit_node(self, node: Node, value=None):
        """ The default method that is called whenever a Node does not override Node.accept() """
        return True

  # ------------------------------------------------------------------------------------

    def visit_annotation(self, node: Annotation, value=None):
        return self.visit_node(node, value)

    def visit_annotation_argument(self, node: AnnotationArgument, value=None):
        return self.visit_node(node, value)

    def visit_annotation_declaration(self, node: AnnotationDeclaration, value=None):
        return self.visit_node(node, value)

    def visit_annotation_property(self, node: AnnotationProperty, value=None):
        return self.visit_node(node, value)

    def visit_array_creator(self, node: ArrayCreator, value=None):
        return self.visit_node(node, value)

    def visit_array_initializer(self, node: ArrayInitializer, value=None):
        return self.visit_node(node, value)

    def visit_array_type(self, node: ArrayType, value=None):
        return self.visit_node(node, value)

    def visit_assert_statement(self, node: AssertStatement, value=None):
        return self.visit_node(node, value)

    def visit_assignment(self, node: Assignment, value=None):
        return self.visit_node(node, value)

    def visit_binary_expression(self, node: BinaryExpression, value=None):
        return self.visit_node(node, value)

    def visit_block(self, node: Block, value=None):
        return self.visit_node(node, value)

    def visit_break_statement(self, node: BreakStatement, value=None):
        return self.visit_node(node, value)

    def visit_cast_expression(self, node: CastExpression, value=None):
        return self.visit_node(node, value)

    def visit_catch_clause(self, node: CatchClause, value=None):
        return self.visit_node(node, value)

    def visit_catch_var(self, node: CatchVar, value=None):
        return self.visit_node(node, value)

    def visit_class_creator(self, node: ClassCreator, value=None):
        return self.visit_node(node, value)

    def visit_class_declaration(self, node: ClassDeclaration, value=None):
        return self.visit_node(node, value)

    def visit_compilation_unit(self, node: CompilationUnit, value=None):
        return self.visit_node(node, value)

    def visit_conditional_expression(self, node: ConditionalExpression, value=None):
        return self.visit_node(node, value)

    def visit_constructor_declaration(self, node: ConstructorDeclaration, value=None):
        return self.visit_node(node, value)

    def visit_continue_statement(self, node: ContinueStatement, value=None):
        return self.visit_node(node, value)

    def visit_dimension_expression(self, node: DimensionExpression, value=None):
        return self.visit_node(node, value)

    def visit_do_while_loop(self, node: DoWhileLoop, value=None):
        return self.visit_node(node, value)

    def visit_empty_statement(self, node: EmptyStatement, value=None):
        return self.visit_node(node, value)

    def visit_enhanced_for_control(self, node: EnhancedForControl, value=None):
        return self.visit_node(node, value)

    def visit_enum_declaration(self, node: EnumDeclaration, value=None):
        return self.visit_node(node, value)

    def visit_enum_field(self, node: EnumField, value=None):
        return self.visit_node(node, value)

    def visit_exports_directive(self, node: ExportsDirective, value=None):
        return self.visit_node(node, value)

    def visit_expression_statement(self, node: ExpressionStatement, value=None):
        return self.visit_node(node, value)

    def visit_field_declaration(self, node: FieldDeclaration, value=None):
        return self.visit_node(node, value)

    def visit_for_control(self, node: ForControl, value=None):
        return self.visit_node(node, value)

    def visit_for_loop(self, node: ForLoop, value=None):
        return self.visit_node(node, value)

    def visit_formal_parameter(self, node: FormalParameter, value=None):
        return self.visit_node(node, value)

    def visit_function_call(self, node: FunctionCall, value=None):
        return self.visit_node(node, value)

    def visit_function_declaration(self, node: FunctionDeclaration, value=None):
        return self.visit_node(node, value)

    def visit_generic_type(self, node: GenericType, value=None):
        return self.visit_node(node, value)

    def visit_if_statement(self, node: IfStatement, value=None):
        return self.visit_node(node, value)

    def visit_import(self, node: Import, value=None):
        return self.visit_node(node, value)

    def visit_increment_expression(self, node: IncrementExpression, value=None):
        return self.visit_node(node, value)

    def visit_index_expression(self, node: IndexExpression, value=None):
        return self.visit_node(node, value)

    def visit_initializer_block(self, node: InitializerBlock, value=None):
        return self.visit_node(node, value)

    def visit_interface_declaration(self, node: InterfaceDeclaration, value=None):
        return self.visit_node(node, value)

    def visit_labeled_statement(self, node: LabeledStatement, value=None):
        return self.visit_node(node, value)

    def visit_lambda(self, node: Lambda, value=None):
        return self.visit_node(node, value)

    def visit_literal(self, node: Literal, value=None):
        return self.visit_node(node, value)

    def visit_member_access(self, node: MemberAccess, value=None):
        return self.visit_node(node, value)

    def visit_method_reference(self, node: MethodReference, value=None):
        return self.visit_node(node, value)

    def visit_modifier(self, node: Modifier, value=None):
        return self.visit_node(node, value)

    def visit_module_compilation_unit(self, node: ModuleCompilationUnit, value=None):
        return self.visit_node(node, value)

    def visit_name(self, node: Name, value=None):
        return self.visit_node(node, value)

    def visit_null_literal(self, node: NullLiteral, value=None):
        return self.visit_node(node, value)

    def visit_opens_directive(self, node: OpensDirective, value=None):
        return self.visit_node(node, value)

    def visit_package(self, node: Package, value=None):
        return self.visit_node(node, value)

    def visit_parenthesis(self, node: Parenthesis, value=None):
        return self.visit_node(node, value)

    def visit_primitive_type(self, node: PrimitiveType, value=None):
        return self.visit_node(node, value)

    def visit_provides_directive(self, node: ProvidesDirective, value=None):
        return self.visit_node(node, value)

    def visit_requires_directive(self, node: RequiresDirective, value=None):
        return self.visit_node(node, value)

    def visit_return_statement(self, node: ReturnStatement, value=None):
        return self.visit_node(node, value)

    def visit_super(self, node: Super, value=None):
        return self.visit_node(node, value)

    def visit_super_call(self, node: SuperCall, value=None):
        return self.visit_node(node, value)

    def visit_switch(self, node: Switch, value=None):
        return self.visit_node(node, value)

    def visit_switch_case(self, node: SwitchCase, value=None):
        return self.visit_node(node, value)

    def visit_synchronized_block(self, node: SynchronizedBlock, value=None):
        return self.visit_node(node, value)

    def visit_this(self, node: This, value=None):
        return self.visit_node(node, value)

    def visit_this_call(self, node: ThisCall, value=None):
        return self.visit_node(node, value)

    def visit_this_parameter(self, node: ThisParameter, value=None):
        return self.visit_node(node, value)

    def visit_throw_statement(self, node: ThrowStatement, value=None):
        return self.visit_node(node, value)

    def visit_try_resource(self, node: TryResource, value=None):
        return self.visit_node(node, value)

    def visit_try_statement(self, node: TryStatement, value=None):
        return self.visit_node(node, value)

    def visit_type_argument(self, node: TypeArgument, value=None):
        return self.visit_node(node, value)

    def visit_type_intersection(self, node: TypeIntersection, value=None):
        return self.visit_node(node, value)

    def visit_type_literal(self, node: TypeLiteral, value=None):
        return self.visit_node(node, value)

    def visit_type_parameter(self, node: TypeParameter, value=None):
        return self.visit_node(node, value)

    def visit_type_test(self, node: TypeTest, value=None):
        return self.visit_node(node, value)

    def visit_type_union(self, node: TypeUnion, value=None):
        return self.visit_node(node, value)

    def visit_unary_expression(self, node: UnaryExpression, value=None):
        return self.visit_node(node, value)

    def visit_uses_directive(self, node: UsesDirective, value=None):
        return self.visit_node(node, value)

    def visit_variable_declaration(self, node: VariableDeclaration, value=None):
        return self.visit_node(node, value)

    def visit_variable_declarator(self, node: VariableDeclarator, value=None):
        return self.visit_node(node, value)

    def visit_void_type(self, node: VoidType, value=None):
        return self.visit_node(node, value)

    def visit_while_loop(self, node: WhileLoop, value=None):
        return self.visit_node(node, value)

    def visit_yield_statement(self, node: YieldStatement, value=None):
        return self.visit_node(node, value)
    
class NodeModifier(NodeVisitor):
    def __call__(self, node: Node):
        typecheck(node, Node)
        proceed, node = node.accept(self, None)
        if not isinstance(proceed, bool):
            raise TypeError('Node.accept(NodeModifier) first return value must be True or False')
        if not isinstance(node, Node):
            raise TypeError('Node.accept(NodeModifier) second return value must be Node')
        if proceed:
            for name, child in node.__dict__.items():
                if isinstance(child, Node):
                    newchild = self(child)
                    if newchild is not child:
                        setattr(node, name, newchild)
            
        return node
        
    def visit_node(self, node: Node, value=None):
        return True, node