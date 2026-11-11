"""Curated interview content: SQL & PostgreSQL, and Database Engineering."""


def Q(text, difficulty, easy, technical, interview):
    return {
        "text": text,
        "difficulty": difficulty,
        "answers": {"easy": easy.strip(), "technical": technical.strip(), "interview": interview.strip()},
    }


def T(title, slug, difficulty, order, minutes, description, content, questions):
    content = {k: v.strip() for k, v in content.items()}
    return {
        "title": title, "slug": slug, "difficulty": difficulty, "order_index": order,
        "estimated_minutes": minutes, "description": description,
        "content": content, "questions": questions,
    }


SQL = []
DB = []

# ---------------------------------------------------------------------------
# 1. SQL statement categories
# ---------------------------------------------------------------------------
SQL.append(T(
    "SQL Fundamentals: DDL, DML, DQL, DCL, TCL", "sql-fundamentals", "beginner", 1, 30,
    "The five SQL statement families, and the difference between DELETE, TRUNCATE and DROP.",
    {
        "definition": "SQL statements fall into families by purpose: DDL defines structure (CREATE, ALTER, DROP), DML changes data (INSERT, UPDATE, DELETE), DQL reads data (SELECT), DCL controls access (GRANT, REVOKE) and TCL controls transactions (BEGIN, COMMIT, ROLLBACK, SAVEPOINT).",
        "easy_explanation": "Think of a database as a filing cabinet. DDL builds and rearranges the cabinet itself (drawers, labels). DML puts papers in, edits them or throws them away. DQL is just looking at what is inside. DCL decides who has a key to which drawer. TCL lets you say 'treat this group of changes as one action: either keep all of it or undo all of it'.",
        "analogy": "A library: DDL builds shelves, DML shelves and removes books, DQL is reading, DCL is issuing library cards with permissions, TCL is the checkout desk that either completes a whole batch of loans or cancels it.",
        "technical_explanation": "The categories are a convention rather than a strict grammar. In PostgreSQL, DDL is fully transactional: you can run CREATE TABLE or ALTER TABLE inside BEGIN and ROLLBACK it, which is not true in MySQL where most DDL causes an implicit commit. SELECT is DQL but SELECT ... FOR UPDATE takes row locks, and INSERT ... RETURNING / UPDATE ... RETURNING return rows like a query. TRUNCATE is classed as DDL (it takes an ACCESS EXCLUSIVE lock and does not scan rows), while DELETE is DML (row by row, fires row triggers, generates dead tuples that VACUUM must clean). DROP removes the object entirely. Privileges are managed with GRANT/REVOKE on objects (tables, schemas, functions) and roles.",
        "code_example": """-- DDL
CREATE TABLE accounts (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner      text NOT NULL,
    balance    numeric(12,2) NOT NULL DEFAULT 0 CHECK (balance >= 0)
);
ALTER TABLE accounts ADD COLUMN created_at timestamptz NOT NULL DEFAULT now();

-- DML
INSERT INTO accounts (owner, balance) VALUES ('asha', 500), ('ravi', 300);
UPDATE accounts SET balance = balance + 50 WHERE owner = 'asha';

-- DQL
SELECT owner, balance FROM accounts ORDER BY balance DESC;

-- TCL: transfer is all-or-nothing
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE owner = 'asha';
UPDATE accounts SET balance = balance + 100 WHERE owner = 'ravi';
COMMIT;

-- DCL
CREATE ROLE report_reader NOLOGIN;
GRANT SELECT ON accounts TO report_reader;
REVOKE SELECT ON accounts FROM report_reader;""",
        "code_language": "sql",
        "interview_answer": "SQL is grouped by intent. DDL (CREATE, ALTER, DROP, TRUNCATE) defines schema. DML (INSERT, UPDATE, DELETE, MERGE) modifies rows. DQL is SELECT. DCL (GRANT, REVOKE) manages privileges. TCL (BEGIN, COMMIT, ROLLBACK, SAVEPOINT) groups statements into atomic units. A useful PostgreSQL point: DDL is transactional, so a failed migration can be rolled back entirely, which MySQL cannot do. Follow-up: 'Where does TRUNCATE sit?' It is DDL-like: it empties the table without scanning rows, takes an ACCESS EXCLUSIVE lock, and can be rolled back in PostgreSQL, but it does not fire row-level DELETE triggers.",
    },
    [
        Q("What are DDL, DML, DQL, DCL and TCL? Give examples of each.", "beginner",
          "They are five groups of SQL commands, sorted by what they do. DDL (CREATE, ALTER, DROP) builds the structure, like constructing shelves. DML (INSERT, UPDATE, DELETE) changes the stuff on the shelves. DQL (SELECT) only reads. DCL (GRANT, REVOKE) decides who is allowed in. TCL (BEGIN, COMMIT, ROLLBACK) bundles changes so they succeed or fail together.",
          """DDL (Data Definition Language) defines or changes objects: CREATE TABLE, ALTER TABLE, DROP INDEX, TRUNCATE. DML (Data Manipulation Language) changes rows: INSERT, UPDATE, DELETE, and MERGE in PostgreSQL 15+. DQL (Data Query Language) is SELECT. DCL (Data Control Language) manages permissions: GRANT and REVOKE. TCL (Transaction Control Language) manages transaction boundaries: BEGIN, COMMIT, ROLLBACK, SAVEPOINT, ROLLBACK TO SAVEPOINT.

```sql
CREATE TABLE t (id int PRIMARY KEY);   -- DDL
INSERT INTO t VALUES (1);              -- DML
SELECT * FROM t;                       -- DQL
GRANT SELECT ON t TO some_role;        -- DCL
BEGIN; DELETE FROM t; ROLLBACK;        -- TCL around DML
```

In PostgreSQL even DDL participates in transactions, so DDL can be rolled back. Some people fold DQL into DML; the classification is conventional, not part of the standard grammar.""",
          """One-line definition: the five categories classify SQL by purpose - structure, change, read, access control, transaction control.

How it works: DDL (CREATE/ALTER/DROP/TRUNCATE) changes the catalog. DML (INSERT/UPDATE/DELETE/MERGE) changes rows. DQL is SELECT. DCL is GRANT/REVOKE. TCL is BEGIN/COMMIT/ROLLBACK/SAVEPOINT.

Example:
```sql
CREATE TABLE orders (id bigint PRIMARY KEY, total numeric NOT NULL);
BEGIN;
INSERT INTO orders VALUES (1, 99.50);
SAVEPOINT s1;
UPDATE orders SET total = -1 WHERE id = 1;
ROLLBACK TO s1;
COMMIT;
GRANT SELECT ON orders TO analyst;
```

Trade-offs and pitfalls: the categories are a teaching convention. SELECT ... FOR UPDATE is DQL syntactically but takes locks; TRUNCATE is DDL-ish but behaves like a fast bulk delete. In PostgreSQL DDL is transactional, in MySQL it implicitly commits.

Likely follow-up: 'Is TRUNCATE DDL or DML?' Usually classed as DDL because it does not scan rows or fire row-level triggers and takes an ACCESS EXCLUSIVE lock."""),
        Q("What is the difference between DELETE, TRUNCATE and DROP?", "beginner",
          "DELETE removes the rows you pick, one at a time, and you can undo it before commit. TRUNCATE wipes every row in the table in one fast move but keeps the empty table. DROP throws away the whole table, rows and structure both. It is like removing selected pages, ripping out all pages but keeping the binder, or throwing the whole binder away.",
          """DELETE is DML: it accepts a WHERE clause, visits each matching row, marks it dead (MVCC), fires row-level triggers, honours ON DELETE foreign key actions, and can use RETURNING. Space is reclaimed later by VACUUM. TRUNCATE is bulk: no WHERE, no row scan, it swaps in new empty storage, takes an ACCESS EXCLUSIVE lock, does not fire ON DELETE row triggers (it fires TRUNCATE triggers), and fails if other tables reference it via foreign key unless you add CASCADE. Add RESTART IDENTITY to reset sequences. In PostgreSQL TRUNCATE is transactional and MVCC-safe. DROP TABLE removes the table, its indexes, triggers and data; dependents block it unless CASCADE.

```sql
DELETE FROM logs WHERE created_at < now() - interval '90 days';
TRUNCATE TABLE staging_import RESTART IDENTITY;
DROP TABLE IF EXISTS tmp_report;
```""",
          """One-line definition: DELETE removes chosen rows, TRUNCATE removes all rows quickly, DROP removes the table itself.

How it works: DELETE is row-by-row DML. Each deleted row becomes a dead tuple until VACUUM reclaims it, row triggers fire, and a WHERE clause limits scope. TRUNCATE discards the table's data files and replaces them with empty ones; no WHERE, no row triggers, ACCESS EXCLUSIVE lock. DROP deletes the object and everything attached to it.

Example:
```sql
DELETE FROM orders WHERE status = 'cancelled' RETURNING id;
TRUNCATE orders, order_items RESTART IDENTITY;
DROP TABLE orders CASCADE;
```

Pitfalls: a huge DELETE bloats the table and generates lots of WAL, so for archiving use partitions and drop old partitions. TRUNCATE blocks even readers while it runs and cannot target a table referenced by a foreign key unless you truncate both or use CASCADE. In PostgreSQL TRUNCATE and DROP are rollback-able inside a transaction, unlike in Oracle or MySQL.

Follow-up: 'Does TRUNCATE reset auto-increment?' Only with RESTART IDENTITY in PostgreSQL; by default sequences keep their values."""),
        Q("What does a transaction do, and what are COMMIT, ROLLBACK and SAVEPOINT?", "beginner",
          "A transaction is a group of statements treated as one unit. COMMIT says 'make all of this permanent'. ROLLBACK says 'forget all of it'. A SAVEPOINT is a bookmark inside the transaction so you can undo only the part after the bookmark. A bank transfer is the classic case: debit and credit must both happen or neither.",
          """BEGIN starts a transaction (PostgreSQL otherwise autocommits each statement). COMMIT makes changes durable and visible to others; ROLLBACK discards them. SAVEPOINT name marks a point; ROLLBACK TO SAVEPOINT name undoes work after it while keeping the transaction open; RELEASE SAVEPOINT name forgets the mark. If any statement errors in PostgreSQL, the transaction enters an aborted state and every later statement fails with 'current transaction is aborted' until you ROLLBACK or ROLLBACK TO a savepoint taken before the error. Savepoints are what ORMs use for nested 'atomic' blocks.

```sql
BEGIN;
INSERT INTO accounts(owner, balance) VALUES ('x', 10);
SAVEPOINT before_risky;
INSERT INTO accounts(owner, balance) VALUES ('y', -5); -- violates CHECK
ROLLBACK TO before_risky;
COMMIT;  -- only the first insert is kept
```""",
          """One-line definition: a transaction is an atomic unit of work; COMMIT persists it, ROLLBACK discards it, SAVEPOINT allows partial rollback.

How it works: after BEGIN, changes are visible only to your session until COMMIT. Durability comes from the write-ahead log flushed at commit. An error aborts the whole transaction in PostgreSQL, so you either roll back or roll back to a savepoint.

Example:
```sql
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
```

Trade-offs and pitfalls: long-running open transactions hold locks and prevent VACUUM from removing dead rows, so keep them short. Each savepoint opens a subtransaction, and heavy use (hundreds per transaction) can hurt performance.

Follow-up: 'What happens if the connection drops before COMMIT?' The server rolls the transaction back, so nothing is applied."""),
        Q("What is the difference between CHAR, VARCHAR and TEXT, and between INT and BIGINT/NUMERIC in PostgreSQL?", "beginner",
          "CHAR(n) always pads to n characters, VARCHAR(n) allows up to n, and TEXT has no limit. In PostgreSQL all three are stored the same efficient way, so TEXT is usually fine. For numbers, INT is a medium whole number, BIGINT is a much bigger one, and NUMERIC is exact decimal math, which is what you want for money.",
          """In PostgreSQL, text, varchar(n) and char(n) all use the same varlena storage; there is no performance advantage to varchar(n). char(n) pads with spaces, which is rarely useful. Use text plus a CHECK (length(col) <= n) if you need a limit. integer is 4 bytes (about +/-2.1 billion), bigint 8 bytes, smallint 2 bytes. numeric(p,s) is exact arbitrary precision decimal; real and double precision are binary floating point and give results like 0.1+0.2 <> 0.3, so never use them for money. Prefer timestamptz over timestamp for instants, and identity columns (GENERATED ... AS IDENTITY) over serial in new schemas.

```sql
SELECT 0.1::double precision + 0.2::double precision = 0.3::double precision AS float_eq,  -- false
       0.1::numeric + 0.2::numeric = 0.3::numeric AS numeric_eq;                          -- true
```""",
          """One-line definition: PostgreSQL has fixed-width and variable-width character types and exact vs approximate numerics, and choosing correctly avoids bugs.

How it works: char(n) is blank-padded and compared ignoring trailing spaces; varchar(n) enforces a maximum length; text is unlimited. Internally they share the same storage, so varchar(255) is not faster than text. Integers are fixed width; numeric is exact and slower; float types are approximate.

Example:
```sql
CREATE TABLE payments (
    id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    note   text CHECK (length(note) <= 200),
    amount numeric(12,2) NOT NULL
);
```

Pitfalls: using float for money gives rounding drift; using int for an ID on a high-volume table can overflow at 2,147,483,647, and changing to bigint later rewrites the table. Use timestamptz so values are stored as UTC instants.

Follow-up: 'When would you use varchar(n)?' When the limit is a real business rule that should be enforced by the type, such as a 2-letter country code, though a CHECK on text achieves the same."""),
    ],
))

# ---------------------------------------------------------------------------
# 2. Constraints & keys
# ---------------------------------------------------------------------------
SQL.append(T(
    "Constraints and Keys", "sql-constraints-keys", "beginner", 2, 35,
    "Primary, foreign, unique, check and not-null constraints; surrogate vs natural keys; cascading actions.",
    {
        "definition": "Constraints are declarative rules the database enforces on every write: PRIMARY KEY, FOREIGN KEY, UNIQUE, NOT NULL, CHECK and EXCLUDE. Keys are the columns that identify rows (primary, candidate, foreign) and link tables.",
        "easy_explanation": "Constraints are the bouncers of your table. NOT NULL says 'this cannot be empty', UNIQUE says 'no two rows can share this value', PRIMARY KEY says 'this is the one official ID of the row', FOREIGN KEY says 'this value must exist in another table', and CHECK says 'this value must satisfy a rule, like price above zero'. Because the database enforces them, bad data cannot slip in from any application.",
        "analogy": "A primary key is a passport number, a foreign key is the passport number written on a visa application (it must belong to a real passport), and a unique constraint is 'one visa per email address'.",
        "technical_explanation": "A PRIMARY KEY is UNIQUE plus NOT NULL and there can be only one per table; PostgreSQL implements it with a unique B-tree index. UNIQUE allows multiple NULLs by default because NULLs are not equal to each other (use NULLS NOT DISTINCT in PostgreSQL 15+ to change this). A FOREIGN KEY references a unique or primary key of the parent; the referencing column is not indexed automatically, so you should add an index to make joins and parent deletes fast. Referential actions: NO ACTION (default, checked at end of statement), RESTRICT, CASCADE, SET NULL, SET DEFAULT. Constraints can be DEFERRABLE INITIALLY DEFERRED to be checked at COMMIT. CHECK constraints must be deterministic per row and cannot reference other rows. EXCLUDE constraints (backed by GiST) prevent overlapping ranges, for example double-booked rooms.",
        "code_example": """CREATE TABLE customers (
    id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email text NOT NULL UNIQUE,
    name  text NOT NULL
);

CREATE TABLE orders (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    total       numeric(12,2) NOT NULL CHECK (total >= 0),
    status      text NOT NULL DEFAULT 'new' CHECK (status IN ('new','paid','shipped','cancelled'))
);
CREATE INDEX orders_customer_id_idx ON orders (customer_id);

-- Prevent overlapping bookings for the same room
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE TABLE bookings (
    room_id int NOT NULL,
    during  tstzrange NOT NULL,
    EXCLUDE USING gist (room_id WITH =, during WITH &&)
);""",
        "code_language": "sql",
        "interview_answer": "Constraints move data integrity into the database so every client is protected. PRIMARY KEY identifies a row and implies UNIQUE NOT NULL. FOREIGN KEY guarantees the referenced parent row exists. UNIQUE prevents duplicates (but permits several NULLs by default). CHECK enforces row-level rules. NOT NULL forbids missing values. PostgreSQL does not index foreign key columns automatically, so create the index yourself. Follow-up: 'Why not enforce this in application code only?' Because multiple services, scripts and race conditions bypass app checks; only a constraint is race-free.",
    },
    [
        Q("What is the difference between a primary key and a unique key?", "beginner",
          "A primary key is the official ID of a row: it cannot be empty and there can only be one per table. A unique key also stops duplicates but you can have many of them in a table, and by default they may contain empty (NULL) values. Think of the national ID number versus an email address that must also be one per person.",
          """A table has at most one PRIMARY KEY, which is UNIQUE and NOT NULL, and is the default target for foreign keys. A table can have many UNIQUE constraints. In PostgreSQL a UNIQUE column accepts multiple NULLs because NULL = NULL is not true, unless you declare UNIQUE NULLS NOT DISTINCT (PostgreSQL 15+). Both are implemented with a unique B-tree index. A foreign key may reference either a primary key or any unique constraint. Candidate keys are all minimal column sets that could be the primary key; you pick one as primary and the rest become UNIQUE.

```sql
CREATE TABLE users (
    id    bigint PRIMARY KEY,
    email text UNIQUE,          -- many NULL emails allowed
    phone text UNIQUE NULLS NOT DISTINCT  -- at most one NULL
);
```""",
          """One-line definition: both guarantee uniqueness, but a primary key is the single, non-null row identifier, while unique constraints are additional alternate keys.

How it works: each is backed by a unique B-tree index. The primary key is NOT NULL by definition and there is one per table. UNIQUE columns may be nullable, and PostgreSQL treats NULLs as distinct so several NULLs are allowed (NULLS NOT DISTINCT in version 15+ changes that).

Example:
```sql
CREATE TABLE employees (
    id    bigint PRIMARY KEY,
    email text NOT NULL UNIQUE,
    ssn   text UNIQUE
);
```

Pitfalls: composite uniqueness needs a multi-column constraint, UNIQUE (tenant_id, email), not two separate ones. Do not choose a mutable natural value as primary key because every referencing table must be updated when it changes.

Follow-up: 'Can a foreign key reference a unique column?' Yes, any column set with a unique constraint or unique index can be referenced."""),
        Q("Surrogate key vs natural key: which would you choose for a primary key?", "intermediate",
          "A natural key is a real-world value like an email or passport number. A surrogate key is a made-up ID like 1, 2, 3 or a UUID that has no meaning. Natural values can change or turn out not to be unique, so most teams use a meaningless ID as the primary key and put a unique constraint on the natural value.",
          """Natural keys carry business meaning (ISO country code, ISBN) and avoid an extra column but can change, be reused, be wrongly entered, or be composite and wide, which bloats every foreign key and index referencing them. Surrogate keys (bigint identity, UUID) are stable, narrow and meaningless. The usual approach is a surrogate primary key plus a UNIQUE constraint on the natural key. bigint identity is compact and index-friendly because values are sequential; random UUIDv4 causes scattered B-tree inserts and larger indexes, while time-ordered UUIDv7 (native uuidv7() in PostgreSQL 18) keeps locality. Small stable lookup tables (country codes, currencies) are fine with natural keys.

```sql
CREATE TABLE products (
    id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku text NOT NULL UNIQUE
);
```""",
          """One-line definition: a natural key is a business attribute used as identifier; a surrogate key is a system-generated identifier with no business meaning.

How it works: foreign keys copy the primary key into child tables and their indexes. A narrow, immutable surrogate key keeps those copies small and never needs cascading updates. The natural identifier is still protected with a UNIQUE constraint so business rules hold.

Example:
```sql
CREATE TABLE customers (
    id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email text NOT NULL UNIQUE
);
```

Trade-offs: surrogate keys add a column and a join may be needed to see the business value; natural keys can be changed by the business (emails, phone numbers, even national IDs). UUIDs are good for distributed ID generation and for not exposing counts, but random UUIDv4 fragments indexes; prefer time-ordered UUIDs if using them.

Follow-up: 'Would you ever use a natural key?' Yes for small immutable reference data such as ISO currency codes, where the code is itself the stable identifier."""),
        Q("How do foreign keys work, and what do ON DELETE CASCADE, SET NULL and RESTRICT do?", "practical",
          "A foreign key says 'this value must point to a real row in another table', like an order must belong to a real customer. The ON DELETE option decides what happens to child rows when the parent is deleted: CASCADE deletes them too, SET NULL blanks the link, RESTRICT refuses the delete while children exist.",
          """A FOREIGN KEY (child_col) REFERENCES parent(col) makes PostgreSQL check, on every insert/update of the child and every delete/update of the parent, that a matching parent row exists. ON DELETE actions: NO ACTION (default; error at end of statement, can be deferred), RESTRICT (error immediately, cannot be deferred), CASCADE (delete child rows), SET NULL / SET DEFAULT (modify the child column). ON UPDATE works the same for key changes. The referenced column needs a unique index but the referencing column is NOT indexed automatically; without an index, deleting a parent row sequentially scans the child table and cascades are slow. Cascades fire silently, so CASCADE on large relationships can delete far more than expected; many teams prefer RESTRICT plus explicit deletes or soft deletes.

```sql
CREATE TABLE order_items (
    order_id bigint NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sku      text   NOT NULL,
    qty      int    NOT NULL CHECK (qty > 0),
    PRIMARY KEY (order_id, sku)
);
CREATE INDEX ON order_items (sku);
```""",
          """One-line definition: a foreign key is a constraint guaranteeing every value in a child column matches an existing key in the parent table, which is referential integrity.

How it works: PostgreSQL checks the relationship on child writes and on parent deletes/updates, and applies the declared action. CASCADE deletes children, SET NULL clears them, RESTRICT or NO ACTION raise an error. Constraints can be DEFERRABLE to allow temporary violations inside a transaction.

Example:
```sql
ALTER TABLE orders
  ADD CONSTRAINT orders_customer_fk
  FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT;
CREATE INDEX ON orders (customer_id);
```

Pitfalls: always index the referencing column, otherwise parent deletes and joins scan the child. CASCADE is convenient for owned data like order_items but dangerous for shared data. Adding an FK to a big table takes locks; use ADD CONSTRAINT ... NOT VALID then VALIDATE CONSTRAINT to avoid long blocking.

Follow-up: 'RESTRICT vs NO ACTION?' Both block deletion; RESTRICT checks immediately and cannot be deferred, NO ACTION is checked at end of statement and can be deferred."""),
        Q("What is a CHECK constraint, and how is it different from enforcing a rule in the application?", "practical",
          "A CHECK constraint is a rule attached to a column or table, such as 'price must be greater than zero'. The database rejects any insert or update that breaks it, no matter which program sent it. Application checks can be skipped by another service, a script, or a bug; the database rule cannot.",
          """CHECK (boolean_expression) is evaluated for each inserted or updated row; the row is rejected if the expression is FALSE, but accepted if it is TRUE or NULL (so combine with NOT NULL when needed). The expression may use only that row's columns and immutable functions, not subqueries or other tables (use triggers, FKs or EXCLUDE for cross-row rules). Add constraints on existing large tables with NOT VALID then VALIDATE CONSTRAINT to avoid a long exclusive scan. Constraints are visible in the catalog and documented in the schema, which makes them self-enforcing documentation.

```sql
ALTER TABLE orders ADD CONSTRAINT total_nonneg CHECK (total >= 0) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT total_nonneg;

-- CHECK passes on NULL!
CREATE TABLE t (age int CHECK (age > 0));
INSERT INTO t VALUES (NULL);  -- succeeds
```""",
          """One-line definition: a CHECK constraint is a per-row boolean rule enforced by the database on every INSERT and UPDATE.

How it works: PostgreSQL evaluates the expression for each written row and raises an error if it is false. A NULL result counts as pass, so NOT NULL must be declared separately if NULL is not allowed.

Example:
```sql
CREATE TABLE products (
    id    bigint PRIMARY KEY,
    price numeric(10,2) NOT NULL CHECK (price > 0),
    discount_pct int CHECK (discount_pct BETWEEN 0 AND 100)
);
```

Trade-offs: constraints give race-free, universal enforcement across all clients, while app validation gives friendlier messages. Use both: the app for UX, the database as the last line of defence. Limits: CHECK cannot look at other rows or tables; use a unique index, FK, exclusion constraint or trigger for those.

Follow-up: 'How do you add a CHECK to a billion-row table safely?' Add it NOT VALID (instant, enforces new writes), then VALIDATE CONSTRAINT, which scans without blocking writes for long."""),
    ],
))

# ---------------------------------------------------------------------------
# 3. Joins
# ---------------------------------------------------------------------------
SQL.append(T(
    "SQL Joins", "sql-joins", "practical", 3, 50,
    "INNER, LEFT, RIGHT, FULL, CROSS and self joins; anti-joins; ON vs WHERE; join algorithms.",
    {
        "definition": "A JOIN combines rows from two or more tables based on a related column. INNER JOIN keeps only matching pairs; LEFT, RIGHT and FULL OUTER joins also keep unmatched rows from one or both sides, filling the missing side with NULL; CROSS JOIN produces every combination.",
        "easy_explanation": "Imagine two lists: customers and orders. An INNER JOIN gives you only customers who actually have orders, side by side with those orders. A LEFT JOIN gives you every customer, and for those with no orders the order columns are just blank. A FULL JOIN keeps everyone from both lists, blank where there is no partner. A CROSS JOIN pairs every customer with every possible item, like a menu of all combinations.",
        "analogy": "Matching guests to seats at a wedding: INNER shows only guests who have a seat, LEFT shows all guests (seatless ones get a blank), FULL shows all guests and all empty seats, CROSS tries every guest in every seat.",
        "technical_explanation": "Logically a join is a filtered Cartesian product. The planner picks a physical algorithm: Nested Loop (for each outer row probe the inner, best with an index on the inner side and few outer rows), Hash Join (build a hash table on the smaller input, probe with the other; equality joins only, needs enough work_mem) and Merge Join (both inputs sorted on the key; good for large pre-sorted inputs). For outer joins, the placement of predicates matters: a condition on the nullable side in WHERE turns a LEFT JOIN into an INNER JOIN because NULL fails the comparison, while the same condition in ON keeps the preserved rows. An anti-join (rows with no match) is written either LEFT JOIN ... WHERE right.key IS NULL or NOT EXISTS, and PostgreSQL plans both as a Hash/Merge Anti Join. Joining on columns with duplicates multiplies rows (fan-out), a common source of inflated SUMs.",
        "code_example": """CREATE TEMP TABLE customers (id int PRIMARY KEY, name text);
CREATE TEMP TABLE orders (id int PRIMARY KEY, customer_id int, total numeric);
INSERT INTO customers VALUES (1,'Asha'),(2,'Ravi'),(3,'Meera');
INSERT INTO orders VALUES (10,1,250),(11,1,100),(12,2,75);

-- INNER: only customers with orders
SELECT c.name, o.total FROM customers c JOIN orders o ON o.customer_id = c.id;

-- LEFT: all customers, NULL total for Meera
SELECT c.name, o.total FROM customers c LEFT JOIN orders o ON o.customer_id = c.id;

-- Anti-join: customers who never ordered
SELECT c.name FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);

-- FULL: reconcile two sources
SELECT c.name, o.id FROM customers c FULL JOIN orders o ON o.customer_id = c.id;

-- CROSS: all combinations
SELECT c.name, s.size FROM customers c CROSS JOIN (VALUES ('S'),('M')) AS s(size);""",
        "code_language": "sql",
        "interview_answer": "A join combines rows from two tables on a condition. INNER returns matches only; LEFT returns all left rows plus matches or NULLs; RIGHT mirrors it; FULL returns everything from both; CROSS returns the Cartesian product; a self join joins a table to itself using aliases. In outer joins, put filters on the right table in ON, not WHERE, or you silently convert it to an INNER join. For 'rows with no match' use NOT EXISTS or LEFT JOIN ... IS NULL. Follow-up: 'How does PostgreSQL execute a join?' With nested loop, hash or merge join, chosen by cost based on row estimates, indexes and sort order.",
    },
    [
        Q("Explain the different types of SQL joins with examples.", "practical",
          "INNER JOIN keeps only rows that match in both tables. LEFT JOIN keeps every row from the left table and fills in blanks (NULL) when there is no match on the right. RIGHT JOIN is the mirror image. FULL JOIN keeps all rows from both sides. CROSS JOIN pairs every row with every row. A self join is a table joined to itself, such as employees and their managers.",
          """Given customers c and orders o: INNER JOIN returns only pairs satisfying ON. LEFT [OUTER] JOIN returns all c rows, with o columns NULL where unmatched. RIGHT JOIN is LEFT with sides swapped (most people just rewrite it as a LEFT). FULL [OUTER] JOIN returns all rows from both, NULL-extending either side. CROSS JOIN has no condition and returns |c| x |o| rows. Self join uses two aliases of one table. NATURAL JOIN and USING (col) are shorthand for equality on same-named columns; NATURAL is discouraged because adding a column can change the meaning. JOIN without a type is INNER.

```sql
SELECT c.name, o.total
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id;

SELECT e.name AS employee, m.name AS manager
FROM employees e
LEFT JOIN employees m ON m.id = e.manager_id;
```""",
          """One-line definition: joins combine rows from multiple tables using a relationship, and the join type controls what happens to unmatched rows.

How it works: INNER keeps matched pairs. LEFT keeps all left rows and NULL-fills the right. RIGHT does the opposite. FULL keeps both. CROSS yields the Cartesian product. A self join uses aliases to relate rows within one table.

Example:
```sql
SELECT c.name, COALESCE(SUM(o.total), 0) AS spent
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.id, c.name;
```

Pitfalls: a join on a non-unique key multiplies rows, which inflates aggregates; a WHERE filter on the right side of a LEFT JOIN turns it into an INNER JOIN; forgetting the join condition accidentally creates a CROSS JOIN. Index the join columns.

Follow-up: 'LEFT JOIN vs RIGHT JOIN?' They are equivalent with tables swapped; most teams standardise on LEFT for readability."""),
        Q("What is the difference between INNER JOIN and LEFT JOIN? When does a LEFT JOIN behave like an INNER JOIN?", "practical",
          "INNER JOIN drops rows that have no partner. LEFT JOIN keeps all rows from the left table, even without a partner. The trap: if you add a filter on the right table in the WHERE clause, rows with blanks get filtered out, so your LEFT JOIN quietly turns into an INNER JOIN.",
          """For unmatched left rows, a LEFT JOIN produces the right-side columns as NULL. A WHERE predicate such as o.status = 'paid' evaluates to NULL (not true) on those rows, so they are removed after the join, giving INNER JOIN semantics. To filter the right table while preserving all left rows, move the predicate into the ON clause. Predicates on the left table are fine in WHERE. The same logic explains why 'o.id IS NULL' in WHERE is the correct way to find unmatched rows (anti-join).

```sql
-- Behaves like INNER JOIN: customers without paid orders vanish
SELECT c.name, o.id FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.status = 'paid';

-- Keeps every customer; only paid orders are attached
SELECT c.name, o.id FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id AND o.status = 'paid';
```""",
          """One-line definition: INNER JOIN returns only matching rows; LEFT JOIN returns all rows from the left table plus matches, with NULLs where there is none.

How it works: after the join, unmatched left rows carry NULLs for right columns. A WHERE condition on a right column is evaluated against those NULLs, fails, and removes the row, so the outer join degenerates into an inner join. Conditions placed in ON are applied while matching, before NULL-extension, so left rows survive.

Example:
```sql
SELECT c.name, COUNT(o.id) AS paid_orders
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id AND o.status = 'paid'
GROUP BY c.id, c.name;
```
This lists every customer, including those with zero paid orders.

Pitfalls: this bug is common in reporting queries and silently drops rows. Use COUNT(o.id), not COUNT(*), so unmatched rows count as 0.

Follow-up: 'How do you find customers with no orders?' LEFT JOIN orders and WHERE o.id IS NULL, or NOT EXISTS; both plan as an anti-join."""),
        Q("How do you find rows in one table that have no matching rows in another (anti-join)? Compare NOT IN, NOT EXISTS and LEFT JOIN / IS NULL.", "intermediate",
          "To find customers who never placed an order you can use NOT EXISTS, LEFT JOIN with a NULL check, or NOT IN. NOT EXISTS and LEFT JOIN are the safe ones. NOT IN breaks in a nasty way if the list contains even one NULL: it then returns no rows at all.",
          """NOT EXISTS (correlated subquery) is NULL-safe and PostgreSQL plans it as a Hash Anti Join or Merge Anti Join. LEFT JOIN ... WHERE right.key IS NULL is equivalent and also becomes an anti-join; choose a right-side column that is NOT NULL (the key). NOT IN (subquery) is three-valued: x NOT IN (1, NULL) evaluates to NULL for any x not equal to 1, so no rows qualify. The planner also cannot use an anti-join for NOT IN, and may fall back to a slow hashed SubPlan or repeated scans on big sets. Rule of thumb: use NOT EXISTS; use NOT IN only on a column declared NOT NULL.

```sql
SELECT c.* FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);

SELECT c.* FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.id IS NULL;
```""",
          """One-line definition: an anti-join returns rows from table A that have no match in table B.

How it works: NOT EXISTS and LEFT JOIN ... IS NULL are both planned by PostgreSQL as an anti-join, which stops probing as soon as a match is found. NOT IN uses three-valued logic: if the subquery returns any NULL, 'x NOT IN (...)' can never be TRUE, so the result is empty.

Example:
```sql
SELECT c.id, c.name
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.id
);
```

Trade-offs: NOT EXISTS is correct with NULLs and efficient. LEFT JOIN/IS NULL is equally good but slightly less readable. NOT IN is only safe when the subquery column is NOT NULL, and it is usually slower.

Follow-up: 'Why does NOT IN return nothing when the list has a NULL?' Because comparing with NULL yields UNKNOWN, and NOT UNKNOWN is UNKNOWN, which WHERE treats as false."""),
        Q("What is a self join? Write a query to list each employee with their manager's name.", "practical",
          "A self join is joining a table to itself, using two nicknames (aliases) so SQL can tell the two copies apart. The typical case is an employees table where each row stores its manager's ID, which is just another employee ID. One copy plays the employee, the other plays the manager.",
          """A self join treats one table as two aliased inputs. For hierarchy, employees(id, name, manager_id) has manager_id referencing employees(id). Use LEFT JOIN so the top-level employee with a NULL manager still appears. Self joins also solve 'compare a row with other rows in the same table' problems, such as employees earning more than their manager or pairs of rows with equal values. For arbitrary depth hierarchies a recursive CTE is the right tool, since each self join only walks one level.

```sql
SELECT e.name AS employee, m.name AS manager
FROM employees e
LEFT JOIN employees m ON m.id = e.manager_id;

-- Employees who earn more than their manager
SELECT e.name FROM employees e
JOIN employees m ON m.id = e.manager_id
WHERE e.salary > m.salary;
```""",
          """One-line definition: a self join joins a table to itself using two aliases, to relate rows within the same table.

How it works: the planner treats e and m as separate inputs of the same table and joins them on e.manager_id = m.id. Use LEFT JOIN to retain rows with no counterpart, such as the CEO.

Example:
```sql
SELECT e.name AS employee, m.name AS manager
FROM employees e
LEFT JOIN employees m ON m.id = e.manager_id
ORDER BY manager NULLS FIRST, employee;
```

Pitfalls: forgetting aliases makes column names ambiguous; a plain INNER join drops the top of the hierarchy. A self join only goes one level up; for full chains or org trees use a recursive CTE. Index manager_id.

Follow-up: 'How would you find all reports under a manager at any depth?' A WITH RECURSIVE query that starts from the manager and repeatedly joins employees on manager_id."""),
        Q("What is a CROSS JOIN and when would you actually use one?", "practical",
          "A CROSS JOIN pairs every row of one table with every row of another, with no matching condition. If there are 3 sizes and 4 colours you get 12 combinations. It is useful for generating combinations or filling in a calendar, but dangerous if you do it by accident on big tables.",
          """CROSS JOIN returns the Cartesian product: m rows x n rows. The comma join FROM a, b without a WHERE condition is the same thing, which is how accidental cross joins happen. Legitimate uses: generating all combinations (product variants, test matrices), pairing every entity with every date from generate_series to build a complete grid so missing days show zero, and LATERAL joins (CROSS JOIN LATERAL) where the right side is a function or subquery depending on the left row, for example 'top 3 orders per customer'.

```sql
-- Complete grid of every store and every day, then LEFT JOIN facts onto it
SELECT s.id AS store_id, d::date AS day
FROM stores s
CROSS JOIN generate_series(date '2025-01-01', date '2025-01-07', interval '1 day') AS d;

-- Top 3 orders per customer
SELECT c.id, o.*
FROM customers c
CROSS JOIN LATERAL (
    SELECT * FROM orders o WHERE o.customer_id = c.id ORDER BY o.total DESC LIMIT 3
) o;
```""",
          """One-line definition: CROSS JOIN produces the Cartesian product of two tables, every row paired with every row.

How it works: no join condition is applied, so the result has rows(A) x rows(B) rows. In PostgreSQL FROM a, b without a WHERE is equivalent.

Example:
```sql
SELECT d::date AS day, p.id AS product_id
FROM generate_series(date '2025-03-01', date '2025-03-31', interval '1 day') AS d
CROSS JOIN products p;
```
You then LEFT JOIN actual sales onto this grid so days with no sales show 0 instead of being missing.

Pitfalls: 10,000 x 10,000 rows is 100 million, so an accidental cross join from a missing ON clause can bring a database down. Review any query where row counts explode.

Follow-up: 'What is CROSS JOIN LATERAL?' It lets the right-hand subquery reference columns of the left row, which is the idiomatic PostgreSQL way to get top-N per group."""),
        Q("How does PostgreSQL execute joins? Explain nested loop, hash join and merge join.", "advanced",
          "PostgreSQL has three ways to actually do a join. Nested loop: for each row on one side, look for partners on the other side, fast when one side is tiny or indexed. Hash join: build a quick lookup table from the smaller side, then check the other side against it. Merge join: sort both sides and walk through them together.",
          """Nested Loop: for each outer row, scan or index-probe the inner side. Cost is roughly outer_rows x inner_probe_cost, so it wins when the outer is small and the inner has an index on the join key; it is the only strategy for non-equality joins without special handling. Hash Join: reads the smaller input into an in-memory hash table (spills to disk in batches if it exceeds work_mem x hash_mem_multiplier), then streams the larger input probing it; equality conditions only, startup cost is the build. Merge Join: requires both inputs sorted on the join key (via index or explicit Sort), then advances two pointers; efficient for large sorted inputs and supports full outer joins. The planner chooses by cost using table statistics, so stale statistics (run ANALYZE) lead to bad choices; EXPLAIN ANALYZE shows 'rows=' estimates vs actual.

```sql
EXPLAIN ANALYZE
SELECT c.name, o.total FROM customers c JOIN orders o ON o.customer_id = c.id
WHERE c.id = 42;   -- typically Nested Loop with Index Scans
```""",
          """One-line definition: PostgreSQL implements logical joins with three physical algorithms, nested loop, hash join and merge join, and the planner picks the cheapest by estimated cost.

How it works: Nested Loop probes the inner side once per outer row, ideal for few outer rows plus an index. Hash Join builds a hash table on the smaller input and probes it with the larger, giving linear cost for big equality joins. Merge Join walks two sorted inputs in step, ideal when both are already ordered by an index or the sort is cheap.

Example:
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders o JOIN customers c ON c.id = o.customer_id
WHERE o.created_at > now() - interval '1 day';
```

Pitfalls: wrong row estimates (stale stats, correlated columns) lead to a nested loop over millions of rows. Hash joins spilling to disk show 'Batches: N' greater than 1; raise work_mem for that session. Missing index on the inner join key makes nested loops quadratic.

Follow-up: 'Query suddenly slow after data growth?' Compare estimated vs actual rows in EXPLAIN ANALYZE, run ANALYZE, add the missing index, then re-check the join type."""),
    ],
))

# ---------------------------------------------------------------------------
# 4. Aggregation, GROUP BY, NULL
# ---------------------------------------------------------------------------
SQL.append(T(
    "Aggregation, GROUP BY and NULL Semantics", "sql-aggregation-null", "practical", 4, 45,
    "WHERE vs HAVING, GROUP BY rules, COUNT variants, DISTINCT vs GROUP BY, and three-valued logic with NULL.",
    {
        "definition": "Aggregate functions (COUNT, SUM, AVG, MIN, MAX) collapse many rows into one value per group defined by GROUP BY. SQL uses three-valued logic: any comparison with NULL yields UNKNOWN, which affects filters, joins, NOT IN, and aggregates.",
        "easy_explanation": "GROUP BY sorts rows into piles (for example one pile per department) and the aggregate functions summarise each pile: how many, the total, the average. WHERE removes rows before piling, HAVING removes whole piles after summarising. NULL means 'unknown', not zero or empty, so asking 'is unknown equal to unknown?' gives 'don't know', and that leads to surprises, like COUNT(column) skipping unknowns.",
        "analogy": "Sorting receipts into envelopes by month (GROUP BY), throwing away tiny receipts before sorting (WHERE), and then discarding envelopes with a total below 100 (HAVING). NULL is a receipt with a smudged amount: you cannot say it equals any number.",
        "technical_explanation": "Logical processing order: FROM/JOIN, WHERE, GROUP BY, HAVING, window functions, SELECT, DISTINCT, ORDER BY, LIMIT. That is why WHERE cannot use aggregates or select-list aliases, while ORDER BY can use aliases. In a grouped query every selected column must be in GROUP BY or inside an aggregate (PostgreSQL allows functionally dependent columns if the primary key is grouped). Aggregates ignore NULL inputs except COUNT(*), which counts rows; COUNT(col) counts non-NULL values; COUNT(DISTINCT col) counts distinct non-NULL values; SUM of all NULLs is NULL, so use COALESCE. NULL = NULL is UNKNOWN; use IS [NOT] DISTINCT FROM for null-safe comparison. WHERE keeps only rows where the predicate is TRUE. GROUP BY treats NULLs as one group, and DISTINCT also treats them as equal. The FILTER clause (aggregate FILTER (WHERE ...)) provides conditional aggregation.",
        "code_example": """CREATE TEMP TABLE emp (id int, name text, dept text, salary numeric, bonus numeric);
INSERT INTO emp VALUES
 (1,'A','eng',100,10),(2,'B','eng',120,NULL),(3,'C','ops',80,NULL),(4,'D','ops',90,5),(5,'E',NULL,70,NULL);

-- WHERE filters rows, HAVING filters groups
SELECT dept, COUNT(*) AS headcount, AVG(salary) AS avg_salary
FROM emp
WHERE salary >= 80
GROUP BY dept
HAVING COUNT(*) >= 2;

-- COUNT variants: 5, 2, 5
SELECT COUNT(*), COUNT(bonus), COUNT(DISTINCT dept) FROM emp;

-- NULL-safe comparison and conditional aggregation
SELECT COUNT(*) FILTER (WHERE bonus IS NULL) AS no_bonus,
       SUM(COALESCE(bonus, 0)) AS total_bonus
FROM emp;

-- NOT IN trap: returns zero rows because the list contains NULL
SELECT * FROM emp WHERE id NOT IN (SELECT NULL::int);""",
        "code_language": "sql",
        "interview_answer": "WHERE filters individual rows before grouping and cannot use aggregates; HAVING filters groups after aggregation. Aggregates skip NULLs except COUNT(*). NULL comparisons return UNKNOWN, so use IS NULL, IS DISTINCT FROM, COALESCE, and prefer NOT EXISTS to NOT IN when NULLs are possible. Follow-up: 'Why can I use an alias in ORDER BY but not in WHERE?' Because of logical evaluation order: SELECT is evaluated after WHERE but before ORDER BY.",
    },
    [
        Q("What is the difference between WHERE and HAVING?", "beginner",
          "WHERE picks which individual rows are allowed into the calculation. HAVING picks which groups survive after the calculation is done. So you use WHERE for 'only orders from this year' and HAVING for 'only customers whose total is above 1000'. WHERE cannot use SUM or COUNT; HAVING can.",
          """WHERE is applied to rows after FROM/JOIN and before GROUP BY; it cannot reference aggregates (aggregates do not exist yet) and can use indexes to reduce the rows scanned. HAVING is applied to each group after aggregation and can reference aggregate results. Move any condition that does not depend on an aggregate into WHERE because it reduces work earlier (PostgreSQL may push some HAVING conditions down automatically, but do not rely on it). A HAVING without GROUP BY treats the whole result as one group.

```sql
SELECT customer_id, SUM(total) AS spent
FROM orders
WHERE created_at >= date '2025-01-01'      -- row filter
GROUP BY customer_id
HAVING SUM(total) > 1000;                  -- group filter
```""",
          """One-line definition: WHERE filters rows before grouping; HAVING filters groups after aggregation.

How it works: logical order is FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY. Because WHERE runs before aggregation it cannot use SUM or COUNT; HAVING runs after, so it can.

Example:
```sql
SELECT department_id, COUNT(*) AS n, AVG(salary) AS avg_sal
FROM employees
WHERE status = 'active'
GROUP BY department_id
HAVING COUNT(*) > 5;
```
This keeps active employees only, groups them by department, then keeps departments with more than 5.

Pitfalls: putting a non-aggregate condition in HAVING works but is wasteful, since it filters after the grouping work is done. Also, SELECT aliases are not visible in WHERE or HAVING in PostgreSQL; repeat the expression.

Follow-up: 'Can HAVING be used without GROUP BY?' Yes, then the whole table is one group, for example HAVING COUNT(*) > 0."""),
        Q("What is the difference between COUNT(*), COUNT(column) and COUNT(DISTINCT column)?", "beginner",
          "COUNT(*) counts rows, no matter what is inside them. COUNT(column) counts only rows where that column is not empty (not NULL). COUNT(DISTINCT column) counts the different non-empty values. If a column has 5 rows with values 1, 1, 2, NULL, NULL, you get 5, 3 and 2.",
          """COUNT(*) counts all rows in the group, including rows with NULLs everywhere. COUNT(expr) counts rows where expr IS NOT NULL. COUNT(DISTINCT expr) counts distinct non-NULL values, which requires a sort or hash and is much more expensive on big sets. COUNT(1) is identical to COUNT(*) in PostgreSQL. After a LEFT JOIN, COUNT(*) counts the unmatched row as 1, while COUNT(right.id) gives 0, a classic bug. On a large table PostgreSQL has no stored row count: COUNT(*) must scan a table or index (index-only scans help); for approximate counts, read pg_class.reltuples.

```sql
SELECT COUNT(*) AS all_rows,
       COUNT(bonus) AS with_bonus,
       COUNT(DISTINCT dept) AS departments
FROM emp;

SELECT c.id, COUNT(o.id) AS orders      -- not COUNT(*)
FROM customers c LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.id;
```""",
          """One-line definition: COUNT(*) counts rows, COUNT(col) counts non-NULL values in col, COUNT(DISTINCT col) counts unique non-NULL values.

How it works: aggregates other than COUNT(*) skip NULL inputs. DISTINCT adds a deduplication step by sort or hash.

Example: for bonus values (10, NULL, 10, NULL, 5):
```sql
SELECT COUNT(*), COUNT(bonus), COUNT(DISTINCT bonus) FROM emp;
-- 5, 3, 2
```

Pitfalls: with LEFT JOIN use COUNT(child.id), otherwise customers with no orders show 1 instead of 0. COUNT(*) on a huge table is a scan in PostgreSQL because MVCC means there is no cheap global count; use an estimate from pg_class.reltuples if approximate is acceptable, or maintain a counter table.

Follow-up: 'Is COUNT(1) faster than COUNT(*)?' No, they are identical in PostgreSQL."""),
        Q("How does NULL behave in SQL? What happens with NULL in comparisons, NOT IN, and aggregates?", "intermediate",
          "NULL means 'unknown', not zero and not an empty string. Anything compared with NULL, even NULL itself, gives 'unknown' instead of true or false, and WHERE only keeps rows that are true. That is why you must write IS NULL instead of = NULL, and why NOT IN with a NULL in the list returns nothing.",
          """SQL uses three-valued logic: TRUE, FALSE, UNKNOWN. NULL = NULL, NULL <> 1 and 1 NOT IN (2, NULL) are all UNKNOWN. WHERE, HAVING and JOIN ... ON accept only TRUE. Use IS NULL / IS NOT NULL, and IS [NOT] DISTINCT FROM for null-safe equality. AND/OR rules: FALSE AND UNKNOWN = FALSE, TRUE OR UNKNOWN = TRUE, otherwise UNKNOWN. Aggregates ignore NULLs (except COUNT(*)); SUM/AVG over only NULLs return NULL; AVG divides by the count of non-NULL values, not rows. ORDER BY puts NULLs last in ascending order by default in PostgreSQL (NULLS FIRST/LAST controls it). Arithmetic and concatenation with NULL yields NULL (use COALESCE or concat()). UNIQUE allows multiple NULLs; GROUP BY and DISTINCT treat NULLs as equal.

```sql
SELECT NULL = NULL;                       -- NULL
SELECT 1 NOT IN (2, NULL);                -- NULL (row filtered out)
SELECT 1 IS DISTINCT FROM NULL;           -- true
SELECT AVG(x) FROM (VALUES (10),(NULL)) v(x);  -- 10, not 5
```""",
          """One-line definition: NULL represents a missing or unknown value, and any comparison with it yields UNKNOWN rather than TRUE or FALSE.

How it works: WHERE keeps only rows whose predicate is TRUE, so rows evaluating to UNKNOWN are dropped. Therefore col = NULL never matches; use IS NULL. x NOT IN (list containing NULL) is never TRUE, so the query returns nothing. Aggregates skip NULLs: AVG over (10, NULL) is 10.

Example:
```sql
SELECT * FROM users WHERE deleted_at IS NULL;
SELECT COALESCE(SUM(amount), 0) FROM payments WHERE user_id = 7;
SELECT * FROM a WHERE a.x IS DISTINCT FROM b.x;
```

Pitfalls: NOT IN with NULLs, SUM of an empty set returning NULL, string concatenation with || returning NULL, and unique constraints allowing multiple NULLs. Prefer NOT NULL with defaults when a value is always expected.

Follow-up: 'How do you compare two nullable columns for equality?' Use IS NOT DISTINCT FROM, which treats two NULLs as equal."""),
        Q("What is the difference between DISTINCT and GROUP BY? When would you use each?", "practical",
          "Both can remove duplicate rows. DISTINCT just says 'show each different row once'. GROUP BY says 'make one group for each value, so I can also calculate things like counts and sums per group'. If you only need unique values use DISTINCT; if you need to summarise, use GROUP BY.",
          """SELECT DISTINCT col1, col2 deduplicates the full result rows. GROUP BY col1, col2 produces one row per distinct combination and permits aggregates. Without aggregates they return the same rows, and PostgreSQL usually plans both with HashAggregate or Sort + Unique/GroupAggregate. DISTINCT ON (expr) is a PostgreSQL extension that keeps the first row per group according to ORDER BY, handy for 'latest row per key'. DISTINCT hides join fan-out problems rather than fixing them; investigate the join first. COUNT(DISTINCT x) deduplicates inside an aggregate and can be costly.

```sql
SELECT DISTINCT department_id FROM employees;
SELECT department_id, COUNT(*) FROM employees GROUP BY department_id;

-- latest order per customer (PostgreSQL)
SELECT DISTINCT ON (customer_id) customer_id, id, created_at
FROM orders
ORDER BY customer_id, created_at DESC;
```""",
          """One-line definition: DISTINCT removes duplicate result rows, while GROUP BY partitions rows into groups so aggregates can be computed per group.

How it works: both typically use hashing or sorting to find unique keys. GROUP BY additionally lets you apply COUNT, SUM and so on to each group. Logically DISTINCT runs after SELECT; GROUP BY runs before it.

Example:
```sql
SELECT DISTINCT country FROM customers;
SELECT country, COUNT(*) FROM customers GROUP BY country;
SELECT DISTINCT ON (customer_id) *
FROM orders ORDER BY customer_id, created_at DESC;
```

Pitfalls: sprinkling DISTINCT on a query to hide duplicate rows caused by a bad join hides the bug and costs a sort. SELECT DISTINCT with ORDER BY needs the ordered columns in the select list.

Follow-up: 'Which is faster?' For plain deduplication they usually produce the same plan; check with EXPLAIN. Choose based on intent, and use DISTINCT ON for latest-per-group."""),
        Q("Write a query to find duplicate emails in a users table, and list customers whose total order value exceeds 1000.", "practical",
          "Group rows by the value you suspect is duplicated, count each group, and keep only groups with a count above one using HAVING. The second question is the same idea: group by customer, add up the orders, and keep customers whose total is more than 1000.",
          """Duplicate detection: GROUP BY the key (normalise it, for example lower(email)) and HAVING COUNT(*) > 1. To see the full duplicate rows, join back or use a window COUNT. For totals: join customers to orders, GROUP BY the customer's primary key, HAVING SUM(total) > 1000. In PostgreSQL grouping by customers.id lets you select other customers columns because they are functionally dependent on the primary key.

```sql
SELECT lower(email) AS email, COUNT(*) AS n
FROM users
GROUP BY lower(email)
HAVING COUNT(*) > 1;

SELECT c.id, c.name, SUM(o.total) AS spent
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.id
HAVING SUM(o.total) > 1000
ORDER BY spent DESC;
```""",
          """One-line definition: use GROUP BY with HAVING to filter on group-level facts such as counts and sums.

How it works: grouping by the candidate key collapses rows, COUNT(*) measures each group's size, and HAVING keeps groups with count above 1. The same pattern with SUM answers the totals question.

Example:
```sql
-- duplicates
SELECT lower(email), COUNT(*) FROM users GROUP BY lower(email) HAVING COUNT(*) > 1;

-- big spenders
SELECT c.id, c.name, SUM(o.total) AS spent
FROM customers c JOIN orders o ON o.customer_id = c.id
GROUP BY c.id
HAVING SUM(o.total) > 1000;
```

Pitfalls: normalise case and whitespace before comparing emails; decide whether cancelled orders should be excluded using WHERE o.status <> 'cancelled' before grouping. To prevent duplicates permanently add a unique index on lower(email).

Follow-up: 'How do you see the duplicate rows themselves?' Use a window function: COUNT(*) OVER (PARTITION BY lower(email)) in a subquery and filter where it is greater than 1."""),
    ],
))

# ---------------------------------------------------------------------------
# 5. Subqueries & CTEs
# ---------------------------------------------------------------------------
SQL.append(T(
    "Subqueries and CTEs", "sql-subqueries-ctes", "intermediate", 5, 45,
    "Scalar, correlated and derived-table subqueries, EXISTS vs IN, CTEs and recursive CTEs.",
    {
        "definition": "A subquery is a query nested inside another. A correlated subquery references columns of the outer query and is logically re-evaluated per outer row. A Common Table Expression (CTE, WITH clause) names a subquery for reuse and readability, and WITH RECURSIVE allows queries to traverse hierarchies and graphs.",
        "easy_explanation": "A subquery is a question inside a question: 'show employees who earn more than the average salary', where the average is calculated by an inner query. A correlated subquery asks the inner question again for each row, like 'for each employee, is their salary above their own department's average?'. A CTE gives a name to a step, like writing intermediate results on separate lines instead of one huge nested expression.",
        "analogy": "A CTE is a named scratch pad on the way to the final answer. A recursive CTE is following a family tree: start at one person, then repeatedly add their children until nobody new appears.",
        "technical_explanation": "PostgreSQL's planner can flatten many subqueries: IN and EXISTS subqueries become semi-joins, NOT EXISTS becomes an anti-join, and non-correlated scalar subqueries run once as an InitPlan. A correlated scalar subquery in the SELECT list may execute once per row (SubPlan) unless rewritten as a join or LATERAL. Since PostgreSQL 12, a non-recursive, side-effect-free CTE referenced once is inlined into the parent query; one referenced more than once is materialized, and you can force behaviour with AS MATERIALIZED or AS NOT MATERIALIZED. Before 12 every CTE was an optimization fence. A recursive CTE has an anchor (non-recursive) term UNION [ALL] a recursive term referencing the CTE itself; evaluation iterates on a working table until it yields no new rows. Use UNION (not UNION ALL) or a path array with CYCLE detection to avoid infinite loops on cyclic graphs. Data-modifying CTEs (INSERT/UPDATE/DELETE ... RETURNING) run exactly once and are PostgreSQL-specific.",
        "code_example": """CREATE TEMP TABLE employees (id int PRIMARY KEY, name text, manager_id int, salary numeric, department_id int);
INSERT INTO employees VALUES
 (1,'Ceo',NULL,300,1),(2,'VpEng',1,200,1),(3,'Dev1',2,120,1),(4,'Dev2',2,130,1),(5,'VpOps',1,180,2);

-- Correlated subquery: employees paid above their department average
SELECT e.name FROM employees e
WHERE e.salary > (SELECT AVG(s.salary) FROM employees s WHERE s.department_id = e.department_id);

-- Recursive CTE: full reporting chain below employee 1
WITH RECURSIVE org AS (
    SELECT id, name, manager_id, 0 AS depth, ARRAY[id] AS path
    FROM employees WHERE id = 1
  UNION ALL
    SELECT e.id, e.name, e.manager_id, o.depth + 1, o.path || e.id
    FROM employees e
    JOIN org o ON e.manager_id = o.id
    WHERE NOT e.id = ANY(o.path)           -- cycle guard
)
SELECT depth, name FROM org ORDER BY path;""",
        "code_language": "sql",
        "interview_answer": "A subquery nests one query in another; a correlated one references the outer row. CTEs name intermediate steps for readability and enable recursion. In PostgreSQL 12+ simple CTEs are inlined, multi-referenced ones are materialized, and MATERIALIZED / NOT MATERIALIZED override that. Recursive CTEs have an anchor member plus a recursive member and stop when no new rows appear. Follow-up: 'EXISTS vs IN?' Both become semi-joins and perform about the same in PostgreSQL; EXISTS is the NULL-safe choice for the negated form.",
    },
    [
        Q("What is a correlated subquery? How is it different from a regular subquery?", "intermediate",
          "A regular subquery runs once on its own and hands back a result. A correlated subquery uses a value from the current row of the outer query, so it is conceptually re-run for each outer row. Example: 'employees who earn more than the average of their own department' has to know each employee's department.",
          """An uncorrelated subquery is independent and PostgreSQL evaluates it once (an InitPlan for scalars) or turns it into a join. A correlated subquery references outer columns, so its result depends on the current outer row. The planner often decorrelates EXISTS/IN forms into semi-joins, but a correlated scalar subquery in SELECT or WHERE with an aggregate typically executes as a SubPlan per row, which is O(n) executions; with an index on the inner correlation column that is acceptable for small n, otherwise rewrite with a join to a pre-aggregated derived table or a window function.

```sql
-- correlated: executes per employee (logically)
SELECT e.name, e.salary
FROM employees e
WHERE e.salary > (SELECT AVG(salary) FROM employees WHERE department_id = e.department_id);

-- equivalent with a window function: one pass
SELECT name, salary FROM (
    SELECT name, salary, AVG(salary) OVER (PARTITION BY department_id) AS dept_avg
    FROM employees
) t WHERE salary > dept_avg;
```""",
          """One-line definition: a correlated subquery references columns from the enclosing query, so its result depends on each outer row.

How it works: logically the inner query runs once per outer row with the outer values substituted. PostgreSQL converts EXISTS/IN forms into semi-joins, but correlated scalar subqueries with aggregates often remain per-row SubPlans.

Example:
```sql
SELECT e.name
FROM employees e
WHERE e.salary > (
    SELECT AVG(x.salary) FROM employees x WHERE x.department_id = e.department_id
);
```

Trade-offs: very readable, but can be slow on large tables without an index on the correlation column. Alternatives: join to a grouped derived table, use a window function, or use LATERAL.

Follow-up: 'How do you check whether a subquery runs per row?' EXPLAIN shows 'SubPlan' nodes with loops=N in EXPLAIN ANALYZE; a semi-join appears as Hash Semi Join instead."""),
        Q("What is the difference between IN and EXISTS? Which is faster?", "intermediate",
          "IN checks whether a value appears in a list of values returned by a subquery. EXISTS just asks 'does at least one matching row exist?' and stops at the first hit. For positive checks modern PostgreSQL treats them nearly the same. The big difference shows up with NOT: NOT IN breaks when the list contains NULL, NOT EXISTS does not.",
          """Both IN (subquery) and EXISTS (correlated subquery) are planned as semi-joins in PostgreSQL, so performance is usually identical, and the old advice 'EXISTS is faster for large outer, IN for small' mostly no longer applies. Semantic differences: EXISTS ignores the select list and the NULLs inside; IN compares values using three-valued logic, so NULLs matter, particularly for NOT IN where a single NULL in the subquery makes the whole predicate never true. EXISTS can express multi-column and non-equality correlation easily. Use EXISTS for existence tests, particularly negated ones; use IN for short literal lists or simple key matching.

```sql
SELECT * FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id AND o.total > 500);

SELECT * FROM customers c
WHERE c.id IN (SELECT customer_id FROM orders WHERE total > 500);
```""",
          """One-line definition: IN tests membership in a set of values; EXISTS tests whether a subquery returns at least one row.

How it works: PostgreSQL rewrites both positive forms into a semi-join, stopping at the first match, so performance is usually the same. They differ in NULL handling: NOT IN returns no rows if the subquery yields a NULL, while NOT EXISTS is unaffected.

Example:
```sql
SELECT c.id FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);
```

Trade-offs: EXISTS handles multi-column correlation and is NULL-safe; IN reads more naturally for literal lists such as status IN ('paid', 'shipped'). Always verify with EXPLAIN rather than relying on folklore, because planners differ across databases and versions.

Follow-up: 'When would NOT IN be safe?' Only if the subquery column is declared NOT NULL or filtered with IS NOT NULL."""),
        Q("What is a CTE (WITH clause) and when would you use it instead of a subquery? Does it affect performance in PostgreSQL?", "intermediate",
          "A CTE is a named temporary result you define at the top of a query with WITH and then use like a table. It makes long queries readable by splitting them into named steps, lets you reuse the same step twice, and is the only way to write recursive queries. In recent PostgreSQL versions it usually does not slow things down.",
          """WITH name AS (subquery) SELECT ... FROM name. Benefits: readability, reuse of a result in multiple places, recursion, and data-modifying pipelines (WITH moved AS (DELETE ... RETURNING *) INSERT ...). Performance: before PostgreSQL 12 every CTE was materialized and acted as an optimization fence (predicates were not pushed in). From 12 on, a non-recursive side-effect-free CTE referenced once is inlined like a subquery; if referenced multiple times it is materialized (computed once). Override with AS MATERIALIZED (compute once, fence the planner, useful to reuse expensive work) or AS NOT MATERIALIZED (force inlining). CTEs are not indexed; a materialized CTE scan has no indexes, so large reused intermediate results may be better as a temp table with an index.

```sql
WITH recent AS (
    SELECT customer_id, SUM(total) AS spent
    FROM orders WHERE created_at >= now() - interval '30 days'
    GROUP BY customer_id
)
SELECT c.name, r.spent FROM customers c JOIN recent r ON r.customer_id = c.id
WHERE r.spent > 500;
```""",
          """One-line definition: a CTE is a named subquery defined with WITH that exists for the duration of one statement, improving readability and enabling recursion.

How it works: the planner treats a CTE used once like an inline subquery (PostgreSQL 12+). A CTE referenced several times is computed once and materialized. You can control this with AS MATERIALIZED or AS NOT MATERIALIZED.

Example:
```sql
WITH monthly AS (
    SELECT date_trunc('month', created_at) AS month, SUM(total) AS revenue
    FROM orders GROUP BY 1
)
SELECT month, revenue, revenue - LAG(revenue) OVER (ORDER BY month) AS change
FROM monthly;
```

Trade-offs: CTEs make complex logic readable and testable step by step. Pitfalls: materialized CTEs are optimization barriers and have no indexes; on PostgreSQL before 12 they always were. Use temp tables for large reused intermediates.

Follow-up: 'CTE vs temp table?' A temp table can be indexed and analysed and lives for the session; a CTE lives for one statement."""),
        Q("How do recursive CTEs work? Write a query to traverse an employee hierarchy.", "advanced",
          "A recursive CTE starts with a base set of rows (for example the CEO) and then repeatedly adds the rows connected to what it found last time (people reporting to those people), until nothing new turns up. It is how SQL walks trees such as org charts, categories and folder structures.",
          """Structure: WITH RECURSIVE cte AS ( anchor_query UNION [ALL] recursive_query_referencing_cte ). Execution: run the anchor into a working table; then repeatedly run the recursive term against the previous iteration's rows, append the results, and stop when an iteration returns no rows. UNION ALL keeps duplicates and is faster; UNION removes duplicates and so also stops simple cycles. For graphs with cycles, track a path array (as in the example), or in PostgreSQL 14+ use the CYCLE clause. Add a depth counter for display and to bound runaway recursion. Index the foreign key (manager_id) because each iteration joins on it. Use ORDER BY path to produce tree order.

```sql
WITH RECURSIVE subordinates AS (
    SELECT id, name, manager_id, 1 AS level
    FROM employees WHERE id = 2
  UNION ALL
    SELECT e.id, e.name, e.manager_id, s.level + 1
    FROM employees e
    JOIN subordinates s ON e.manager_id = s.id
)
SELECT * FROM subordinates ORDER BY level, name;
```""",
          """One-line definition: a recursive CTE is a WITH RECURSIVE query that repeatedly joins its own previous output to walk hierarchical or graph data.

How it works: an anchor member seeds a working table; the recursive member joins the base table to the latest iteration rows; results accumulate; the loop stops when an iteration produces nothing.

Example:
```sql
WITH RECURSIVE chain AS (
    SELECT id, name, manager_id, 0 AS depth FROM employees WHERE id = 1
  UNION ALL
    SELECT e.id, e.name, e.manager_id, c.depth + 1
    FROM employees e JOIN chain c ON e.manager_id = c.id
)
SELECT * FROM chain;
```

Pitfalls: cyclic data causes infinite recursion; guard with a path array, UNION instead of UNION ALL, or the CYCLE clause in PostgreSQL 14+. Index manager_id. Deep trees returned as flat rows need an ordering key (a path array) to render properly. For very frequent tree reads consider materialized paths, closure tables, or the ltree extension.

Follow-up: 'Other uses?' Generating number or date series, bill-of-materials explosion, finding connected components in graphs."""),
    ],
))

# ---------------------------------------------------------------------------
# 6. Window functions
# ---------------------------------------------------------------------------
SQL.append(T(
    "Window Functions", "sql-window-functions", "advanced", 6, 55,
    "ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, running totals, frames and top-N-per-group patterns.",
    {
        "definition": "A window function computes a value for each row using a set of related rows (its window) defined by OVER (PARTITION BY ... ORDER BY ... frame), without collapsing rows the way GROUP BY does.",
        "easy_explanation": "GROUP BY squashes many rows into one summary row. A window function keeps every row and adds an extra column calculated by looking at neighbouring rows: this row's rank within its department, the previous month's sales, or the running total so far. It is like keeping the full class list and adding a column that says 'your position in the class'.",
        "analogy": "A race results sheet: every runner stays on the sheet, and next to each name you add their rank, the gap to the runner ahead (LAG) and the running count of finishers so far.",
        "technical_explanation": "Syntax: func(args) OVER (PARTITION BY p ORDER BY o ROWS|RANGE|GROUPS BETWEEN frame_start AND frame_end). Window functions are evaluated after WHERE/GROUP BY/HAVING and before SELECT-level DISTINCT, ORDER BY and LIMIT, so you cannot filter on them in WHERE; wrap in a subquery or CTE. Ranking: ROW_NUMBER() is unique and arbitrary among ties unless ORDER BY is made deterministic; RANK() gives ties the same rank and leaves gaps (1,1,3); DENSE_RANK() gives ties the same rank with no gaps (1,1,2); NTILE(n) buckets rows. Value functions: LAG/LEAD(expr, offset, default), FIRST_VALUE, LAST_VALUE, NTH_VALUE. When ORDER BY is present and no frame is given, the default frame is RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW, so aggregates become running aggregates, and peers (ties) are included together; LAST_VALUE therefore often needs an explicit frame to UNBOUNDED FOLLOWING. Prefer ROWS frames for running totals with duplicate order keys. Multiple windows can be named with a WINDOW clause. An index matching PARTITION BY + ORDER BY can avoid a sort.",
        "code_example": """CREATE TEMP TABLE sales (id serial, region text, month date, amount numeric);
INSERT INTO sales (region, month, amount) VALUES
 ('north','2025-01-01',100),('north','2025-02-01',150),('north','2025-03-01',150),
 ('south','2025-01-01',80),('south','2025-02-01',60),('south','2025-03-01',200);

SELECT region, month, amount,
       ROW_NUMBER() OVER w                                   AS row_num,
       RANK()       OVER (PARTITION BY region ORDER BY amount DESC) AS rnk,
       DENSE_RANK() OVER (PARTITION BY region ORDER BY amount DESC) AS dense_rnk,
       LAG(amount)  OVER w                                   AS prev_amount,
       amount - LAG(amount) OVER w                           AS change,
       SUM(amount)  OVER (PARTITION BY region ORDER BY month
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM sales
WINDOW w AS (PARTITION BY region ORDER BY month)
ORDER BY region, month;""",
        "code_language": "sql",
        "interview_answer": "Window functions calculate over a set of related rows while keeping every row. OVER defines the window: PARTITION BY splits it into groups, ORDER BY orders within a group, and an optional frame bounds the rows used. ROW_NUMBER is unique, RANK leaves gaps after ties, DENSE_RANK does not. LAG/LEAD read neighbouring rows, and SUM() OVER (ORDER BY ...) gives running totals. They cannot appear in WHERE, so wrap them in a CTE to filter. Follow-up: 'Top N per group?' Rank in a subquery with PARTITION BY group, then filter rank <= N.",
    },
    [
        Q("What is the difference between ROW_NUMBER, RANK and DENSE_RANK?", "intermediate",
          "All three number rows in order. ROW_NUMBER gives every row a different number, even when values tie. RANK gives tied rows the same number and then skips ahead (1, 1, 3). DENSE_RANK gives tied rows the same number and does not skip (1, 1, 2). Think of Olympic medals: two golds mean no silver in RANK, but in DENSE_RANK the next person is still second.",
          """All are ranking window functions with OVER (PARTITION BY ... ORDER BY ...). For scores 90, 90, 80: ROW_NUMBER = 1,2,3 (ties broken arbitrarily unless ORDER BY includes a unique tiebreaker); RANK = 1,1,3 (gap equals the number of tied rows); DENSE_RANK = 1,1,2. Use ROW_NUMBER for deduplication or 'exactly one row per group'; RANK or DENSE_RANK when ties should share a position; DENSE_RANK for 'nth highest distinct value'. Without PARTITION BY the whole result is one window. They need ORDER BY to be meaningful.

```sql
SELECT name, score,
       ROW_NUMBER() OVER (ORDER BY score DESC) AS rn,
       RANK()       OVER (ORDER BY score DESC) AS rnk,
       DENSE_RANK() OVER (ORDER BY score DESC) AS drnk
FROM (VALUES ('a',90),('b',90),('c',80)) AS t(name, score);
```""",
          """One-line definition: ROW_NUMBER, RANK and DENSE_RANK assign positions within an ordered window and differ only in how they treat ties.

How it works: ROW_NUMBER always yields unique sequential numbers. RANK gives equal rows the same number and skips following numbers (1,1,3). DENSE_RANK gives equal rows the same number without gaps (1,1,2).

Example:
```sql
SELECT employee_id, salary,
       RANK()       OVER (ORDER BY salary DESC) AS rnk,
       DENSE_RANK() OVER (ORDER BY salary DESC) AS drnk,
       ROW_NUMBER() OVER (ORDER BY salary DESC, employee_id) AS rn
FROM employees;
```

Pitfalls: ROW_NUMBER with ties is non-deterministic unless the ORDER BY has a unique tiebreaker, so results can change between runs. Use ROW_NUMBER to pick one row per group, DENSE_RANK for nth-highest-value questions, RANK for competition-style ranking.

Follow-up: 'Which for the 2nd highest salary?' DENSE_RANK() = 2, because with ties RANK would skip 2 and ROW_NUMBER would return only one of the tied rows."""),
        Q("How do you find the Nth highest salary? Show the second highest salary with and without window functions.", "intermediate",
          "With a window function, rank all salaries from highest to lowest with DENSE_RANK so equal salaries share a rank, then pick rank N. Without windows, you can use OFFSET to skip the first N-1 distinct salaries, or ask for the highest salary that is lower than the maximum.",
          """Option 1, DENSE_RANK in a subquery (windows cannot be filtered in WHERE directly). Option 2, DISTINCT + ORDER BY + OFFSET N-1 LIMIT 1, which returns no row (NULL via scalar subquery) when fewer than N distinct values exist. Option 3 for N=2: MAX(salary) WHERE salary < (SELECT MAX(salary)). Use DENSE_RANK, not RANK or ROW_NUMBER, so that ties on the top salary do not skip or hide the second distinct value. For per-department Nth highest add PARTITION BY department_id.

```sql
SELECT DISTINCT salary FROM (
    SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS r FROM employees
) t WHERE r = 2;

SELECT (SELECT DISTINCT salary FROM employees ORDER BY salary DESC OFFSET 1 LIMIT 1) AS second_highest;

SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees);
```""",
          """One-line definition: the Nth highest salary is the Nth distinct value in descending order, and DENSE_RANK computes that cleanly.

How it works: DENSE_RANK() OVER (ORDER BY salary DESC) gives equal salaries the same rank with no gaps, so filtering rank = N returns the Nth distinct salary. The non-window alternative skips N-1 distinct values with OFFSET.

Example:
```sql
SELECT salary
FROM (
    SELECT DISTINCT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS r
    FROM employees
) t
WHERE r = 3;
```

Pitfalls: ROW_NUMBER returns the wrong answer when salaries tie; RANK may skip the wanted rank. If fewer than N distinct salaries exist, the window query returns no rows; wrap it in a scalar subquery to get NULL instead if the caller needs one row. For each department, add PARTITION BY department_id.

Follow-up: 'Second highest without windows?' SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees)."""),
        Q("How do you get the top N rows per group, for example the latest order per customer or the top 3 earners per department?", "intermediate",
          "Number the rows inside each group from best to worst using ROW_NUMBER with PARTITION BY the group, then keep only the rows numbered N or lower. You cannot filter on the window function in the same SELECT, so you wrap it in a subquery or CTE first.",
          """Pattern: ROW_NUMBER() (or DENSE_RANK() if ties should all be kept) OVER (PARTITION BY group_col ORDER BY sort_col DESC) in a CTE, then WHERE rn <= N. PostgreSQL-specific alternatives: DISTINCT ON (group_col) for N = 1, and CROSS JOIN LATERAL with ORDER BY ... LIMIT N, which can be much faster with an index on (group_col, sort_col DESC) when there are few groups or you already have the list of groups. Always add a unique tiebreaker to ORDER BY for deterministic results.

```sql
WITH ranked AS (
    SELECT e.*, ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY salary DESC, id) AS rn
    FROM employees e
)
SELECT * FROM ranked WHERE rn <= 3;

SELECT d.id, t.*
FROM departments d
CROSS JOIN LATERAL (
    SELECT * FROM employees e WHERE e.department_id = d.id ORDER BY salary DESC LIMIT 3
) t;
```""",
          """One-line definition: top-N-per-group means ranking rows inside each group and keeping the first N.

How it works: ROW_NUMBER() OVER (PARTITION BY group ORDER BY metric DESC) numbers rows per group; a wrapper query filters rn <= N, because window functions cannot be used in WHERE of the same level.

Example:
```sql
SELECT * FROM (
    SELECT o.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC, id DESC) AS rn
    FROM orders o
) x
WHERE rn = 1;
```

Trade-offs: the window approach scans and sorts everything; for many rows and few groups, CROSS JOIN LATERAL with LIMIT N plus an index on (group, sort) reads only N rows per group. DISTINCT ON is concise for N = 1. Use DENSE_RANK or RANK if tied rows must all be returned.

Follow-up: 'How do you make it deterministic?' Add a unique column to ORDER BY, such as the primary key."""),
        Q("Explain LAG and LEAD. How would you compute month-over-month change?", "intermediate",
          "LAG looks at the previous row and LEAD looks at the next row, using the order you specify. If you order monthly revenue by month, LAG gives last month's revenue next to this month's, so you can subtract to get the change or divide to get the percentage.",
          """LAG(expr [, offset [, default]]) OVER (PARTITION BY ... ORDER BY ...) returns the value from offset rows before the current row within the partition (default offset 1); LEAD looks forward. If no such row exists the result is the default or NULL. Compute growth as (cur - prev) / NULLIF(prev, 0) to avoid division by zero. Missing months produce the previous existing row, not the previous calendar month, so join to generate_series first if gaps matter. Other uses: time between events, detecting changes in status (value <> LAG(value)), and sessionization.

```sql
SELECT month, revenue,
       revenue - LAG(revenue) OVER (ORDER BY month) AS change,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS pct_change
FROM (
    SELECT date_trunc('month', created_at)::date AS month, SUM(total) AS revenue
    FROM orders GROUP BY 1
) m
ORDER BY month;
```""",
          """One-line definition: LAG and LEAD return a column value from a previous or following row within the window's ordering, without a self join.

How it works: LAG(col, n, default) OVER (PARTITION BY p ORDER BY o) reads n rows back in the partition; LEAD reads forward. The first or last row gets the default, or NULL.

Example:
```sql
SELECT month, revenue,
       revenue - LAG(revenue) OVER (ORDER BY month) AS mom_change
FROM monthly_revenue;
```

Pitfalls: the 'previous row' is previous in the ordering, so missing months silently compare against an earlier month; generate a calendar with generate_series and LEFT JOIN to fill gaps. Guard percent change with NULLIF(prev, 0). Before window functions this required an expensive self join.

Follow-up: 'Find users whose status changed?' Compare status with LAG(status) OVER (PARTITION BY user_id ORDER BY changed_at) and filter where they differ."""),
        Q("How do you compute a running total, and what is a window frame?", "advanced",
          "Use SUM with OVER and an ORDER BY: each row then shows the sum of all rows up to itself. The frame is the exact slice of rows around the current one that the function looks at, such as 'from the start up to this row' or 'the last 3 rows' for a moving average.",
          """SUM(x) OVER (ORDER BY d) uses the default frame RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW. With RANGE, rows with equal ORDER BY values (peers) are included together, so duplicate dates give the same running total on each of them. Use ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW for a strict row-by-row running total, and ROWS BETWEEN 2 PRECEDING AND CURRENT ROW for a 3-row moving average. GROUPS frames count peer groups, and RANGE supports interval offsets on date or numeric keys, for example RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW. LAST_VALUE needs ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING, otherwise it just returns the current row's peer group.

```sql
SELECT day, amount,
       SUM(amount) OVER (ORDER BY day, id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total,
       AVG(amount) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7
FROM daily_sales;
```""",
          """One-line definition: a running total is an aggregate window function over an ordered window whose frame runs from the first row to the current one.

How it works: SUM(amount) OVER (ORDER BY day) accumulates in order. The frame clause defines the rows considered for each output row: ROWS counts physical rows, RANGE includes all peers with the same ORDER BY value, GROUPS counts peer groups.

Example:
```sql
SELECT account_id, posted_at, amount,
       SUM(amount) OVER (
           PARTITION BY account_id
           ORDER BY posted_at, id
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS balance
FROM ledger;
```

Pitfalls: with the default RANGE frame, ties in the ORDER BY share the same cumulative value, which surprises people; add a unique tiebreaker and use ROWS. LAST_VALUE with the default frame returns the current row, so specify UNBOUNDED FOLLOWING. Large windows over unsorted data cost a sort; an index on (partition, order) helps.

Follow-up: 'Moving average over the last 7 days?' AVG(x) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), assuming one row per day."""),
    ],
))

# The seed and content validator consume a subject-slug -> topics mapping.
# Keep only subjects with curated topics here so empty collections do not
# deactivate existing content for subjects that are still being authored.
TOPICS = {"sql-postgresql": SQL}
