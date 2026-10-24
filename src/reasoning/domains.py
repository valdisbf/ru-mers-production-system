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

TEST_2_FACTS = {
    ("at", "hand", "A", 0),
    ("at", "obj1", "A", 0),
    ("at", "obj2", "C", 0),
    ("empty", "hand", 0),
    ("object", "obj1", 0), ("object", "obj2", 0),
    ("location", "A", 0), ("location", "B", 0), ("location", "C", 0),
    # Legal directed moves; explicitly include reverse links if needed.
    ("route", "A", "B", 0), ("route", "B", "C", 0),
}



ACTIONS = [
    {
        "name": ("grab", "?o", "?loc"),
        "if": [("object", "?o", "?t"),
               ("at", "hand", "?loc", "?t"),
               ("at", "?o", "?loc", "?t"), ("empty", "hand", "?t")],
        "add": [("holding", "?o")],
        "delete": [("empty", "hand"), ("at", "?o", "?loc")],
    },
    {
        "name": ("move", "?from", "?to"),
        "if": [("at", "hand", "?from", "?t"),
               ("route", "?from", "?to", "?t"),
               ("location", "?to", "?t")],
        "add": [("at", "hand", "?to")],
        "delete": [("at", "hand", "?from")],
    },
    {
        "name": ("release", "?o", "?loc"),
        "if": [("object", "?o", "?t"), ("holding", "?o", "?t"),
               ("at", "hand", "?loc", "?t")],
        "add": [("at", "?o", "?loc"), ("empty", "hand")],
        "delete": [("holding", "?o")],
    },
]

# SCHEMAS is a structure to get an action by its name
SCHEMAS = {action["name"][0]: action for action in ACTIONS}


TASK_2_SCHEMAS = {
    "grab": {
        "name": ("grab", "?o", "?loc"),
        "if": [
            ("object", "?o", "?t"),
            ("at", "sherlock", "?loc", "?t"),
            ("at", "?o", "?loc", "?t"),
            ("empty", "sherlock", "?t"),
        ],
        "add": [
            ("holding", "?o"),
        ],
        "delete": [
            ("empty", "sherlock"),
            ("at", "?o", "?loc"),
        ],
    },

    "move": {
        "name": ("move", "?from", "?to"),
        "if": [
            ("at", "sherlock", "?from", "?t"),
            ("passage", "?from", "?to", "?t"),
            ("location", "?to", "?t"),
        ],
        "add": [
            ("at", "sherlock", "?to"),
        ],
        "delete": [
            ("at", "sherlock", "?from"),
        ],
    },

    "release": {
        "name": ("release", "?o", "?loc"),
        "if": [
            ("object", "?o", "?t"),
            ("holding", "?o", "?t"),
            ("at", "sherlock", "?loc", "?t"),
        ],
        "add": [
            ("at", "?o", "?loc"),
            ("empty", "sherlock"),
        ],
        "delete": [
            ("holding", "?o"),
        ],
    },
}
TASK2_INITIAL_FACTS = {
    # Rooms
    ("location", "library", 0),
    ("location", "study", 0),
    ("location", "foyer", 0),
    ("location", "gallery", 0),
    ("location", "laboratory", 0),
    ("location", "hallway", 0),
    ("location", "garden", 0),
    ("location", "terrace", 0),

    # Sherlock starts at the evidence collection point.
    ("at", "sherlock", "terrace", 0),
    ("empty", "sherlock", 0),

    # Movable objects
    ("object", "letter_opener", 0),
    ("object", "letter", 0),
    ("object", "sample_vial", 0),
    ("object", "key", 0),

    # Evidence to collect
    ("evidence", "letter_opener", 0),
    ("evidence", "letter", 0),
    ("evidence", "sample_vial", 0),

    # Initial object locations:
    # the letter opener remains in the study, matching Task 1.
    ("at", "letter_opener", "study", 0),
    ("at", "letter", "library", 0),
    ("at", "sample_vial", "laboratory", 0),

    # Leave this object untouched to demonstrate persistence.
    ("at", "key", "terrace", 0),

    # Passages: each tuple permits movement in ONE direction.
    # Both directions are listed so Sherlock can return with evidence.
    ("passage", "foyer", "hallway", 0),
    ("passage", "hallway", "foyer", 0),

    ("passage", "hallway", "gallery", 0),
    ("passage", "gallery", "hallway", 0),

    ("passage", "gallery", "study", 0),
    ("passage", "study", "gallery", 0),

    ("passage", "hallway", "library", 0),
    ("passage", "library", "hallway", 0),

    ("passage", "gallery", "laboratory", 0),
    ("passage", "laboratory", "gallery", 0),

    ("passage", "foyer", "garden", 0),
    ("passage", "garden", "foyer", 0),

    ("passage", "garden", "terrace", 0),
    ("passage", "terrace", "garden", 0),
}