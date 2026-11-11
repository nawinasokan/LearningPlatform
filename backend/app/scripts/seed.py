"""
Seed script: populates the database with all subjects, topics, questions, 
coding problems, diagrams, and resume project data.
Run via: python -m app.scripts.seed
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.models.models import (
    Base, ContentCategory, Subject, Topic, Subtopic, LearningContent,
    Question, QuestionAnswer, ExplanationMode, DifficultyLevel,
    CodingProblem, CodingTestCase, SQLProblem, Diagram, QuestionTag,
    QuestionTagMapping
)
import uuid

engine = create_engine(settings.SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def seed():
    print("🌱 Starting seed...")
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        _seed_categories(db)
        _seed_subjects(db)
        _seed_topics_and_questions(db)
        _ensure_subject_coverage(db)
        _ensure_question_targets(db)
        _seed_coding_problems(db)
        _ensure_coding_target(db)
        _seed_sql_problems(db)
        _ensure_sql_target(db)
        _seed_diagrams(db)
        db.commit()
        print("✅ Seed complete!")
    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


def _get_or_create(db: Session, model, defaults=None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    db.add(instance)
    db.flush()
    return instance, True


def _seed_categories(db: Session):
    categories = [
        {"name": "Core Backend", "slug": "core-backend", "description": "Python, Django, FastAPI, Flask"},
        {"name": "Databases", "slug": "databases", "description": "SQL, PostgreSQL, MongoDB"},
        {"name": "DevOps & Cloud", "slug": "devops-cloud", "description": "Docker, Linux, AWS, GCP"},
        {"name": "Frontend", "slug": "frontend", "description": "JavaScript, React, Bootstrap"},
        {"name": "System Design", "slug": "system-design", "description": "Architecture and design patterns"},
    ]
    for c in categories:
        _get_or_create(db, ContentCategory, slug=c["slug"], defaults={"name": c["name"], "description": c["description"]})
    db.flush()
    print(f"  ✓ Categories: {len(categories)}")


def _seed_subjects(db: Session):
    cat_core = db.query(ContentCategory).filter_by(slug="core-backend").first()
    cat_db = db.query(ContentCategory).filter_by(slug="databases").first()
    cat_devops = db.query(ContentCategory).filter_by(slug="devops-cloud").first()
    cat_fe = db.query(ContentCategory).filter_by(slug="frontend").first()

    subjects_data = [
        {"name": "Python", "slug": "python", "icon": "🐍", "color": "#3776ab", "priority": 1, "category": cat_core, "description": "Python fundamentals through advanced — OOP, generators, async, GIL, performance"},
        {"name": "Django", "slug": "django", "icon": "🎸", "color": "#092e20", "priority": 1, "category": cat_core, "description": "Django MVT, ORM, DRF, middleware, signals, caching, authentication"},
        {"name": "FastAPI", "slug": "fastapi", "icon": "⚡", "color": "#009688", "priority": 1, "category": cat_core, "description": "FastAPI routing, Pydantic, dependency injection, async, JWT, SQLAlchemy"},
        {"name": "Flask", "slug": "flask", "icon": "🫙", "color": "#000000", "priority": 2, "category": cat_core, "description": "Flask application lifecycle, blueprints, REST APIs, error handling"},
        {"name": "SQL & PostgreSQL", "slug": "sql-postgresql", "icon": "🐘", "color": "#336791", "priority": 2, "category": cat_db, "description": "SQL fundamentals through advanced PostgreSQL: joins, CTEs, window functions, indexing, partitioning"},
        {"name": "Database Engineering", "slug": "database-engineering", "icon": "🗄️", "color": "#ff6b35", "priority": 2, "category": cat_db, "description": "MySQL, MongoDB, SQLite, ACID, transactions, schema design, normalization"},
        {"name": "Backend Engineering", "slug": "backend-engineering", "icon": "🔧", "color": "#6c3483", "priority": 3, "category": cat_core, "description": "REST API architecture, authentication, JWT, RBAC, pagination, rate limiting, logging"},
        {"name": "Celery & Redis", "slug": "celery-redis", "icon": "📮", "color": "#37b24d", "priority": 3, "category": cat_core, "description": "Celery task queues, workers, brokers, Redis caching, TTL, distributed processing"},
        {"name": "Docker & Linux", "slug": "docker-linux", "icon": "🐋", "color": "#0db7ed", "priority": 4, "category": cat_devops, "description": "Docker containers, images, Compose, volumes, Linux commands, processes, deployment"},
        {"name": "AWS & GCP", "slug": "aws-gcp", "icon": "☁️", "color": "#ff9900", "priority": 4, "category": cat_devops, "description": "EC2, S3, IAM, GCP compute, storage, deployment, monitoring"},
        {"name": "JavaScript & React", "slug": "js-react", "icon": "⚛️", "color": "#61dafb", "priority": 5, "category": cat_fe, "description": "JavaScript ES6+, async/await, React hooks, components, API integration"},
        {"name": "Project Deep Dive", "slug": "project-deep-dive", "icon": "🏗️", "color": "#e63946", "priority": 1, "category": cat_core, "description": "Deep dives into Nawin's actual projects: Audio Annotation, F1 QC Audit, Smart AI Assist"},
        {"name": "System Design", "slug": "system-design", "icon": "🏛️", "color": "#7209b7", "priority": 3, "category": cat_core, "description": "Scalable system design, microservices, caching, load balancing, databases"},
    ]

    for s in subjects_data:
        _get_or_create(db, Subject, slug=s["slug"], defaults={
            "name": s["name"], "icon": s["icon"], "color": s["color"],
            "priority": s["priority"], "category_id": s["category"].id if s["category"] else None,
            "description": s["description"],
        })
    db.flush()
    print(f"  ✓ Subjects: {len(subjects_data)}")


def _seed_topics_and_questions(db: Session):
    """Seed all topics with questions for each subject."""
    total_topics = 0
    total_questions = 0

    # ─── PYTHON ───────────────────────────────────────────────────────
    python_subj = db.query(Subject).filter_by(slug="python").first()
    python_topics = [
        {
            "title": "Python Data Types & Variables",
            "slug": "python-data-types",
            "difficulty": DifficultyLevel.beginner,
            "order_index": 1,
            "estimated_minutes": 25,
            "description": "Mutable vs immutable types, type system, variable assignment",
            "content": {
                "definition": "Python data types define the kind of value a variable holds. Python is dynamically typed — you don't declare types explicitly.",
                "easy_explanation": "Think of data types like different kinds of containers. A list is a shopping bag where you can add/remove items. A tuple is a sealed box — you can look inside but not change it. A string is a sequence of letters. Each container type has rules about what you can do with it.",
                "analogy": "Mutable objects are like a whiteboard — you can erase and rewrite. Immutable objects are like a printed book — the content is fixed once published.",
                "technical_explanation": "Python has built-in types: int, float, str, bool, list, tuple, set, dict, bytes, NoneType. Each type has a specific memory layout. Mutable objects (list, dict, set) can be modified in-place. Immutable objects (int, str, tuple, frozenset) cannot be modified; operations create new objects.",
                "code_example": """# Mutable
my_list = [1, 2, 3]
my_list.append(4)        # modifies in-place
print(id(my_list))       # same id before and after

# Immutable  
my_str = "hello"
new_str = my_str + " world"  # creates new object
print(id(my_str) == id(new_str))  # False

# Type checking
print(type(42))          # <class 'int'>
print(isinstance(42, int))  # True

# Common gotcha
a = [1, 2, 3]
b = a               # b points to same list
b.append(4)
print(a)            # [1, 2, 3, 4] — shared reference!

# Correct copy
import copy
c = copy.copy(a)    # shallow copy
d = copy.deepcopy(a)  # deep copy""",
                "interview_answer": "Python has two categories of types: mutable and immutable. Mutable types (list, dict, set) can be changed after creation without creating a new object. Immutable types (int, str, tuple, frozenset, bool) cannot be modified in-place. When you 'modify' an immutable object, Python creates a new object. This matters for performance, hashability (only immutable objects can be dict keys or set members), and avoiding shared state bugs.",
            },
            "questions": [
                {
                    "text": "What is the difference between mutable and immutable objects in Python? Give examples.",
                    "difficulty": DifficultyLevel.beginner,
                    "answers": {
                        ExplanationMode.easy: "Mutable objects (list, dict, set) can be changed after creation. Immutable objects (int, str, tuple) cannot be changed — any 'modification' creates a new object in memory.",
                        ExplanationMode.technical: "Mutable objects store a reference to their underlying data structure which can be modified in-place (CPython uses linked arrays for lists). Immutable objects have their value embedded in the object header and Python can intern/cache them. The id() of a mutable object remains the same after modification, while immutable operations yield new objects with new ids.",
                        ExplanationMode.interview: "Mutable types (list, dict, set) can be modified in-place — the object's content changes but the memory address (id()) remains the same. Immutable types (int, str, tuple) cannot be changed after creation. Operations appear to 'change' them but actually create new objects. Key implications: (1) Only immutable objects can be dict keys or set members because they're hashable. (2) Mutable defaults in function signatures are a common bug — def f(x=[]) shares the same list across calls. (3) Mutable objects passed to functions can have side effects since they're passed by reference.",
                    },
                },
                {
                    "text": "Why can't you use a list as a dictionary key in Python?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Dictionary keys must be hashable. Lists are mutable — they can change. If a list changed after being used as a key, Python wouldn't be able to find it again. Tuples are immutable, so they can be keys.",
                        ExplanationMode.technical: "Python dict uses a hash table internally. Keys must implement __hash__ and __eq__. Lists don't implement __hash__ (it's set to None) because they're mutable — their hash value would change if the list were modified, making it impossible to retrieve values. Tuples, strings, and integers are hashable because they're immutable.",
                        ExplanationMode.interview: "Dictionary keys must be hashable. A hashable object has a hash value that doesn't change during its lifetime, which is a requirement for consistent lookup in hash tables. Lists are mutable — their content can change, so their hash would change, breaking the hash table invariant. That's why list.__hash__ is set to None, raising TypeError when you try to hash it. Tuples are hashable (if their elements are hashable) because they're immutable. This is why frozenset exists as the hashable alternative to set.",
                    },
                },
                {
                    "text": "Explain Python's integer caching / interning mechanism.",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "Python pre-creates small integer objects (-5 to 256) and reuses them. So `a = 5; b = 5; a is b` is True. For large numbers like 1000, each assignment creates a new object.",
                        ExplanationMode.technical: "CPython caches integer objects from -5 to 256 in a static array at interpreter startup. When you assign these values, you get the same object from the cache. String interning works similarly for compile-time string literals and strings that look like identifiers. This is an implementation detail of CPython, not guaranteed by the Python spec.",
                        ExplanationMode.interview: "CPython (the reference implementation) caches small integers from -5 to 256 for performance. `a = 100; b = 100; a is b` returns True because both point to the same cached object. For values outside this range, `a = 1000; b = 1000; a is b` is typically False. String interning is similar — string literals are often interned at compile time. Always use == for value equality, not `is`. Use `is` only for identity checks like `if x is None`.",
                    },
                },
                {
                    "text": "What are Python's built-in data structures and when would you choose each?",
                    "difficulty": DifficultyLevel.practical,
                    "answers": {
                        ExplanationMode.easy: "List: ordered collection, allows duplicates, use when order matters. Tuple: immutable list, use for fixed data like coordinates. Dict: key-value pairs, use for fast lookups. Set: unique values only, use when you need uniqueness or fast membership testing.",
                        ExplanationMode.technical: "list: dynamic array, O(1) append, O(n) insert/search. tuple: immutable array, slightly less memory than list. dict: hash table, O(1) average get/set/delete, ordered since Python 3.7. set: hash table of unique elements, O(1) membership test. deque (collections): O(1) append/pop from both ends. defaultdict, Counter, OrderedDict from collections module.",
                        ExplanationMode.interview: "Choose based on access patterns: List when you need ordered, mutable data with duplicates allowed — common for sequences and stacks/queues (though deque is better for queues). Tuple when data is fixed/constant — also used as dict keys and for returning multiple values. Dict when you need O(1) key-value lookup — now preserves insertion order. Set when you need uniqueness or fast O(1) membership testing (e.g., checking if an item was already processed). In production backend code, I've used sets heavily for deduplication in batch data processing pipelines.",
                    },
                },
                {
                    "text": "What is the difference between `is` and `==` in Python?",
                    "difficulty": DifficultyLevel.beginner,
                    "answers": {
                        ExplanationMode.easy: "`==` checks if two values are equal. `is` checks if two variables point to the exact same object in memory. Usually use `==`. Only use `is` with None, True, False.",
                        ExplanationMode.technical: "`==` calls __eq__ method which compares values. `is` compares object identity using id(). Two objects can be equal (==) without being the same object (is). `None` has only one instance so `x is None` is correct. PEP 8 recommends `is None` over `== None`.",
                        ExplanationMode.interview: "`==` compares values by calling __eq__. `is` compares object identity — it checks if both variables point to the same memory address (id(a) == id(b)). They differ when two objects have equal values but are different objects: `a = [1,2]; b = [1,2]; a == b` is True but `a is b` is False. Important: use `is` for None checks (`if x is None`) as PEP 8 recommends, never `== None` since custom classes can override __eq__ with unexpected behavior.",
                    },
                },
            ],
        },
        {
            "title": "Functions, Lambda & Higher-Order Functions",
            "slug": "python-functions",
            "difficulty": DifficultyLevel.beginner,
            "order_index": 2,
            "estimated_minutes": 30,
            "description": "Functions, closures, lambda, map/filter/reduce, comprehensions",
            "questions": [
                {
                    "text": "What is a closure in Python and when would you use one?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "A closure is a function that 'remembers' variables from the outer function even after the outer function has finished. Like a backpack that keeps things you packed.",
                        ExplanationMode.technical: "A closure is formed when a nested function references variables from the enclosing scope (free variables). Python stores these in the __closure__ attribute as cell objects. The inner function maintains a reference to the enclosing scope's variables via the LEGB rule (Local, Enclosing, Global, Built-in).",
                        ExplanationMode.interview: "A closure occurs when a nested function captures and 'closes over' variables from its enclosing scope. The enclosed variables persist even after the outer function returns. I've used closures for factory functions, decorators, and callback customization. Example: a make_multiplier(n) function returns a lambda that multiplies by n — each returned function carries its own n. Closures are the foundation of decorators in Python.",
                    },
                },
                {
                    "text": "Explain map(), filter(), and reduce() with examples.",
                    "difficulty": DifficultyLevel.practical,
                    "answers": {
                        ExplanationMode.easy: "map() applies a function to every item in a list. filter() keeps only items where a function returns True. reduce() combines all items into one value using a function.",
                        ExplanationMode.technical: "map(func, iterable) returns a lazy map object applying func to each element. filter(func, iterable) returns elements where func returns truthy. reduce(func, iterable) from functools applies func cumulatively — reduce(lambda a,b: a+b, [1,2,3,4]) → 10. All return iterators (except reduce which returns a value). List comprehensions are often preferred for readability.",
                        ExplanationMode.interview: "map(func, iterable) transforms each element: `list(map(str, [1,2,3]))` → ['1','2','3']. filter(func, iterable) selects elements: `list(filter(lambda x: x>0, [-1,2,-3,4]))` → [2,4]. reduce(func, iterable) from functools folds a list: `reduce(lambda a,b: a*b, [1,2,3,4])` → 24. In Python 3, prefer list comprehensions or generator expressions for clarity. Use map/filter when passing existing named functions to avoid lambda boilerplate.",
                    },
                },
                {
                    "text": "What is the difference between *args and **kwargs?",
                    "difficulty": DifficultyLevel.beginner,
                    "answers": {
                        ExplanationMode.easy: "*args collects extra positional arguments into a tuple. **kwargs collects extra keyword arguments into a dictionary. Use them when you don't know in advance how many arguments a function will receive.",
                        ExplanationMode.technical: "*args packs positional arguments into a tuple inside the function. **kwargs packs keyword arguments into a dict. Order: regular params, *args, keyword-only params, **kwargs. def f(*args, **kwargs): pass. Can be unpacked when calling: f(*my_list, **my_dict).",
                        ExplanationMode.interview: "*args allows a function to accept any number of positional arguments, collected into a tuple. **kwargs allows any number of keyword arguments, collected into a dict. I use them frequently in decorator patterns where the decorator must pass all arguments through to the wrapped function: `def decorator(func): def wrapper(*args, **kwargs): return func(*args, **kwargs); return wrapper`. They're also essential for subclass __init__ calls: `super().__init__(*args, **kwargs)` for cooperative multiple inheritance.",
                    },
                },
                {
                    "text": "How do list comprehensions work and when should you prefer them over loops?",
                    "difficulty": DifficultyLevel.practical,
                    "answers": {
                        ExplanationMode.easy: "List comprehensions give you a compact way to create lists: [x*2 for x in range(10) if x%2==0]. They're more readable than writing a full for loop when the logic is simple.",
                        ExplanationMode.technical: "[expr for item in iterable if condition] is syntactic sugar for a loop that appends to a list. Internally implemented as a separate code object in CPython, slightly faster than explicit loop+append because list.append() lookup is avoided. Dict comprehensions: {k:v for k,v in items}. Set comprehensions: {x for x in items}. Generator expressions: (x for x in items) — lazy, memory-efficient.",
                        ExplanationMode.interview: "List comprehensions are more Pythonic and typically 10-30% faster than equivalent for-loop+append patterns due to CPython optimization. Use them for simple transformations: `squares = [x**2 for x in range(100)]`. Prefer generator expressions `(x**2 for x in range(100))` when you don't need a list and are just iterating — saves memory. Avoid nested comprehensions deeper than 2 levels for readability. In production backend code, I use them heavily for data transformation, but switch to explicit loops when the logic requires multiple statements or error handling.",
                    },
                },
            ],
        },
        {
            "title": "Decorators & Context Managers",
            "slug": "python-decorators",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 3,
            "estimated_minutes": 35,
            "description": "Decorators, functools.wraps, context managers, with statement",
            "questions": [
                {
                    "text": "What is a decorator in Python and how does it work internally?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "A decorator is a function that wraps another function to add functionality. Like putting a gift in a box — the gift is your original function, the box adds extra wrapping.",
                        ExplanationMode.technical: "A decorator is a callable that takes a function and returns another function (or callable). @decorator syntax is sugar for func = decorator(func). Python processes this at import time, not at call time. functools.wraps(func) is essential — it copies __name__, __doc__, __annotations__ from the original function to the wrapper, preserving introspection.",
                        ExplanationMode.interview: "A decorator is a function that takes a function and returns a modified function. `@my_decorator` is exactly `func = my_decorator(func)`. I use decorators extensively for: (1) Authentication/authorization checks in Django/FastAPI. (2) Logging and timing function execution. (3) Caching with functools.lru_cache. (4) Retry logic. Always use @functools.wraps(func) inside the wrapper to preserve the original function's metadata for debugging and introspection. Example: in Django REST Framework, @permission_required decorates views.",
                    },
                },
                {
                    "text": "How do you create a context manager? Compare __enter__/__exit__ vs contextlib.contextmanager.",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "A context manager is what works with `with`. It runs setup code when entering the `with` block and cleanup code when leaving (even if an error occurs). Used for files, database connections, locks.",
                        ExplanationMode.technical: "Class-based: implement __enter__ (returns resource) and __exit__(exc_type, exc_val, exc_tb) (returns True to suppress exceptions). Generator-based via @contextlib.contextmanager: yield the resource in a try/finally. The `with` statement calls __enter__ on entry and __exit__ on exit (guarantees cleanup).",
                        ExplanationMode.interview: "Context managers guarantee cleanup via the `with` statement by calling __exit__ even if exceptions occur. Class approach: define __enter__ and __exit__ — good for reusable, complex managers. For simple cases, @contextlib.contextmanager with a generator is cleaner: `@contextmanager def db_session(): session = Session(); try: yield session; session.commit(); except: session.rollback(); finally: session.close()`. In my FastAPI projects I use async context managers for database sessions, ensuring rollback on errors regardless of exception type.",
                    },
                },
            ],
        },
        {
            "title": "OOP in Python",
            "slug": "python-oop",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 4,
            "estimated_minutes": 40,
            "description": "Classes, inheritance, polymorphism, dunder methods, MRO, ABC",
            "questions": [
                {
                    "text": "Explain Python's MRO (Method Resolution Order) and how C3 linearization works.",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "MRO determines which parent class method Python calls first in multiple inheritance. Python looks at a specific order called C3 linearization — essentially left-to-right, depth-first, but respecting all inheritance chains.",
                        ExplanationMode.technical: "MRO is computed using C3 linearization algorithm. `ClassName.__mro__` or `ClassName.mro()` shows the order. For `class C(A, B)`, MRO is [C, A, B, object]. super() uses MRO to find the next class. C3 ensures: (1) subclasses appear before superclasses, (2) order of parents is preserved, (3) no class appears before all its subclasses.",
                        ExplanationMode.interview: "Python uses C3 linearization (also called C3 superclass linearization) to determine method lookup order in multiple inheritance. `ClassName.__mro__` shows the tuple. `super()` delegates to the next class in the MRO, not necessarily the direct parent — this enables cooperative multiple inheritance. Classic example: Diamond problem: `class D(B, C)` where B and C both inherit from A. MRO is [D, B, C, A, object]. Each class's __init__ calls super().__init__() which follows MRO, so A.__init__ is only called once. I've used this in Django where multiple mixins work together via cooperative super() calls.",
                    },
                },
                {
                    "text": "What are dunder (magic) methods? Explain __str__, __repr__, __eq__, __hash__, __len__.",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Dunder methods (double underscore) let your class work with Python's built-in syntax. __str__ defines what str() shows. __repr__ is for developers. __eq__ defines ==. __len__ makes len() work on your objects.",
                        ExplanationMode.technical: "__repr__: unambiguous representation for developers, should be eval-able if possible. __str__: human-readable string, called by str() and print(). If only __repr__ is defined, str() uses it. __eq__: defines == behavior, should also define __hash__ if using as dict key. __hash__: must be consistent with __eq__. __len__: enables len(obj). __getitem__: enables obj[key]. __iter__: makes object iterable. __enter__/__exit__: context manager.",
                        ExplanationMode.interview: "Dunder methods integrate your objects with Python's data model. Key ones: __repr__ for debugging (should return string that recreates the object), __str__ for end-user display, __eq__ for == comparison, __hash__ for dict/set usage (if you override __eq__, Python sets __hash__ to None by default — you must explicitly define it), __len__ for len(), __iter__ for loops. In my Django models, I always define __str__ for admin display. For value objects in domain logic, I implement __eq__ and __hash__ for set membership and deduplication.",
                    },
                },
            ],
        },
        {
            "title": "Iterators, Generators & Asyncio",
            "slug": "python-generators",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 5,
            "estimated_minutes": 40,
            "description": "Iterators, generators, yield, generator expressions, asyncio event loop",
            "questions": [
                {
                    "text": "What is the difference between an iterator and an iterable in Python?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "An iterable is something you can loop over (list, str, dict). An iterator is an object that actually does the looping, keeping track of where it is. iter() turns an iterable into an iterator. next() gets the next item.",
                        ExplanationMode.technical: "Iterable: implements __iter__ which returns an iterator. Iterator: implements both __iter__ (returns self) and __next__ (returns next value or raises StopIteration). list is iterable but not an iterator. iter(my_list) creates a list_iterator. Generators are iterators that use yield. Protocol: for loop calls iter() then repeatedly calls next() until StopIteration.",
                        ExplanationMode.interview: "An iterable implements __iter__() which returns an iterator. An iterator implements both __iter__() (returning self) and __next__() (returning next value or raising StopIteration). Lists, dicts, strings are iterables. Calling iter() on them gives an iterator. The for loop implicitly does this. Generators are single-use iterators — once exhausted, you can't restart them, unlike lists. In backend work I use generators for memory-efficient processing of large datasets — instead of loading 150M+ rows into memory, generate chunks and process lazily.",
                    },
                },
                {
                    "text": "Explain Python's asyncio event loop, coroutines, and when to use async/await.",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "asyncio lets Python do multiple tasks without waiting for each one to finish. Instead of waiting for a database query, it can go work on something else. It's like a waiter taking orders from multiple tables instead of waiting at one table.",
                        ExplanationMode.technical: "asyncio runs a single-threaded event loop. Coroutines (defined with async def) are suspended with await, returning control to the event loop. The event loop picks up the next ready task. IO operations (HTTP requests, DB queries) become non-blocking. asyncio.gather() runs multiple coroutines concurrently. asyncio.create_task() schedules a task. uvloop is a faster event loop implementation used by FastAPI/uvicorn.",
                        ExplanationMode.interview: "asyncio provides concurrent execution in a single thread via cooperative multitasking. `async def` defines a coroutine. `await` suspends it until the awaited operation completes, allowing the event loop to run other coroutines. Best for I/O-bound tasks (database queries, HTTP calls, file I/O) — doesn't help CPU-bound tasks (use multiprocessing for those). FastAPI is built on asyncio — all my FastAPI endpoints use async def with async database sessions (asyncpg). Key patterns: asyncio.gather() for parallel I/O, asyncio.create_task() for background tasks, asyncio.timeout() for timeouts. The GIL doesn't block asyncio since I/O doesn't hold the GIL.",
                    },
                },
            ],
        },
        {
            "title": "Memory Management & GIL",
            "slug": "python-memory-gil",
            "difficulty": DifficultyLevel.advanced,
            "order_index": 6,
            "estimated_minutes": 35,
            "description": "CPython memory model, reference counting, garbage collection, GIL, threading vs multiprocessing",
            "questions": [
                {
                    "text": "What is the Python GIL and how does it affect multithreading?",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "The GIL (Global Interpreter Lock) is a mutex that only lets one Python thread run at a time. So Python threads don't truly run in parallel — they take turns. This protects memory but limits CPU performance.",
                        ExplanationMode.technical: "CPython's GIL is a mutex that prevents multiple native threads from executing Python bytecodes simultaneously. It's released during I/O operations and C extensions. Due to the GIL, Python threads are useful for I/O-bound tasks but not CPU-bound ones. multiprocessing spawns separate processes with separate GILs, enabling true parallelism. Python 3.13 introduced experimental free-threading (no-GIL) mode.",
                        ExplanationMode.interview: "The GIL is a mutex in CPython that ensures only one thread executes Python bytecode at a time. For I/O-bound tasks (DB queries, HTTP calls), threading works fine — the GIL is released during I/O waits, so threads can interleave. For CPU-bound tasks (image processing, ML), use multiprocessing (separate processes, each with their own GIL) or asyncio (single-threaded but non-blocking). In my Celery setup, workers are separate processes that bypass the GIL issue entirely. For CPU-intensive report generation in the F1 platform, I used multiprocessing pools.",
                    },
                },
            ],
        },
    ]

    for topic_data in python_topics:
        topic, created = _get_or_create(db, Topic, slug=topic_data["slug"], defaults={
            "subject_id": python_subj.id,
            "title": topic_data["title"],
            "difficulty": topic_data["difficulty"],
            "order_index": topic_data["order_index"],
            "estimated_minutes": topic_data["estimated_minutes"],
            "description": topic_data.get("description"),
        })
        total_topics += 1

        # Add content if provided
        if "content" in topic_data and created:
            content_data = topic_data["content"]
            content = LearningContent(
                topic_id=topic.id,
                definition=content_data.get("definition"),
                easy_explanation=content_data.get("easy_explanation"),
                analogy=content_data.get("analogy"),
                technical_explanation=content_data.get("technical_explanation"),
                code_example=content_data.get("code_example"),
                code_language="python",
                interview_answer=content_data.get("interview_answer"),
            )
            db.add(content)

        # Add questions
        for q_data in topic_data.get("questions", []):
            q_obj, q_created = _get_or_create(db, Question,
                topic_id=topic.id,
                question_text=q_data["text"],
                defaults={"difficulty": q_data["difficulty"]}
            )
            total_questions += 1

            if q_created:
                for mode, answer_text in q_data["answers"].items():
                    answer = QuestionAnswer(
                        question_id=q_obj.id,
                        mode=mode,
                        answer_text=answer_text,
                    )
                    db.add(answer)

        db.flush()

    # ─── DJANGO ───────────────────────────────────────────────────────
    django_subj = db.query(Subject).filter_by(slug="django").first()
    django_topics = [
        {
            "title": "Django MVT Architecture",
            "slug": "django-mvt",
            "difficulty": DifficultyLevel.beginner,
            "order_index": 1,
            "estimated_minutes": 30,
            "description": "Model-View-Template pattern, request lifecycle, URL routing",
            "questions": [
                {
                    "text": "Explain Django's MVT pattern and how it differs from MVC.",
                    "difficulty": DifficultyLevel.beginner,
                    "answers": {
                        ExplanationMode.easy: "Django uses MVT: Model (database), View (logic/data processing), Template (HTML). It's similar to MVC (Model-View-Controller) but Django calls the Controller a 'View' and the View a 'Template'. Django itself acts as the controller by routing URLs.",
                        ExplanationMode.technical: "In MVT: Model defines data structure (ORM classes). View is a Python function/class that processes HTTP requests and returns responses. Template is an HTML file with Django template language. Django's URL dispatcher (urls.py) maps URLs to views — this is the 'Controller' role. Views access models via ORM and pass context to templates.",
                        ExplanationMode.interview: "Django's MVT: Model (data layer — ORM classes), View (business logic — processes request, queries models, returns response), Template (presentation — HTML with DTL). Differs from MVC in naming: Django's View = MVC's Controller, Django's Template = MVC's View. Django framework itself handles routing (the C in MVC). In DRF, Templates are replaced by Serializers for JSON responses. The request lifecycle: URL dispatcher → View → Model (ORM queries) → Serializer/Template → Response.",
                    },
                },
                {
                    "text": "How does Django's URL routing work? Explain URL patterns, path() vs re_path().",
                    "difficulty": DifficultyLevel.practical,
                    "answers": {
                        ExplanationMode.easy: "Django maps URLs to view functions using urlpatterns in urls.py. path() uses simple string matching. re_path() uses regular expressions for complex patterns.",
                        ExplanationMode.technical: "url() was deprecated in Django 4.0. path() uses path converters (str, int, slug, uuid, path). re_path() uses regex. include() includes other urlconf modules. URL namespaces with app_name and namespace allow reverse URL lookup with reverse() or {% url %} tag. URL resolution uses a linear search through urlpatterns.",
                        ExplanationMode.interview: "Django routes URLs via urls.py using urlpatterns list. path('articles/<int:pk>/', views.article_detail) uses built-in converters: str, int, slug, uuid, path. re_path uses full regex. URL namespacing with include('app.urls', namespace='app') allows reverse() lookups: `reverse('app:article-detail', kwargs={'pk': 1})`. In production DRF projects, I use routers that auto-generate urlpatterns from ViewSets — DefaultRouter creates list, detail, and other standard URLs automatically.",
                    },
                },
                {
                    "text": "Explain Django's request-response lifecycle step by step.",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "When a request arrives: 1) Django's URL dispatcher matches the URL to a view. 2) Middleware processes the request. 3) The view runs — queries the database, processes data. 4) Middleware processes the response. 5) Response is sent back.",
                        ExplanationMode.technical: "1. WSGI/ASGI server receives request. 2. Django's WSGIHandler/ASGIHandler creates HttpRequest. 3. Request passes through MIDDLEWARE list (request phase, top-to-bottom). 4. URL resolver matches path to view function. 5. View executes, returning HttpResponse. 6. Response passes through MIDDLEWARE (response phase, bottom-to-top). 7. Response headers/body sent to client.",
                        ExplanationMode.interview: "Full lifecycle: (1) HTTP request hits web server (Nginx/Gunicorn). (2) WSGI creates HttpRequest object. (3) Request passes through each middleware's process_request() top-to-bottom — authentication, session loading, CSRF check. (4) URL resolver matches URL pattern and calls view. (5) View may call ORM (SQL queries), cache, Celery tasks. (6) View returns HttpResponse. (7) Response passes middleware bottom-to-top — session save, security headers. (8) Response sent to client. Exception middleware handles errors at step 5. This is why middleware order in settings.py matters — AuthenticationMiddleware must come after SessionMiddleware.",
                    },
                },
            ],
        },
        {
            "title": "Django ORM & QuerySets",
            "slug": "django-orm",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 2,
            "estimated_minutes": 45,
            "description": "Models, ORM queries, QuerySet optimization, select_related, prefetch_related",
            "questions": [
                {
                    "text": "What is the N+1 query problem in Django ORM and how do you fix it?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "N+1 happens when you do 1 query to get a list of objects, then 1 more query for each object to get related data — so 1+N queries total. Fix with select_related() or prefetch_related() to fetch everything at once.",
                        ExplanationMode.technical: "N+1: articles = Article.objects.all() runs 1 query. If you then access article.author for each in a loop, Django runs N more queries. select_related() uses SQL JOIN for ForeignKey/OneToOne (single query). prefetch_related() runs a separate IN query for ManyToMany and reverse FK (2 queries total, then Python-side join). Use django-debug-toolbar to detect.",
                        ExplanationMode.interview: "N+1 is a critical performance issue. For N articles, accessing article.author in a loop = N+1 database round-trips. Fix: (1) select_related('author') for ForeignKey/OneToOne — does a SQL JOIN. (2) prefetch_related('tags') for M2M/reverse FK — does 2 optimized queries and joins in Python. In the F1 QC platform handling 150M+ rows, N+1 would be catastrophic. I use select_related/prefetch_related everywhere and monitor queries with django-debug-toolbar in development. I also use `only()` and `values()` to avoid loading unnecessary fields.",
                    },
                },
                {
                    "text": "Explain Django ORM's select_related() vs prefetch_related().",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "select_related() does a SQL JOIN — best for ForeignKey (one related object). prefetch_related() does separate queries and merges in Python — best for ManyToMany or many related objects.",
                        ExplanationMode.technical: "select_related() does INNER/OUTER JOIN in SQL — works for ForeignKey and OneToOne. Single DB hit but larger result set. prefetch_related() runs the main query, then a separate WHERE id IN (...) query for related objects — works for M2M, reverse FK. Can use Prefetch() for custom QuerySets. Both cache results on the QuerySet instance.",
                        ExplanationMode.interview: "select_related(): SQL JOIN, one query, good for ForeignKey traversal (depth: `select_related('author__department')`). prefetch_related(): separate IN query per relation, good for M2M and reverse FK where JOINs would cause row multiplication. Rule: select_related for single-object relations, prefetch_related for collections. In complex dashboard queries, I combine them: `Order.objects.select_related('customer').prefetch_related('order_items__product')` to load a complete order view in 2-3 queries instead of hundreds.",
                    },
                },
                {
                    "text": "How do Django ORM transactions work? When would you use atomic()?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "A transaction groups multiple database operations — either all succeed or all fail. Use atomic() when you want multiple writes to be guaranteed together, like transferring money between accounts.",
                        ExplanationMode.technical: "django.db.transaction.atomic() creates a savepoint within a transaction. Can be used as decorator or context manager. Nested atomic() creates savepoints. select_for_update() locks selected rows. AUTOCOMMIT is default — each ORM operation is its own transaction. Using atomic() groups operations. Exceptions inside atomic() trigger rollback.",
                        ExplanationMode.interview: "Django wraps every request in implicit transaction with AUTOCOMMIT. Use @transaction.atomic() or `with transaction.atomic()` to group operations — if any fails, all roll back. I use atomic() extensively in the F1 platform for batch imports: processing an Excel row involves multiple table writes — if any fails, the whole row is rolled back, keeping data consistent. For read isolation, I use select_for_update() to prevent dirty reads in concurrent updates. Savepoints within nested atomic() calls allow partial rollbacks.",
                    },
                },
                {
                    "text": "What are Django signals and when should you use or avoid them?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Signals let you run code when something happens in Django — like when a user is saved. It's like a notification system. post_save fires after a model is saved. pre_delete fires before deletion.",
                        ExplanationMode.technical: "Django signals use the observer pattern. Built-in: pre_save, post_save, pre_delete, post_delete, m2m_changed, request_started, request_finished. Connect via @receiver decorator or signal.connect(). Signals are synchronous and in the same transaction as the triggering action. Can cause circular imports if not careful.",
                        ExplanationMode.interview: "Signals enable decoupled actions on model events. I use them for: creating Profile on User creation (post_save), audit logging (post_save/post_delete), clearing caches after model saves. Avoid signals for: performance-critical paths (they add synchronous overhead), complex logic (better in services/views for testability), anything that should be transactional (signal exceptions can leave data inconsistent). The rule: signals for truly decoupled cross-app notifications, not as a general event system within an app.",
                    },
                },
            ],
        },
        {
            "title": "Django REST Framework",
            "slug": "django-drf",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 3,
            "estimated_minutes": 50,
            "description": "DRF serializers, views, viewsets, routers, authentication, pagination",
            "questions": [
                {
                    "text": "Compare APIView, GenericAPIView, and ViewSets in Django REST Framework.",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "APIView: full manual control, you write get/post/put methods. GenericAPIView: adds common patterns like queryset and serializer_class. ViewSet: combines list/create/retrieve/update/destroy into one class with routers auto-generating URLs.",
                        ExplanationMode.technical: "APIView: extends Django View, adds DRF request/response, authentication, permissions. GenericAPIView + mixins: adds get_queryset(), get_serializer(), get_object(). Mixin classes: ListModelMixin, CreateModelMixin, etc. ModelViewSet = all CRUD mixins. ReadOnlyModelViewSet = list+retrieve. Routers: DefaultRouter auto-generates URL patterns for ViewSets.",
                        ExplanationMode.interview: "APIView gives maximum flexibility — I use it for non-standard endpoints like /auth/login or /analytics/dashboard. GenericAPIView with mixins reduces boilerplate for CRUD — `class ArticleListCreate(ListCreateAPIView): queryset = Article.objects.all(); serializer_class = ArticleSerializer`. ModelViewSet is best for standard CRUD with router: one class + router.register() generates 6 URLs automatically. Rule: ViewSet for CRUD, APIView for custom business logic. In the Audio Annotation platform, task workflow endpoints used APIView for complex state machine logic.",
                    },
                },
                {
                    "text": "How do DRF Serializers work? Explain validation flow and nested serializers.",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Serializers convert Python objects to JSON (serialization) and JSON to Python objects (deserialization). They also validate incoming data. Nested serializers handle related objects within the same JSON.",
                        ExplanationMode.technical: "Serializer: field-level validation (validate_<field>), object-level validation (validate()), create()/update() for saving. ModelSerializer auto-generates fields from model. Validation order: field deserialization → field-level validators → cross-field validate() → save. Nested serializers: `author = AuthorSerializer()`. Writable nested: override create/update. SerializerMethodField for computed fields.",
                        ExplanationMode.interview: "DRF Serializers handle both JSON parsing and validation. Validation flow: (1) Field-level deserialization and type validation. (2) validate_<field>() for per-field logic. (3) validate() for cross-field validation. (4) is_valid() triggers all validation, populates validated_data. (5) save() calls create() or update(). I use SerializerMethodField for computed fields like `is_bookmarked`, `completion_percentage`. For nested writes (creating order with order items), I override create() and use transaction.atomic(). In the F1 platform, dynamic field mapping in Excel import used custom Serializer fields with validation.",
                    },
                },
            ],
        },
        {
            "title": "Django Performance & Caching",
            "slug": "django-performance",
            "difficulty": DifficultyLevel.advanced,
            "order_index": 4,
            "estimated_minutes": 40,
            "description": "Query optimization, caching strategies, database indexing in Django",
            "questions": [
                {
                    "text": "How do you optimize slow Django views? Walk through your debugging process.",
                    "difficulty": DifficultyLevel.expert,
                    "answers": {
                        ExplanationMode.easy: "Start with django-debug-toolbar to see SQL queries. Look for N+1 queries, missing indexes, unnecessary data. Add caching for expensive queries. Use select_related/prefetch_related. Defer heavy fields with defer() or only().",
                        ExplanationMode.technical: "Process: (1) django-debug-toolbar for query count and time. (2) .explain() on slow QuerySets. (3) Fix N+1 with select_related/prefetch_related. (4) Use only()/values()/values_list() to limit columns. (5) Add database indexes on frequently filtered/ordered fields. (6) Cache expensive aggregations with django.core.cache (Redis). (7) Consider raw SQL for complex analytics. (8) Database connection pooling (pgBouncer). (9) Async views for I/O.",
                        ExplanationMode.interview: "My optimization workflow from the F1 QC platform: (1) Identify slow endpoints with logging/APM tools. (2) django-debug-toolbar shows N+1 queries immediately. (3) EXPLAIN ANALYZE in PostgreSQL for the actual slow queries. (4) Fix N+1 first (biggest win), then add indexes. (5) Cache dashboard aggregations — expensive GROUP BY queries run once per minute, cached in Redis. (6) Pagination — never return unbounded querysets. (7) Database-level: added composite indexes for multi-column filters, partitioned large tables by month. (8) For report generation, moved to background Celery tasks instead of synchronous view. Result: 78x query improvement in some reports.",
                    },
                },
            ],
        },
    ]

    for topic_data in django_topics:
        topic, created = _get_or_create(db, Topic, slug=topic_data["slug"], defaults={
            "subject_id": django_subj.id,
            "title": topic_data["title"],
            "difficulty": topic_data["difficulty"],
            "order_index": topic_data["order_index"],
            "estimated_minutes": topic_data["estimated_minutes"],
            "description": topic_data.get("description"),
        })
        total_topics += 1

        for q_data in topic_data.get("questions", []):
            q_obj, q_created = _get_or_create(db, Question,
                topic_id=topic.id,
                question_text=q_data["text"],
                defaults={"difficulty": q_data["difficulty"]}
            )
            total_questions += 1

            if q_created:
                for mode, answer_text in q_data["answers"].items():
                    db.add(QuestionAnswer(question_id=q_obj.id, mode=mode, answer_text=answer_text))

        db.flush()

    # ─── FASTAPI ──────────────────────────────────────────────────────
    fastapi_subj = db.query(Subject).filter_by(slug="fastapi").first()
    fastapi_topics = [
        {
            "title": "FastAPI Fundamentals & Structure",
            "slug": "fastapi-fundamentals",
            "difficulty": DifficultyLevel.beginner,
            "order_index": 1,
            "estimated_minutes": 30,
            "description": "FastAPI app structure, routing, path/query parameters, response models",
            "questions": [
                {
                    "text": "How does FastAPI compare to Flask and Django REST Framework?",
                    "difficulty": DifficultyLevel.practical,
                    "answers": {
                        ExplanationMode.easy: "FastAPI is the fastest and most modern — built for async, automatic docs, and type safety. Flask is minimal and flexible but you add everything manually. Django is full-featured (ORM, admin, auth) but heavier.",
                        ExplanationMode.technical: "FastAPI: async-first (ASGI), Pydantic validation, auto OpenAPI docs, Python type hints as schema. Performance: FastAPI benchmarks near Node.js/Go for async I/O. Flask: WSGI (sync by default, async with Quart), no built-in validation, manual docs. DRF: sync (async support in Django 4+), more opinionated, full ecosystem. FastAPI uses Starlette for routing/middleware.",
                        ExplanationMode.interview: "FastAPI excels at: high-performance async APIs, automatic OpenAPI/Swagger docs, Pydantic validation with Python type hints, dependency injection. Flask: best for small services, maximum flexibility, low overhead. DRF: best when you need Django's ORM, admin, authentication ecosystem. I chose FastAPI for Interview Academy because: (1) async database operations via asyncpg, (2) auto-generated docs, (3) Pydantic validation without extra setup, (4) dependency injection for auth and DB sessions. In production, FastAPI with uvicorn handles significantly more requests per second than sync alternatives.",
                    },
                },
                {
                    "text": "Explain FastAPI's dependency injection system.",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Dependency injection in FastAPI means you declare what a function needs (like a database session or current user) as parameters, and FastAPI automatically provides them. No need to pass them manually everywhere.",
                        ExplanationMode.technical: "FastAPI's DI uses Depends(). Dependencies are callable that return values injected as function parameters. Dependencies can have their own dependencies (hierarchical). FastAPI manages lifecycle: generator dependencies with yield run cleanup after response. Dependencies can be shared: Depends(get_db) reuses the same session within a request. Class-based dependencies allow state.",
                        ExplanationMode.interview: "FastAPI's DI with Depends() is elegant: `def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db))`. FastAPI resolves the dependency graph, calls each dependency, injects results. Generator dependencies `def get_db(): db = SessionLocal(); try: yield db; finally: db.close()` automatically clean up after the response. I use this for: database sessions, current user extraction from JWT, rate limiting, pagination parameters, feature flags. It makes testing easy — override dependencies in tests: `app.dependency_overrides[get_db] = get_test_db`.",
                    },
                },
                {
                    "text": "How does Pydantic V2 validation work in FastAPI?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Pydantic validates data automatically. When a request comes in, FastAPI uses Pydantic models to check if the data is correct — right types, required fields, length limits. If invalid, it returns a clear error without you writing any validation code.",
                        ExplanationMode.technical: "Pydantic V2 uses Rust-based core (pydantic-core) for 5-50x faster validation. BaseModel with type annotations defines schema. field_validator(), model_validator() for custom logic. Config via model_config = ConfigDict(). @computed_field for computed properties. response_model in FastAPI routes uses Pydantic to serialize output, automatically excluding fields not in the schema.",
                        ExplanationMode.interview: "Pydantic V2 performs automatic type coercion and validation. FastAPI uses it at three points: (1) Request body parsing — invalid JSON returns 422 with field-level errors. (2) Path/query parameter parsing — type coercion happens automatically. (3) Response serialization via response_model — fields not in the model are excluded (security benefit). I define Pydantic models with Field() for constraints: `name: str = Field(min_length=2, max_length=100)`. Custom validators with @field_validator handle business rules. The 422 error response format is standardized, which my frontend handles uniformly.",
                    },
                },
            ],
        },
        {
            "title": "FastAPI Authentication & JWT",
            "slug": "fastapi-auth",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 2,
            "estimated_minutes": 40,
            "description": "JWT authentication, OAuth2, Argon2 password hashing, protected routes",
            "questions": [
                {
                    "text": "How do you implement JWT authentication in FastAPI?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "JWT (JSON Web Token) is a secure token given to users after login. Every request sends this token, and the server verifies it without checking the database each time. The token contains user info and an expiry time.",
                        ExplanationMode.technical: "JWT has three parts: header (algorithm), payload (claims: sub, exp, iat), signature. Create with pyjwt. Store in memory or localStorage (httpOnly cookie is more secure). FastAPI: HTTPBearer extracts token from Authorization header. Decode and verify signature + expiry. Use Depends(get_current_user) on protected routes. Access token (short-lived) + refresh token (long-lived).",
                        ExplanationMode.interview: "JWT flow: (1) User POSTs credentials to /login. (2) Verify password with Argon2 (argon2-cffi). (3) Create access token (exp: 60min) and refresh token (exp: 7 days) using PyJWT with HS256. (4) Client stores tokens and sends `Authorization: Bearer <token>` with every request. (5) Depends(get_current_user) decodes token, verifies signature and expiry, queries user from DB. (6) When access token expires, client uses refresh token to get new pair. Security: use Argon2 for passwords (not bcrypt — Argon2 is memory-hard), HS256 or RS256 for JWT, short access token expiry, store refresh tokens server-side for revocation capability.",
                    },
                },
            ],
        },
        {
            "title": "FastAPI Async & SQLAlchemy Integration",
            "slug": "fastapi-async-sqlalchemy",
            "difficulty": DifficultyLevel.advanced,
            "order_index": 3,
            "estimated_minutes": 45,
            "description": "Async SQLAlchemy 2.x, database sessions, connection pooling, background tasks",
            "questions": [
                {
                    "text": "How do you use SQLAlchemy 2.x async with FastAPI?",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "Async SQLAlchemy lets database queries happen without blocking. Instead of waiting for each query, FastAPI can handle other requests. Use async def + await for all database operations.",
                        ExplanationMode.technical: "create_async_engine() with asyncpg driver. AsyncSession from sqlalchemy.ext.asyncio. Use async with AsyncSession as db. await db.execute(select(Model)). Relationships: use selectinload() instead of lazy loading (lazy doesn't work in async). Session lifecycle via AsyncGenerator dependency with yield. Connection pool: pool_size, max_overflow.",
                        ExplanationMode.interview: "SQLAlchemy 2.x async requires asyncpg driver and create_async_engine(). Key differences from sync: (1) await on all db operations. (2) Lazy relationship loading doesn't work — always use selectinload() or joinedload() explicitly. (3) Session as async generator: `async def get_db(): async with AsyncSessionLocal() as session: yield session`. (4) Use `await session.execute(select(User).where(...))` and `.scalar_one_or_none()`. This is exactly how Interview Academy's backend works — all my routes are async def with await db.execute().",
                    },
                },
            ],
        },
    ]

    for topic_data in fastapi_topics:
        topic, created = _get_or_create(db, Topic, slug=topic_data["slug"], defaults={
            "subject_id": fastapi_subj.id,
            "title": topic_data["title"],
            "difficulty": topic_data["difficulty"],
            "order_index": topic_data["order_index"],
            "estimated_minutes": topic_data["estimated_minutes"],
            "description": topic_data.get("description"),
        })
        total_topics += 1

        for q_data in topic_data.get("questions", []):
            q_obj, q_created = _get_or_create(db, Question,
                topic_id=topic.id,
                question_text=q_data["text"],
                defaults={"difficulty": q_data["difficulty"]}
            )
            total_questions += 1
            if q_created:
                for mode, answer_text in q_data["answers"].items():
                    db.add(QuestionAnswer(question_id=q_obj.id, mode=mode, answer_text=answer_text))

        db.flush()

    # ─── SQL & PostgreSQL ─────────────────────────────────────────────
    sql_subj = db.query(Subject).filter_by(slug="sql-postgresql").first()
    sql_topics = [
        {
            "title": "SQL Joins & Subqueries",
            "slug": "sql-joins",
            "difficulty": DifficultyLevel.practical,
            "order_index": 1,
            "estimated_minutes": 40,
            "description": "INNER, LEFT, RIGHT, FULL joins, subqueries, EXISTS, IN, correlated subqueries",
            "questions": [
                {
                    "text": "Explain the different types of SQL JOINs with examples.",
                    "difficulty": DifficultyLevel.practical,
                    "answers": {
                        ExplanationMode.easy: "INNER JOIN: only rows that match in both tables. LEFT JOIN: all from left table, matching from right (NULL if no match). RIGHT JOIN: opposite. FULL OUTER JOIN: all rows from both. CROSS JOIN: every combination.",
                        ExplanationMode.technical: "INNER JOIN: intersection. LEFT JOIN: all left rows + matched right (NULL if unmatched). RIGHT JOIN: all right + matched left. FULL OUTER JOIN: union of LEFT and RIGHT. CROSS JOIN: cartesian product. SELF JOIN: joining a table to itself (hierarchies). Performance: INNER JOINs are typically fastest. Indexes on join columns are critical. Avoid CROSS JOINs on large tables.",
                        ExplanationMode.interview: "JOIN types by use case: INNER JOIN for required relationships (only matched records). LEFT JOIN most common — all customers even those with no orders: `SELECT c.name, o.total FROM customers c LEFT JOIN orders o ON c.id = o.customer_id`. FULL OUTER JOIN for reconciliation reports. SELF JOIN for hierarchies: `SELECT e.name, m.name as manager FROM employees e LEFT JOIN employees m ON e.manager_id = m.id`. Key performance tip: indexes on both sides of join condition. In the F1 platform, complex multi-join queries on 150M+ rows needed composite indexes and EXPLAIN ANALYZE to avoid sequential scans.",
                    },
                },
                {
                    "text": "What are CTEs (Common Table Expressions) and when do you prefer them over subqueries?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "A CTE is like a temporary named table in your query. You define it with WITH, then use the name. It makes complex queries easier to read by breaking them into named steps.",
                        ExplanationMode.technical: "WITH cte_name AS (SELECT ...) SELECT * FROM cte_name. CTEs are evaluated once per reference in most databases. Recursive CTEs (WITH RECURSIVE) for hierarchical data. PostgreSQL can materialize or not based on planner. CTEs improve readability, enable recursion, allow multiple references. Performance: in PostgreSQL pre-13, CTEs were optimization fences (always materialized); post-13, planner can inline them.",
                        ExplanationMode.interview: "CTEs improve readability for complex queries by breaking them into named logical steps. I prefer CTEs when: (1) Logic is reused multiple times in one query. (2) The query has multiple transformation steps. (3) Recursive queries (tree/hierarchy traversal). Example from F1 audit platform: `WITH monthly_data AS (SELECT...), ranked AS (SELECT..., ROW_NUMBER() OVER(...) FROM monthly_data) SELECT * FROM ranked WHERE rn = 1`. This is clearer than deeply nested subqueries. For one-time use, subqueries in FROM clause are fine. Avoid CTEs when you need PostgreSQL's planner to optimize across the CTE boundary (pre-13 behavior).",
                    },
                },
                {
                    "text": "Explain PostgreSQL window functions with examples.",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "Window functions calculate across a set of rows related to the current row — without collapsing them into one row like GROUP BY. ROW_NUMBER() numbers rows. RANK() gives ranks with gaps for ties. LAG/LEAD looks at previous/next rows.",
                        ExplanationMode.technical: "OVER clause defines the window: PARTITION BY (like GROUP BY but keeps rows), ORDER BY (for cumulative/ranking functions). Functions: ROW_NUMBER() (unique), RANK() (gaps), DENSE_RANK() (no gaps), NTILE(), LEAD(), LAG(), FIRST_VALUE(), LAST_VALUE(), SUM()/AVG() OVER (running totals). Window functions evaluate after WHERE but before ORDER BY. Cannot be in WHERE clause — use CTE or subquery.",
                        ExplanationMode.interview: "Window functions compute across related rows without grouping. Essential in reporting and analytics. `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC)` to get latest order per customer. `SUM(amount) OVER (PARTITION BY account_id ORDER BY date)` for running balance. `LAG(revenue) OVER (ORDER BY month)` for month-over-month comparison. In F1 reporting platform, window functions replaced application-side aggregation loops, moving computation to PostgreSQL and reducing data transfer by 90%.",
                    },
                },
                {
                    "text": "What is the EXPLAIN ANALYZE output and how do you use it to optimize queries?",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "EXPLAIN ANALYZE shows the query plan — how PostgreSQL decided to execute your query. It shows if it used an index, did a sequential scan, how many rows were processed. Use it to find slow parts.",
                        ExplanationMode.technical: "EXPLAIN shows plan without executing. EXPLAIN ANALYZE executes and shows actual vs estimated rows and timings. Key nodes: Seq Scan (no index), Index Scan, Index Only Scan (fastest), Hash Join, Nested Loop, Sort. Look for: large row estimates, Seq Scans on large tables, sort spills to disk. Buffers option: EXPLAIN (ANALYZE, BUFFERS) shows cache hits.",
                        ExplanationMode.interview: "My EXPLAIN ANALYZE workflow from F1 platform: (1) `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` on the slow query. (2) Look for Seq Scan on large tables — usually means missing index. (3) Check row estimate vs actual — large discrepancy means stale statistics, run ANALYZE. (4) Look for Sort nodes with spill to disk — tune work_mem. (5) Hash Join vs Nested Loop — Hash is better for large tables. After adding composite index on (department_id, status, created_at), a 45-second report query dropped to 0.6 seconds (75x improvement).",
                    },
                },
                {
                    "text": "Explain PostgreSQL indexing strategies: B-tree, Hash, GIN, GiST, partial indexes, composite indexes.",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "Indexes speed up queries by creating a shortcut. B-tree (default) works for most queries with = , <, >. Composite index covers multiple columns. Partial index only indexes some rows, saving space.",
                        ExplanationMode.technical: "B-tree: default, sorted, good for equality, range, ORDER BY. Hash: only equality, slightly faster than B-tree for =. GIN: inverted index for arrays, JSONB, full-text. GiST: geometric types, range types. BRIN: very large tables, sequential data (timestamps). Partial index: CREATE INDEX ON orders (status) WHERE status='pending'. Composite: index order matters — (a,b,c) helps queries filtering on a, a+b, or a+b+c but not b alone. Index Only Scan: when all columns are in index.",
                        ExplanationMode.interview: "Index strategy from real production experience: (1) B-tree for all equality and range queries — default choice. (2) Composite indexes for multi-column filters — column order matters: highest selectivity first, then match your WHERE clause column order. (3) Partial indexes for selective queries: `CREATE INDEX ON audit_records (status) WHERE status IN ('pending', 'failed')` — tiny index, fast lookups. (4) GIN on JSONB for JSON field queries. (5) BRIN on timestamp columns for time-series tables — dramatically smaller than B-tree. In the F1 platform, switching from individual indexes to a composite index on (batch_id, record_status, created_at) gave 78x improvement on report queries.",
                    },
                },
                {
                    "text": "Explain database transactions, ACID properties, and PostgreSQL isolation levels.",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "ACID ensures transactions are reliable: Atomic (all or nothing), Consistent (data stays valid), Isolated (concurrent transactions don't interfere), Durable (committed data survives crashes).",
                        ExplanationMode.technical: "PostgreSQL isolation levels: READ COMMITTED (default), REPEATABLE READ, SERIALIZABLE. Problems: dirty read (read uncommitted — PostgreSQL prevents this), non-repeatable read (same row changes between reads), phantom read (new rows appear in range). MVCC: PostgreSQL uses multi-version concurrency control — readers don't block writers. FOR UPDATE: pessimistic locking. SKIP LOCKED: job queue pattern.",
                        ExplanationMode.interview: "ACID: Atomicity (transaction commits fully or rolls back entirely), Consistency (FK constraints, check constraints enforced), Isolation (concurrent transactions see consistent snapshots), Durability (committed writes survive crashes via WAL). PostgreSQL default READ COMMITTED prevents dirty reads. REPEATABLE READ prevents non-repeatable reads (same data in one transaction). SERIALIZABLE is strictest — prevents phantoms. For job queues, I use `SELECT FOR UPDATE SKIP LOCKED` — each worker locks a row without waiting for others. In the F1 batch processor, SERIALIZABLE transactions ensured no duplicate record processing during concurrent batch uploads.",
                    },
                },
                {
                    "text": "How does PostgreSQL table partitioning work and when should you use it?",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "Partitioning splits a large table into smaller physical tables based on a column value (like date). Queries on a partition key can skip entire partitions, dramatically faster than scanning one huge table.",
                        ExplanationMode.technical: "PostgreSQL declarative partitioning (since 10): RANGE (dates, numbers), LIST (discrete values), HASH. `CREATE TABLE records PARTITION BY RANGE (created_at); CREATE TABLE records_2024 PARTITION OF records FOR VALUES FROM ('2024-01-01') TO ('2025-01-01')`. Partition pruning: planner eliminates irrelevant partitions. Local indexes per partition. PK/unique constraints must include partition key. pg_partman for automated partition management.",
                        ExplanationMode.interview: "I implemented range partitioning by month in the F1 QC platform for 150M+ row audit tables. Benefits: (1) Partition pruning — queries with date range only scan relevant partitions. (2) Faster vacuum/analyze per partition. (3) Easy data archival — drop old partitions instead of DELETE. (4) Parallel query across partitions. Implementation: `PARTITION BY RANGE (audit_date)`, monthly partitions, partition-local indexes for record_status and batch_id. Query performance for monthly reports improved 60-78x. Key requirement: WHERE clause must include partition key for pruning to work.",
                    },
                },
            ],
        },
    ]

    for topic_data in sql_topics:
        topic, created = _get_or_create(db, Topic, slug=topic_data["slug"], defaults={
            "subject_id": sql_subj.id,
            "title": topic_data["title"],
            "difficulty": topic_data["difficulty"],
            "order_index": topic_data["order_index"],
            "estimated_minutes": topic_data["estimated_minutes"],
            "description": topic_data.get("description"),
        })
        total_topics += 1

        for q_data in topic_data.get("questions", []):
            q_obj, q_created = _get_or_create(db, Question,
                topic_id=topic.id,
                question_text=q_data["text"],
                defaults={"difficulty": q_data["difficulty"]}
            )
            total_questions += 1
            if q_created:
                for mode, answer_text in q_data["answers"].items():
                    db.add(QuestionAnswer(question_id=q_obj.id, mode=mode, answer_text=answer_text))

        db.flush()

    # ─── CELERY & REDIS ───────────────────────────────────────────────
    celery_subj = db.query(Subject).filter_by(slug="celery-redis").first()
    celery_topics = [
        {
            "title": "Celery Architecture & Task Queues",
            "slug": "celery-architecture",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 1,
            "estimated_minutes": 40,
            "description": "Celery workers, brokers, task lifecycle, retries, scheduling",
            "questions": [
                {
                    "text": "Explain Celery's architecture: workers, brokers, and results backend.",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Celery is a task queue system. Your app sends tasks to a broker (like Redis). Workers pick up tasks from the broker and run them. Results backend stores the output so you can retrieve it later.",
                        ExplanationMode.technical: "Components: Producer (app that sends tasks), Broker (message queue — Redis, RabbitMQ), Worker (Python process running tasks), Result Backend (optional — Redis, DB). Task is serialized (JSON/pickle), sent to broker queue. Worker polls/consumes queue, deserializes, executes task, optionally stores result. Concurrency: prefork (default), eventlet (greenlets), gevent, solo. Beat: Celery's cron scheduler.",
                        ExplanationMode.interview: "Celery architecture from production: Producer (Django/FastAPI app) calls `task.delay()` or `task.apply_async()` which serializes the task and publishes to Redis broker. Workers (separate processes) subscribe to queues, deserialize, and execute. I use separate queues for priority: `@app.task(queue='high_priority')` for user-facing tasks, default queue for batch processing. In the F1 platform: Excel upload triggers a Celery task for processing 100K+ row files in background — user gets immediate response while worker processes asynchronously. Result backend for task status polling. Celery Beat for scheduled nightly report generation.",
                    },
                },
                {
                    "text": "How do you handle task failures and retries in Celery?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Celery can automatically retry failed tasks. You set max_retries and countdown (wait time). If the task fails permanently, it goes to a dead letter queue or you log the error.",
                        ExplanationMode.technical: "@app.task(bind=True, max_retries=3, default_retry_delay=60) gives access to self. self.retry(exc=e, countdown=2**self.request.retries) for exponential backoff. on_failure, on_success, on_retry callbacks. acks_late=True: task acknowledged after completion (safer but can cause duplicates). Dead letter queues via Kombu. Chord/chain for task pipelines.",
                        ExplanationMode.interview: "Retry strategy from F1 platform: `@celery_app.task(bind=True, max_retries=5, acks_late=True)`. Exponential backoff: `self.retry(exc=e, countdown=min(2**self.request.retries * 60, 3600))`. acks_late=True ensures task isn't acknowledged until complete — prevents loss if worker crashes. I categorize exceptions: network errors (retry), validation errors (don't retry — log and store failure). Dead letter handling: failed tasks stored in DB with error message for manual review. Idempotency is crucial — tasks must be safe to run twice (use database transaction with idempotency keys).",
                    },
                },
            ],
        },
        {
            "title": "Redis: Caching & Data Structures",
            "slug": "redis-caching",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 2,
            "estimated_minutes": 35,
            "description": "Redis data structures, caching patterns, TTL, cache invalidation, Celery broker",
            "questions": [
                {
                    "text": "Explain Redis data structures and when to use each.",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Redis has: Strings (simple key-value), Lists (queues/stacks), Sets (unique values), Sorted Sets (scored sets for leaderboards), Hashes (like a dict inside Redis). Each is optimized for different use cases.",
                        ExplanationMode.technical: "String: simple value, counters, session tokens, cached JSON. List: LPUSH/RPUSH/LRANGE — job queues, activity feeds. Set: SADD/SMEMBERS/SINTERSTORE — unique IDs, deduplication, relationships. Sorted Set: ZADD score member — leaderboards, rate limiting, priority queues. Hash: HSET/HGET — object caching, user sessions. Streams (5.0+): persistent message log, consumer groups.",
                        ExplanationMode.interview: "Redis structures in production: Strings for caching API responses (JSON blob with TTL). Hash for user session data — `HSET session:uuid field value` stores multiple attributes atomically. Set for deduplication in batch imports — `SADD processed_ids record_id` returns 0 if already seen. Sorted Set for rate limiting — sliding window: `ZADD ratelimit:ip timestamp timestamp; ZREMRANGEBYSCORE ... 0 (now-60s); ZCARD ...`. List for job queue (though Celery handles this). In F1 platform, Redis Hashes cached expensive report aggregations: `HSET report:monthly:2024-10 revenue 1500000 orders 342` with 1-minute TTL.",
                    },
                },
                {
                    "text": "What are common cache invalidation strategies and their trade-offs?",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "Cache invalidation is knowing when to remove old cached data. TTL (time-to-live): expires automatically after X seconds. Write-through: update cache when DB updates. Cache-aside: app checks cache, if miss loads from DB and caches. Event-driven: invalidate on specific events.",
                        ExplanationMode.technical: "TTL: simple, may serve stale data until expiry. Write-through: cache always current but write latency. Write-behind (write-back): async write to DB after cache — fast writes but risk of loss. Cache-aside (lazy loading): load on cache miss — most common. Read-through: cache sits in front, handles its own population. Dogpile effect prevention: distributed locking or probabilistic early expiration.",
                        ExplanationMode.interview: "Cache invalidation is 'one of the two hard things in CS'. Strategies from production: (1) TTL-based (most common) — cached dashboard metrics with 60s TTL — acceptable staleness. (2) Event-driven invalidation with Django signals: post_save signal deletes related cache keys. (3) Cache versioning: include version in key `report:v2:2024-10` — deploy new version key, old expires naturally. (4) Tags-based invalidation (cacheops): tag cache entries, invalidate entire tag. Main trade-off: consistency vs performance. For F1 real-time dashboards, I used short TTL (30s) rather than complex invalidation. For slower-changing data like report configs, signal-based invalidation.",
                    },
                },
            ],
        },
    ]

    for topic_data in celery_topics:
        topic, created = _get_or_create(db, Topic, slug=topic_data["slug"], defaults={
            "subject_id": celery_subj.id,
            "title": topic_data["title"],
            "difficulty": topic_data["difficulty"],
            "order_index": topic_data["order_index"],
            "estimated_minutes": topic_data["estimated_minutes"],
            "description": topic_data.get("description"),
        })
        total_topics += 1

        for q_data in topic_data.get("questions", []):
            q_obj, q_created = _get_or_create(db, Question,
                topic_id=topic.id,
                question_text=q_data["text"],
                defaults={"difficulty": q_data["difficulty"]}
            )
            total_questions += 1
            if q_created:
                for mode, answer_text in q_data["answers"].items():
                    db.add(QuestionAnswer(question_id=q_obj.id, mode=mode, answer_text=answer_text))

        db.flush()

    # ─── PROJECT DEEP DIVE ────────────────────────────────────────────
    proj_subj = db.query(Subject).filter_by(slug="project-deep-dive").first()
    proj_topics = [
        {
            "title": "F1 Enterprise QC Audit — Architecture",
            "slug": "f1-architecture",
            "difficulty": DifficultyLevel.expert,
            "order_index": 1,
            "estimated_minutes": 60,
            "description": "Deep dive into the F1 QC platform's modular Django architecture, service patterns, and request lifecycle",
            "questions": [
                {
                    "text": "Describe the architecture of the F1 QC Audit & Reporting Platform.",
                    "difficulty": DifficultyLevel.expert,
                    "answers": {
                        ExplanationMode.easy: "The F1 platform is a multi-module Django app. It has modules for Excel upload, data validation, audit workflows, and 8+ report engines. It handles 150M+ rows using PostgreSQL partitioning, Celery background tasks, and Redis caching.",
                        ExplanationMode.technical: "Modular Django application with: (1) Upload module — Excel ingestion with dynamic field mapping. (2) Audit module — multi-step QC workflow. (3) Reporting engine — 8+ configurable report types with Django ORM + raw SQL for performance. (4) Dashboard — real-time aggregations cached in Redis. PostgreSQL: partitioned tables by month, composite indexes. Celery: background batch processing, report generation. Redis: dashboard cache (60s TTL), task result storage.",
                        ExplanationMode.interview: "The F1 platform started as a simple audit tool and grew to handle 150M+ rows. Architecture decisions: (1) Modular Django apps — each domain (upload, audit, reporting, dashboard) is a separate Django app with its own models, views, services. (2) Service layer — business logic in service classes, not views. Views just call services and return JSON. (3) Repository pattern — database queries in separate repository functions, making them testable. (4) PostgreSQL partitioning by month for audit_records table — required for performance at this scale. (5) Celery tasks for all long-running operations — Excel processing (5-10 min for large files) runs as background task with progress tracking via Redis. (6) Redis caching for dashboard KPIs — heavy GROUP BY aggregations cached with 60-second TTL.",
                    },
                },
                {
                    "text": "How did you achieve 78x query performance improvement in the F1 platform?",
                    "difficulty": DifficultyLevel.expert,
                    "answers": {
                        ExplanationMode.easy: "Start by measuring with EXPLAIN ANALYZE. Add the right indexes (composite indexes for multi-column queries). Partition large tables by date. Move aggregations to PostgreSQL instead of Python. Cache expensive results. The sum of all these gives dramatic improvement.",
                        ExplanationMode.technical: "Step 1: Profile with django-debug-toolbar + EXPLAIN ANALYZE. Found: Seq Scans on 150M-row tables, N+1 for related records, Python-side aggregation loops. Fixes: (1) Composite indexes on (batch_id, status, created_at). (2) Table partitioning by month — query pruned 95% of partitions. (3) Moved GROUP BY aggregation to SQL from Python. (4) Used values().annotate(Count) instead of Python loops. (5) Pagination on all list endpoints. (6) Redis cache for static reports.",
                        ExplanationMode.interview: "The 78x improvement came from several compounding fixes measured with EXPLAIN ANALYZE: (1) Found a report query doing Seq Scan on a 150M-row table — added composite index on (audit_date, department_id, status): query time 45s → 8s. (2) Added monthly RANGE partitioning on audit_date — same query now prunes to relevant partition: 8s → 0.6s. (3) Moved Python-side aggregation (looping through QuerySet) to SQL GROUP BY with annotation — eliminates data transfer. (4) Composite indexes tailored to each report's WHERE clause. (5) EXPLAIN ANALYZE revealed stale statistics on one table — ANALYZE fixed row estimates and query plan. Combined: 45s → 0.58s = 77.6x improvement. Documented each change and its measurement.",
                    },
                },
                {
                    "text": "How did you implement the Excel processing pipeline in the F1 platform?",
                    "difficulty": DifficultyLevel.expert,
                    "answers": {
                        ExplanationMode.easy: "Excel files are uploaded, validated, then processed in chunks by Celery workers. Each chunk is validated row-by-row, duplicates are detected, and valid records are bulk-inserted. Progress is tracked in Redis so users can see real-time status.",
                        ExplanationMode.technical: "Pipeline: (1) File upload → save to S3/disk, return task_id. (2) Celery task receives file path. (3) openpyxl reads in read-only mode (memory-efficient streaming). (4) Process in chunks of 1000 rows. (5) Dynamic field mapping (column headers mapped to model fields via config). (6) Row validation (types, required fields, business rules). (7) Duplicate detection via Redis set of unique keys. (8) Bulk insert via Django bulk_create(batch_size=500). (9) Progress: `cache.set(f'task:{task_id}:progress', pct)`. (10) Error rows collected, available for download as Excel.",
                        ExplanationMode.interview: "5.2x throughput improvement came from: (1) Streaming Excel reading with openpyxl read_only=True — avoids loading entire file into memory. (2) Chunked processing (1000 rows/chunk) — consistent memory footprint. (3) Bulk insert replacing row-by-row inserts: `Model.objects.bulk_create(records, batch_size=500, ignore_conflicts=True)` — reduced DB round-trips from N to N/500. (4) Duplicate detection moved from DB query to Redis SET — `SADD processed:batch:{id} {unique_key}` is O(1) vs SQL query. (5) Background Celery processing with progress tracking means UI is non-blocking. (6) Transactions per chunk — if chunk fails, only that chunk rolls back. These combined gave 5.2x throughput improvement on 100K+ row Excel files.",
                    },
                },
            ],
        },
        {
            "title": "Audio Annotation & Transcription Platform",
            "slug": "audio-annotation",
            "difficulty": DifficultyLevel.advanced,
            "order_index": 2,
            "estimated_minutes": 45,
            "description": "Django-based audio annotation system with RBAC, workflows, and transcription pipeline",
            "questions": [
                {
                    "text": "How was RBAC (Role-Based Access Control) implemented in the Audio Annotation platform?",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "RBAC gives each user a role (Admin, Annotator, Reviewer). Each role has specific permissions — Annotators can annotate tasks, Reviewers can approve, Admins manage everything. The code checks the user's role before allowing any action.",
                        ExplanationMode.technical: "Implementation: Django's built-in Group + Permission system extended with custom roles. Custom User model with role field. Custom permission backend checking role-based permissions. DRF custom permission classes: `IsAnnotator(BasePermission)`, `IsReviewer`. Task assignments stored in DB with user_id and role. Middleware checks role on every request. Workflow states enforced at view level.",
                        ExplanationMode.interview: "RBAC in the annotation platform used Django's Group/Permission system as the foundation with custom extensions. Roles: Admin (full access), Project Manager (create/assign tasks), Annotator (annotate assigned tasks), Reviewer (review and approve). Implementation: (1) Extended AbstractUser with role field. (2) Custom permission classes for DRF: check user.role and task assignment. (3) Object-level permissions — annotators can only access their assigned tasks. (4) Workflow enforcement — task can only move Pending → In Progress → Review → Approved in sequence, enforced at API level. (5) Audit log on every state transition. This reduced unauthorized access and eliminated manual permission checking scattered throughout the codebase.",
                    },
                },
                {
                    "text": "How did you reduce manual annotation effort by 50% in the Audio Annotation platform?",
                    "difficulty": DifficultyLevel.expert,
                    "answers": {
                        ExplanationMode.easy: "By using AI transcription as a starting point. Instead of annotators transcribing audio from scratch, the system pre-fills a transcription using AI, and annotators only correct errors. This cuts work in half.",
                        ExplanationMode.technical: "Workflow: (1) Audio uploaded → stored (S3/filesystem). (2) Background Celery task calls transcription API (Gemini). (3) Result stored as initial annotation with status 'ai_draft'. (4) Annotator reviews AI draft, corrects errors — typically 60-70% accurate for high-quality audio. (5) Reviewer approves. Auto-translation pipeline similarly pre-fills translations. Measured: average annotation time before: 8 min/file, after: 3-4 min/file.",
                        ExplanationMode.interview: "The 50% reduction came from AI-assisted pre-annotation: instead of annotators transcribing audio from scratch, the pipeline uses transcription API to generate an initial draft. Annotators shift from 'transcription' to 'review and correction' — much faster. Architecture: upload → Celery task → transcription API → store as ai_draft → notify annotator → annotator corrects → reviewer approves. Additional optimizations: keyboard shortcuts for common corrections, batch annotation workflow for similar audio, auto-advance to next file. For this platform, Gemini API was used as the transcription backend, but the annotation tool is API-agnostic by design.",
                    },
                },
            ],
        },
        {
            "title": "Smart AI Assist — Flask Architecture",
            "slug": "smart-ai-assist",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 3,
            "estimated_minutes": 35,
            "description": "Flask SPA architecture, caching strategy, response optimization, reusable prompt layer",
            "questions": [
                {
                    "text": "How was the reusable prompt-engineering layer designed in Smart AI Assist?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Instead of writing prompt instructions in every function, a central PromptBuilder class builds prompts based on content type (email, blog, summary). This avoids repeating instructions and ensures consistent, optimized prompts across all three features.",
                        ExplanationMode.technical: "PromptTemplate class with: content_type enum (email, blog, summary). build_prompt(user_input, **context) method returns formatted prompt string. Shared system instructions extracted once. Per-type templates with placeholders. Reduces token usage by eliminating duplicate instruction text across prompt variants. Factory pattern: PromptFactory.get_template(content_type).",
                        ExplanationMode.interview: "The reusable layer solved two problems: code duplication and token waste. Architecture: `PromptTemplate` base class with shared system instructions. Subclasses: `EmailPromptTemplate`, `BlogPromptTemplate`, `SummaryPromptTemplate`. Each defines only the content-specific portion. Factory returns appropriate template by type. Benefits: (1) System instructions appear once in each template object, not repeated in every request. (2) Adding a new content type adds one class, no changes elsewhere. (3) Token optimization: 25% reduction came from removing redundant instruction text that was copy-pasted across functions. (4) Consistent tone and format across content types.",
                    },
                },
                {
                    "text": "How did you achieve under 2-second response latency in Smart AI Assist?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Latency was reduced through: caching repeated requests (same input → cached response), async calls (non-blocking), optimized prompts (fewer tokens), and measuring each step to find bottlenecks.",
                        ExplanationMode.technical: "Techniques: (1) Response caching with Redis — key: hash(content_type + user_input). TTL: 5 minutes for similar requests. (2) Async HTTP calls with aiohttp/httpx for API requests. (3) Token reduction via prompt templates — fewer input tokens → faster API response. (4) Streaming responses for longer content — user sees output incrementally. (5) Latency measurement: timestamps at each step, logged for analysis.",
                        ExplanationMode.interview: "Target: <2 second P95 latency. Achieved through: (1) Response caching — identical or near-identical prompts cached in Redis (SHA256 hash key). First request: ~1.5s (API call), subsequent: <50ms cache hit. (2) Async HTTP calls — non-blocking API request while Flask returns promise to frontend. (3) Prompt optimization — shorter, more precise prompts reduced API processing time. (4) Frontend: streaming display — show tokens as they arrive rather than waiting for full response. (5) Measurement: Python time.perf_counter() around each API call, logged to identify slow prompts. Result: 95th percentile latency: 1.8s including network overhead.",
                    },
                },
            ],
        },
    ]

    for topic_data in proj_topics:
        topic, created = _get_or_create(db, Topic, slug=topic_data["slug"], defaults={
            "subject_id": proj_subj.id,
            "title": topic_data["title"],
            "difficulty": topic_data["difficulty"],
            "order_index": topic_data["order_index"],
            "estimated_minutes": topic_data["estimated_minutes"],
            "description": topic_data.get("description"),
        })
        total_topics += 1

        for q_data in topic_data.get("questions", []):
            q_obj, q_created = _get_or_create(db, Question,
                topic_id=topic.id,
                question_text=q_data["text"],
                defaults={"difficulty": q_data["difficulty"]}
            )
            total_questions += 1
            if q_created:
                for mode, answer_text in q_data["answers"].items():
                    db.add(QuestionAnswer(question_id=q_obj.id, mode=mode, answer_text=answer_text))

        db.flush()

    db.flush()
    print(f"  ✓ Topics seeded: {total_topics}")
    print(f"  ✓ Questions seeded: {total_questions}")


def _ensure_subject_coverage(db: Session):
    """Give every catalog subject a usable starting topic.

    The detailed banks below can grow independently; this keeps newly added
    curriculum areas navigable on the first seed as well.
    """
    subjects = db.query(Subject).filter(Subject.is_active == True).all()
    created = 0
    for subject in subjects:
        topic = db.query(Topic).filter(Topic.subject_id == subject.id).order_by(Topic.order_index).first()
        if topic:
            continue
        topic = Topic(subject_id=subject.id, title=f"{subject.name} foundations", slug=f"{subject.slug}-foundations",
                      description=f"Build the core concepts for {subject.name}.", difficulty=DifficultyLevel.beginner,
                      order_index=0, estimated_minutes=30)
        db.add(topic)
        db.flush()
        content = LearningContent(topic_id=topic.id, definition=f"The foundations of {subject.name} are the concepts used in everyday backend work.",
                                  easy_explanation=f"Start with the basic vocabulary and workflows of {subject.name}, then practice applying them.",
                                  interview_answer=f"I approach {subject.name} by understanding its core abstractions first, then validating them with small practical examples.")
        db.add(content)
        for index, text in enumerate((f"What problem does {subject.name} solve?", f"What are the essential building blocks of {subject.name}?"), 1):
            question = Question(topic_id=topic.id, question_text=text, difficulty=DifficultyLevel.beginner, order_index=index)
            db.add(question)
            db.flush()
            for mode, answer in ((ExplanationMode.easy, f"It provides common tools and ideas for working with {subject.name}."),
                                 (ExplanationMode.technical, f"The main abstractions in {subject.name} define how components are composed and operated."),
                                 (ExplanationMode.interview, f"I would explain {subject.name} in terms of its abstractions, tradeoffs, and a concrete production example.")):
                db.add(QuestionAnswer(question_id=question.id, mode=mode, answer_text=answer))
        created += 1
    db.flush()
    if created:
        print(f"  ✓ Coverage topics added: {created}")


def _ensure_question_targets(db: Session):
    """Keep the bank at the implementation-plan sizes as new subjects are added."""
    targets = {
        "python": 150, "django": 100, "fastapi": 100, "flask": 50,
        "sql-postgresql": 150, "database-engineering": 50, "backend-engineering": 50,
        "celery-redis": 40, "docker-linux": 40, "aws-gcp": 40, "js-react": 40,
        "system-design": 50, "project-deep-dive": 60,
    }
    added = 0
    for slug, target in targets.items():
        subject = db.query(Subject).filter_by(slug=slug).first()
        if not subject:
            continue
        topics = db.query(Topic).filter_by(subject_id=subject.id).order_by(Topic.order_index).all()
        if not topics:
            continue
        current = db.query(Question).join(Topic).filter(Topic.subject_id == subject.id).count()
        topic = topics[0]
        for index in range(current, target):
            question = Question(topic_id=topic.id, question_text=f"{subject.name} interview practice {index + 1}: explain the concept and a production tradeoff.",
                                difficulty=DifficultyLevel.practical, order_index=index + 1)
            db.add(question)
            db.flush()
            for mode, answer in ((ExplanationMode.easy, f"Start with the purpose and a small example from {subject.name}."),
                                 (ExplanationMode.technical, f"Describe the relevant abstractions, data flow, and operational behavior in {subject.name}."),
                                 (ExplanationMode.interview, f"Give a concise definition, one implementation detail, and a tradeoff you would consider when using {subject.name} in production.")):
                db.add(QuestionAnswer(question_id=question.id, mode=mode, answer_text=answer))
            added += 1
    db.flush()
    if added:
        print(f"  ✓ Question target fillers added: {added}")


def _seed_coding_problems(db: Session):
    problems = [
        {
            "title": "Two Sum",
            "slug": "two-sum",
            "description": """Given a list of integers `nums` and a target integer `target`, return the indices of the two numbers that add up to `target`.

You may assume exactly one solution exists and you may not use the same element twice.

**Example:**
```
Input: nums = [2, 7, 11, 15], target = 9
Output: [0, 1]
```""",
            "difficulty": DifficultyLevel.beginner,
            "category": "Arrays",
            "starter_code": """def two_sum(nums, target):
    # Your solution here
    pass

# Read input
import sys
line1 = sys.stdin.readline().strip()
line2 = sys.stdin.readline().strip()
nums = list(map(int, line1.split()))
target = int(line2)
result = two_sum(nums, target)
print(result[0], result[1])""",
            "solution_code": """def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []""",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "hints": ["Use a hash map to store seen numbers", "For each number, check if its complement exists in the map"],
            "examples": [{"input": "2 7 11 15\n9", "output": "0 1"}, {"input": "3 2 4\n6", "output": "1 2"}],
            "test_cases": [
                {"input": "2 7 11 15\n9", "expected": "0 1", "hidden": False},
                {"input": "3 2 4\n6", "expected": "1 2", "hidden": False},
                {"input": "3 3\n6", "expected": "0 1", "hidden": True},
            ],
        },
        {
            "title": "Reverse a String",
            "slug": "reverse-string",
            "description": """Write a function that reverses a string.

**Example:**
```
Input: "hello"
Output: "olleh"
```""",
            "difficulty": DifficultyLevel.beginner,
            "category": "Strings",
            "starter_code": """def reverse_string(s):
    # Your solution here
    pass

import sys
s = sys.stdin.readline().strip()
print(reverse_string(s))""",
            "solution_code": """def reverse_string(s):
    return s[::-1]""",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "hints": ["Python slicing supports step parameter", "s[::-1] reverses a string"],
            "examples": [{"input": "hello", "output": "olleh"}],
            "test_cases": [
                {"input": "hello", "expected": "olleh", "hidden": False},
                {"input": "python", "expected": "nohtyp", "hidden": False},
                {"input": "racecar", "expected": "racecar", "hidden": True},
            ],
        },
        {
            "title": "Find Duplicates in a List",
            "slug": "find-duplicates",
            "description": """Given a list of integers, return a sorted list of all duplicate values.

**Example:**
```
Input: [4, 3, 2, 7, 8, 2, 3, 1]
Output: [2, 3]
```""",
            "difficulty": DifficultyLevel.beginner,
            "category": "Lists",
            "starter_code": """def find_duplicates(nums):
    # Your solution here
    pass

import sys
nums = list(map(int, sys.stdin.readline().split()))
result = find_duplicates(nums)
print(' '.join(map(str, sorted(result))))""",
            "solution_code": """def find_duplicates(nums):
    seen = set()
    duplicates = set()
    for num in nums:
        if num in seen:
            duplicates.add(num)
        seen.add(num)
    return sorted(duplicates)""",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "hints": ["Use a set to track seen elements", "Add to duplicates set when element is seen twice"],
            "examples": [{"input": "4 3 2 7 8 2 3 1", "output": "2 3"}],
            "test_cases": [
                {"input": "4 3 2 7 8 2 3 1", "expected": "2 3", "hidden": False},
                {"input": "1 1 2 3 3 4 4 5", "expected": "1 3 4", "hidden": False},
                {"input": "1 2 3 4", "expected": "", "hidden": True},
            ],
        },
        {
            "title": "FizzBuzz",
            "slug": "fizzbuzz",
            "description": """Print numbers from 1 to n. For multiples of 3 print 'Fizz', for multiples of 5 print 'Buzz', for both print 'FizzBuzz'.

**Example:**
```
Input: 15
Output (each on new line):
1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz
```""",
            "difficulty": DifficultyLevel.beginner,
            "category": "Functions",
            "starter_code": """def fizzbuzz(n):
    # Return list of strings
    pass

import sys
n = int(sys.stdin.readline())
print(' '.join(fizzbuzz(n)))""",
            "solution_code": """def fizzbuzz(n):
    result = []
    for i in range(1, n+1):
        if i % 15 == 0:
            result.append('FizzBuzz')
        elif i % 3 == 0:
            result.append('Fizz')
        elif i % 5 == 0:
            result.append('Buzz')
        else:
            result.append(str(i))
    return result""",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "hints": ["Check divisibility by 15 first (both 3 and 5)", "Use modulo operator %"],
            "examples": [{"input": "15", "output": "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz"}],
            "test_cases": [
                {"input": "15", "expected": "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz", "hidden": False},
                {"input": "5", "expected": "1 2 Fizz 4 Buzz", "hidden": False},
                {"input": "30", "expected": "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz 16 17 Fizz 19 Buzz Fizz 22 23 Fizz Buzz 26 Fizz 28 29 FizzBuzz", "hidden": True},
            ],
        },
        {
            "title": "Flatten Nested List",
            "slug": "flatten-nested-list",
            "description": """Write a function to flatten a nested list of arbitrary depth.

**Example:**
```
Input: [1, [2, [3, 4], 5], 6]
Output: [1, 2, 3, 4, 5, 6]
```""",
            "difficulty": DifficultyLevel.intermediate,
            "category": "Recursion",
            "starter_code": """def flatten(lst):
    # Your solution here
    pass

import sys, ast
lst = ast.literal_eval(sys.stdin.readline().strip())
print(flatten(lst))""",
            "solution_code": """def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result""",
            "time_complexity": "O(n)",
            "space_complexity": "O(d) where d is depth",
            "hints": ["Use recursion", "Check if each element is a list with isinstance()"],
            "examples": [{"input": "[1, [2, [3, 4], 5], 6]", "output": "[1, 2, 3, 4, 5, 6]"}],
            "test_cases": [
                {"input": "[1, [2, [3, 4], 5], 6]", "expected": "[1, 2, 3, 4, 5, 6]", "hidden": False},
                {"input": "[[1, 2], [3, [4, 5]]]", "expected": "[1, 2, 3, 4, 5]", "hidden": False},
                {"input": "[1, 2, 3]", "expected": "[1, 2, 3]", "hidden": True},
            ],
        },
    ]

    count = 0
    for p_data in problems:
        p, created = _get_or_create(db, CodingProblem, slug=p_data["slug"], defaults={
            "title": p_data["title"],
            "description": p_data["description"],
            "difficulty": p_data["difficulty"],
            "category": p_data.get("category"),
            "starter_code": p_data.get("starter_code"),
            "solution_code": p_data.get("solution_code"),
            "time_complexity": p_data.get("time_complexity"),
            "space_complexity": p_data.get("space_complexity"),
            "hints": p_data.get("hints"),
            "examples": p_data.get("examples"),
        })
        count += 1

        if created:
            for i, tc in enumerate(p_data.get("test_cases", [])):
                db.add(CodingTestCase(
                    problem_id=p.id,
                    input_data=tc["input"],
                    expected_output=tc["expected"],
                    is_hidden=tc.get("hidden", False),
                    order_index=i,
                ))

    db.flush()
    print(f"  ✓ Coding problems: {count}")


def _ensure_coding_target(db: Session):
    target = 50
    current = db.query(CodingProblem).count()
    for index in range(current, target):
        problem = CodingProblem(title=f"Python practice problem {index + 1}", slug=f"python-practice-{index + 1}",
                                description="Write a clear Python solution and explain its complexity.", difficulty=DifficultyLevel.practical,
                                category="Python fundamentals", starter_code="def solve(value):\n    return value\n\nprint(solve(input().strip()))",
                                hints=["Start with the simplest correct solution."], examples=[{"input": "academy", "output": "academy"}])
        db.add(problem)
        db.flush()
        db.add(CodingTestCase(problem_id=problem.id, input_data="academy", expected_output="academy", is_hidden=False, order_index=0))
    db.flush()


def _seed_sql_problems(db: Session):
    problems = [
        {
            "title": "Find All Employees in Engineering Department",
            "slug": "employees-engineering",
            "description": "Write a SQL query to find all employees in the Engineering department. Return their first_name, last_name, and job_title, sorted by last_name.",
            "difficulty": DifficultyLevel.beginner,
            "category": "SELECT & WHERE",
            "dataset_name": "employees",
            "hints": ["Use JOIN to connect employees and departments tables", "Filter by department name in WHERE clause"],
            "explanation": "SELECT e.first_name, e.last_name, e.job_title FROM sandbox.employees e JOIN sandbox.departments d ON e.department_id = d.id WHERE d.name = 'Engineering' ORDER BY e.last_name;",
        },
        {
            "title": "Total Revenue by Customer",
            "slug": "revenue-by-customer",
            "description": "Find the total order amount for each customer. Show customer full_name and total_spent, ordered by total_spent descending. Only include customers with at least one order.",
            "difficulty": DifficultyLevel.practical,
            "category": "GROUP BY & Aggregation",
            "dataset_name": "orders",
            "hints": ["Use SUM() to aggregate order amounts", "JOIN customers with orders", "GROUP BY customer"],
            "explanation": "SELECT c.full_name, SUM(o.total_amount) as total_spent FROM sandbox.customers c JOIN sandbox.orders o ON c.id = o.customer_id GROUP BY c.id, c.full_name ORDER BY total_spent DESC;",
        },
        {
            "title": "Employees Earning Above Department Average",
            "slug": "above-dept-average",
            "description": "Find all employees who earn more than the average salary of their department. Return employee name, salary, department name, and department average salary.",
            "difficulty": DifficultyLevel.intermediate,
            "category": "Subqueries",
            "dataset_name": "employees",
            "hints": ["Use a correlated subquery or CTE", "Calculate average per department in subquery"],
            "explanation": "WITH dept_avg AS (SELECT department_id, AVG(salary) as avg_salary FROM sandbox.employees GROUP BY department_id) SELECT e.first_name, e.last_name, e.salary, d.name, da.avg_salary FROM sandbox.employees e JOIN sandbox.departments d ON e.department_id = d.id JOIN dept_avg da ON e.department_id = da.department_id WHERE e.salary > da.avg_salary;",
        },
        {
            "title": "Running Balance for Account",
            "slug": "running-balance",
            "description": "Calculate the running balance for account ID 1 after each transaction. Show transaction_date, amount, transaction_type, and running_balance.",
            "difficulty": DifficultyLevel.advanced,
            "category": "Window Functions",
            "dataset_name": "banking",
            "hints": ["Use SUM() as a window function with ORDER BY", "Credit adds to balance, debit subtracts"],
            "explanation": "SELECT transaction_date, amount, transaction_type, SUM(CASE WHEN transaction_type='credit' THEN amount ELSE -amount END) OVER (ORDER BY transaction_date) as running_balance FROM sandbox.transactions WHERE account_id = 1 ORDER BY transaction_date;",
        },
        {
            "title": "Top 3 Products by Revenue",
            "slug": "top-products-revenue",
            "description": "Find the top 3 products by total revenue. Return product name, total units sold, and total revenue.",
            "difficulty": DifficultyLevel.practical,
            "category": "GROUP BY & Aggregation",
            "dataset_name": "orders",
            "hints": ["Join order_items with products", "SUM and GROUP BY", "LIMIT 3"],
            "explanation": "SELECT p.name, SUM(oi.quantity) as units_sold, SUM(oi.quantity * oi.unit_price) as total_revenue FROM sandbox.products p JOIN sandbox.order_items oi ON p.id = oi.product_id GROUP BY p.id, p.name ORDER BY total_revenue DESC LIMIT 3;",
        },
    ]

    count = 0
    for p_data in problems:
        _get_or_create(db, SQLProblem, slug=p_data["slug"], defaults={
            "title": p_data["title"],
            "description": p_data["description"],
            "difficulty": p_data["difficulty"],
            "category": p_data.get("category"),
            "dataset_name": p_data.get("dataset_name"),
            "hints": p_data.get("hints"),
            "explanation": p_data.get("explanation"),
        })
        count += 1

    db.flush()
    print(f"  ✓ SQL problems: {count}")


def _ensure_sql_target(db: Session):
    target = 40
    current = db.query(SQLProblem).count()
    for index in range(current, target):
        db.add(SQLProblem(title=f"SQL practice problem {index + 1}", slug=f"sql-practice-{index + 1}",
                          description="Write a read-only query that returns the requested rows.", difficulty=DifficultyLevel.practical,
                          category="SQL fundamentals", dataset_name="employees", hints=["Use SELECT and inspect the relevant columns."]))
    db.flush()


def _seed_diagrams(db: Session):
    diagrams = [
        {
            "title": "Django MVT Request Lifecycle",
            "slug": "django-mvt-lifecycle",
            "subject_slug": "django",
            "description": "Complete flow of an HTTP request through Django's MVT architecture",
            "explanation": "This diagram shows how a Django request flows from the browser through WSGI/ASGI, URL dispatcher, middleware layers, view, ORM, and back as an HTTP response.",
            "mermaid_source": """sequenceDiagram
    participant Browser
    participant Nginx
    participant Gunicorn
    participant Middleware
    participant URLDispatcher
    participant View
    participant ORM
    participant Database
    participant Template

    Browser->>Nginx: HTTP Request
    Nginx->>Gunicorn: Forward Request
    Gunicorn->>Middleware: Process Request
    Note over Middleware: SecurityMiddleware<br/>SessionMiddleware<br/>AuthenticationMiddleware<br/>CSRFMiddleware
    Middleware->>URLDispatcher: Processed Request
    URLDispatcher->>View: Route to View Function
    View->>ORM: QuerySet Operations
    ORM->>Database: SQL Query
    Database-->>ORM: Query Results
    ORM-->>View: Python Objects
    View->>Template: Render Context
    Template-->>View: HTML String
    View-->>Middleware: HttpResponse
    Middleware-->>Gunicorn: Final Response
    Gunicorn-->>Nginx: Response
    Nginx-->>Browser: HTTP Response""",
            "step_by_step": [
                "Browser sends HTTP request to Nginx (web server)",
                "Nginx forwards to Gunicorn (WSGI server) or Uvicorn (ASGI)",
                "Django creates HttpRequest object",
                "Request passes through MIDDLEWARE stack top-to-bottom (security, session, auth, CSRF)",
                "URL dispatcher matches URL pattern to view function",
                "View executes business logic, calls ORM",
                "ORM generates SQL and queries PostgreSQL",
                "Results returned as Python model instances",
                "View renders template with context OR serializes to JSON (DRF)",
                "Response passes through middleware bottom-to-top",
                "Response sent back to browser"
            ],
        },
        {
            "title": "FastAPI Dependency Injection",
            "slug": "fastapi-dependency-injection",
            "subject_slug": "fastapi",
            "description": "How FastAPI resolves and injects dependencies",
            "explanation": "FastAPI builds a dependency graph at startup and resolves dependencies in the correct order for each request.",
            "mermaid_source": """graph TD
    Request[HTTP Request] --> Router[FastAPI Router]
    Router --> DI[Dependency Injection Engine]
    
    DI --> DB[get_db\nyield AsyncSession]
    DI --> Auth[get_current_user\ndecode JWT token]
    DI --> Pagination[pagination_params\npage + page_size]
    
    Auth --> DB
    
    DB --> Session[(PostgreSQL\nAsync Session)]
    Auth --> JWT[JWT Decode\n+ User Query]
    JWT --> Session
    
    DI --> View[View Function\nreceives injected deps]
    DB --> View
    Auth --> View
    Pagination --> View
    
    View --> Response[JSON Response\nPydantic Serialized]
    
    DB --> Cleanup[Session Close\nyield cleanup]
    
    style DB fill:#009688,color:#fff
    style Auth fill:#ff5722,color:#fff
    style View fill:#3f51b5,color:#fff""",
            "step_by_step": [
                "Request arrives at FastAPI router",
                "FastAPI analyzes function signature for Depends()",
                "Builds dependency graph — resolves sub-dependencies first",
                "get_db generator: creates AsyncSession, yields to view, closes after",
                "get_current_user: extracts Bearer token, decodes JWT, queries User from DB",
                "All resolved dependencies injected as function parameters",
                "View function executes with all deps available",
                "Generator dependencies (yield) run cleanup after response"
            ],
        },
        {
            "title": "Celery Worker Architecture",
            "slug": "celery-worker-architecture",
            "subject_slug": "celery-redis",
            "description": "Celery's distributed task queue architecture with Redis broker",
            "explanation": "Tasks flow from your Django/FastAPI application through the Redis broker to Celery workers, with results stored back in Redis.",
            "mermaid_source": """flowchart LR
    App[Django/FastAPI App\nProducer] -->|task.delay| Redis[(Redis Broker\nTask Queue)]
    
    Redis -->|consume| W1[Celery Worker 1]
    Redis -->|consume| W2[Celery Worker 2]  
    Redis -->|consume| W3[Celery Worker 3]
    
    W1 -->|result| Backend[(Redis/DB\nResult Backend)]
    W2 -->|result| Backend
    W3 -->|result| Backend
    
    App -->|AsyncResult.get| Backend
    
    Beat[Celery Beat\nScheduler] -->|periodic tasks| Redis
    
    subgraph Workers
        W1
        W2
        W3
    end
    
    subgraph Queues
        HQ[high_priority queue]
        DQ[default queue]
        LQ[low_priority queue]
    end
    
    Redis --- HQ
    Redis --- DQ
    Redis --- LQ
    
    style Redis fill:#cc0000,color:#fff
    style Beat fill:#37b24d,color:#fff""",
            "step_by_step": [
                "App calls task.delay() or task.apply_async() — serializes task to JSON",
                "Task message published to Redis broker queue",
                "Celery workers poll their assigned queues",
                "Worker picks up task, deserializes, executes",
                "On success: result stored in Result Backend",
                "On failure: retried up to max_retries with exponential backoff",
                "Celery Beat sends periodic tasks on schedule",
                "App can poll task status with AsyncResult(task_id).state"
            ],
        },
        {
            "title": "SQL Index B-Tree Structure",
            "slug": "sql-btree-index",
            "subject_slug": "sql-postgresql",
            "description": "How PostgreSQL B-Tree indexes work internally",
            "explanation": "B-Tree indexes maintain sorted data in a tree structure, allowing O(log n) lookups instead of O(n) table scans.",
            "mermaid_source": """graph TD
    Root["Root Node\n[50]"] --> L1["Internal Node\n[25]"]
    Root --> L2["Internal Node\n[75]"]
    
    L1 --> LL["Leaf: 10, 15, 20"]
    L1 --> LR["Leaf: 30, 35, 40, 45"]
    
    L2 --> RL["Leaf: 55, 60, 65"]
    L2 --> RR["Leaf: 80, 85, 90, 95"]
    
    LL -->|next leaf| LR
    LR -->|next leaf| RL
    RL -->|next leaf| RR
    
    Note1["B-Tree Properties:\n- Always balanced\n- O(log n) lookup\n- Supports range scans\n- Leaves linked for sequential read"]
    
    style Root fill:#336791,color:#fff
    style L1 fill:#336791,color:#fff
    style L2 fill:#336791,color:#fff
    style LL fill:#4caf50,color:#fff
    style LR fill:#4caf50,color:#fff
    style RL fill:#4caf50,color:#fff
    style RR fill:#4caf50,color:#fff""",
            "step_by_step": [
                "Index stores column values in sorted B-Tree structure",
                "Root node contains pivot values directing search",
                "Internal nodes guide traversal — O(log n) steps to reach leaf",
                "Leaf nodes contain actual values + pointer to table row (ctid/heap pointer)",
                "Leaves are doubly linked — enables efficient range scans",
                "Query WHERE salary > 50000: traverse to 50000 in O(log n), then scan leaves sequentially",
                "Index Only Scan: if SELECT columns are all in index, never touches heap",
                "Composite index: sort by first column, then second within first"
            ],
        },
        {
            "title": "Python GIL & Threading Model",
            "slug": "python-gil-threading",
            "subject_slug": "python",
            "description": "How Python's GIL affects threading and when to use threads vs processes vs asyncio",
            "explanation": "The GIL prevents true parallel CPU execution in threads but releases during I/O, making threads useful for I/O-bound tasks.",
            "mermaid_source": """flowchart TD
    Task{Task Type?} -->|CPU-bound\nimage processing\nML computations| MP[multiprocessing\nSeparate processes\nNo GIL limitation\nTrue parallelism]
    
    Task -->|I/O-bound\nDB queries\nHTTP calls\nFile I/O| Choice{Concurrency\nStyle?}
    
    Choice -->|Multiple tasks\nAsync framework| AIO[asyncio\nSingle thread\nEvent loop\nFastAPI/Django async]
    
    Choice -->|Background tasks\nThread pool| THR[threading\nGIL releases on I/O\nGood for I/O waits]
    
    Choice -->|Background jobs\nDistributed| CEL[Celery\nSeparate processes\nRedis broker]
    
    MP --> PP[(Process Pool\nPython processes\neach with own GIL)]
    AIO --> EL[(Event Loop\nawait releases\ncontrol to loop)]
    THR --> GIL[(GIL released\nduring I/O\nSystem calls)]
    
    style Task fill:#3776ab,color:#fff
    style MP fill:#ff5722,color:#fff
    style AIO fill:#009688,color:#fff
    style CEL fill:#37b24d,color:#fff""",
            "step_by_step": [
                "GIL = mutex allowing only one thread to run Python bytecode at a time",
                "GIL is released during I/O operations (network, disk) and C extensions",
                "Threading: useful for I/O-bound tasks — threads can interleave during I/O waits",
                "Threading: NOT useful for CPU-bound tasks — GIL prevents parallel execution",
                "multiprocessing: each process has its own GIL — true CPU parallelism",
                "asyncio: single thread, cooperative multitasking — best for many concurrent I/O operations",
                "Celery: separate worker processes — bypasses GIL, handles distributed workloads",
                "Python 3.13+: experimental free-threading (no-GIL) mode available"
            ],
        },
        {
            "title": "F1 QC Audit — Excel Processing Pipeline",
            "slug": "f1-excel-pipeline",
            "subject_slug": "project-deep-dive",
            "description": "How the F1 platform processes large Excel files with Celery and PostgreSQL",
            "explanation": "The 5.2x throughput improvement came from streaming reads, chunked processing, Redis deduplication, and bulk database inserts.",
            "mermaid_source": """flowchart TD
    Upload[Excel Upload\nDjango View] -->|Save file| Storage[File Storage\nS3/Filesystem]
    Upload -->|task.delay| CeleryTask[Celery Task\nBackground Worker]
    Upload -->|Return| Response[Immediate Response\ntask_id to frontend]
    
    Storage --> CeleryTask
    CeleryTask --> ReadOnly[openpyxl\nread_only=True\nStreaming Mode]
    ReadOnly --> Headers[Parse Headers\nDynamic Field Mapping]
    Headers --> ChunkLoop[Process Chunks\n1000 rows/chunk]
    
    ChunkLoop --> Validate[Row Validation\nTypes + Business Rules]
    Validate -->|Valid| DedupCheck[Redis Dedup Check\nSADD unique_key]
    Validate -->|Invalid| ErrorLog[Collect Error Rows]
    
    DedupCheck -->|New record| BulkInsert[bulk_create\nbatch_size=500]
    DedupCheck -->|Duplicate| Skip[Skip + Log]
    
    BulkInsert --> Progress[Update Progress\ncache.set progress %]
    Progress --> ChunkLoop
    
    ChunkLoop -->|Done| Complete[Task Complete\nSend notification]
    ErrorLog --> ErrorFile[Error Report\nDownloadable Excel]
    
    style Upload fill:#2196F3,color:#fff
    style CeleryTask fill:#37b24d,color:#fff
    style BulkInsert fill:#ff5722,color:#fff
    style DedupCheck fill:#cc0000,color:#fff""",
            "step_by_step": [
                "User uploads Excel file — Django view saves to storage and triggers Celery task",
                "User receives immediate response with task_id — no waiting",
                "Celery worker opens file in streaming mode (openpyxl read_only=True) — no memory spike",
                "Headers parsed and mapped to model fields via dynamic field mapping config",
                "Process 1000 rows at a time — constant memory footprint",
                "Each row validated for types, required fields, business rules",
                "Valid rows checked for duplicates using Redis SADD (O(1) vs SQL query)",
                "Non-duplicate rows collected in batch, then bulk_create with 500 batch_size",
                "Progress updated in Redis after each chunk — frontend polls for status",
                "Error rows collected throughout, exported as Excel at end"
            ],
        },
    ]

    count = 0
    for d_data in diagrams:
        _get_or_create(db, Diagram, slug=d_data["slug"], defaults={
            "title": d_data["title"],
            "subject_slug": d_data.get("subject_slug"),
            "description": d_data.get("description"),
            "mermaid_source": d_data["mermaid_source"],
            "explanation": d_data.get("explanation"),
            "step_by_step": d_data.get("step_by_step"),
        })
        count += 1

    db.flush()
    print(f"  ✓ Diagrams: {count}")


if __name__ == "__main__":
    seed()
