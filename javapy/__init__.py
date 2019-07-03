from .parser import Parser, JavaSyntaxError, parse_file, parse_str
from .tokenize import tokenize

def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(description='Parse a javapy file')
    parser.add_argument('file', type=argparse.FileType('rb'),
                        help='The javapy file to parse')

    args = parser.parse_args(args)

    with args.file as file:
        parser = Parser(tokenize(file.readline))

    unit = parser.parse_compilation_unit()

    import os.path

    filename = os.path.join(os.path.dirname(args.file.name), os.path.splitext(args.file.name)[0] + '.java')

    with open(filename, 'w') as file:
        file.write(str(unit))

    print("Converted", filename)

if __name__ == "__main__":
    main()