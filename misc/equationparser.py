import dataclasses
from typing import Any

from misc.pyparse import parsers as p
from misc.pyparse import mapping as m

# Define our parsers

from misc.pyparse.pyparse import ParserState

__operation = p.string(('*', '/', '+', '-', '%', '^'))

__numerical_constant = p.regex('([0-9]|e|pi)+')

__parenthesis = p.many(p.lazy(lambda: __statement.between(p.string('('), p.string(')')))).map(m.singleton_list_unpacker)

__expression = p.any_of(
    # Recursively add parenthesis, which contain a value (which could be more parenthesis)
    __parenthesis,

    # Or a value
    p.sequence_of(
        __numerical_constant,
        # you can but a number next to parenthesis for *
        # 4(4) = 4 * 4
        p.optional(__parenthesis)
    ).map(m.singleton_list_unpacker)
    # If only a value is matched, remove the list around it
)

# Statements contain a (numerical constant OR parenthesis containing another statement) seperated by an operation
__statement = p.seperated_by(__operation, __expression)


# Define the evaluator

def evaluate(node: Any):
    pass


# TESTING


@dataclasses.dataclass
class TestCase:
    equation: str
    expected_result: Any
    expected_value: int
    furthest_index: int = -1


def test_equation(case: TestCase) -> ParserState:
    final_state = __statement.run(case.equation.replace(' ', ''))

    if case.furthest_index < 0:
        # Must match full
        assert not final_state.is_incomplete_match(), \
            "Expected complete match, only matched up to {} ({} < {})".format(final_state.furthest_index,
                                                                              final_state.index,
                                                                              len(final_state.target))
    else:
        assert final_state.furthest_index == case.furthest_index, \
            "Expected match up to {}, actually matched up to {}".format(case.furthest_index,
                                                                        final_state.furthest_index)

    assert case.expected_result == final_state.result, \
        """Results did not match expected
        Expected: `{}`
        Actual  : `{}`""".format(case.expected_result, final_state.result)

    return final_state


# I don't like math
tests = [
    TestCase(equation="1",
             expected_result=['1'], expected_value=1,
             furthest_index=-1),
    TestCase(equation="1+1",
             expected_result=['1', '+', '1'], expected_value=2,
             furthest_index=-1),
    TestCase(equation="1+(1-2)",
             expected_result=['1', '+', ['1', '-', '2']], expected_value=0,
             furthest_index=-1),
    TestCase(equation="12 + 13 * (12 + (41 - (698) + 23 ^ 90 / (123epi ^ 2)) / 921)",
             expected_result=[
                     '12', '+', '13', '*',
                     [
                         '12', '+',
                         [
                             '41', '-', ['698'], '+', '23', '^', '90', '/',
                             ['123epi', '^', '2']
                         ],
                         '/', '921'
                     ]
                 ], expected_value=2,
             furthest_index=-1)
]

# Parse our math stuff with
for idx, test in enumerate(tests):
    p.setup_debugging(False)

    print("\n###########################\n")
    print("Test {}/{}".format(idx + 1, len(tests)))

    result = test_equation(test)

    print("Passed! Results:")
    print("\n###########################\n")

    if result.is_incomplete_match():
        result.print_syntax_error()
        print()

    print("Input :", test.equation)
    print("Output:", result.get_string_result())

    print()

    print("Maximum Call Depth   :", p.max_call_depth, "method calls")
    print("Total Transformations:", p.ParserState.total_transformations)

print("\n###########################\n")
print("All tests passed!")
