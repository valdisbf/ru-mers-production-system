from itertools import count
_rule_ids = count()

def backward_answers(wm, query, rules):
    """Display-independent answer set, using the supplied substitution function."""
    return {substitute(query, binding)
            for binding in backward_chain(wm, rules, query)}

# List available instances of actions that match the action
def instances(wm, schema, t):
    return list(applicable(wm, schema, t))

# get an action from the set of actions available at the time based on the name
def choose(wm, name, schemas, t):
    options = instances(wm, schemas[name[0]], t)
    matching = [a for a in options if tuple(a["name"]) == name]
    assert len(matching) == 1, ("Expected one applicable instance", name, matching)
    return matching[0]

# ===========================================================================
#  Renames variables of a rule so it doesnt clash in iterations
# ===========================================================================
def freshen_rule(rule):
    suffix = next(_rule_ids)
    renaming = {}

    patterns = [rule["then"], *rule["if"]]

    for pattern in patterns:
        for term in pattern:
            if is_var(term) and term not in renaming:
                renaming[term] = f"{term}__{suffix}"

    return {
        "then": substitute(rule["then"], renaming),
        "if": [
            substitute(condition, renaming)
            for condition in rule["if"]
        ],
    }

# ===========================================================================
#  Matching machinery
# ===========================================================================
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

    return wm


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


# ===========================================================================
#  Recursive function to match query
#  subst = bindings that are known applying the conditions to the rule
# ===========================================================================
def prove_conditions(wm, rules, conditions, subst=None, path=set()):
    """Yield bindings that satisfy every condition."""
    if subst is None:
        subst = {}
    
    # All conditions have matched successfully.
    if not conditions:
        yield subst
        return
   
    first, * remaining = conditions

    for bindings in backward_chain(wm, rules, first, subst, path):
        yield from prove_conditions(
            wm, rules, remaining, bindings, path
        )


def backward_chain(wm, rules, query, subst=None, path=set()):
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

    if subst is None:
        subst = {}

    # Apply the bindings before checking for a repeated goal.
    goal = substitute(query, subst)

    # Check if goal is a ground fact
    is_ground = not any(is_var(term) for term in goal)

    if is_ground and goal in path:
        return  # Circular proof: abandon this branch.

    # Create a new path; do not modify the caller's path.
    next_path = path | {goal} if is_ground else path

    # Goal: yield matches from working memory; i.e. return a set of bindings that match the query
    yield from wm.ask(query, subst)

    # Find rules where conclusion matches the query
    #For each rule whose conclusion matches goal:
    for rule in rules:
        new_rule = freshen_rule(rule)

        bindings = unify(new_rule['then'], query, subst)
        
        if bindings is not None:

            #yield solutions from prove_conditions(rule's conditions)
            yield from prove_conditions(wm, rules, new_rule['if'], bindings, next_path)
       


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
    
    # Get all bindings that match the actions conditions at this time
    # Uses backwards chaining to check all conditions of the action to find facts that match
    for b in prove_conditions(wm, [], action["if"], {"?t": t}):
        inst = {
            "name":      substitute(action["name"], b),
            "add":       [substitute(f, b) for f in action.get("add", [])],
            "delete": [substitute(f, b) for f in action.get("delete", [])],
        }
        if all(_is_ground(f) for f in [inst["name"]] + inst["add"] + inst["delete"]):
            yield inst
 
def step(wm, action, t, persistence=True):
    """
    Advance the world from step `t` to `t+1` by firing one action. This
    is where "moving knowledge through time" happens. Produce, at t+1:
 
      1. The action's 'add' facts, stamped with t+1 (the effect).
      2. Every fact that held at t and was NOT terminated by this action,
         re-asserted at t+1 (it persisted).
 
    Return the updated working memory (keep the step-t facts too, so history
    queries like "where was obj2 at step 1?" still work).
    """
    # Make sure the current delete actions is not added to the wm
    terminated = {tuple(f) for f in action["delete"]}
    
    if persistence:
        # Find the facts that hold at the current time
        holding_now = [f for f in wm.facts if f[-1] == t]      # snapshot first
        for f in holding_now:
            if f[:-1] not in terminated:
                # Increase the time of all actions that should continue to hold
                wm.tell(f[:-1] + (t + 1,))
    # Add the new facts                
    for f in action["add"]:
        wm.tell(tuple(f) + (t + 1,))
    return wm

## Helpers:

def _is_ground(pattern):
    return not any(is_var(t) for t in pattern)


def _match_all(wm, conditions, subst):
    """Yield every binding that satisfies ALL `conditions` against `wm`.

    Match the first condition with wm.ask, then the rest under each resulting
    binding (a conjunctive match)."""
    if not conditions:
        yield subst
        return
    first, rest = conditions[0], conditions[1:]
    for b in wm.ask(first, subst):
        yield from _match_all(wm, rest, b)


