package com.test;

import java.util.*;
import java.util.functions.*;
import static java.lang.Math.*;

/** Test doc
Line 2
 */
public class Test {
	public static int x = 3;
	public static String str = "\nTest Line 1\nTest Line 2\n";
	/** 
	 * Test doc
	 * Line 2
	 */
	public static void main(String[] args) {
		System.out.println("Program start!");
		int x, y;
		y = x = 5 * 23 + (int)Math.pow(6, 7);
		IntFunction<String> itos = String::valueOf;
		Function<? extends String, Integer> stoi = str -> {
			return Integer.parseInt(str);
		};
		Supplier<StringBuilder> sbsupplier = StringBuilder::new;
		var rand = new Random();
		if(rand.nextBoolean()) {
			System.out.println(stoi.apply(itos.apply(0b101110101)));
		}
		switch(rand.nextInt(10)) {
			case 0, 1:
				System.out.println("A");
				break;
			case 2, 3:
				System.out.println("B");
				break;
			case 4:
				System.out.println("C");
				break;
			case 5:
				System.out.println("D");
				break;
			case 6, 7, 8:
				System.out.println("E");
				break;
			case 9:
			case 10:
				System.out.println("F");
				break;
			default:
				throw new AssertionError();
		}
		int[] ints = {1, 2, 3, 4};
		int[] ints2[] = new int[5][];
		char ch = switch(rand.nextInt(10)) {
			case 0, 1 -> "A";
			case 2, 3 -> "B";
			case 4 -> "C";
			case 5 -> "D";
			case 6, 7, 8 -> "E";
			case 9, 10 -> "F";
			default -> throw new AssertionError();
		};
		char ch2 = switch(rand.nextInt(10)) {
			case 0, 1:
				break "A";
			case 2, 3:
				break "B";
			case 4:
				break "C";
			case 5:
				break "D";
			case 6:
				break "E";
			case 8:
				break "F";
			default:
				break "G";
		};
		label: {
			int foo = 5;
			for(@Annotation int i = 0; i > -10; i--) {
				foo += i;
				foo /= i;
				System.out.println(foo);
			}
		}
		int foo = 7;
		for(x = 0; x < 10; x++) {
			foo -= x;
			foo *= x;
			System.out.println(foo);
		}
		for(int i : ints) {
			System.out.println(foo /= i);
		}
		abstract class Greeter {
			Greeter() {
				System.out.println("New " + this.getClass().getName() + " created!");
			}
			abstract void greet();
		}
		var v1 = 3; var v2 = new Greeter() {
			void greet() {
				System.out.println("hi!");
			}
		};
		do
			v1 += 2;
		while({self.condition});
		if(rand.nextBoolean()) {
			System.out.println("A");
		} else if(rand.nextInt(10) < 5) {
			System.out.println("B");
		}
		int@Annotation [] ints2[] = new @Annotation int[3] @Annotation [];
		for(int i : ints2) {
			System.out.println(i);
		}
		for(int i = 3, j = 10; i < j; i += 2, (i += 2), j++) {
			System.out.println(i + j);
		}
		List<String> list1 = java.util.List.of("first", "second", "third");
		try {
			list1.add("fourth");
		} catch(RuntimeException | UnsupportedOperationException e) {
		} catch(SecurityException | IllegalStateException e2) {
		} catch(NullPointerException | ClassNotFoundException e3) {
		}
		try(Scanner scan = new Scanner(new File("missing.txt"))) {
			scan.useDelimiter("\\A");
			throw new AssertionError();
		} catch(FileNotFoundException e) {
		}
	}
}

@interface Annotation {
	Annotation[] value() default {};
}

class Thing {
	final String id;
	{
		var b = new StringBuilder();
		for(char c = "a"; c < "z"; c++) {
			b.append(c);
		}
		id = b.toString();
	}
	@Annotation(@Annotation)
	@SuppressWarnings("unused")
	public Thing() {
		System.out.println("New Thing created!");
	}
	@SuppressWarnings({"unchecked", "resource"})
	public void doThing() {
		synchronized(this) {
			System.out.println(this.id);
		}
		return;
	}
}

interface Interface {
	void test();
	int getId();
	default String getName() {
		return String.valueOf(this.getId());
	}
	void setName(String newname);
}

enum Day {
	MONDAY("Mon."),
	TUESDAY("Tues."),
	WEDNESDAY("Wed."),
	THURSDAY("Thurs."),
	FRIDAY("Fri."),
	@Annotation
	SATURDAY("Sat.") {
		@Override
		public boolean isWeekend() {
			return true;
		}
	},
	SUNDAY("Sun.") {
		@Override
		public boolean isWeekend() {
			return true;
		}
	};
	public final String abbr;
	Day(String abbr) {
		this.abbr = abbr;
	}
	public boolean isWeekend() {
		return false;
	}
}