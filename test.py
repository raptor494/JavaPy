import javapy
import io
from javapy.parser import JavaParser
from javapy.tokenize import print_tokens

tokens = javapy.tokenize(io.BytesIO(b"""
public abstract class Test:
    public static void main(String[] args):
        println(R"Hello, world!")
        List<String> strs = ["one", "two", "three", "four", "five", "six", "seven"]
        Map<String, Integer> map = { 			"one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7
        }
        for String str : strs:
            println(map.get(str))
""").readline)

print_tokens(tokens)