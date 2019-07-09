import javapy
from javapy.parser import JavaParser

javapy.tree.INDENT_WITH = '    '

unit = javapy.parse_str(R"""
package com.test;

class Test {
    public static void main(String[] args) {
        println("Hello, world!");
    }
}

""", parser=JavaParser)

unit2 = javapy.parse_str(R"""
package com.test

class Test:
    public static void main(String[] args):
        println("Hello, world!")

""")

unit = str(unit)
unit2 = str(unit2)

assert unit == unit2, f"Units did not match:\n{unit}\n==================\n{unit2}"

print(unit)
