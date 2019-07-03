# JavaPy
### Description
This is a Python program which allows you to write Java using Python indentation and without semicolons.
I wrote it in my spare time, so there may be lots of bugs. I tried to support every syntactical element in the Java language that I could.
### Usage
Call the program with `python javapy.py <filename>` and it will output a file
called the same thing except with a `.java` extension.
The program tries to format the file to be human-readable but may not be quite right in places. Use your own formatter as necessary.
The parser does not check for semantically invalid syntax, such as duplicate variable names, duplicate methods, improper package names, illegal modifiers, etc.
### Differences from Normal Java
##### Code Blocks
Blocks are usually not allowed anymore. Instead of blocks, use a Python *Suite*, which is a colon followed by a series of elements all indented the same amount.
**Examples**:
Normal Java: 
```java
public class Example {
    public static final int x, y;
} 
```
JavaPy:
```java
public class Example:
    public static final int x, y
```
Normal Java:
```java
public int foo(int x) {
    if(x < 10) {
        return 2*x - 1;
    } else {
        return x % 3 * x - 6;
    }
}
```
JavaPy:
```java
public int foo(int x):
    if x < 10:
        return 2*x - 1
    else:
        return x % 3 * x - 6
```
##### Statements containing other statements
If a statement would normally require a parenthesised condition after
its keyword, the parenthesis are now optional.
**Examples**:
Normal Java:
```java
if(condition) {
    doSomething();
} else if(anotherCondition) {
    doSomethingElse();
} else {
    doSomething2();
}
```
JavaPy:
```java
if condition:
    doSomething()
else if anotherCondition:
    doSomethingElse()
else:
    doSomething2()
```
Normal Java:
```java
synchronized(this) {
    doSomethingWithThis();
}
```
JavaPy:
```java
synchronized: // If you leave the lock expression out, it defaults to 'this'.
    doSomethingWithThis()
```
Normal Java:
```java
try(Scanner keys = new Scanner(System.in)) {
    System.out.print("Enter a number: ");
    int x = Integer.parseInt(keys.nextLine());
    System.out.println("Your number was: " + x);
} catch(NumberFormatException e) {
    e.printStackTrace();
} finally {
    System.out.println("Goodbye");
}
```
JavaPy:
```java
try var keys = new Scanner(System.in):
    System.out.print("Enter a number: ")
    int x = Integer.parseInt(keys.nextLine())
    System.out.println("Your number was: " + x)
catch NumberFormatException e:
    e.printStackTrace()
finally:
    System.out.println("Goodbye")
```
##### Import Declarations
The one statement I have brought over from python is the from ... import ... statement. 
Syntax: `from <package-or-type-name> import [static] <qualified-name-or-wildcard> {, <qualified-name-or-wildcard>}`
**Examples**
Normal Java:
```java
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
```
JavaPy:
```python
from java.util import List, ArrayList, Map
```
Normal Java:
```java
import static com.test.Example.foo;
import static com.test.Example.bar;
import static com.test.Example.kaz;
```
JavaPy:
```python
from com.test.Example import static foo, bar, kaz
```
Normal Java:
```java
import java.util.*;
import java.util.function.*;
```
JavaPy:
```python
from java.util import *, function.*
```
Additionally, a single normal import statement can have multiple comma-separated imports in it.
**Example**
```java
import java.util.List, java.util.ArrayList
```
##### Optional parenthesis
Sometimes, you may want to put certain things on multiple lines. You could end a line with a backslash (\\) to join it with the following line, like in Python, or
you could wrap it in parenthesis.
**Examples**
Normal Java:
```java
for(int x = aVeryLongExpression(), 
        y = anotherVeryLongExpression(), 
        z = yetAnotherVeryLongExpression();
    x + y < z; 
    x++, y--, z--) {
    System.out.println(x+y+z);
}
```
JavaPy:
```java
for (int x = aVeryLongExpression(),
         y = anotherVeryLongExpression(), 
         z = yetAnotherVeryLongExpression()); \
        x + y < z; \
        x++, y++, z++:
    System.out.println(x+y+z)
```
Normal Java:
```java
public abstract class Example extends Superclass implements Interface1,     
    Interface2, 
    Interface3,
    Interface4 {
    ...
}
```
JavaPy:
```java
public abstract class Example extends Superclass implements (Interface1,
    Interface2,
    Interface3,
    Interface4):
    ;
```
Normal Java:
```java
module com.test {
    exports com.test.types;
    requires com.example.services;
    provides com.example.services.ExampleService with com.test.services.MyService,
        com.test.services.TheirService;
}
```
JavaPy:
```java
module com.test:
    exports com.test.types
    requires com.example.services
    provides com.example.services.ExampleService with (com.test.services.MyService,
        com.test.services.TheirService)
```
Normal Java:
```java
HashMap<String, 
    HashMap<Integer, 
        List<Pair<String, ?>>>> map = new HashMap<>();
```
JavaPy:
```java
HashMap<(String,
    HashMap<Integer,
        List<Pair<String, ?>>>)> map = new HashMap<>()
```
Normal Java:
```java
try(var resource1 = getResource1();
    var resource2 = getResource2()) {
    doStuffWithResources();
} catch(NoSuchElementException 
        | NullPointerException 
        | ClassNotFoundException 
        | IllegalArgumentException e) {
    e.printStackTrace();
} catch(IOException
        | IllegalStateException e) {
    e.printStackTrace();
}
```
JavaPy:
```java
try (var resource1 = getResource1();
     var resource2 = getResource2()):
    doStuffWithResources()
catch (NoSuchElementException 
        | NullPointerException 
        | ClassNotFoundException 
        | IllegalArgumentException) e:
    e.printStackTrace()
catch (IOException
        | IllegalStateException e):
    e.printStackTrace()
```
Normal Java:
```java
switch(day) {
    case MONDAY,
        TUESDAY,
        WEDNESDAY -> {
            if(day == Day.MONDAY) {
                message = "It's a monday";
            } else {
                message = "meh";
            }
        }
    case THURSDAY, FRIDAY -> {
        message = "Almost";
    }
    default -> throw new WeekendException();
}
```
JavaPy:
```java
switch day:
    case (MONDAY,
          TUESDAY,
          WEDNESDAY) ->
        if day == Day.MONDAY:
            message = "It's a monday"
        else:
            message = "meh"
    case THURSDAY, FRIDAY -> message = "Almost"
    default -> throw new WeekendException()
```
Normal Java:
```java
import java.util.List;
import java.util.Set;
import java.util.Map;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.HashMap;
```
JavaPy:
```python
from java.util import (
    List,
    Set,
    Map,
    ArrayList,
    HashSet,
    HashMap
)
```
##### Unnecessary Commas
In Java, you can add a comma at the end of a list initializer:
```java
int[] ints = {1,2,3,4,5,};
```
Python has that, plus allows you to do it in function arguments. Well, JavaPy
allows you to do it in function arguments, too.
```java
foo(1,2,3,4,5,)
```
##### Places where blocks ARE needed
In some places, I just couldn't do the Suite syntax for a code block, like
in lambda expressions or anonymous classes. So, for those, you'll just need to wrap
the block in braces. (Note that the block still needs to be indented)
**Examples**
Normal Java:
```java
new Object() {
    public void foo() {
        System.out.println("Foo");
    }
}
```
JavaPy:
```java
new Object() {
    public void foo():
        System.out.println("Foo")
}
```
Normal Java:
```java
(String str, int x) -> {
    if(str == null) {
        System.out.println("Str is null");
    } else {
        assert Integer.parseInt(str) == x;
    }
}
```
JavaPy:
```java
(String str, int x) -> {
    if str == null:
        System.out.println("Str is null")
    else:
        assert Integer.parseInt(str) == x
}
```
##### More
See `example.javapy` for a lot more code examples.