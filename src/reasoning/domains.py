TEST_1_FACTS = {
    ("parent", "mary", "ann"),
    ("parent", "ann", "sam"),
    ("parent", "sam", "leo"),
    ("parent", "mary", "bob"),
    ("parent", "bob", "ivy"),
    ("parent", "tom", "nina"),
}

TEST_1_RULES = [

    {"if": [("parent", "?x", "?y"), ("parent", "?y", "?z")],
     "then": ("grandparent", "?x", "?z")},
    {"if": [("parent", "?x", "?y")],
     "then": ("ancestor", "?x", "?y")},
    {"if": [("parent", "?x", "?y"), ("ancestor", "?y", "?z")],
     "then": ("ancestor", "?x", "?z")},
]