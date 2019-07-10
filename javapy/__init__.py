from .parser import Parser, JavaParser, JavaSyntaxError, parse_file, parse_str
from .tokenize import tokenize

import unittest

class UnitTests(unittest.TestCase):
    def test_parser(self):
        import os.path
        import pprint
        from textwrap import indent
        self.maxDiff = None
        with open(os.path.join(os.path.dirname(__file__), 'test.java'), 'rb') as file:
            java_unit = parse_file(file, parser=JavaParser)
        with open(os.path.join(os.path.dirname(__file__), 'test.javapy'), 'rb') as file:
            javapy_unit = parse_file(file, parser=Parser)
        self.assertEqual(java_unit, javapy_unit, f"java_unit != javapy_unit.\njava_unit:\n{indent(pprint.pformat(java_unit), '    ')}\njavapy_unit:\n{indent(pprint.pformat(javapy_unit), '    ')}")
        java_unit_str = str(java_unit)
        javapy_unit_str = str(javapy_unit)
        self.assertEqual(java_unit_str, javapy_unit_str, f"str(java_unit) != str(javapy_unit).")
        
        

def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(description='Parse a javapy file')
    parser.add_argument('file', type=argparse.FileType('rb'),
                        help='The javapy file to parse')
    parser.add_argument('--type', options=('Java', 'JavaPy'),
                        help='What syntax to use')

    args = parser.parse_args(args)

    with args.file as file:
        parser = parse_file(file, parser=JavaParser if args.type is 'Java' else Parser)

    unit = parser.parse_compilation_unit()

    import os.path

    filename = os.path.join(os.path.dirname(args.file.name), os.path.splitext(args.file.name)[0] + '.java')

    with open(filename, 'w') as file:
        file.write(str(unit))

    print("Converted", filename)

if __name__ == "__main__":
    main()