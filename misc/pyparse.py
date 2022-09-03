import collections.abc
import re
from collections.abc import Callable, Sequence
from re import Pattern
from typing import Any

# String parsing library implemented as a functional programming example
# Matthew Meredith (merematt@udel.edu)
# UDEL CISC 108

# Technically this is not "truly" functional programming because I am using classes,
# but I am using them like immutable structs with helper methods so it's okay :)


def is_iterable(maybe_iterable: Any) -> bool:
    return isinstance(maybe_iterable, Sequence) and not isinstance(maybe_iterable, str)


def maybe_iterable__to_string(maybe_iterable: Sequence | Any) -> str | list[str]:
    return '[{}]'.format(' '.join([maybe_iterable__to_string(current) for current in maybe_iterable])) \
        if is_iterable(maybe_iterable) \
        else str(maybe_iterable)


class ParserState:
    """State of the target. Do not directly modify the state, instead use:

        - update_result_shift_length(str)
        - update_result(Any, next_index)
        - add_error(str)
        - add_errors(list[str])
        """

    def __init__(self,
                 target: str = None,
                 traverse: bool = None,
                 index: int = None,
                 result: Any = None,
                 is_error: bool = None,
                 errors: list[str] = None,
                 previous: 'ParserState' = None):
        """Create a new ParserState.

        Uses values from previous (if present, or defaults) to fill any fields not passed into the constructor

        Parameters
            - target                     : The target string
            - traverse   (default False) : If traversing the string forwards is allowed
            - index          (default 0) : The index of the string we are currently at
            - result                     : The current parsed result
            - is_error   (default False) : If an error has been encountered
            - errors (default list[str]) : A string list of errors
            - previous                   : The previous state for default values"""

        if previous is not None:
            # Merge new data into previous
            self._target = target if target is not None else previous.get_target()
            self._traverse = traverse if traverse is not None else previous.can_traverse()
            self._index = index if index is not None else previous.current_index()
            self._result = result if result is not None else previous.get_result()
            self._is_error = is_error if is_error is not None else previous.is_error()
            self._errors = errors if errors is not None else previous.get_errors()
        else:
            # Merge new data with defaults
            self._target = target  # default is None
            self._traverse = traverse if traverse is not None else False
            self._index = index if index is not None else 0
            self._result = result  # default is None
            self._is_error = is_error if is_error is not None else False
            self._errors = errors if errors is not None else []

        debug(self)

    # Getters

    def is_error(self):
        """Current error state"""

        return self._is_error

    def get_errors(self):
        """Current errors"""

        return self._errors

    def get_result(self):
        """Current result"""

        return self._result

    def get_string_result(self):
        """Get the result as a string"""

        return maybe_iterable__to_string(self._result)

    def current_index(self):
        """Current index"""

        return self._index

    def can_traverse(self):
        return self._traverse

    def get_target(self):
        """The full target string"""

        return self._target

    # Helper Functions

    def get_target_segment(self, start_index: int = None) -> str:
        """The current segment of the target string according to _target[(start_index|_index):]"""

        return self._target[(start_index if start_index is not None else self._index):]

    def has_chars_remaining(self, num_chars: int, start_index: int = None):
        """If there are num_chars remaining in get_target_segment(start_index)"""

        return len(self.get_target_segment(start_index)) >= num_chars

    def remaining_target_is_empty(self):
        """If the target has no more remaining characters"""

        return not self.has_chars_remaining(1)

    def __str__(self):
        return """ParserState: {}
        Target string         = {}
        Can Parsers Traverse? = {}
        Current Index         = {}
        Parsing Result        = {}
        String Result         = {}
        Error?                = {}
        Errors                = {}""".format(
            hex(id(self)),
            self._target,
            self._traverse,
            self._index,
            self._result,
            self.get_string_result(),
            self._is_error,
            ', '.join(self._errors)
        )

    # State Updaters

    def update_result_shift_length(self, new_result: str):
        """Returns a new ParserState with new_result as the result and the index incremented by len(new_result)

        Copies all other values from self"""

        return self.update_result_with_offset(new_result, len(new_result))

    def update_result_with_offset(self, new_result: Any, offset: int):
        """Returns a new ParserState with new_result as the result and the index incremented by offset

        Copies all other values from self"""

        return self.update_result(new_result, self._index + offset)

    def update_result(self, new_result: Any, next_index: int = None):
        """Returns a new ParserState with new_result as the result and next_index as the index

        Copies all other values from self"""

        debug('ParserState: updating: [{}, {}]'.format(new_result, next_index))

        return ParserState(result=new_result, index=next_index, previous=self)

    # Error Management

    def assign_errors(self, parser_name: str):
        """Prefix all errors with '<parser_name>: '"""
        return ParserState(errors=['{}: {}'.format(parser_name, error) for error in self._errors], previous=self)

    def error_target_empty(self, parser_name: str = None):
        """Return an error state that the parser is empty"""

        return self.add_error("{}reached EOF".format(parser_name + ": " if parser_name is not None else ""))

    def add_error(self, message: str):
        """Returns a new ParserState with _is_error=True and _errors contains message

        Copies all other values from self"""

        return ParserState(is_error=True, errors=self._errors + [message], previous=self)

    def add_errors(self, messages: list[str]):
        """Returns a new ParserState with _is_error=True and _errors containing messages

        Copies all other values from self"""

        return ParserState(is_error=True, errors=self._errors + messages, previous=self)


class PyParse:
    """Generic object target. Specific functions must be implemented

    Accepts an initial state transformer function. State transformers act upon a ParserState, returning the new state"""

    def __init__(self, state_transformer: Callable[[ParserState], ParserState]):
        self.state_transformer = state_transformer

    def run(self, target: Any, traverse=False) -> ParserState:
        """INITIAL run method. Do not run this on every target in a call, it will not work

        Chained parsers will call each other"""

        # Begin the callchain >:)
        return self.state_transformer(ParserState(target=target, traverse=traverse))

    def map(self, results_transformer: Callable[[Any], Any]) -> 'PyParse':
        def transform(state: ParserState) -> ParserState:
            new_state = self.state_transformer(state)

            if not new_state.is_error():
                return new_state.update_result(results_transformer(new_state.get_result()), new_state.current_index())

            return new_state

        return PyParse(transform)

    def between(self, left: 'PyParse', right: 'PyParse' = None):
        return sequence(left, self, right if right is not None else left).map(lambda x: x[1] if is_iterable(x) else x)


# Built-in Parsers

def string(to_match: str | tuple[str, ...]) -> PyParse:
    """Match a string exactly. Will traverse the target if enabled"""

    def find_string_transformer(state: ParserState) -> ParserState:
        if state.is_error():
            return state

        if state.remaining_target_is_empty():
            return state.error_target_empty("string")

        # First index to search on
        c_idx = state.current_index()

        while True:
            # Get the current position onward
            current = state.get_target_segment(c_idx)

            debug('string: matching: {} @ c_idx={} ({})'.format(to_match, str(c_idx), current))

            if len(current) == 0:
                # There's nothing here
                return state.add_error("string: Expected {}, found EOF".format(to_match))

            if current.startswith(to_match):
                # Found it
                return state.update_result(to_match, c_idx + len(to_match))

            if state.can_traverse() and state.has_chars_remaining(len(to_match), c_idx + 1):
                # We are allowed to keep searching and have enough string to do so, increment go deeper
                c_idx += 1
                continue
            else:
                # We are not allowed or have no chance to find the string
                return state.add_error(
                    "string: Expected {}, found {}".format(
                        to_match,
                        state.get_target_segment() if state.can_traverse() else current[:len(to_match) + 8])
                )

    return PyParse(find_string_transformer)


def regex(pattern: Pattern[str]) -> PyParse:
    """Match a regex pattern"""

    def find_regex_transformer(state: ParserState) -> ParserState:
        if state.is_error():
            return state

        if state.remaining_target_is_empty():
            return state.error_target_empty("regex")

        debug('regex: matching: {} in {}'.format(str(pattern), state.get_target_segment()))

        match = pattern.match(state.get_target_segment())

        if match is None:
            return state.add_error("regex: Expected {}, found {}".format(pattern, state.get_target_segment()[:10]))

        return state.update_result_shift_length(match.group(0))

    return PyParse(find_regex_transformer)


__digit_regex = re.compile("^[0-9]+")
__letter_regex = re.compile("^[A-Za-z]")

DIGITS = regex(__digit_regex)
LETTERS = regex(__letter_regex)


# Built in processors

def optional(parser: PyParse) -> PyParse:
    """Make a target optional. Cannot be passed to many(). Instead to optional(many(target))"""

    def optional_parser_transformer(state: ParserState) -> ParserState:
        if state.is_error():
            return state

        debug('optional: matching {} against {}'.format(str(parser.state_transformer), state.get_target_segment()))

        # Execute the target
        temp_state = parser.state_transformer(state)

        if temp_state.is_error():
            # If an error occurred pretend it never happened
            return state

        # Return the match
        return temp_state

    return PyParse(optional_parser_transformer)


def sequence(*parsers: PyParse) -> PyParse:
    """Match a sequence of parsers"""

    def parser_sequence_transformer(state: ParserState) -> ParserState:
        if state.is_error():
            return state

        if state.remaining_target_is_empty():
            return state.error_target_empty("sequence")

        results = []
        current = state

        # Parsers will all work on the "same" state in a chain (its "immutable")
        for parser in parsers:
            debug(
                'sequence: matching {} against {}'.format(str(parser.state_transformer), current.get_target_segment()))

            current = parser.state_transformer(current)

            if current.is_error():
                return current.assign_errors("sequence")

            results.append(current.get_result())

        # Move all the results back into the state
        if len(results) == 0:
            return state.add_error("sequence: parsers matched nothing!")

        return current.update_result(results)

    return PyParse(parser_sequence_transformer)


def any_one(*parsers: PyParse) -> PyParse:
    """Match any one of the supplied parsers"""

    def any_parser_transformer(state: ParserState) -> ParserState:
        if state.is_error():
            return state

        if state.remaining_target_is_empty():
            return state.error_target_empty("any_one")

        index = 1

        for parser in parsers:
            debug('any_one ({}/{}): matching {} against {}'.format(index, len(parsers), str(parser.state_transformer), state.get_target_segment()))
            index += 1
            temp_state = parser.state_transformer(state)

            if not temp_state.is_error():
                return temp_state

        return state.add_error("any_one: no target matched!")

    return PyParse(any_parser_transformer)


def many(parser: PyParse, minimum_number=1) -> PyParse:
    """Match many of a target"""

    def many_transformer(state: ParserState) -> ParserState:
        if state.is_error():
            return state

        if state.remaining_target_is_empty():
            return state.error_target_empty("many")

        results = []
        current = state

        # match the parser as many times as we can
        while True:
            debug(
                'many: matching many {} against {}'.format(str(parser.state_transformer), current.get_target_segment()))

            temp_state = parser.state_transformer(current)

            if temp_state.is_error():
                # failed, ignore and stop searching
                break
            else:
                # found, try again
                results.append(temp_state.get_result())
                current = temp_state
                continue

        # Process results

        if len(results) < minimum_number:
            return state.add_error("many: {} matches, {} required!".format(len(results), minimum_number))

        return current.update_result(results)

    return PyParse(many_transformer)


def seperated_by(seperator: PyParse, target: PyParse) -> PyParse:
    """Find instances of a target seperated by a seperator"""

    def parser_sequence_transformer(state: ParserState) -> ParserState:
        if state.is_error():
            return state

        debug('seperated_by: matching {} seperated by {}'.format(
            str(target.state_transformer),
            str(seperator.state_transformer)))

        results = []

        current_state = target.state_transformer(state)

        if current_state.is_error():
            # Prepend all errors
            return current_state.assign_errors("seperated_by")

        while True:
            # Append our result
            results.append(current_state.get_result())

            if current_state.remaining_target_is_empty():
                return current_state.update_result(results)

            # Find a seperator
            seperator_state = seperator.state_transformer(current_state)

            if seperator_state.is_error() or seperator_state.remaining_target_is_empty():
                return current_state.update_result(results)
            
            # Find the next value
            current_state = target.state_transformer(seperator_state)

            if current_state.is_error():
                # Return the results WITHOUT the last seperator
                return current_state.update_result(results) if seperator_state.is_error() \
                    else seperator_state.update_result(results)
            else:
                # Add the seperator if there is a next value
                results.append(seperator_state.get_result())

    return PyParse(parser_sequence_transformer)


def lazy(provider: Callable[[], PyParse]) -> PyParse:
    """Don't load the target until its being called, enables recursion within parsers"""

    def lazy_transformer(state: ParserState) -> ParserState:
        if state.is_error():
            return state

        if state.remaining_target_is_empty():
            return state.error_target_empty("lazy")

        debug("lazy: loading " + str(provider))

        return provider().state_transformer(state)

    return PyParse(lazy_transformer)


# Logging
do_debugging = False


def debug(*varargs: Any):
    if do_debugging:
        print('debug: ', *varargs)
