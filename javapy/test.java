package com.test;

import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;
import java.util.Set;
import java.util.HashSet;
import java.util.EnumSet;
import java.util.Collection;
import java.util.Arrays;
import java.util.Collections;
import java.util.stream.Collectors;

public abstract class Test {
	public static void main(String[] args) {
		println("Hello, world!");
		List<String> strs = java.util.List.of("one", "two", "three", "four", "five", "six", "seven");
		Map<String, Integer> map = java.util.Map.of(
			"one", 1,
			"two", 2,
			"three", 3,
			"four", 4,
			"five", 5,
			"six", 6,
			"seven", 7
		);
		for(String str : strs) {
			println(map.get(str));
		}
	}
}

interface Named {
	String getName();
}

enum Day implements Named {
	MONDAY("Mon."),
	TUESDAY("Tues."),
	WEDNESDAY("Wed."),
	THURSDAY("Thurs."),
	FRIDAY("Fri."),
	SATURDAY("Sat."),
	SUNDAY("Sun.");

	public static final Set<Day> VALUES, WEEKDAYS, WEEKENDS;

	static {
		VALUES = Collections.unmodifiableSet(EnumSet.allOf(Day.class));
		WEEKDAYS = VALUES.stream().filter(day -> switch(day) {
													 case SATURDAY, SUNDAY -> false;
													 default -> true;
												 }).collect(Collectors.toSet());
		WEEKENDS = Collections.unmodifiableSet(EnumSet.complementOf(WEEKDAYS));
	}

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
	
	@Override
	public String getName() { return name(); }

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

interface Animal {
	void speak();
	String getAnimalName();
}

class Dog implements Animal {
	@Override
	public void speak() {
		println("Woof!");
	}
	
	@Override
	public String getAnimalName() {
		return "Dog";
	}
}

class Cat implements Animal {
	@Override
	public void speak() {
		println("Meow");
	}
	
	@Override
	public String getAnimalName() {
		return "Cat";
	}
}

class Pet implements Animal, Named {
	private final Animal animal;
	private String name;
	
	public Pet(Animal animal, String name) {
		this.animal = animal;
		this.name = name;
	}
	
	@Override
	public void speak() { animal.speak(); }
	
	@Override
	public String getAnimalName() { return animal.getAnimalName(); }
	
	@Override
	public String getName() { return name; }
}