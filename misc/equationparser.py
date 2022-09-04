import dataclasses
from typing import Any

from misc import pyparse as p
# Define our parsers
from misc.pyparse import ParserState

# We're still debugging
# p.do_debugging = True

__operation = p.string(('*', '/', '+', '-', '%', '^'))

__numerical_constant = p.regex('([0-9]|e|pi)+')

__parenthesis = p.lazy(lambda: __statement.between(p.string('('), p.string(')')))

__expression = p.any_of(
    # Recursively add parenthesis, which contain a value (which could be more parenthesis)
    __parenthesis,

    # Or a value
    p.sequence_of(
        __numerical_constant,
        # you can but a number next to parenthesis for *
        # 4(4) = 4 * 4
        p.optional(__parenthesis)
    ).map(lambda x: x[0] if len(x) == 1 else x)
    # If only a value is matched, remove the list around it
)

# Statements contain a (numerical constant OR parenthesis containing another statement) seperated by an operation
__statement = p.seperated_by(__operation, __expression)


# Do some math


@dataclasses.dataclass
class EquationTest:
    equation: str
    expected_result: Any
    furthest_index: int = -1


def test_equation(equation: EquationTest) -> ParserState:
    final_state = __statement.run(test.equation.replace(' ', ''))

    if test.furthest_index < 0:
        # Must match full
        assert not final_state.is_incomplete_match(), \
            "Expected complete match, only matched up to {} ({} < {})".format(final_state.furthest_index,
                                                                              final_state.index,
                                                                              len(final_state.target))
    else:
        assert final_state.furthest_index == test.furthest_index, \
            "Expected match up to {}, actually matched up to {}".format(test.furthest_index,
                                                                        final_state.furthest_index)

    assert test.expected_result == final_state.result, \
        """Results did not match expected
        Expected: `{}`
        Actual  : `{}`""".format(test.expected_result, final_state.result)

    return final_state


# I don't like math
tests = [
    EquationTest("1", ['1'], -1),
    EquationTest("1+1", ['1', '+', '1'], -1),
    EquationTest("1+(1-2)", ['1', '+', ['1', '-', '2']], -1),
    EquationTest("12 + 13 * (12 + (41 - (698) + 23 ^ 90 / (123epi ^ 2)) / 921)",
                 ['12', '+', '13', '*',
                  ['12', '+',
                   ['41', '-',
                    ['698'], '+', '23', '^', '90', '/',
                    ['123epi', '^', '2']
                    ],
                   '/', '921']],
                 -1)
]

# p.do_debugging = True

# Parse our math stuff with
for idx, test in enumerate(tests):
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

    print("Maximum Call Depth:", p.max_call_depth, "method calls")

print("\n###########################\n")
print("All tests passed!")
