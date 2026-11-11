"""Curated SQL practice bank for the SQL Lab.

Every problem runs against the `sandbox` schema built by ``backend/scripts/init_sandbox.sql``
(search_path=sandbox). ``expected_query`` is the reference solution; the grader compares the
learner's result set with it (row order only when ``order_matters`` is true).

Datasets
  employees : departments, employees, employee_salary_history
  orders    : customers, products, orders, order_items
  banking   : accounts, transactions
  activity  : logins, contact_imports
  learning  : students, courses, enrollments
"""

PROBLEMS = []


def _add(title, slug, difficulty, category, dataset_name, description, expected_query,
         order_matters, hints, explanation):
    PROBLEMS.append({
        "title": title,
        "slug": slug,
        "description": description.strip(),
        "difficulty": difficulty,
        "category": category,
        "dataset_name": dataset_name,
        "expected_query": expected_query.strip(),
        "order_matters": order_matters,
        "hints": hints,
        "explanation": explanation.strip(),
    })


# ═══════════════════════════ BEGINNER ═══════════════════════════

_add(
    "Active Engineers by Salary", "employees-engineering", "beginner", "SELECT / JOIN / ORDER BY", "employees",
    r"""
List the **active** employees who work in the **Engineering** department.

Return `first_name`, `last_name`, `salary`, ordered by `salary` highest first (break ties by `id`).
""",
    r"""
SELECT e.first_name, e.last_name, e.salary
FROM employees e
JOIN departments d ON d.id = e.department_id
WHERE d.name = 'Engineering'
  AND e.is_active
ORDER BY e.salary DESC, e.id
""",
    True,
    ["Employees only store `department_id`; the department name lives in `departments`.",
     "Join the two tables on `departments.id = employees.department_id`, then filter on `departments.name`.",
     "`is_active` is a boolean, so `WHERE e.is_active` is enough. Add `e.id` as the last ORDER BY key so ties are stable."],
    r"""
Approach: join employees to departments (the only place the name is stored), filter on the department name and the boolean flag, then sort. An INNER JOIN is right because we only want employees that have a department; employees with a NULL `department_id` can never match `d.id`, so they are dropped silently, which is exactly what we want here.

Alternatives: you can avoid the join with `WHERE department_id = (SELECT id FROM departments WHERE name = 'Engineering')`. That is fine while the name is unique, but it throws "more than one row returned by a subquery" if two departments ever share a name, whereas the join just returns both. Interviewers like hearing that trade-off.

Pitfalls: `ORDER BY salary DESC` alone is not deterministic when salaries tie (two senior developers earn the same), so always add a unique tie-breaker. Do not compare booleans with `= 'true'` strings.

Performance: `employees(department_id)` is the natural index (foreign keys are not indexed automatically in PostgreSQL). For a tiny table the planner will seq-scan anyway.
""")

_add(
    "Employees Without a Department", "employees-null-department", "beginner", "NULL handling", "employees",
    r"""
Find employees who are not assigned to any department.

Return `id`, `first_name`, `last_name`, `job_title`, ordered by `id`.
""",
    r"""
SELECT id, first_name, last_name, job_title
FROM employees
WHERE department_id IS NULL
ORDER BY id
""",
    True,
    ["NULL means 'unknown', so `department_id = NULL` is never true.",
     "Use the dedicated predicate `IS NULL`."],
    r"""
Approach: `WHERE department_id IS NULL`. Any comparison with NULL (`=`, `<>`, `<`) yields UNKNOWN, and WHERE only keeps rows where the predicate is TRUE, so `= NULL` returns zero rows with no error, a classic silent bug.

Related traps: `department_id <> 1` also excludes the NULL rows (UNKNOWN is filtered out), so "everyone not in department 1" needs `department_id IS DISTINCT FROM 1` or `OR department_id IS NULL`. `COUNT(department_id)` ignores NULLs while `COUNT(*)` does not. `NOT IN (subquery containing NULL)` returns nothing at all (see the departments-with-no-employees problem).

Performance: `IS NULL` can use a normal B-tree index in PostgreSQL. If NULLs are rare and you query them often, a partial index `WHERE department_id IS NULL` is tiny and fast.
""")

_add(
    "Hired in a Date Range", "hired-in-range", "beginner", "WHERE / BETWEEN", "employees",
    r"""
List employees hired from **2022-01-01 to 2023-12-31 inclusive**.

Return `id`, `first_name`, `hire_date`, ordered by `hire_date` then `id`.
""",
    r"""
SELECT id, first_name, hire_date
FROM employees
WHERE hire_date BETWEEN DATE '2022-01-01' AND DATE '2023-12-31'
ORDER BY hire_date, id
""",
    True,
    ["`BETWEEN a AND b` is inclusive on both ends.",
     "`hire_date` is a DATE, so there is no time-of-day to worry about for this column."],
    r"""
Approach: `BETWEEN` on a DATE column. It is shorthand for `>= low AND <= high`, so both endpoints are included.

Pitfall: BETWEEN with TIMESTAMP columns. `order_date BETWEEN '2024-01-01' AND '2024-01-31'` stops at midnight on Jan 31 and silently drops almost all of that day. For timestamps use a half-open range: `>= '2024-01-01' AND < '2024-02-01'`. Many teams use half-open ranges everywhere for that reason.

Performance: a B-tree index on `hire_date` supports this range scan. Do not wrap the column in a function (`WHERE EXTRACT(YEAR FROM hire_date) IN (2022, 2023)`), because that makes the predicate non-sargable and defeats the index.
""")

_add(
    "Customers Named Like 'an'", "customers-name-search", "beginner", "LIKE / ILIKE", "orders",
    r"""
Find customers whose `full_name` contains the letters `an` anywhere, **ignoring case**.

Return `id`, `full_name`, `city`, ordered by `full_name`.
""",
    r"""
SELECT id, full_name, city
FROM customers
WHERE full_name ILIKE '%an%'
ORDER BY full_name
""",
    True,
    ["`%` matches any run of characters (including none) and `_` matches exactly one.",
     "`LIKE` is case-sensitive in PostgreSQL; there is a case-insensitive variant."],
    r"""
Approach: `ILIKE '%an%'` (PostgreSQL's case-insensitive LIKE). The portable alternative is `LOWER(full_name) LIKE '%an%'`.

Pitfalls: a leading wildcard (`'%an%'`) cannot use a plain B-tree index, so on a big table it is a sequential scan. A prefix search (`'An%'`) can use a B-tree (with `text_pattern_ops` or the C collation). For substring search at scale use a `pg_trgm` GIN index. Also remember `_` and `%` are wildcards: to search for a literal underscore escape it (`LIKE '%\_%'`). NULL names would never match (NULL LIKE x is UNKNOWN).

Interview angle: `LIKE` vs `=`: `=` needs an exact match, LIKE a pattern; neither handles typos, which is where trigram or full-text search comes in.
""")

_add(
    "Customers in Selected Cities", "customers-in-cities", "beginner", "IN / NULL handling", "orders",
    r"""
List customers whose city is **Chennai, Mumbai or Delhi**.

Return `id`, `full_name`, `city`, ordered by `city` then `full_name`.
""",
    r"""
SELECT id, full_name, city
FROM customers
WHERE city IN ('Chennai', 'Mumbai', 'Delhi')
ORDER BY city, full_name
""",
    True,
    ["`IN (...)` is shorthand for several `OR city = ...` tests.",
     "Customers with a NULL city can never match an `IN` list."],
    r"""
Approach: `city IN ('Chennai','Mumbai','Delhi')`, equivalent to three ORed equalities.

NULL pitfall: with a NULL city, `city IN (...)` is UNKNOWN so the row is excluded, which is what we want here. The dangerous cousin is `city NOT IN ('Chennai','Mumbai','Delhi')`: it also drops the NULL-city customers (UNKNOWN again), so "everyone outside these cities" silently loses customers whose city is unknown. Write `city IS NULL OR city NOT IN (...)` when you mean it.

Performance: an IN list of constants becomes an index-friendly `= ANY(array)`. Very long lists are better expressed as a join against a VALUES list or a temp table.
""")

_add(
    "Five Most Expensive Products", "top-5-expensive-products", "beginner", "ORDER BY / LIMIT", "orders",
    r"""
Return the **five most expensive products**.

Return `name`, `category`, `price`, highest price first (break ties by `id`).
""",
    r"""
SELECT name, category, price
FROM products
ORDER BY price DESC, id
LIMIT 5
""",
    True,
    ["Sort first, then cut the result with LIMIT.",
     "LIMIT without ORDER BY returns an arbitrary set of rows."],
    r"""
Approach: `ORDER BY price DESC LIMIT 5`. LIMIT is applied after sorting, and without an ORDER BY the rows you get are undefined.

Edge cases: if the 5th and 6th product share a price, `LIMIT 5` picks one of them arbitrarily unless you add a tie-breaker (we use `id`). If the business rule is "include everyone tied for 5th place", use `FETCH FIRST 5 ROWS WITH TIES` (PostgreSQL 13+) or `RANK() OVER (ORDER BY price DESC) <= 5`.

Performance: with an index on `price`, PostgreSQL can walk the index backwards and stop after five rows (top-N heapsort otherwise). Deep OFFSET pagination is the expensive pattern; use keyset pagination (`WHERE (price, id) < (...)`) for large lists.
""")

_add(
    "Distinct Shipping Cities", "distinct-shipping-cities", "beginner", "DISTINCT", "orders",
    r"""
List every city that orders have been shipped to, without repeats.

Return one column `shipping_city`, sorted alphabetically.
""",
    r"""
SELECT DISTINCT shipping_city
FROM orders
ORDER BY shipping_city
""",
    True,
    ["Many orders ship to the same city; you want each city once.",
     "`DISTINCT` applies to the whole selected row, not just the first column."],
    r"""
Approach: `SELECT DISTINCT shipping_city`. DISTINCT de-duplicates entire result rows, so `SELECT DISTINCT a, b` returns unique (a, b) pairs, not unique `a` values. That is the usual misconception.

DISTINCT vs GROUP BY: `SELECT shipping_city FROM orders GROUP BY shipping_city` produces the same result and typically the same plan (HashAggregate or sort + unique). Use GROUP BY when you also need aggregates. `COUNT(DISTINCT x)` counts unique non-NULL values; NULL is treated as one group by DISTINCT/GROUP BY but ignored by COUNT(DISTINCT).

Performance: DISTINCT forces a sort or hash of all rows; on a large table an index on the column allows an index-only scan with skip-ahead (loose index scan has to be emulated with a recursive CTE in PostgreSQL).
""")
