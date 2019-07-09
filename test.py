import javapy
from javapy.parser import JavaParser

javapy.tree.INDENT_WITH = '    '

unit = javapy.parse_str(R"""
package com.test;

import java.util.List;
import java.util.stream.Collectors;

public abstract class Test {
    public static void main(String[] args) {
        println("Hello, world!");
        List<String> strs = java.util.List.of("one", "two", "three");
    }
}

enum Day {
    MONDAY("Mon."),
    TUESDAY("Tues."),
    WEDNESDAY("Wed."),
    THURSDAY("Thurs."),
    FRIDAY("Fri."),
    SATURDAY("Sat."),
    SUNDAY("Sun.");

    public final String abbreviation;

    Day(String abbr) {
        abbreviation = abbr;
    }

    @Override
    public String toString() {
        var sb = new StringBuilder();
        sb.append(name().charAt(0));
        sb.append(name(), 1, name().length());
        return sb.toString();
    }

    public static Day fromAbbreviation(String abbr) {
        return (
            switch(abbr) {
                case "Mon.", "Mon" -> MONDAY;
                case "Tues.", "Tues" -> TUESDAY;
                case "Wed.", "Wed" -> WEDNESDAY;
                case "Thurs.", "Thurs" -> THURSDAY;
                case "Fri.", "Fri" -> FRIDAY;
                case "Sat.", "Sat" -> SATURDAY;
                case "Sun.", "Sun" -> SUNDAY;
                default -> throw new IllegalArgumentException("'" + abbr + "' does not correspond to any known abbreviation.");
            }
        );
    }

}

""", parser=JavaParser)

unit2 = javapy.parse_str(R"""
package com.test

from java.util import List, stream.Collectors

public abstract class Test:
    public static void main(String[] args):
        println(R"Hello, world!")
        List<String> strs = ["one", "two", "three"]

enum Day:
    MONDAY("Mon.")
    TUESDAY("Tues.")
    WEDNESDAY("Wed.")
    THURSDAY("Thurs.")
    FRIDAY("Fri.")
    SATURDAY("Sat.")
    SUNDAY("Sun.")

    public final String abbreviation

    Day(String abbr):
        abbreviation = abbr

    @Override
    public String toString():
        var sb = new StringBuilder()
        sb.append(name().charAt(0))
        sb.append(name(), 1, name().length())
        return sb.toString()

    public static Day fromAbbreviation(String abbr):
        return (
            switch abbr {
                case "Mon.", "Mon" -> MONDAY
                case "Tues.", "Tues" -> TUESDAY
                case "Wed.", "Wed" -> WEDNESDAY
                case "Thurs.", "Thurs" -> THURSDAY
                case "Fri.", "Fri" -> FRIDAY
                case "Sat.", "Sat" -> SATURDAY
                case "Sun.", "Sun" -> SUNDAY
                default -> throw new IllegalArgumentException("'" + abbr + "' does not correspond to any known abbreviation.")
            }
        )

""")

unit = str(unit)
unit2 = str(unit2)

assert unit == unit2, f"Units did not match:\n{unit}\n==================\n{unit2}\n\n1 Error."

print(unit)
