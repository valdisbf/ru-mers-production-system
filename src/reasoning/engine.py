
# ===========================================================================
#  Matching machinery
# ===========================================================================
import itertools


def is_var(t):
    """
    True if `t` is a variable. Convention: a variable is a string that starts
    with '?'. Everything else (other strings, numbers) is a constant.

    A "fact" or "pattern" is a flat tuple whose first item is usually the
    predicate name and the rest are its arguments, e.g.
        ("at", "obj1", "A")         a ground fact  (no variables)
        ("at", "?o", "?loc")        a pattern      (two variables)

    Examples:
        >>> is_var("?o")
        True
        >>> is_var("obj1")
        False
        >>> is_var("at")
        False
    """
    return isinstance(t, str) and t.startswith("?")

def _walk(t, s):
    """Follow a chain of bindings to the end. If ?x -> ?y and ?y -> "A", then
    walking ?x yields "A". Internal helper for unify/substitute.

        >>> _walk("?x", {"?x": "?y", "?y": "A"})
        'A'
        >>> _walk("?x", {})         # unbound variable walks to itself
        '?x'
    """
    while is_var(t) and t in s:
        t = s[t]
    return t


def unify(pattern, fact, subst):
    """
    Try to make `pattern` and `fact` identical by binding variables. Both are
    flat tuples of the same shape. Either side may contain variables.

    `subst` is a dict of bindings already assumed (pass {} or None to start
    fresh). Returns a new, extended dict of bindings if they can be matched, or
    None if they cannot. The input dict is never modified.

    Read the result as "what each variable must equal for the two to match".

    Examples:
        # a pattern against a ground fact -> binds the pattern's variables
        >>> unify(("at", "?o", "?loc"), ("at", "obj1", "A"), {})
        {'?o': 'obj1', '?loc': 'A'}

        # a constant that disagrees -> no match
        >>> unify(("at", "hand", "B"), ("at", "hand", "A"), {}) is None
        True

        # a variable used twice must take the same value in both places
        >>> unify(("edge", "?x", "?x"), ("edge", "a", "a"), {})
        {'?x': 'a'}
        >>> unify(("edge", "?x", "?x"), ("edge", "a", "b"), {}) is None
        True

        # bindings already assumed are respected and extended
        >>> unify(("at", "?o", "?loc"), ("at", "obj1", "A"), {"?o": "obj1"})
        {'?o': 'obj1', '?loc': 'A'}

        # variable-vs-variable is fine (used by backward chaining)
        >>> unify(("holding", "?a"), ("holding", "?b"), {})
        {'?a': '?b'}
    """
    if subst is None:
        subst = {}
    if len(pattern) != len(fact):
        return None
    r = dict(subst)
    for p, f in zip(pattern, fact):
        p, f = _walk(p, r), _walk(f, r)
        if p == f:
            continue
        if is_var(p):
            r[p] = f
        elif is_var(f):
            r[f] = p
        else:
            return None
    return r

def substitute(pattern, subst):
    """
    Fill a pattern's variables in with their bound values, using the bindings
    in `subst`. Variables that have no binding are left untouched. Typically
    you unify() to get bindings, then substitute() them into another pattern.

    Examples:
        >>> b = unify(("at", "?o", "?loc"), ("at", "obj1", "A"), {})
        >>> b
        {'?o': 'obj1', '?loc': 'A'}
        >>> substitute(("grab", "?o", "?loc"), b)      # -> a ground action name
        ('grab', 'obj1', 'A')

        >>> substitute(("at", "?o", "?loc"), {"?o": "obj1"})   # ?loc still open
        ('at', 'obj1', '?loc')
    """
    return tuple(_walk(t, subst) if is_var(t) else t for t in pattern)



# ===========================================================================
#  WorkingMemory management
#  (this is the "rules for WM management" the engine is built on)
# ===========================================================================
class WorkingMemory:
    """
    The set of facts currently believed, with operations to change it and to
    query it. Facts are ground tuples. Build one from an iterable of facts:

        >>> wm = WorkingMemory([("parent", "mary", "ann"),
        ...                     ("parent", "ann", "sam")])
        >>> wm
        WorkingMemory(2 facts)
    """

    def __init__(self, facts=()):
        self.facts = set(facts)

    def tell(self, fact):
        """
        Assert a fact (add it to memory). Adding one already present does
        nothing. The memory is a set, so there are never duplicates.

            >>> wm = WorkingMemory()
            >>> wm.tell(("empty", "hand"))
            >>> wm.holds(("empty", "hand"))
            True
            >>> wm.tell(("empty", "hand"))      # harmless second time
            >>> len(wm.facts)
            1
        """
        self.facts.add(tuple(fact))

    def retract(self, fact):
        """
        Remove a fact (make it no longer believed). Removing one that isn't
        there does nothing.

            >>> wm = WorkingMemory([("empty", "hand")])
            >>> wm.retract(("empty", "hand"))
            >>> wm.holds(("empty", "hand"))
            False
            >>> wm.retract(("empty", "hand"))   # harmless when absent
        """
        self.facts.discard(tuple(fact))

    def ask(self, pattern, subst=None):
        """
        Find every way `pattern` matches a fact in memory. Yields one binding
        dict per matching fact (see unify). Use it to test a condition or to
        read out values. Order is unspecified (memory is a set).

            >>> wm = WorkingMemory([("parent", "mary", "ann"),
            ...                     ("parent", "mary", "bob"),
            ...                     ("parent", "ann", "sam")])

            # who are mary's children? -> collect the ?c bindings
            >>> sorted(b["?c"] for b in wm.ask(("parent", "mary", "?c")))
            ['ann', 'bob']

            # a fully-ground pattern: zero or one match, usable as a test
            >>> list(wm.ask(("parent", "mary", "ann")))
            [{}]
            >>> list(wm.ask(("parent", "mary", "zzz")))
            []

            # continue from existing bindings (e.g. ?x already fixed to mary)
            >>> sorted(b["?c"] for b in wm.ask(("parent", "?x", "?c"),
            ...                                 {"?x": "mary"}))
            ['ann', 'bob']
        """
        for f in self.facts:
            e = unify(tuple(pattern), f, subst)
            if e is not None:
                yield e

    def holds(self, fact):
        """
        True if this exact ground fact is believed right now. (For a pattern
        with variables, use `ask` instead.)

            >>> wm = WorkingMemory([("at", "obj1", "A")])
            >>> wm.holds(("at", "obj1", "A"))
            True
            >>> wm.holds(("at", "obj1", "B"))
            False
        """
        return tuple(fact) in self.facts

    def snapshot(self):
        """
        Return a copy of the current facts, so you can save the state, change
        memory, and later put it back with `restore`. Handy for exploring an
        action without committing to it.

            >>> wm = WorkingMemory([("at", "obj1", "A")])
            >>> saved = wm.snapshot()
            >>> wm.tell(("holding", "obj2"))      # try something out
            >>> wm.restore(saved)                 # ... and undo it
            >>> wm.holds(("holding", "obj2"))
            False
        """
        return set(self.facts)

    def restore(self, snap):
        """Reset memory to a previously taken `snapshot`. See `snapshot`."""
        self.facts = set(snap)

    def __repr__(self):
        return "WorkingMemory({} facts)".format(len(self.facts))


# ===========================================================================
#  Task 1 (monotonic): forward + backward over the SAME rules.
# ===========================================================================
def forward_chain(wm, rules):
    """
    Repeatedly match each rule's conditions against `wm` and 'tell' its 
    conclusion, until a full pass adds nothing new.

    Hint: to match a rule, match its first condition with wm.ask(...), then the
    next under each resulting binding, and so on (a conjunctive match). For each
    complete binding, substitute() into the conclusion and tell() it.
    Return wm (now containing everything entailed).
    """

    fact_added = True

    # Repeat until a complete pass adds nothing new
    while fact_added:
        
        fact_added = False
        new_facts = set()

        # Go through each rule
        for rule in rules:
            # Find every combination of facts satisfying all its conditions
            conditions = rule['if']

            # Match its first condition with wm.ask, then the next, and so on.
            bindings = match_conditions(wm, conditions)

            for b in bindings:
                # Derive the conclusion; substitute each matching set of bindings into the conclusion using substitute()
                conclusion = substitute(rule['then'], b)

                # Check if the conclusion exists already
                if (conclusion not in wm.facts):
                    new_facts.add(conclusion) # new_facts is a set, so it contains no duplicates
                    fact_added = True

        # Add the new facts to the working memory
        for fact in new_facts:
            wm.tell(fact)

        
        


# ===========================================================================
#  Recursive function to match conditions
# ===========================================================================
def match_conditions(wm, conditions, subst=None):
    """Yield bindings that satisfy every condition."""
    if subst is None:
        subst = {}

    # All conditions have matched successfully.
    if not conditions:
        yield subst
        return

    first, *remaining = conditions

    for bindings in wm.ask(first, subst):
        yield from match_conditions(wm, remaining, bindings)


def backward_chain(wm, rules, query, subst=None):
    """
    Goal-driven. Establish `query` (a possibly-variabled pattern) either because
    it matches a fact in `wm`, or because some rule concludes it and all that
    rule's conditions can, recursively, be established. Yield each binding under
    which `query` holds. Bound the recursion so recursive rules terminate.

    Hint: before using a rule, rename its variables to fresh ones
    (e.g. add a unique suffix). Otherwise a recursive rule like `ancestor` reuses
    the same variable names at different depths and clashes with itself, so you
    will only ever get the shallowest answer.
    """
    query = tuple(query)
    qvars = [t for t in query if is_var(t)]
    counter = itertools.count(1)
    seen = set()
    for s in _prove([(query, 0)], dict(subst or {}), wm, rules, 25, counter):
        answer = {v: _walk(v, s) for v in qvars}
        key = tuple(sorted(answer.items()))
        if key not in seen:
            seen.add(key)
            yield answer


def provable(wm, rules, query, subst=None, max_depth=25):
    """True if `query` can be established (see backward_chain)."""
    return next(backward_chain(wm, rules, query, subst), None) is not None

def _prove(goals, subst, wm, rules, max_depth, counter):
    """Prove a list of (goal, depth) pairs left to right; yield each binding."""
    if not goals:
        yield subst
        return
    (goal, depth), rest = goals[0], goals[1:]
    goal = substitute(goal, subst)

    # 1) the goal is a known fact
    for b in wm.ask(goal, subst):
        yield from _prove(rest, b, wm, rules, max_depth, counter)

    # 2) some rule concludes the goal and its conditions can be proven
    if depth >= max_depth:
        return
    for rule in rules:
        suffix = "#%d" % next(counter)                 # fresh variables
        b = unify(goal, _rename(rule["then"], suffix), subst)
        if b is None:
            continue
        subgoals = [(_rename(c, suffix), depth + 1) for c in rule["if"]]
        yield from _prove(subgoals + list(rest), b, wm, rules, max_depth, counter)

def _rename(pattern, suffix):
    """Give every variable in `pattern` a fresh name (so a recursive rule never
    clashes with itself)."""
    return tuple(t + suffix if is_var(t) else t for t in pattern)



# ===========================================================================
#  Task 2 (time): carry knowledge forward under persistence.
# ===========================================================================
def applicable(wm, action, t):
    """
    Yield each ground instance of `action` whose conditions all hold in `wm` at
    step `t`. Bind the action's time variable to `t`, then do the same
    match as forward_chain over its conditions.
 
    Example of what a yielded instance might look like (you choose the shape),
    for grab firing at t=0 with the example world:
        {"name": ("grab", "obj1", "A"),
         "add":       [("holding", "obj1")],
         "terminate": [("empty", "hand"), ("at", "obj1", "A")]}
    """
    raise NotImplementedError
 
def step(wm, action, t):
    """
    Advance the world from step `t` to `t+1` by firing one action. This
    is where "moving knowledge through time" happens. Produce, at t+1:
 
      1. The action's 'add' facts, stamped with t+1 (the effect).
      2. Every fact that held at t and was NOT terminated by this action,
         re-asserted at t+1 (it persisted).
 
    Return the updated working memory (keep the step-t facts too, so history
    queries like "where was obj2 at step 1?" still work).
    """
    raise NotImplementedError


