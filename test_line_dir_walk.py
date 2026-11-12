# -*- coding: utf-8 -*-
"""Direction walk: rings without a single cut must stay unsettled. No QGIS."""
import importlib.util
import pathlib
import unittest


def _load():
    path = pathlib.Path(__file__).resolve().parent / "tools" / "line_dir" / "ntal_walk.py"
    spec = importlib.util.spec_from_file_location("ntal_walk_test", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WALK = _load()


def _run(pairs, roots, terminals=(), interior=()):
    edges = [{"id": eid, "length": 1.0, "start": (0.0, 0.0), "end": (1.0, 0.0)} for eid, _a, _b in pairs]
    ends = {eid: (a, b) for eid, a, b in pairs}
    return WALK._walk(set(roots), edges, ends, set(terminals), set(interior))


class WalkTests(unittest.TestCase):
    def test_branch_is_not_an_error(self):
        oriented, _loops, pseudo, cuts, ambiguous = _run(
            [(1, 10, 11), (2, 11, 12), (3, 11, 13)], [10]
        )
        self.assertEqual(pseudo, [])
        self.assertEqual(ambiguous, [])
        self.assertEqual(cuts, set())
        self.assertEqual(oriented[1], (10, 11))
        self.assertEqual(oriented[2], (11, 12))
        self.assertEqual(oriented[3], (11, 13))

    def test_ring_without_end_marks_only_the_meeting_line(self):
        oriented, _loops, pseudo, _cuts, ambiguous = _run(
            [(1, 10, 11), (2, 11, 12), (3, 12, 10)], [10]
        )
        self.assertEqual(ambiguous, [])
        self.assertEqual(pseudo, [2])
        self.assertEqual(oriented[1], (10, 11))
        self.assertEqual(oriented[3], (10, 12))

    def test_one_junction_end_orients_the_ring(self):
        oriented, _loops, pseudo, cuts, ambiguous = _run(
            [(1, 10, 11), (2, 11, 12), (3, 12, 10)], [10], terminals=[12]
        )
        self.assertEqual(pseudo, [])
        self.assertEqual(ambiguous, [])
        self.assertEqual(cuts, {12})
        self.assertEqual(set(oriented), {1, 2, 3})
        self.assertEqual(oriented[1][0], 10)
        self.assertEqual(oriented[2], (11, 12))
        self.assertEqual(oriented[3], (10, 12))

    def test_several_ends_on_one_ring_are_not_guessed(self):
        oriented, _loops, pseudo, cuts, ambiguous = _run(
            [(1, 10, 11), (2, 11, 12), (3, 12, 10)], [10], terminals=[11, 12]
        )
        self.assertEqual(pseudo, [])
        self.assertEqual(cuts, set())
        self.assertEqual(oriented, {})
        self.assertEqual(set(ambiguous), {1, 2, 3})

    def test_end_in_the_middle_of_a_line_does_not_settle_the_ring(self):
        oriented, _loops, pseudo, cuts, ambiguous = _run(
            [(1, 10, 11), (2, 11, 12), (3, 12, 13), (4, 13, 14), (5, 14, 15), (6, 15, 10)],
            [10],
            interior=[1, 2, 3, 4, 5, 6],
        )
        self.assertEqual(pseudo, [])
        self.assertEqual(cuts, set())
        self.assertEqual(oriented, {})
        self.assertEqual(set(ambiguous), {1, 2, 3, 4, 5, 6})

    def test_end_on_a_branch_changes_nothing(self):
        oriented, _loops, pseudo, cuts, ambiguous = _run(
            [(1, 10, 11), (2, 11, 12)], [10], terminals=[11]
        )
        self.assertEqual(pseudo, [])
        self.assertEqual(ambiguous, [])
        self.assertEqual(cuts, set())
        self.assertEqual(oriented[1], (10, 11))
        self.assertEqual(oriented[2], (11, 12))


if __name__ == "__main__":
    unittest.main()
