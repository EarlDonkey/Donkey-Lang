# Donky

**A small programming language you can learn in an afternoon, and use to write real programs.**

Donky is a programming language. You write instructions in a `.donk` file, run them with the Donky interpreter, and the computer does what you said.

It's small on purpose. There aren't many features, so the whole language fits in your head. Once you've read this guide, you'll know all of it.

---

## Table of contents

1. [What is a programming language?](#1-what-is-a-programming-language)
2. [Getting started](#2-getting-started)
3. [Your first program](#3-your-first-program)
4. [Variables and numbers](#4-variables-and-numbers)
5. [Strings — working with text](#5-strings--working-with-text)
6. [Making decisions: if / else](#6-making-decisions-if--else)
7. [Repeating things: while and for](#7-repeating-things-while-and-for)
8. [Lists (arrays)](#8-lists-arrays)
9. [Dictionaries (maps)](#9-dictionaries-maps)
10. [Functions — reusable code](#10-functions--reusable-code)
11. [When things go wrong: try / catch](#11-when-things-go-wrong-try--catch)
12. [Talking to the user: input](#12-talking-to-the-user-input)
13. [Files](#13-files)
14. [Splitting your code into files: import](#14-splitting-your-code-into-files-import)
15. [A complete program: a notes app](#15-a-complete-program-a-notes-app)
16. [Cheat sheet](#16-cheat-sheet)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. What is a programming language?

A programming language is a way to give a computer instructions. You write those instructions in a text file, save it with a `.donk` extension, and run it. The computer reads your instructions top to bottom, does what they say, and stops.

Here's the smallest program in Donky:

```donky
print("Hello, world!");
```

`print` means "show this on the screen." The text in quotes is what gets shown. The `;` at the end is a period — it tells Donky the instruction is finished. Save this as `hello.donk`, run it, and you'll see:

```
Hello, world!
```

That's it. You've written a program.

---

## 2. Getting started

### If you have the .exe

Download `donky.exe` (or the `donky/` folder that contains it). Open a terminal in that folder. Run:

```
donky hello.donk
```

### If you have the source

You need Python 3.10 or newer. Then:

```
python -m donky.run hello.donk
```

Or, to try code without writing a file first, start the interactive prompt:

```
python -m donky
```

You'll get a `donky>` prompt. Type `1 + 2` and press Enter. It prints `3`. Type `:quit` to leave.

### Three ways to run

- `donky myfile.donk` — run a program.
- `donky` (no file) — start the REPL (a live prompt).
- `donky --check-only myfile.donk` — just check for errors, don't run.

---

## 3. Your first program

Save this as `hello.donk`:

```donky
print("Hello, world!");
print("My name is Donky.");
print(2 + 2);
```

Run it. You'll see:

```
Hello, world!
My name is Donky.
4
```

Three `print` instructions. Notice that `print` can show text (`"Hello, world!"`) or the answer to a math problem (`2 + 2`). It shows whatever you give it.

**One rule to remember:** every instruction ends with `;`. Forget it and Donky will complain.

---

## 4. Variables and numbers

A **variable** is a name for a value. You create one with `let`.

```donky
let age = 10;
print(age);

let price = 4.99;
print(price);

let total = age + price;
print(total);
```

Prints:

```
10
4.99
14.99
```

### Math

Donky understands the usual math:

```donky
print(2 + 3);    // 5 — addition
print(10 - 4);   // 6 — subtraction
print(3 * 4);    // 12 — multiplication
print(10 / 4);   // 2.5 — division (always gives a decimal)
print(10 div 4); // 2 — integer division (throws away the remainder)
print(10 % 4);   // 2 — remainder
```

**`div` vs `/`**: `/` gives you a decimal answer. `div` throws away the decimal part. Use `/` for measuring things (2.5 liters), `div` for counting things (how many whole groups of 4 fit in 10).

### Two kinds of numbers

- `42` — a whole number (integer)
- `3.14` — a decimal number (float)

Donky handles both. You don't have to think about which is which most of the time.

### Changing a variable

```donky
let score = 0;
print(score);     // 0
score = score + 10;
print(score);     // 10
score = score + 5;
print(score);     // 15
```

The `=` here is **assignment** — "make the variable hold this value now." It's not testing whether the two sides are equal. (Testing equality is `==`, two equals signs.)

### Try it

Change the program to compute your age in days. (Multiply by 365.)

---

## 5. Strings — working with text

A **string** is text inside quotes. `"hello"` is a string. So is `"Good morning, Mr. Smith!"`.

### Joining strings

Use `+`:

```donky
let first = "Ada";
let last = "Lovelace";
let full = first + " " + last;
print(full);  // Ada Lovelace
```

### Length

```donky
let s = "hello";
print(len(s));   // 5
```

### Getting one character

Put the position (starting at 0) in square brackets:

```donky
let s = "hello";
print(s[0]);   // h
print(s[1]);   // e
print(s[4]);   // o
```

Positions start at **zero**, not one. `s[0]` is the first character. If you ask for `s[5]` on a 5-character string, Donky will complain — positions go from 0 to 4.

### Changing case, trimming, splitting

```donky
print(upper("hello"));        // HELLO
print(lower("HELLO"));        // hello
print(trim("  hi  "));        // "hi" (whitespace removed from the ends)
print(replace("a-b-c", "-", "+"));  // a+b+c

// Split into pieces:
let parts = split("apple,banana,cherry", ",");
print(parts);        // [apple, banana, cherry]
print(len(parts));   // 3

// Join pieces back together:
print(join(parts, " | "));  // apple | banana | cherry
```

### Checking if text contains something

```donky
print(contains("hello world", "world"));  // true
print(contains("hello world", "xyz"));    // false
```

### Loop over the characters

```donky
let s = "abc";
for c in s {
    print(c);
}
```

Prints:

```
a
b
c
```

### Comparing strings

```donky
print("apple" == "apple");   // true
print("apple" != "banana");  // true
print("apple" < "banana");   // true (alphabetical)
```

### Try it

Write a program that takes your name and prints "Hello, [name]!" — but in ALL CAPS. (Use `upper`.)

---

## 6. Making decisions: if / else

An `if` statement runs some code only when a condition is true.

```donky
let age = 15;

if age >= 18 {
    print("You can vote.");
} else {
    print("Not yet.");
}
```

Prints:

```
Not yet.
```

`>=` means "greater than or equal to." Here's the full family:

- `==` — equal to
- `!=` — not equal to
- `<` — less than
- `<=` — less than or equal to
- `>` — greater than
- `>=` — greater than or equal to

### Multiple conditions

Chain `else if` to test several things:

```donky
let score = 87;

if score >= 90 {
    print("A");
} else if score >= 80 {
    print("B");
} else if score >= 70 {
    print("C");
} else {
    print("F");
}
```

Prints:

```
B
```

Donky checks top to bottom. The first true one wins. **Important:** only one block runs.

### And / or / not

```donky
let age = 15;
let has_id = true;

if age >= 18 && has_id {      // AND: both must be true
    print("You can enter.");
}

if age < 18 || !has_id {      // OR (either), NOT (reverse)
    print("Stop.");
}
```

`&&` means **and**. `||` means **or**. `!` means **not**. `!has_id` is true when `has_id` is false.

### Try it

Write a program that reads a number and prints "positive", "negative", or "zero".

---

## 7. Repeating things: while and for

### `while` — repeat while something is true

```donky
let countdown = 3;

while countdown > 0 {
    print(countdown);
    countdown = countdown - 1;
}
print("Liftoff!");
```

Prints:

```
3
2
1
Liftoff!
```

A `while` loop checks its condition before each pass. When the condition becomes false, it stops. **Beware:** if the condition never becomes false, the loop never ends. Always make sure the body changes something that affects the condition.

### `for` — loop over a list

The most useful loop. It walks through each item of a list, string, or map:

```donky
for fruit in ["apple", "banana", "cherry"] {
    print(fruit);
}
```

Prints:

```
apple
banana
cherry
```

You don't have to count anything. `for` handles it. This is why `for` is nicer than `while` most of the time.

### Stopping early: `break`

```donky
for n in [1, 2, 3, 4, 5] {
    if n == 3 {
        break;
    }
    print(n);
}
```

Prints:

```
1
2
```

`break` jumps out of the loop immediately, ignoring the rest.

### Skipping one: `continue`

```donky
for n in [1, 2, 3, 4, 5] {
    if n % 2 == 0 {
        continue;
    }
    print(n);
}
```

Prints:

```
1
3
5
```

`continue` says "skip the rest of this pass, go to the next one." So even numbers get skipped.

### Try it

Write a program that prints the numbers 1 through 100, but replaces multiples of 3 with "Fizz", multiples of 5 with "Buzz", and multiples of both with "FizzBuzz." (This is the classic FizzBuzz puzzle.)

---

## 8. Lists (arrays)

An **array** is a list of values in order, written with square brackets.

```donky
let colors = ["red", "green", "blue"];
print(colors);       // [red, green, blue]
print(len(colors));  // 3
print(colors[0]);    // red
print(colors[2]);    // blue
```

Same as with strings, positions start at 0. `colors[0]` is the first item.

### Changing an item

```donky
let nums = [10, 20, 30];
nums[1] = 99;
print(nums);   // [10, 99, 30]
```

### Adding and removing

```donky
let a = [1, 2, 3];

push(a, 4);      // add to the end
print(a);        // [1, 2, 3, 4]

let last = pop(a);   // remove and return the last item
print(last);         // 4
print(a);            // [1, 2, 3]
```

### Looping over a list

```donky
let scores = [90, 85, 92, 88];

for s in scores {
    print(s);
}

// Compute the total:
let total = 0;
for s in scores {
    total = total + s;
}
print(total);              // 355
print(total / len(scores)); // 88.75
```

### Sorting

```donky
let nums = [3, 1, 4, 1, 5, 9, 2, 6];
sort(nums);
print(nums);   // [1, 1, 2, 3, 4, 5, 6, 9]

let words = ["charlie", "alice", "bob"];
sort(words);
print(words);   // [alice, bob, charlie]
```

`sort` puts things in ascending order — numbers from small to large, strings alphabetically. **Important:** `sort` modifies the array in place. It doesn't return a new one.

You can't sort a mixed-type array like `[1, "two"]`. All elements have to be the same kind.

### Try it

Write a program that stores ten of your favorite numbers in a list, sorts them, and prints the smallest and largest.

---

## 9. Dictionaries (maps)

A **map** (sometimes called a dictionary) stores values under labels, called **keys**. You write it with curly braces:

```donky
let ages = {"alice": 30, "bob": 25, "carol": 40};
print(ages["alice"]);   // 30
print(ages["carol"]);   // 40
```

The key (`"alice"`) looks up the value (`30`). This is useful when you want to look things up by name, not by position.

### Adding and updating

```donky
let ages = {};
ages["dave"] = 22;
ages["eve"]  = 28;
print(ages);   // {dave: 22, eve: 28}

ages["dave"] = 23;   // overwrite
print(ages["dave"]); // 23
```

### Checking if a key exists

```donky
let ages = {"alice": 30};
print(contains(ages, "alice"));   // true
print(contains(ages, "bob"));     // false
```

**Danger:** if you ask for a key that doesn't exist, Donky will crash. Check `contains` first if you're not sure:

```donky
if contains(ages, "bob") {
    print(ages["bob"]);
} else {
    print("no age for bob");
}
```

### Getting all the keys

```donky
let ages = {"alice": 30, "bob": 25};
print(keys(ages));     // [alice, bob]
print(len(ages));      // 2
```

### Looping over a map

`for` over a map gives you each key:

```donky
let scores = {"math": 92, "science": 88, "english": 95};

for subject in scores {
    print(subject + ": " + str(scores[subject]));
}
```

Prints:

```
math: 92
science: 88
english: 95
```

### A real use: counting

```donky
let words = ["apple", "banana", "apple", "cherry", "banana", "apple"];
let counts = {};

for w in words {
    if contains(counts, w) {
        counts[w] = counts[w] + 1;
    } else {
        counts[w] = 1;
    }
}

print(counts);   // {apple: 3, banana: 2, cherry: 1}
```

That pattern — check if the key exists, increment or set to 1 — is used constantly. Remember it.

### Try it

Write a program that reads a sentence, splits it into words with `split(sentence, " ")`, and counts how many times each word appears.

---

## 10. Functions — reusable code

A **function** is a named chunk of code you can call whenever you want. It can take **arguments** (inputs) and give back a **return value** (output).

```donky
fn add(a, b) -> num {
    return a + b;
}

print(add(2, 3));   // 5
print(add(10, 20)); // 30
```

Let's break it down:

- `fn add(a, b)` — define a function named `add`, taking two arguments called `a` and `b`.
- `-> num` — it will return a number.
- `{ return a + b; }` — the body. `return` gives a value back to whoever called it.

### No return value

If a function doesn't need to give anything back, say `-> void`:

```donky
fn greet(name) -> void {
    print("Hello, " + name + "!");
}

greet("Ada");   // Hello, Ada!
```

### Different return types

```donky
fn is_even(n) -> bool {
    return n % 2 == 0;
}

fn shout(s) -> str {
    return upper(s) + "!";
}

fn sum(arr) -> num {
    let total = 0;
    for x in arr {
        total = total + x;
    }
    return total;
}
```

### Recursion — a function that calls itself

```donky
fn factorial(n) -> num {
    if n < 2 {
        return 1;
    }
    return n * factorial(n - 1);
}

print(factorial(5));   // 120 (5 × 4 × 3 × 2 × 1)
```

This is one of the most powerful ideas in programming. A function that calls itself, with a `if` that says when to stop, can solve things that would be painful to write as loops.

### Try it

Write a function `is_palindrome(s) -> bool` that returns true if the string reads the same forward and backward. ("racecar" → true, "hello" → false.)

---

## 11. When things go wrong: try / catch

Sometimes a program does something impossible — divides by zero, reads a file that isn't there. Normally that crashes the program. `try` / `catch` lets you handle it gracefully.

```donky
try {
    let x = 10 / 0;
    print("This never runs.");
} catch e {
    print("Something went wrong: " + e);
}
```

Prints:

```
Something went wrong: division by zero
```

The `try` block runs normally. If anything inside it fails, execution jumps to the `catch` block, with `e` set to the error message.

### Throwing your own errors

You can raise errors on purpose with `throw`:

```donky
fn divide(a, b) -> num {
    if b == 0 {
        throw "cannot divide by zero";
    }
    return a / b;
}

try {
    print(divide(10, 2));
    print(divide(5, 0));
} catch e {
    print("oops: " + e);
}
```

Prints:

```
5.0
oops: cannot divide by zero
```

### Reading a file that might not exist

```donky
if file_exists("data.txt") {
    let text = read_file("data.txt");
    print(text);
} else {
    print("No data file yet.");
}
```

`file_exists` is the safest check. You can also use `try` / `catch` on `read_file` directly:

```donky
try {
    let text = read_file("data.txt");
    print(text);
} catch e {
    print("Couldn't read the file.");
}
```

### Try it

Write a program that asks for two numbers and divides them. If the user enters zero for the second number, print a friendly message instead of crashing.

---

## 12. Talking to the user: input

`input("prompt")` pauses the program, shows the prompt, and waits for the user to type something and press Enter. Whatever they type comes back as a **string**.

```donky
let name = input("What's your name? ");
print("Hello, " + name + "!");
```

```
What's your name? Ada
Hello, Ada!
```

### Reading numbers

`input` always gives you a string, even if the user typed `42`. To turn the string into a number, use `num`:

```donky
let age_str = input("How old are you? ");
let age = num(age_str);
print("Next year you'll be " + str(age + 1));
```

### A complete guessing game

```donky
let secret = 42;
let guess = 0;

while guess != secret {
    guess = num(input("Guess a number: "));
    if guess < secret {
        print("Too low!");
    } else if guess > secret {
        print("Too high!");
    }
}
print("You got it!");
```

This is the pattern every interactive program uses: prompt, read, decide, repeat.

### Try it

Change the game so the secret number is random. (Donky doesn't have a random builtin yet — ask the user to think of the number, then have the computer guess by narrowing the range with too high / too low responses.)

---

## 13. Files

### Reading

```donky
let text = read_file("myfile.txt");
print(text);
```

`read_file` reads the whole file into a string. If the file doesn't exist, it crashes — so check first with `file_exists`, or wrap in try/catch.

### Writing

```donky
write_file("output.txt", "Hello, file!\n");
```

This **overwrites** the file. If it didn't exist, it creates it. If it did, it replaces its contents.

### Existence check

```donky
if file_exists("data.txt") {
    print("File exists!");
} else {
    print("No file.");
}
```

### Working with lines

```donky
let text = read_file("poem.txt");
let lines = split(text, "\n");

for line in lines {
    print("> " + line);
}
```

Note `"\n"` — that's a **newline character**. In a string, `\n` means "go to a new line." So `split(text, "\n")` splits on newlines, giving you an array of lines.

### Path gotcha on Windows

Use **forward slashes** in file paths, like `"C:/Users/Ada/data.txt"`. Backslashes are special in Donky strings (they start escape sequences like `\n`).

### Try it

Write a program that appends a new line to a file each time it runs. (Hint: read the file if it exists, add your line, write it back.)

---

## 14. Standard library

Donky ships with five modules of helpers, written in Donky itself. You import them the same way as any file — the path is `lib/` at the repo root.

```donky
import "lib/list.donk";
import "lib/format.donk";
```

### `lib/list.donk` — working with arrays

Higher-order helpers. All take a function as an argument. You write those functions with `fn(...) { ... }` — anonymous functions, defined right in the call.

| Function | What it does |
|---|---|
| `map(arr, f)` | Apply `f` to each element, return a new array |
| `filter(arr, f)` | Keep elements where `f` returns true |
| `reduce(arr, f, init)` | Fold the array into one value |
| `sort_by(arr, f)` | Sort ascending by the result of `f`; stable, non-mutating |
| `reverse(arr)` | New array, reversed |
| `unique(arr)` | New array, duplicates removed, order preserved |
| `any(arr, f)` | True if any element satisfies `f` |
| `all(arr, f)` | True if every element satisfies `f` |
| `count(arr, f)` | How many elements satisfy `f` |

```donky
import "lib/list.donk";

let nums = [1, 2, 3, 4, 5];

print(map(nums, fn(x) -> num { return x * x; }));       // [1, 4, 9, 16, 25]
print(filter(nums, fn(x) -> bool { return x % 2 == 0; })); // [2, 4]
print(reduce(nums, fn(a, b) -> num { return a + b; }, 0)); // 15
print(reverse(nums));                                     // [5, 4, 3, 2, 1]
print(unique([1, 2, 1, 3, 2]));                           // [1, 2, 3]
```

**Trick:** `sort_by` returns ascending. For descending, negate a numeric key:
```donky
sort_by(items, fn(x) -> num { return -x.score; })
```

### `lib/format.donk` — formatting output

| Function | What it does |
|---|---|
| `format_num(x, places)` | Number → string with `places` decimals (truncates) |
| `repeat(s, n)` | String `s` repeated `n` times |
| `pad_left(s, width, ch)` | Pad `s` on the left with `ch` until `width` wide |
| `pad_right(s, width, ch)` | Pad on the right |

```donky
import "lib/format.donk";

print(format_num(10 / 3, 2));       // "3.33"
print(format_num(-0.5, 3));         // "-0.500"
print(pad_left("42", 5, " "));      // "   42"
print(pad_left("42", 5, "0"));      // "00042"
print(repeat("=", 10));             // "=========="
```

**Note:** `format_num` truncates rather than rounds. `format_num(3.999, 2)` gives `"3.99"`. If you need rounding, that's a future feature.

### `lib/strings.donk` — string helpers

| Function | What it does |
|---|---|
| `starts_with(s, prefix)` | True if `s` begins with `prefix` |
| `ends_with(s, suffix)` | True if `s` ends with `suffix` |
| `slice(s, start, end)` | Substring from `start` (inclusive) to `end` (exclusive) |
| `index_of(s, needle)` | Position of first `needle` in `s`, or -1 |

```donky
import "lib/strings.donk";

print(starts_with("hello", "he"));  // true
print(ends_with("hello", "lo"));    // true
print(slice("hello", 1, 4));        // "ell"
print(index_of("hello", "ll"));     // 2
print(index_of("hello", "zz"));     // -1
```

### `lib/csv.donk` — reading and writing CSV

| Function | What it does |
|---|---|
| `parse_line(line)` | Split one CSV line into an array of strings |
| `format_line(fields)` | Join an array of strings into a CSV line |
| `parse_table(text)` | Parse a whole CSV file body into an array of rows |
| `format_table(rows)` | Format an array of rows back into a CSV body |

```donky
import "lib/csv.donk";

let rows = parse_table(read_file("data.csv"));
for row in rows {
    print(row[0] + " has " + row[1] + " items");
}
```

**Limitation:** no quoted fields in v1. Values containing commas will be split incorrectly.

### `lib/math.donk` — numeric helpers

| Function | What it does |
|---|---|
| `min(a, b)` | The smaller of two numbers |
| `max(a, b)` | The larger |
| `abs(n)` | Absolute value |
| `pow(base, exp)` | Integer exponent (base^exp) |
| `sqrt(n)` | Square root (Newton's method); throws on negative |

```donky
import "lib/math.donk";

print(min(3, 7));       // 3
print(abs(-5));         // 5
print(pow(2, 10));      // 1024
print(sqrt(16));        // 4.0
```

### Combining modules

A real program often imports several:

```donky
import "lib/list.donk";
import "lib/format.donk";

let scores = [72, 95, 88, 60, 91];
let sorted = reverse(sort_by(scores, fn(x) -> num { return x; }));
for s in sorted {
    print(pad_left(str(s), 4, " "));
}
// Output:
//   95
//   91
//   88
//   72
//   60
```

### Writing your own library

Any `.donk` file can be imported. Put reusable functions in `lib/` (or anywhere), import from your program:

`lib/mystuff.donk`:
```donky
fn greet(name) -> str {
    return "Hello, " + name + "!";
}
```

`main.donk`:
```donky
import "lib/mystuff.donk";
print(greet("Ada"));   // Hello, Ada!
```

**Rules:** `import` must be at the top level. Paths are relative to the importing file. The same file imported twice is only loaded once. Give your functions unique names — there's no namespace isolation yet.

## 15. Splitting your code into files: import

When a program gets big, put helper functions in a separate file and import it.

Save `lib/math.donk`:

```donky
fn double(n) -> num {
    return n * 2;
}

fn square(n) -> num {
    return n * n;
}

fn clamp(n, lo, hi) -> num {
    if n < lo { return lo; }
    if n > hi { return hi; }
    return n;
}
```

Save `use_math.donk`:

```donky
import "lib/math.donk";

print(double(5));       // 10
print(square(3));       // 9
print(clamp(15, 0, 10)); // 10
```

Run `donky use_math.donk`. The functions from `lib/math.donk` are now available in your program, as if you'd typed them at the top.

### Rules

- `import` must be at the top level (not inside a function or `if` block).
- The path is relative to the file doing the import.
- Importing the same file twice is fine — Donky silently skips the second.
- Importing in a cycle (A imports B, B imports A) works — Donky handles it.
- There are no namespaces yet. If two files both define `helper`, the second one wins. Give your functions unique names.

### Try it

Make a `lib/strings.donk` with helper functions like `starts_with(s, prefix) -> bool` and `repeat(s, n) -> str`. Import it in a test program.

---

## 16. A complete program: a notes app

Here's a real, useful program that uses everything above. Save as `notes.donk`:

```donky
import "lib/format.donk";

let path = "notes.txt";
if len(args) > 0 {
    path = args[0];
}

fn load(p) -> array {
    if !file_exists(p) {
        return [];
    }
    let text = read_file(p);
    if len(text) == 0 {
        return [];
    }
    return split(text, "\n");
}

fn save(p, notes) -> void {
    write_file(p, join(notes, "\n"));
}

let notes = load(path);
print("Loaded " + str(len(notes)) + " note(s).");

while true {
    print("");
    print("=== Notes ===");
    print("1) add   2) list   3) delete   4) save   5) quit");
    let choice = input("choice: ");

    if choice == "1" {
        push(notes, input("note: "));
        print("added");
    } else if choice == "2" {
        if len(notes) == 0 {
            print("(empty)");
        } else {
            let i = 0;
            for n in notes {
                print("  " + str(i + 1) + ". " + n);
                i = i + 1;
            }
        }
    } else if choice == "3" {
        if len(notes) == 0 {
            print("nothing to delete");
        } else {
            let i = 0;
            for n in notes {
                print("  " + str(i + 1) + ". " + n);
                i = i + 1;
            }
            let n = num(input("delete #: "));
            let kept = [];
            let j = 1;
            for note in notes {
                if j != n {
                    push(kept, note);
                }
                j = j + 1;
            }
            notes = kept;
            print("deleted");
        }
    } else if choice == "4" {
        save(path, notes);
        print("saved");
    } else if choice == "5" {
        print("bye");
        break;
    }
}
```

Run it. Add notes. Save. Quit. Run it again. **Your notes are still there.** That's what a real program feels like.

---

## 17. Cheat sheet

Keep this handy.

### Comments
```donky
// anything after two slashes to end of line is a comment
```

### Values
```donky
42          // whole number
3.14        // decimal
"hello"     // string
true        // boolean
false       // boolean
[1, 2, 3]   // array
{"a": 1}    // map
```

### Variables
```donky
let x = 10;         // create
x = 20;             // change (must exist)
```

### Math
```donky
+  -  *  /  %       // usual
div                 // integer division (throws away remainder)
```

### Comparison
```donky
==  !=  <  <=  >  >=
```

### Logic
```donky
&&    // and
||    // or
!     // not
```

### Text
```donky
len(s)              // number of characters
s[0]                // one character (0-indexed)
s + t               // concatenate
upper(s)            // uppercase
lower(s)            // lowercase
trim(s)             // strip leading/trailing whitespace
split(s, sep)       // string -> array of strings
join(arr, sep)      // array of strings -> string
contains(s, sub)    // bool
replace(s, old, new) // string
```

### Arrays
```donky
arr[0]              // one element (0-indexed)
push(arr, x)        // add to end
pop(arr)            // remove and return last
len(arr)            // number of items
sort(arr)           // sort in place (ascending)
```

### Maps
```donky
m["key"]            // get value (crashes if missing)
m["key"] = v        // set value
contains(m, "key")  // true if key exists
keys(m)             // array of all keys
len(m)              // number of entries
```

### Type checking
```donky
type(x)             // "number" / "string" / "bool" / "array" / "map" / "function"
num(s)              // string -> number
str(x)              // anything -> string
```

### Files and I/O
```donky
input("prompt")     // read a line from the user (returns string)
args                // array of command-line arguments (strings)
read_file(path)     // whole file as string
write_file(path, s) // write string to file (overwrites)
file_exists(path)   // bool
```

### Statements
```donky
let x = expr;                    // declare
x = expr;                        // assign
print(expr);                     // display
if cond { ... } else { ... }     // branch
if cond { ... } else if cond2 { ... } else { ... }

while cond { ... }               // loop while true
for x in container { ... }       // loop over each element
break;                           // exit current loop
continue;                        // skip to next iteration of loop

try { ... } catch e { ... }      // error handling
throw "message";                 // raise an error

import "file.donk";              // include another file
```

### Functions
```donky
fn name(a, b) -> num {           // returns a number
    return a + b;
}

fn greet(name) -> void {         // returns nothing
    print("Hello, " + name);
}
```

Return types: `num`, `str`, `bool`, `array`, `map`, `any`, `void`.

---

## 18. Troubleshooting

**"parse error: expected ';'"**
You forgot a semicolon at the end of a statement. Check the line and column in the error — they point to where Donky got confused, usually right after where the `;` should be.

**"parse error: expected '{', got..."**
You probably wrote `if condition` without opening a block. Donky needs `{ }` around every `if`, `else`, `while`, `for`, and function body, even for a single statement.

**"undefined variable 'x'"**
You used `x` before declaring it with `let x = ...`. Check the spelling too — Donky is case-sensitive, so `X` and `x` are different.

**"assignment to undefined variable 'x'"**
You tried `x = 5;` without first doing `let x = ...;`. In Donky, `=` updates; `let` creates. To create: `let x = 5;`.

**"index N out of range"**
You asked for a position that doesn't exist. Arrays and strings start at 0, so `[1, 2, 3][3]` is an error (valid positions: 0, 1, 2).

**"key 'X' not in map"**
You tried to look up a map key that isn't there. Use `contains(m, "X")` first.

**"condition must be bool"**
Donky is strict — `if` conditions have to be `true` or `false`, not a number. If you want "any nonzero is true" behavior (like some languages), write `if x != 0 { ... }` explicitly.

**"'+' needs two numbers or two strings"**
You tried to add a number and a string. Convert first: `str(5) + " apples"`, not `5 + " apples"`.

**"input(): end of input"**
The user pressed Ctrl+D (or you're running non-interactively without providing input). Make sure you're running the program at a real terminal, not from a script that closes stdin.

**Nothing happens when I run**
Make sure the file has a `.donk` extension and you spelled it right. `donky myfile.donk`.

**"cannot read file"**
The path is wrong, or (on Windows) you used a backslash inside a string. Use forward slashes: `"C:/Users/you/file.txt"`.

---

## Where to go next

You now know all of Donky. To get better:

1. **Rewrite your favorite little tools in Donky.** A unit converter. A flashcard quiz. A log filter. The more you write, the more fluent you get.
2. **Read the examples folder.** Every file is a small program using one feature well.
3. **Look at the source.** `donky/lexer.py` is 250 readable lines. Reading how a language is built is a superpower.
4. **Write a library.** Put helper functions in `lib/` and `import` them. You'll invent things the language needs.

If you find something missing — a feature, a builtin, a clearer error message — that's not a bug in *you*, that's a bug in *Donky*. Read the source, find the place, change it, run the tests. **That's how languages grow.**

Welcome to programming.