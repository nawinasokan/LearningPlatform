"""JavaScript, React and System Design interview content."""


def Q(text, difficulty, easy, technical, interview):
    return {"text": text, "difficulty": difficulty,
            "answers": {"easy": easy.strip(), "technical": technical.strip(), "interview": interview.strip()}}


def T(title, slug, difficulty, order, minutes, description, definition, easy, technical, interview,
      questions, code=None, lang="javascript", analogy=None):
    content = {"definition": definition.strip(), "easy_explanation": easy.strip(),
               "technical_explanation": technical.strip(), "interview_answer": interview.strip()}
    if analogy:
        content["analogy"] = analogy.strip()
    if code:
        content["code_example"] = code.strip("\n")
        content["code_language"] = lang
    return {"title": title, "slug": slug, "difficulty": difficulty, "order_index": order,
            "estimated_minutes": minutes, "description": description, "content": content,
            "questions": questions}


JS_REACT = []
SYSTEM_DESIGN = []

# ---------------------------------------------------------------- JS: scope & closures
JS_REACT.append(T(
    "Scope, Hoisting and Closures", "js-scope-closures", "practical", 1, 30,
    "How var, let and const behave, what hoisting and the temporal dead zone really are, and how closures capture variables.",
    "A closure is a function bundled with a reference to the lexical environment in which it was created, so it can keep reading and writing those variables after the outer function has returned.",
    "Variables live in boxes that belong to a block or function. A function remembers which boxes were around when it was written, and keeps access to them even after the code that created the boxes has finished. That memory is a closure.",
    "Every execution context has an environment record. var is function-scoped and initialised to undefined at hoisting time. let and const are block-scoped and hoisted but left uninitialised until their declaration runs, which is the temporal dead zone (TDZ): reading them earlier throws ReferenceError. const forbids rebinding, not mutation of the object it points to. Function declarations are hoisted with their body; function expressions assigned to var only hoist the variable as undefined. Closures keep the whole outer environment alive, which is why they power module patterns, memoisation and event handlers, and also why they can leak memory when large objects stay referenced.",
    "A closure is a function plus its lexical environment. It lets a function keep private state, for example a counter, between calls. let/const are block scoped with a temporal dead zone, var is function scoped and hoisted as undefined. The classic pitfall is var in a loop sharing one binding across callbacks, which let fixes by creating a fresh binding per iteration.",
    [
        Q("What is the difference between var, let and const, and what is the temporal dead zone?", "beginner",
          "var is the old way to declare a variable and it ignores curly braces, so it leaks out of if-blocks and loops. let and const respect blocks. const also means you cannot point the name at a different value later. The temporal dead zone is the stretch between the start of a block and the line where a let or const is declared, where touching the name is an error. Think of a reserved table at a restaurant: the name is on it, but you cannot sit until the host seats you.",
          """var is function scoped, can be redeclared, and is hoisted and initialised to undefined. let and const are block scoped, cannot be redeclared in the same scope, and are hoisted into the TDZ: the binding exists from the start of the block but is uninitialised until the declaration is evaluated, so access throws ReferenceError. typeof is not safe inside the TDZ either. Top-level var and function declarations in scripts create properties on the global object; let/const do not.
```js
console.log(a); // undefined (var hoisted)
var a = 1;
try { console.log(b); } catch (e) { console.log(e.name); } // ReferenceError (TDZ)
let b = 2;
const o = { n: 1 }; o.n = 2;   // allowed: mutation
// o = {};                      // TypeError: assignment to constant
```""",
          """**Definition:** var is function-scoped and hoisted with value undefined; let and const are block-scoped and hoisted but unusable until their declaration runs, which is the temporal dead zone. const prevents rebinding, not mutation.

**How it works:** At the start of execution the engine creates bindings for every declaration in a scope. var bindings are initialised to undefined immediately. let/const bindings stay uninitialised, so any read before the declaration line throws a ReferenceError, which catches use-before-define bugs that var silently hides.

**Example:**
```js
console.log(x);        // undefined
var x = 1;
{
  // console.log(y);   // ReferenceError: TDZ
  let y = 2;
}
const user = { name: "a" };
user.name = "b";       // fine, the object is mutable
```

**Trade-offs and pitfalls:** Default to const, use let only when you reassign, avoid var. const does not make an object immutable; use Object.freeze (shallow) or immutable update patterns. A function declaration is hoisted with its body, but a function expression assigned to var is not callable before assignment.

**Follow-up: why does var in a for loop with setTimeout print the same number?** All callbacks share one function-scoped binding, which equals the final value when they run. let creates a new binding per iteration, so each callback sees its own value."""),
        Q("What is a closure and where would you use one in real code?", "practical",
          "A closure is a function that remembers the variables around it when it was created. Imagine writing a note and putting it in a backpack with the things it refers to: wherever the note goes, the backpack goes too. You use this to keep private data, like a counter that nobody else can change, or to give an event handler the specific item it belongs to.",
          """Each function object stores a [[Environment]] reference to the lexical environment where it was defined. When it is called, name lookups walk that chain outward. Because the reference is held, the outer variables are not garbage collected while the inner function is reachable. Uses: private state (module pattern), factories and currying, memoisation caches, debounce/throttle timers, React hooks (every render's callbacks close over that render's props and state), and partial application. The cost is memory retention: a closure in a long-lived listener can keep a large outer object alive.
```js
function makeCounter() {
  let n = 0;                       // private
  return { inc: () => ++n, get: () => n };
}
const c = makeCounter();
c.inc(); c.inc();
console.log(c.get()); // 2
```""",
          """**Definition:** A closure is a function together with the lexical environment it was created in, so it can access those outer variables even after the outer function has returned.

**How it works:** Functions capture a reference to their defining scope, not a copy of values. Lookups walk the scope chain, and the engine keeps captured variables alive as long as the function is reachable.

**Example:**
```js
function memoize(fn) {
  const cache = new Map();           // captured, private
  return (arg) => {
    if (!cache.has(arg)) cache.set(arg, fn(arg));
    return cache.get(arg);
  };
}
const square = memoize(x => x * x);
```

**Trade-offs and pitfalls:** Closures capture variables by reference, so later mutation is visible; this is the cause of the loop bug with var and of stale closures in React effects. They can retain large objects and cause memory leaks if listeners are never removed.

**Follow-up: how do closures relate to React hooks?** Each render creates new functions that close over that render's props and state, which is why an effect with an empty dependency array keeps seeing the initial values."""),
        Q("Explain hoisting. Why can you call a function declaration before it is defined but not a function expression or arrow function?", "practical",
          "Before running your code, JavaScript reads through it and sets up the names. Function declarations are set up completely, with their code, so you can call them early. With a function expression you wrote 'var greet = function...', only the name greet is set up early and it is empty until that line runs. So calling it early fails.",
          """Hoisting is the effect of the creation phase of an execution context: declarations are processed before code executes. Function declarations are instantiated with their function object at the top of the scope. var declarations are created and set to undefined, so var f = function(){} yields f === undefined until the assignment, and calling it throws TypeError: f is not a function. let/const/class declarations are hoisted into the TDZ and throw ReferenceError. Arrow functions are always expressions, so they follow the variable rules. Within blocks in strict mode, function declarations are block scoped.
```js
hello();                 // works
function hello() { console.log("hi"); }

try { bye(); } catch (e) { console.log(e.constructor.name); } // TypeError
var bye = function () {};

try { later(); } catch (e) { console.log(e.constructor.name); } // ReferenceError
const later = () => {};
```""",
          """**Definition:** Hoisting means declarations are registered in their scope before any code runs, but what is available at that point depends on the kind of declaration.

**How it works:** During the creation phase the engine allocates bindings. Function declarations are initialised with the full function. var is initialised to undefined. let, const and class are created but uninitialised (TDZ).

**Example:**
```js
console.log(typeof f1);  // "function"
console.log(typeof f2);  // "undefined"
function f1() {}
var f2 = function () {};
```
Calling f2() on the first line would throw TypeError because f2 is undefined at that time.

**Trade-offs and pitfalls:** Relying on hoisting hurts readability; declare before use and enable lint rules such as no-use-before-define. Do not declare functions inside blocks in sloppy mode because behaviour differs between engines and modes.

**Follow-up: is let hoisted?** Yes, the binding is created at scope entry, which is exactly why the TDZ exists and why a shadowing let in an inner block makes outer same-name reads throw rather than see the outer variable."""),
    ],
    code="""function makeCounter() {
  let count = 0;
  return { inc: () => ++count, value: () => count };
}
const c = makeCounter();
c.inc();
console.log(c.value()); // 1

for (var i = 0; i < 3; i++) setTimeout(() => console.log("var", i)); // 3 3 3
for (let j = 0; j < 3; j++) setTimeout(() => console.log("let", j)); // 0 1 2""",
    analogy="A closure is a backpack: the function carries the variables it needs wherever it goes."))

# ---------------------------------------------------------------- JS: this, prototypes, equality
JS_REACT.append(T(
    "this, Prototypes and Equality", "js-this-prototypes", "intermediate", 2, 35,
    "How this is determined, call/apply/bind, prototype-based inheritance and the rules behind == versus ===.",
    "this is a binding set at call time (except in arrow functions, which inherit it lexically); objects inherit through a prototype chain; === compares without coercion while == applies the abstract equality coercion algorithm.",
    "this means 'who is calling me'. Objects can borrow behaviour from another object they point to, called a prototype. Triple equals asks 'same type and same value?'; double equals first tries to convert them to the same type, which gives surprising answers.",
    "this resolution order: new binding (new Fn) > explicit (call/apply/bind) > implicit (obj.method()) > default (undefined in strict mode, globalThis otherwise). Arrow functions have no own this and capture the enclosing one; bind cannot override that. Every object has an internal [[Prototype]] (Object.getPrototypeOf); property reads walk the chain until found or null. Constructor functions and class syntax set the instance prototype to Fn.prototype; class is syntax sugar over this. Object.create(proto) creates an object with a given prototype. == coerces: null == undefined is true and equals nothing else, objects are converted with ToPrimitive, and NaN != NaN (use Number.isNaN or Object.is). === never coerces.",
    "this is decided by how a function is called, not where it is defined, except arrow functions. Inheritance is via the prototype chain; class is sugar. Use === by default; the one idiomatic use of == is x == null to match null or undefined.",
    [
        Q("How is the value of this determined in JavaScript, and what do call, apply and bind do?", "intermediate",
          "this is a hidden argument that points at 'the object doing the thing right now'. If you write dog.bark(), this inside bark is dog. If you pull bark out and call it alone, it loses its dog. call and apply let you call a function and choose what this is; bind makes a new copy of the function with this locked in. Arrow functions do not have their own this, they use the one from the surrounding code.",
          """Rules in priority order: 1) new: this is the new object. 2) Explicit: fn.call(thisArg, a, b), fn.apply(thisArg, [a, b]) invoke immediately; fn.bind(thisArg, ...partial) returns a bound function (its this cannot be changed again, though new still wins). 3) Implicit: obj.fn() uses obj. 4) Default: undefined in strict mode or modules/classes, globalThis in sloppy mode. Arrow functions resolve this lexically from the enclosing scope. Detached methods (const f = obj.m; f()) lose this; common in callbacks.
```js
const user = { name: "Ana", hi() { return this.name; } };
const f = user.hi;
// f() -> undefined in strict mode (this is undefined -> TypeError on property access)
console.log(f.call({ name: "Bo" })); // "Bo"
const bound = user.hi.bind(user);
console.log(bound()); // "Ana"
```""",
          """**Definition:** this is a per-call binding determined by the call site, with arrow functions as the exception since they capture this lexically.

**How it works:** The engine checks, in order: constructor call with new, explicit binding with call/apply/bind, method call on an object, then the default (undefined in strict mode). call and apply invoke at once and differ only in argument passing (list vs array). bind returns a new function with this and optional leading arguments fixed.

**Example:**
```js
class Timer {
  constructor() { this.n = 0; }
  start() { setInterval(() => { this.n++; }, 1000); } // arrow keeps this
}
const t = new Timer();
const { start } = t;     // start() now would lose this
```

**Trade-offs and pitfalls:** Passing obj.method as a callback loses this; fix with bind, an arrow wrapper or a class field arrow. Do not use arrow functions as object methods or constructors when you need dynamic this. Bound functions allocate a new function each time, which matters for React prop identity.

**Follow-up: can you re-bind a bound function?** No, calling bind again on a bound function does not change its original this."""),
        Q("Explain prototypal inheritance and how it relates to the class keyword.", "intermediate",
          "In JavaScript every object can point to another object as its 'parent', called its prototype. If you ask for something the object does not have, JavaScript looks at the parent, then the parent's parent, until it finds it or runs out. The class keyword is just a nicer way of writing the same parent-pointer setup. It is like asking a colleague a question, and they pass it up the chain if they do not know.",
          """Every object has [[Prototype]], read with Object.getPrototypeOf(o). Property lookup walks the chain and stops at null. Assignment writes to the object itself (shadowing), unless a setter exists on the chain. Functions have a .prototype property used as the [[Prototype]] of instances created with new. class Foo extends Bar sets Foo.prototype's prototype to Bar.prototype and Foo's own prototype to Bar (static inheritance); methods are non-enumerable on Foo.prototype; classes are not hoisted usable (TDZ) and must be called with new. Fields declared in the body become own properties per instance; #private fields are truly private.
```js
class Animal { speak() { return this.name + " makes a sound"; } constructor(n){ this.name=n; } }
class Dog extends Animal { speak() { return super.speak() + ": woof"; } }
const d = new Dog("Rex");
console.log(Object.getPrototypeOf(d) === Dog.prototype);               // true
console.log(Object.getPrototypeOf(Dog.prototype) === Animal.prototype); // true
console.log(d.hasOwnProperty("speak"));                                 // false
```""",
          """**Definition:** In JavaScript objects inherit directly from other objects via an internal [[Prototype]] link; the chain is searched on property reads.

**How it works:** obj.x checks obj, then Object.getPrototypeOf(obj), and so on until null. new Fn() creates an object whose prototype is Fn.prototype. class is syntactic sugar over constructor functions plus prototype wiring, with extras: strict mode, non-enumerable methods, super, private fields and the requirement to use new.

**Example:**
```js
const base = { greet() { return "hi " + this.name; } };
const child = Object.create(base);
child.name = "Zed";
console.log(child.greet());               // "hi Zed"
console.log(Object.hasOwn(child, "greet")); // false
```

**Trade-offs and pitfalls:** Putting mutable objects on a prototype shares them across instances. Deep chains slow lookups and complicate reasoning; prefer composition. Never reassign prototypes of live objects with Object.setPrototypeOf in hot code because it deoptimises. Use Object.hasOwn rather than for-in without a guard.

**Follow-up: what does __proto__ vs prototype mean?** prototype is a property on constructor functions; __proto__ (accessor for [[Prototype]]) is the actual link on every object, and prefer Object.getPrototypeOf."""),
        Q("What is the difference between == and ===, and when is each appropriate?", "beginner",
          "Triple equals checks that both the type and the value match, so 5 and '5' are different. Double equals first tries to turn both sides into the same type and then compares, so 5 == '5' is true. That conversion has odd rules, such as null being equal to undefined but nothing else, so most teams just use triple equals everywhere.",
          """=== is strict equality: different types are never equal; same type compares by value for primitives and identity for objects; NaN === NaN is false; +0 === -0 is true. == is abstract equality: if types match it behaves like ===; null == undefined is true and null/undefined equal nothing else; number vs string converts the string to a number; booleans convert to numbers first; objects compared with primitives go through ToPrimitive (valueOf/toString). Examples: '' == 0 true, '0' == false true, [] == false true, [] == ![] true, but null == 0 false. Object.is fixes NaN and signed zero.
```js
console.log(5 == "5", 5 === "5");          // true false
console.log(null == undefined, null === undefined); // true false
console.log(NaN === NaN, Object.is(NaN, NaN));      // false true
console.log([] == false);                  // true (coercion)
```""",
          """**Definition:** === compares value and type with no coercion; == performs type coercion according to the abstract equality algorithm before comparing.

**How it works:** For == with different types, the engine converts operands: strings to numbers, booleans to numbers, objects to primitives, with the special rule that null and undefined are only loosely equal to each other. === returns false immediately for different types. Objects are compared by reference in both.

**Example:**
```js
0 == "";            // true
"1" == 1;           // true
null == undefined;  // true
null == 0;          // false
[1] == 1;           // true
{} === {};          // false (different references)
```

**Trade-offs and pitfalls:** == results are hard to remember and not transitive ('0' == 0, 0 == '' but '0' != ''). Use === by default and enforce with eqeqeq in ESLint, which usually allows the null exception. Use Number.isNaN or Object.is for NaN checks.

**Follow-up: when is == fine?** value == null is a concise, well-defined check for both null and undefined."""),
    ],
    code="""function Person(name) { this.name = name; }
Person.prototype.hi = function () { return "hi " + this.name; };
const p = new Person("Ana");
console.log(p.hi(), Object.getPrototypeOf(p) === Person.prototype); // hi Ana true

const hi = p.hi;
console.log(hi.call({ name: "Bo" })); // hi Bo
console.log(5 == "5", 5 === "5");     // true false"""))

# ---------------------------------------------------------------- JS: async
JS_REACT.append(T(
    "Event Loop, Promises and async/await", "js-async", "intermediate", 3, 40,
    "How the single-threaded event loop orders microtasks and macrotasks, and how promises and async/await sit on top of it.",
    "JavaScript runs one call stack; asynchronous callbacks are queued and the event loop runs them when the stack is empty, always draining the microtask queue (promise reactions) before the next macrotask (timers, I/O, UI events).",
    "JavaScript is like a single cashier. Slow jobs, like waiting for a delivery, are handed off and the cashier keeps serving. When a job finishes, it joins a queue. Small urgent follow-ups, like promise results, are served before the next ordinary customer.",
    "The call stack executes synchronous code. Web APIs/libuv handle timers, network and I/O and enqueue callbacks as macrotasks (task queue). Promise reactions (then/catch/finally), queueMicrotask and MutationObserver go to the microtask queue. After each macrotask, and after the stack empties, the engine drains all microtasks (including newly queued ones) before rendering or taking the next macrotask. A promise has states pending, fulfilled, rejected, and is immutable once settled. async functions return promises; await suspends the function and resumes it as a microtask. Promise.all fails fast, allSettled waits for all, race takes the first settle, any the first fulfil. Unhandled rejections are reported by the runtime. Await in a for loop is sequential; use Promise.all for concurrency.",
    "One thread, one stack. After each task the engine drains microtasks (promise callbacks) before the next macrotask (setTimeout, I/O). async/await is syntax over promises. Run independent awaits concurrently with Promise.all and always handle rejections.",
    [
        Q("Explain the JavaScript event loop, and the difference between microtasks and macrotasks.", "intermediate",
          "JavaScript can only do one thing at a time. When something slow is needed, like a timer or a network request, the browser does it in the background and puts the result in a waiting line. The event loop keeps checking: is the main work finished? If yes, take the next item from the line. There are two lines, and the short urgent one, used by promises, is always emptied first.",
          """Order of a loop turn: run one macrotask (script, timer callback, I/O callback, UI event) to completion; then drain the microtask queue fully (promise then-callbacks, queueMicrotask, await continuations); then the browser may render (requestAnimationFrame callbacks run just before paint); then the next macrotask. Consequences: a promise callback runs before a setTimeout(…, 0) scheduled earlier; microtasks that keep queueing microtasks can starve rendering and timers; long synchronous code blocks everything. In Node, process.nextTick runs before promise microtasks, and phases (timers, poll, check/setImmediate) exist.
```js
console.log("1 sync");
setTimeout(() => console.log("4 macrotask"), 0);
Promise.resolve().then(() => console.log("3 microtask"));
console.log("2 sync");
// 1 sync, 2 sync, 3 microtask, 4 macrotask
```""",
          """**Definition:** The event loop is the mechanism that lets single-threaded JavaScript handle asynchronous work by running queued callbacks when the call stack is empty.

**How it works:** Each iteration runs one macrotask to completion, then drains the entire microtask queue, then may render, then picks the next macrotask. Timers, I/O and UI events produce macrotasks; promise reactions and queueMicrotask produce microtasks, which therefore always run before the next timer.

**Example:**
```js
setTimeout(() => console.log("timeout"), 0);
Promise.resolve().then(() => console.log("promise"));
(async () => { console.log("a"); await null; console.log("b"); })();
console.log("sync");
// a, sync, promise, b, timeout
```

**Trade-offs and pitfalls:** Blocking the stack with heavy synchronous work freezes the UI; split work, use Web Workers, or yield with setTimeout/scheduler. Endless microtask chains starve the loop. setTimeout delays are minimums, not guarantees.

**Follow-up: where does await fit?** Code after await is scheduled as a microtask once the awaited promise settles."""),
        Q("How do Promises and async/await work, and how do you run async operations in parallel and handle errors?", "practical",
          "A promise is a receipt for a result that is not ready yet. It will end up either 'done with a value' or 'failed with an error'. async/await is a friendlier way to write code that waits on promises, so it reads from top to bottom. If you await several jobs one after another, they run one after another; start them together and wait for all to run them in parallel.",
          """A promise is pending until resolved or rejected; then(onFulfilled, onRejected) returns a new promise, enabling chains; a thrown error or rejection skips to the next catch. An async function always returns a promise; return value resolves it, a throw rejects it; await p pauses the function and resumes in a microtask. try/catch around await catches rejections. Sequential awaits add latencies; start promises first, then await Promise.all([...]). Promise.allSettled returns every outcome, race resolves with the first settled, any with the first fulfilled (AggregateError if all reject). An un-awaited promise that rejects causes unhandledrejection. Forgetting return in a then chain breaks sequencing.
```js
async function load(ids) {
  try {
    const users = await Promise.all(ids.map(id => fetch(`/api/u/${id}`).then(r => {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    })));
    return users;
  } catch (e) { console.error("failed", e); throw e; }
}
```""",
          """**Definition:** A Promise represents the eventual result of an async operation; async/await is syntax that lets you consume promises in a sequential style.

**How it works:** A promise settles once into fulfilled or rejected. then/catch callbacks run as microtasks. await unwraps a promise and suspends the async function; a rejection becomes a thrown exception at the await point, handled with try/catch.

**Example:**
```js
const [user, orders] = await Promise.all([
  fetchJson("/api/user"),
  fetchJson("/api/orders"),
]);
```
This takes the time of the slowest call, not the sum.

**Trade-offs and pitfalls:** await inside a for loop serialises calls; use Promise.all when independent, but limit concurrency for large arrays. Promise.all rejects on the first failure while the others keep running; use allSettled when you need every result. fetch does not reject on HTTP 4xx/5xx, so check response.ok. Always attach error handling to avoid unhandled rejections; consider AbortController for cancellation and timeouts.

**Follow-up: difference between Promise.race and Promise.any?** race settles with the first settled promise, even a rejection; any waits for the first fulfilment."""),
        Q("What is the output of a snippet mixing setTimeout, promises and async functions, and how do you reason about it?", "advanced",
          "You go line by line running the normal code first. Anything that says 'later' goes into a waiting line. Promise results and the code after an await go into the urgent line, and timers go into the normal line. When the normal code ends, you empty the urgent line, then handle one timer, then empty the urgent line again.",
          """Method: 1) execute synchronous code top to bottom, noting that an async function runs synchronously until its first await. 2) Each await/then schedules a microtask when the awaited promise is already resolved (await of a native promise takes one microtask tick). 3) After the stack empties, drain microtasks in FIFO order, including newly added ones. 4) Take the next macrotask, then drain microtasks again. Pitfall: setTimeout 0 callbacks are macrotasks and run after all pending microtasks, regardless of order of registration.
```js
console.log("A");
setTimeout(() => console.log("B"), 0);
Promise.resolve().then(() => console.log("C"));
(async () => {
  console.log("D");
  await Promise.resolve();
  console.log("E");
})();
console.log("F");
// A D F C E B
```""",
          """**Definition:** Predicting async output means simulating the call stack, microtask queue and macrotask queue in order.

**How it works:** Synchronous code runs first, including the body of an async function up to its first await. Continuations after await and promise callbacks go in the microtask queue in the order they were scheduled. Only when microtasks are empty does the loop run the next timer callback.

**Example:**
```js
console.log(1);
setTimeout(() => console.log(2), 0);
Promise.resolve().then(() => console.log(3)).then(() => console.log(4));
console.log(5);
// 1 5 3 4 2
```
Both then-callbacks run before the timer because chained microtasks are drained in the same checkpoint.

**Trade-offs and pitfalls:** Do not rely on subtle ordering between timers and promises in production; make dependencies explicit with await. Mixing process.nextTick, setImmediate and promises in Node has its own ordering. Returning a promise from a then adds extra ticks, which changes interleavings.

**Follow-up: what if a microtask schedules another microtask forever?** The loop never reaches the next macrotask or render, so the page freezes."""),
    ],
    code="""console.log("1 sync");
setTimeout(() => console.log("4 timeout"), 0);
Promise.resolve().then(() => console.log("3 microtask"));
console.log("2 sync");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const t = Date.now();
  await Promise.all([sleep(100), sleep(100)]);
  console.log("parallel ~100ms", Date.now() - t >= 100);
})();"""))

# ---------------------------------------------------------------- JS: utilities
JS_REACT.append(T(
    "Debounce, Copying and Array Methods", "js-utilities", "practical", 4, 30,
    "Classic coding-round utilities: debounce vs throttle, shallow vs deep copy, and map/filter/reduce.",
    "Debounce delays work until activity stops, throttle limits work to once per interval, copies are shallow (one level) or deep (all levels), and map/filter/reduce are non-mutating array transforms built from callbacks.",
    "Debounce is waiting until someone stops typing before searching. Throttle is allowing at most one search per second however fast they type. A shallow copy photocopies the cover of a folder; a deep copy photocopies every page inside.",
    "debounce(fn, wait) keeps a timer in a closure and resets it on every call; the call runs after wait ms of quiet (leading/trailing variants exist). throttle(fn, wait) runs at most once per window. Shallow copies: spread {...o}, [...a], Object.assign, Array.slice copy only the top level; nested objects remain shared. Deep copy: structuredClone (handles Date, Map, Set, cyclic refs; throws on functions, drops prototypes and class instances become plain objects), JSON.parse(JSON.stringify(x)) loses undefined, functions, Dates (become strings), Map/Set, and fails on cycles. map returns a same-length array, filter selects, reduce folds to one value with an accumulator and initial value; none mutate the source, but sort, splice, push, reverse do.",
    "Debounce waits for quiet, throttle caps the rate. Spread is a shallow copy; use structuredClone for a deep copy. map transforms, filter selects, reduce aggregates, and all return new values rather than mutating.",
    [
        Q("What is the difference between debounce and throttle? Implement debounce.", "practical",
          "Debounce means 'wait until the user stops'. If they keep typing, the timer keeps restarting, and the search only happens after a pause. Throttle means 'at most once every so often', for example while scrolling, run the handler once every 200 milliseconds no matter how many scroll events happen.",
          """Debounce: each call clears the pending timeout and sets a new one, so fn runs once, wait ms after the last call (trailing edge). Use for search-as-you-type, window resize end, autosave. Throttle: run immediately and ignore calls until the interval passes, optionally running a trailing call. Use for scroll, mousemove, drag, rate-limited API calls. Both rely on a closure over timer state, preserve this and arguments, and in React must be created once (useMemo/useRef) or the timer state is lost per render; cancel on unmount.
```js
function debounce(fn, wait) {
  let t;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), wait);
  };
}
function throttle(fn, wait) {
  let last = 0;
  return function (...args) {
    const now = Date.now();
    if (now - last >= wait) { last = now; fn.apply(this, args); }
  };
}
```""",
          """**Definition:** Debounce postpones execution until a burst of calls has been quiet for a delay; throttle guarantees execution at most once per time window.

**How it works:** Both wrap a function and hold state in a closure. Debounce stores a timer id and resets it on each call. Throttle stores the timestamp (or a flag) of the last execution and skips calls inside the window.

**Example:**
```js
function debounce(fn, wait) {
  let timer;
  const debounced = (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
  debounced.cancel = () => clearTimeout(timer);
  return debounced;
}
const onSearch = debounce((q) => console.log("search", q), 300);
```

**Trade-offs and pitfalls:** Debounce adds latency equal to the wait and may never fire during continuous input unless a maxWait is added; throttle may drop the final value unless a trailing call is included. In React, wrap the debounced function in useMemo or useRef so each render does not create a new timer, and cancel it in the effect cleanup. Prefer AbortController to cancel stale requests as well.

**Follow-up: which one for a search box, which for infinite scroll?** Debounce for the search box; throttle (or IntersectionObserver) for scroll."""),
        Q("What is the difference between a shallow copy and a deep copy, and how do you deep-clone an object in modern JavaScript?", "practical",
          "A shallow copy makes a new outer object, but anything inside it, like a nested object, is still the same one shared with the original. Change the inner thing in the copy and the original changes too. A deep copy duplicates everything all the way down so they are fully independent.",
          """Shallow: {...o}, Object.assign({}, o), [...a], a.slice() copy own enumerable properties one level; nested references are shared. Deep: structuredClone(value) (browsers, Node 17+) uses the structured clone algorithm: supports Date, RegExp, Map, Set, ArrayBuffer, typed arrays, Error and cyclic references; throws DataCloneError for functions and DOM nodes; discards prototypes (class instances become plain objects) and getters. JSON round trip drops undefined/functions/symbols, converts Date to string, NaN/Infinity to null, Map/Set to {} and throws on cycles. For immutable state updates, copy only the path you change rather than deep cloning everything.
```js
const a = { n: 1, inner: { x: 1 }, d: new Date() };
const s = { ...a };
s.inner.x = 99;
console.log(a.inner.x);          // 99 (shared)
const deep = structuredClone(a);
deep.inner.x = 5;
console.log(a.inner.x);          // 99 (independent)
```""",
          """**Definition:** A shallow copy duplicates only the top-level container so nested objects remain shared references; a deep copy recursively duplicates every nested value.

**How it works:** Spread and Object.assign copy property values; for objects those values are references. structuredClone walks the object graph, tracking visited nodes so cycles work, and builds a new graph.

**Example:**
```js
const state = { user: { name: "A", tags: ["x"] } };
const next = { ...state, user: { ...state.user, tags: [...state.user.tags, "y"] } };
console.log(state.user.tags.length, next.user.tags.length); // 1 2
```

**Trade-offs and pitfalls:** Deep cloning is O(size of graph) and often unnecessary; in React state updates copy only the changed path so unchanged references stay equal for memoisation. JSON.parse(JSON.stringify()) silently corrupts Dates, undefined, Map, Set and throws on cycles. structuredClone cannot clone functions or class prototypes. Libraries such as lodash cloneDeep handle more edge cases at a cost.

**Follow-up: does Object.freeze make an object immutable?** Only shallowly; nested objects stay mutable unless frozen recursively."""),
        Q("Explain map, filter and reduce, and use reduce to group an array of objects by a key.", "beginner",
          "map goes through a list and makes a new list by changing every item. filter makes a new list keeping only the items that pass a test. reduce walks through the list while carrying a running result, such as a total, and gives you one final value. None of them change the original list.",
          """map(cb) returns an array of the same length with cb(item, index, array) results. filter(cb) keeps items for which cb is truthy. reduce(cb, initial) calls cb(acc, item, index, array) and returns the final acc; always pass an initial value, otherwise an empty array throws TypeError and the first element is used as the accumulator. They are chainable and non-mutating, but callbacks must not mutate the source. Complexity is O(n) per pass; chaining makes multiple passes. forEach returns nothing; for early exit use some/every/find or a for...of loop. Object.groupBy (ES2024) also exists.
```js
const items = [{ t: "a", n: 1 }, { t: "b", n: 2 }, { t: "a", n: 3 }];
const grouped = items.reduce((acc, it) => {
  (acc[it.t] ||= []).push(it.n);
  return acc;
}, {});
console.log(grouped); // { a: [1, 3], b: [2] }
```""",
          """**Definition:** map transforms each element, filter keeps elements that satisfy a predicate, reduce folds an array into a single accumulated value; all return new values without mutating the input.

**How it works:** Each iterates the array calling your callback. map collects return values, filter collects items whose callback is truthy, reduce threads an accumulator through every call and returns the last one.

**Example:**
```js
const orders = [{ price: 10, paid: true }, { price: 5, paid: false }, { price: 7, paid: true }];
const total = orders.filter(o => o.paid).map(o => o.price).reduce((s, p) => s + p, 0);
console.log(total); // 17
```

**Trade-offs and pitfalls:** Omitting reduce's initial value breaks on empty arrays and mixes types. Chaining creates intermediate arrays; for huge data use a single reduce or a for loop. Mutating the accumulator is acceptable inside reduce when it is your own fresh object, but spreading the accumulator on every step is O(n squared). map with an async callback returns promises; wrap with Promise.all.

**Follow-up: difference between map and forEach?** map returns a new array and is for transformation; forEach is for side effects and returns undefined."""),
    ],
    code="""function debounce(fn, wait) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
}
const log = debounce((x) => console.log("called with", x), 50);
log(1); log(2); log(3); // only "called with 3"

const a = { inner: { x: 1 } };
const shallow = { ...a };
const deep = structuredClone(a);
shallow.inner.x = 2;
console.log(a.inner.x, deep.inner.x); // 2 1"""))

# ---------------------------------------------------------------- JS: ES6, modules, DOM, fetch
JS_REACT.append(T(
    "ES6+, Modules, Events and Fetch", "js-es6-dom-network", "practical", 5, 35,
    "Modern syntax, ES modules vs CommonJS, event delegation, and the browser rules behind fetch and CORS.",
    "ES6+ added block scoping, arrow functions, destructuring, spread/rest, template literals, classes, modules, Map/Set, optional chaining and more; in the browser, events bubble for delegation and cross-origin requests are governed by CORS.",
    "Modern JavaScript gives shorter, safer ways to write common things. Events in a page travel upward like a message passed up a chain of command, so one manager can handle messages for all employees. CORS is the browser asking another website, 'do you allow this site to read your answers?'",
    "Destructuring/spread/rest, default parameters, optional chaining (?.), nullish coalescing (??, which unlike || keeps 0 and ''), template literals, Symbol, Map/Set/WeakMap, iterators and generators, Proxy. ES modules (import/export) are static, asynchronous, strict, live bindings, singletons per URL, tree-shakeable; CommonJS (require/module.exports) is synchronous and dynamic with copied values. Events: capture phase down, target, bubble phase up; stopPropagation, preventDefault, event.target vs currentTarget. Delegation attaches one listener to a parent and uses event.target.closest(selector). CORS: browsers enforce same-origin policy; servers opt in with Access-Control-Allow-Origin; non-simple requests trigger an OPTIONS preflight; credentials need an exact origin plus Access-Control-Allow-Credentials. fetch only rejects on network failure, so check response.ok.",
    "Know destructuring, spread, ?. and ??, and ES modules with live bindings. Delegation uses bubbling with one parent listener. CORS is enforced by the browser and configured on the server, never fixed by the client.",
    [
        Q("Which ES6+ features do you use most, and what are the practical differences between spread/rest, destructuring, ?? and ||?", "beginner",
          "Destructuring pulls values out of objects or arrays into variables in one line. Spread copies or merges things into a new array or object, and rest gathers leftovers. Optional chaining safely reads something that might not exist. Nullish coalescing gives a default only when a value is missing, while || also replaces valid values like 0 or an empty string.",
          """Destructuring: const { a, b: renamed = 1, ...others } = obj; const [x, , z] = arr. Spread in calls and literals: f(...args), [...a, ...b], { ...o, k: v } (later keys win, shallow). Rest collects remaining items in params or patterns. Optional chaining a?.b?.[0]?.() short-circuits to undefined on null/undefined. ?? returns the right side only for null/undefined; || for any falsy value (0, '', false, NaN). ??= and ||= are logical assignments. Template literals support multi-line and expressions; default params evaluate at call time; arrow functions have lexical this and no arguments object.
```js
const cfg = { retries: 0, name: "" };
console.log(cfg.retries || 3);   // 3  (bug: 0 is valid)
console.log(cfg.retries ?? 3);   // 0
const { retries, ...rest } = cfg;
const merged = { ...rest, retries: 5 };
console.log(merged.user?.id);    // undefined, no throw
```""",
          """**Definition:** These are ES2015+ syntax features that make data access and copying more concise and safer: destructuring, spread/rest, optional chaining and nullish coalescing.

**How it works:** Destructuring binds names from a pattern. Spread expands iterables or own enumerable properties; rest collects remaining ones. ?. stops evaluation and yields undefined when the left side is null or undefined. ?? falls back only on null or undefined.

**Example:**
```js
function connect({ host = "localhost", port = 5432, ...opts } = {}) {
  return { url: `${host}:${port}`, opts };
}
const timeout = options.timeout ?? 30;   // keeps 0
const city = user?.address?.city;        // safe deep read
```

**Trade-offs and pitfalls:** Spread is a shallow copy and later properties overwrite earlier ones. Using || for defaults wrongly overrides 0, '' and false. Excessive optional chaining can hide data-shape bugs. Destructuring a null or undefined value throws, so give a default like = {}.

**Follow-up: difference between arrow functions and regular functions?** Arrows have no own this, arguments or prototype and cannot be used with new."""),
        Q("What is the difference between ES modules and CommonJS, and what are live bindings and tree shaking?", "intermediate",
          "Both are ways to split code into files and share pieces between them. CommonJS, used in older Node code, loads files while the program runs and hands you copies. ES modules are the modern standard: imports are known before the code runs, so tools can drop unused code, and an import always shows the current value from the exporting file.",
          """CommonJS: require() is synchronous, dynamic (can be called conditionally), returns module.exports, which is a snapshot reference, cached per resolved filename; this at top-level is exports. ES modules: static import/export declarations parsed before execution, enabling static analysis and tree shaking (dead export elimination by bundlers); loaded asynchronously, evaluated once (singleton), always strict, top-level await allowed, imports are read-only live bindings to the exporter's variable, circular imports work via bindings (TDZ applies). Dynamic import() returns a promise and enables code splitting. In Node, .mjs or "type": "module" selects ESM; interop between them has caveats. Side-effect imports and CJS modules defeat tree shaking; mark packages with sideEffects: false.
```js
// counter.js
export let count = 0;
export function inc() { count++; }
// main.js
import { count, inc } from "./counter.js";
inc();
console.log(count); // 1  (live binding; CJS would have copied 0)
const { heavy } = await import("./heavy.js"); // lazy load
```""",
          """**Definition:** CommonJS is Node's original synchronous require/module.exports system; ES modules are the standard static import/export system with live bindings, supported by browsers and bundlers.

**How it works:** Because ESM import declarations are static, the engine and bundlers build the dependency graph before running code, can eliminate unused exports (tree shaking), and fetch modules in parallel. Imported names are live read-only views of the exporter's bindings, while require returns the exports object as it was at call time.

**Example:**
```js
// math.js
export const add = (a, b) => a + b;
export const unused = () => {};
// app.js
import { add } from "./math.js";   // 'unused' can be dropped from the bundle
button.onclick = async () => {
  const { chart } = await import("./chart.js"); // split point
};
```

**Trade-offs and pitfalls:** Mixing ESM and CJS needs care (default export interop, __dirname missing in ESM). Barrel files and side-effectful modules reduce tree shaking. Circular dependencies can expose uninitialised bindings.

**Follow-up: how does dynamic import() help performance?** It creates a separate chunk loaded on demand, shrinking the initial bundle."""),
        Q("What is event delegation and how do bubbling and capturing make it work?", "practical",
          "When you click a button inside a list, the click does not stay at the button, it travels up through the list and the rest of the page. Event delegation uses that: instead of giving every item its own listener, put one listener on the list and check which item was clicked. It is like one receptionist handling every visitor rather than hiring one per visitor.",
          """DOM events propagate in three phases: capture (window down to the target), target, then bubble (back up). addEventListener(type, fn, { capture, once, passive }) defaults to bubble. event.target is the originating element; event.currentTarget is the element the listener is attached to. Delegation: attach one listener to a stable ancestor, then match with event.target.closest(selector) and confirm ancestor.contains(match). Benefits: fewer listeners, works for dynamically added children, simpler cleanup. Limits: events that do not bubble (focus, blur, mouseenter; use focusin/focusout), stopPropagation breaks it, and handler logic runs for every event in the subtree.
```js
const list = document.querySelector("#todos");
list.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-action='delete']");
  if (!btn || !list.contains(btn)) return;
  btn.closest("li").remove();
});
```""",
          """**Definition:** Event delegation is handling events for many child elements with a single listener on a common ancestor, relying on event bubbling.

**How it works:** Events fire at the target and then bubble up through each ancestor. The parent's listener inspects event.target (using closest to cope with clicks on inner spans or icons) and decides what to do.

**Example:**
```js
document.querySelector("#menu").addEventListener("click", (e) => {
  const item = e.target.closest("[data-id]");
  if (item) openItem(item.dataset.id);
});
```
Items added later work automatically with no new listeners.

**Trade-offs and pitfalls:** Not every event bubbles (focus, blur, mouseenter, scroll on elements), so use focusin/focusout or capture. Calling stopPropagation in a child can silence delegated handlers. Heavy logic in a high-level listener runs for every event, so filter early. React uses delegation itself, attaching listeners at the root container.

**Follow-up: difference between target and currentTarget?** target is the element that triggered the event; currentTarget is the element whose listener is running."""),
        Q("What is CORS, why does a preflight request happen, and why does fetch not reject on a 404?", "intermediate",
          "Browsers stop a page from one website reading data from a different website unless that other site says it is allowed. That permission is called CORS. For riskier requests the browser first asks 'would you allow this?' with a small request called a preflight. As for fetch, a 404 is still a successful conversation with the server, so the promise only fails when the network itself fails.",
          """Same-origin policy blocks cross-origin reads (origin = scheme + host + port). CORS lets servers opt in via response headers: Access-Control-Allow-Origin (exact origin or *), Allow-Methods, Allow-Headers, Allow-Credentials, Max-Age, Expose-Headers. Simple requests (GET/HEAD/POST with safelisted headers and content types) are sent directly; others (PUT/DELETE, JSON content type, Authorization header) trigger an OPTIONS preflight with Origin, Access-Control-Request-Method and -Headers; the server must answer 2xx with matching Allow headers. With credentials: 'include', Allow-Origin cannot be * and Allow-Credentials: true is required. CORS protects users' browsers, not servers: curl ignores it and it is not authentication. fetch rejects only on network errors/aborts; HTTP errors resolve with response.ok === false.
```js
const res = await fetch("https://api.example.com/items", {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  body: JSON.stringify({ name: "x" }),
});
if (!res.ok) throw new Error(`HTTP ${res.status}`);
const data = await res.json();
```""",
          """**Definition:** CORS (Cross-Origin Resource Sharing) is a browser-enforced mechanism by which a server declares which other origins may read its responses.

**How it works:** For a non-simple cross-origin request the browser first sends an OPTIONS preflight asking whether the method and headers are allowed. If the response carries matching Access-Control-Allow-* headers, the browser sends the real request and exposes the response to JavaScript; otherwise it blocks it with a CORS error.

**Example:** A React app on https://app.example.com calling https://api.example.com with an Authorization header needs the API to return:
```
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
```

**Trade-offs and pitfalls:** Never reflect arbitrary origins with credentials enabled. A wildcard cannot be combined with cookies. CORS is not a server-side security control; the API still needs authentication. Preflights add a round trip, so set Access-Control-Max-Age. In development a proxy avoids CORS entirely. fetch does not reject on 4xx/5xx, so check response.ok and handle errors.

**Follow-up: the request actually reached the server but the browser blocked it, why?** CORS restricts reading the response, not sending simple requests, so state-changing requests still need CSRF protection."""),
    ],
    code="""const list = { addEventListener() {} }; // browser-only API shown conceptually below
// Delegation (browser):
// list.addEventListener("click", e => {
//   const btn = e.target.closest("button[data-id]");
//   if (btn) remove(btn.dataset.id);
// });

const cfg = { retries: 0 };
console.log(cfg.retries || 3, cfg.retries ?? 3); // 3 0
const { retries, ...rest } = { retries: 1, a: 2, b: 3 };
console.log(retries, rest); // 1 { a: 2, b: 3 }"""))

# ---------------------------------------------------------------- React: rendering
JS_REACT.append(T(
    "React Rendering Model", "react-rendering", "intermediate", 6, 40,
    "Virtual DOM and reconciliation, keys, props vs state, JSX and function components, and what causes re-renders.",
    "React renders components as functions of props and state into a tree of elements, diffs it against the previous tree (reconciliation), and commits only the minimal DOM changes; keys identify list items across renders.",
    "Think of React as an editor that compares your new draft with the last draft and only erases and rewrites the lines that changed. Props are settings handed in from outside; state is the component's own memory.",
    "JSX compiles to jsx()/createElement calls returning plain element objects. A render phase calls components (must be pure) to build a new element tree; reconciliation compares with the previous tree using two heuristics: elements of different types produce different subtrees (unmount and remount), and keys identify children among siblings. Then the commit phase applies DOM mutations and runs layout effects then effects. Props are read-only inputs from the parent; state is owned and updated via setters which schedule a re-render, are batched in React 18 everywhere, and are applied on the next render (snapshot semantics). A component re-renders when its state changes, its parent re-renders (even with same props, unless memoised), or a consumed context value changes. Re-render does not mean DOM update. Index keys cause state to attach to the wrong item when lists reorder. Fibers are the internal units enabling interruptible rendering.",
    "React re-renders a component when its state, a context it reads, or its parent changes, diffs the element trees, and commits minimal DOM updates. Keys must be stable, unique ids. Props flow down and are read-only; state is local and immutable-updated.",
    [
        Q("What is the virtual DOM, how does reconciliation work, and why do keys matter?", "intermediate",
          "The virtual DOM is a lightweight description of what the screen should look like, kept as plain JavaScript objects. When something changes, React builds a new description, compares it with the old one, and updates only the parts of the real page that differ. Keys are name tags on list items, so React can tell which item is which when the list is reordered instead of guessing by position.",
          """On each render React produces a tree of element objects. Reconciliation (the diff) is O(n) thanks to heuristics: different element types at the same position tear down the old subtree and build a new one (state is lost); same type updates props in place; children lists are matched by key (then by index if no key). Stable unique keys let React move existing instances, preserving their state and DOM nodes. Index keys are fine only for static lists; with reordering, insertion or deletion, state (such as input text) sticks to the position, not the item. Changing a key deliberately resets a component's state. The virtual DOM is not inherently faster than hand-tuned DOM code; its benefit is declarative UI with acceptable cost.
```jsx
{todos.map(t => <TodoItem key={t.id} todo={t} />)}   // stable id
// <TodoItem key={index} ... />  // wrong for reorderable lists
<Profile key={userId} userId={userId} />  // new key -> fresh state
```""",
          """**Definition:** The virtual DOM is React's in-memory tree of element objects; reconciliation diffs the new tree against the previous one to compute the minimal real DOM updates.

**How it works:** Render produces elements; React compares them level by level. Same type and key means update; different type means unmount and remount. For lists, keys match old and new children so items are moved rather than recreated.

**Example:**
```jsx
function List({ items }) {
  return <ul>{items.map(i => <li key={i.id}><input defaultValue={i.text} /></li>)}</ul>;
}
```
With key={i.id}, reordering items keeps each input's typed text attached to the right row; with index keys the text would stay in position.

**Trade-offs and pitfalls:** Keys must be unique among siblings and stable across renders; never use Math.random(). Index keys cause state and animation bugs on reorder. Defining a component inside another component creates a new type every render and remounts it. The diff is a heuristic and does not detect moved subtrees under different parents.

**Follow-up: is the virtual DOM why React is fast?** Not by itself; it makes declarative updates cheap enough. Performance still depends on avoiding unnecessary renders and expensive work."""),
        Q("What is the difference between props and state, and why must state be updated immutably?", "beginner",
          "Props are the information a parent hands to a child, and the child must not change them, like instructions on a form. State is a component's own memory that can change over time, like a counter. Updating state creates a fresh value instead of editing the old one, because React decides whether to redraw by checking if the value is actually a new one.",
          """Props: read-only inputs; changing them requires the parent to re-render with new values. State: data owned by the component, created with useState/useReducer; calling the setter schedules a re-render with the new value. React compares old and new state with Object.is; mutating an object or array in place keeps the same reference, so React may skip the update and memoised children (React.memo, useMemo, useEffect deps) see no change. Use new copies: spread, map/filter, toSpliced, or Immer. Updates based on previous state should use the functional form because state in a render is a snapshot; batched updates otherwise overwrite each other.
```jsx
const [todos, setTodos] = useState([]);
const add = (t) => setTodos(prev => [...prev, t]);          // new array
const toggle = (id) => setTodos(prev =>
  prev.map(x => x.id === id ? { ...x, done: !x.done } : x)); // copy changed item
// todos.push(t); setTodos(todos);   // bug: same reference
const [n, setN] = useState(0);
const inc3 = () => { setN(c => c + 1); setN(c => c + 1); setN(c => c + 1); }; // +3
```""",
          """**Definition:** Props are immutable inputs passed from parent to child; state is mutable-by-replacement data a component owns and that triggers re-renders when set.

**How it works:** A state setter schedules a render. React compares the new value to the old with Object.is and bails out if equal. State inside a render is a snapshot, so setN(n + 1) three times in one handler results in +1, whereas the updater form setN(c => c + 1) queues three transformations.

**Example:**
```jsx
function Cart() {
  const [items, setItems] = useState([]);
  const add = (p) => setItems(prev => [...prev, p]);
  const remove = (id) => setItems(prev => prev.filter(i => i.id !== id));
  return <Items items={items} onAdd={add} onRemove={remove} />;
}
```

**Trade-offs and pitfalls:** Mutating state breaks memoisation and may skip renders. Copying deeply nested state is verbose, so use Immer or flatten state. Do not copy props into state unless you need an editable draft; derive values during render instead. Do not store derived data in state.

**Follow-up: where should state live?** In the lowest common ancestor of the components that need it (lifting state up), moving to context or a store only when prop drilling becomes painful."""),
        Q("What causes a React component to re-render, and how do you prevent unnecessary re-renders?", "intermediate",
          "A component redraws when its own state changes, when its parent redraws, or when a shared value it reads, called context, changes. Redrawing is usually cheap and fine. If it becomes slow, you can tell React to skip children whose inputs did not change, or move the slow part so it is not affected by the change.",
          """Triggers: setState/dispatch with a changed value, parent re-render (children re-render by default regardless of props), context value change for all consumers, and external store updates (useSyncExternalStore). Not triggers: mutating a ref or local variable. Tools: React.memo (shallow prop comparison; fails if you pass new object/function props each render), useMemo/useCallback to stabilise references, moving state down (colocation), lifting content up via children prop so it is not re-created, splitting context, selectors in stores (Zustand), virtualising long lists, and the React Compiler (automatic memoisation). Measure first with React DevTools Profiler. A render is not a DOM update; React only commits differences.
```jsx
const Row = React.memo(function Row({ item, onSelect }) { /* ... */ });
function List({ items }) {
  const onSelect = useCallback((id) => console.log(id), []);  // stable
  return items.map(i => <Row key={i.id} item={i} onSelect={onSelect} />);
}
```""",
          """**Definition:** A component re-renders when its state changes, its parent renders, or a context it consumes changes; React then diffs and commits only actual DOM differences.

**How it works:** Rendering calls the component function again. By default this cascades to all children. React.memo wraps a component so it is skipped when props are shallow-equal. Stable props require stable references, hence useCallback and useMemo.

**Example:**
```jsx
function Page() {
  const [text, setText] = useState("");
  return (<>
    <input value={text} onChange={e => setText(e.target.value)} />
    <ExpensiveChart />   {/* re-renders every keystroke unless memoised or moved */}
  </>);
}
```
Fix by moving the input and its state into its own component, or wrapping the chart in React.memo.

**Trade-offs and pitfalls:** Memoisation costs comparisons and memory and can add bugs when dependencies are wrong. Inline objects, arrays and arrow functions as props defeat React.memo. Overusing context for fast-changing values re-renders every consumer. Profile first, optimise the proven bottleneck, prefer structural fixes over memo everywhere.

**Follow-up: does a re-render mean the DOM updates?** No. If the output matches, React performs no DOM mutation."""),
    ],
    code="""function TodoList({ todos, onToggle }) {
  return (
    <ul>
      {todos.map((t) => (
        <li key={t.id}>
          <label>
            <input type="checkbox" checked={t.done} onChange={() => onToggle(t.id)} />
            {t.text}
          </label>
        </li>
      ))}
    </ul>
  );
}""", lang="jsx"))

# ---------------------------------------------------------------- React: hooks core
JS_REACT.append(T(
    "useState, useEffect and useRef", "react-hooks-core", "intermediate", 7, 45,
    "State snapshots, effect dependencies and cleanup, stale closures, and refs.",
    "useState holds per-component state, useEffect synchronises a component with an external system after render using a dependency array and optional cleanup, and useRef stores a mutable value that persists across renders without causing one.",
    "useState is a notebook the component keeps between redraws. useEffect is a to-do item you hand to React: 'after you draw, do this, and undo it before doing it again'. useRef is a sticky note that survives redraws and changing it does not trigger a redraw.",
    "Each render is a snapshot: props, state and handlers close over that render's values. useState returns [value, setter]; setter with same value (Object.is) bails out; lazy initialiser useState(() => expensive()) runs once. useEffect(setup, deps) runs after paint; if deps change, React runs the previous cleanup, then setup. [] runs on mount and cleanup on unmount; omitted deps runs after every render. In development Strict Mode mounts, unmounts and remounts to expose missing cleanup. Stale closure: an effect or timer capturing an old value because deps are wrong; fix by listing deps, using functional updates, or storing the latest value in a ref. useRef returns {current}; use it for DOM nodes, timers, previous values, never for render output. useLayoutEffect runs synchronously before paint. Effects are for synchronisation, not for deriving state or handling events.",
    "Effects synchronise with outside systems; list every reactive value in deps and return a cleanup. Stale closures come from outdated captured values. Refs hold mutable values that do not trigger renders.",
    [
        Q("How does useEffect work, what are the dependency array rules, and why is cleanup important?", "intermediate",
          "useEffect lets you run code after the screen has been drawn, such as starting a subscription or fetching data. The list of dependencies tells React when to run it again: only when something in the list changed. The cleanup function is how you tidy up, like unsubscribing, before the effect runs again or the component disappears.",
          """Timing: effects run after the browser paints (useLayoutEffect before paint). Dependencies are compared with Object.is. [] runs once after mount; no array runs after every render; [a, b] runs when a or b change. Before re-running, and on unmount, React calls the previous cleanup with the previous values. Every reactive value used inside (props, state, functions defined in the component) must be in deps; eslint-plugin-react-hooks enforces it. Objects/functions created in render are new each time, so move them inside the effect or memoise. Strict Mode in development runs setup, cleanup, setup to surface bugs. Cleanup is needed for subscriptions, timers, listeners, and abort of in-flight requests.
```jsx
useEffect(() => {
  const ctrl = new AbortController();
  fetch(`/api/users/${id}`, { signal: ctrl.signal })
    .then(r => r.json()).then(setUser)
    .catch(e => { if (e.name !== "AbortError") setError(e); });
  return () => ctrl.abort();      // cleanup on id change/unmount
}, [id]);
```""",
          """**Definition:** useEffect runs side effects after render to synchronise a component with something outside React, re-running when its dependencies change and cleaning up before each re-run and on unmount.

**How it works:** After commit, React compares each dependency with the previous render using Object.is. If any changed, it calls the old cleanup then the new setup. Effects capture the values of the render they belong to.

**Example:**
```jsx
useEffect(() => {
  const onResize = () => setWidth(window.innerWidth);
  window.addEventListener("resize", onResize);
  return () => window.removeEventListener("resize", onResize);
}, []);
```

**Trade-offs and pitfalls:** Missing deps cause stale data; suppressing the lint rule hides bugs. Putting an object or function created during render in deps re-runs the effect every render. Setting state unconditionally in an effect with no deps loops infinitely. Race conditions in fetching need abort or an ignore flag. Do not use effects to compute derived values or respond to clicks; do that in render or event handlers. For data fetching prefer a library such as React Query.

**Follow-up: why does my effect run twice in development?** Strict Mode deliberately mounts, unmounts and remounts to check your cleanup is correct; it does not happen in production."""),
        Q("What is a stale closure in React, and how do you fix it?", "advanced",
          "Every time a component draws, its functions remember the values from that particular draw. If a timer or listener was created in an earlier draw, it keeps using the old values and never sees newer ones. The fixes are to tell React to recreate it when the value changes, to update state in a way that does not need the old value, or to keep the latest value in a ref.",
          """Because each render has its own props/state, callbacks created in it close over those values. An effect with [] deps captures the first render's values forever, so setInterval(() => setCount(count + 1)) increments only to 1. Fixes: (1) correct deps so the effect re-subscribes; (2) functional updates setCount(c => c + 1), which need no captured value; (3) a ref updated each render (latestRef.current = value) read inside the long-lived callback; (4) useReducer, whose dispatch is stable; (5) React's useEffectEvent (experimental/stable in newer releases) for non-reactive reads inside effects. Choose based on whether re-subscribing is cheap.
```jsx
function Counter() {
  const [count, setCount] = useState(0);
  const countRef = useRef(count);
  countRef.current = count;
  useEffect(() => {
    const id = setInterval(() => {
      setCount(c => c + 1);                 // fix 2
      console.log("latest:", countRef.current); // fix 3
    }, 1000);
    return () => clearInterval(id);
  }, []);
  return <p>{count}</p>;
}
```""",
          """**Definition:** A stale closure is a function that captured state or props from an earlier render and keeps using those outdated values.

**How it works:** React renders are snapshots; closures inside a render see that render's values. Long-lived callbacks (intervals, listeners, effects with incomplete deps) are not recreated, so they keep reading the old snapshot.

**Example:**
```jsx
useEffect(() => {
  const id = setInterval(() => setCount(count + 1), 1000); // stale: count is 0
  return () => clearInterval(id);
}, []);
// fix: setCount(c => c + 1)
```

**Trade-offs and pitfalls:** Adding the value to deps is correct but re-creates the timer each tick; the functional updater avoids that when you only need the previous state. A ref escapes reactivity, so use it only for reading the latest value in callbacks, not for rendering. Disabling exhaustive-deps lint is the root cause of most stale bugs.

**Follow-up: why does an alert in a click handler show an old value after quick updates?** The handler closed over the render in which it was created, which is intended snapshot behaviour."""),
        Q("What is useRef used for, and how does it differ from useState?", "beginner",
          "useRef gives you a box that keeps its contents between redraws. Unlike state, putting something new in the box does not make React redraw the screen. People use it to grab a real page element like an input to focus it, or to remember things like a timer id.",
          """useRef(initial) returns a stable object { current }. The identity is the same every render; mutating .current is synchronous and does not schedule a render. Use cases: DOM access via the ref attribute (inputRef.current.focus()), storing timer or subscription ids, the previous value of a prop, an 'is mounted' or latest-callback holder, and instance-like variables. Do not read or write refs during rendering except for lazy initialisation, since that makes rendering impure. useState triggers a re-render and its value is a snapshot per render. forwardRef (or ref as a prop in React 19) exposes a child's DOM node; useImperativeHandle limits what is exposed.
```jsx
function SearchBox() {
  const inputRef = useRef(null);
  const prev = useRef();
  const [q, setQ] = useState("");
  useEffect(() => { prev.current = q; });
  return (<>
    <input ref={inputRef} value={q} onChange={e => setQ(e.target.value)} />
    <button onClick={() => inputRef.current.focus()}>Focus</button>
  </>);
}
```""",
          """**Definition:** useRef returns a persistent mutable container ({ current }) whose changes do not trigger re-renders.

**How it works:** React keeps the same ref object across renders. Setting current is a plain mutation. When passed to a host element's ref attribute, React assigns the DOM node to current at commit and null on unmount.

**Example:**
```jsx
function Video({ src }) {
  const ref = useRef(null);
  return (<>
    <video ref={ref} src={src} />
    <button onClick={() => ref.current.play()}>Play</button>
  </>);
}
```

**Trade-offs and pitfalls:** Anything displayed should be state, not a ref, because ref changes will not update the UI. Reading ref.current during render can show stale or inconsistent values under concurrent rendering. Prefer declarative props over imperative DOM calls; reserve refs for focus, scroll, measurement and media control.

**Follow-up: how do you access a child component's DOM node?** Pass the ref as a prop (React 19) or use forwardRef, optionally restricting methods with useImperativeHandle."""),
    ],
    code="""function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return <time>{now.toLocaleTimeString()}</time>;
}""", lang="jsx"))

# Map curated topics to the subject slug consumed by the seed script.
TOPICS = {"js-react": JS_REACT}
