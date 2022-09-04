import dataclasses
import inspect
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


def maybe_iterable__to_string(maybe_iterable: Sequence | Any, joiner: str = ' ') -> str | list[str]:
    return '[{}]'.format(joiner.join([maybe_iterable__to_string(current, joiner) for current in maybe_iterable])) \
        if is_iterable(maybe_iterable) \
        else str(maybe_iterable)


ResultProvider = Callable[[], Any]


@dataclasses.dataclass(frozen=True)
class ParserState:
    """State of the target. Do not directly modify the state, instead use:

        - update_result_shift_length(str)
        - update_result(Any, next_index)
        - add_error(str)
        - add_errors(list[str])
        """

    target: str = None
    traverse: bool = False
    index: int = 0
    furthest_index: int = 0
    result: Any = None
    is_error: bool = False
    errors: list[str] = dataclasses.field(default_factory=list)

    def update(self,
               target: str = None,
               traverse: bool = None,
               index: int = None,
               furthest_index: int = None,
               result: Any | Callable[[], Any] = None,
               is_error: bool = None,
               errors: list[str] = None):
        """Update a ParserState.

        Will use values from this instance to fill any fields not passed into the constructor
        Setting any value to `None` will replace it with the previous or default value (except result, see below)

        Parameters
            - target                     : The target string
            - traverse   (default False) : If traversing the string forwards is allowed
            - index          (default 0) : The index of the string we are currently at
            - result                     : The current parsed result. Can be a provider function (used to set None)
            - is_error   (default False) : If an error has been encountered
            - errors (default list[str]) : A string list of errors"""

        args = {
            "target": target,
            "traverse": traverse,
            "index": index,
            "furthest_index": furthest_index if furthest_index is not None else self.furthest_index,
            "result": result,
            "is_error": is_error,
            "errors": errors
        }

        t_idx = index if index is not None else self.index

        if t_idx is not None and t_idx > args["furthest_index"]:
            args["furthest_index"] = t_idx

        composed = {key: value for (key, value) in args.items() if value is not None}

        # If the result is a provider, build it first
        if isinstance(result, Callable):
            composed["result"] = result()

        updated = dataclasses.replace(self, **composed)

        debug(updated.get_state_string(True))

        return updated

    # Helper Functions

    def get_string_result(self, joiner: str = ' '):
        """Get the result as a string"""

        return maybe_iterable__to_string(self.result, joiner)

    def get_target_segment(self, start_index: int = None) -> str:
        """The current segment of the target string according to _target[(start_index|_index):]"""

        return self.target[(start_index if start_index is not None else self.index):]

    def has_chars_remaining(self, num_chars: int, start_index: int = None):
        """If there are num_chars remaining in get_target_segment(start_index)"""

        return len(self.get_target_segment(start_index)) >= num_chars

    def is_remaining_target_empty(self, start_index: int = None):
        """If the target has no more remaining characters"""

        return not self.has_chars_remaining(1, start_index)

    def is_incomplete_match(self):
        """If the parser matched all the way to the end of the string"""

        return self.index < len(self.target)

    def get_incomplete_match(self):
        """Get the area of the target where the error occurred"""

        return self.get_target_segment(self.furthest_index - 10 if self.furthest_index > 10 else 0)[:20]

    # State Updaters

    def update_result_shift_length(self, new_result: str, furthest_index: int = None):
        """Returns a new ParserState with new_result as the result and the index incremented by len(new_result)

        Copies all other values from self"""

        return self.update_result_offset_index(new_result, len(new_result), furthest_index)

    def update_result_offset_index(self, new_result: Any | ResultProvider, offset: int, furthest_index: int = None):
        """Returns a new ParserState with new_result as the result and the index incremented by offset

        Copies all other values from self"""

        return self.update_result_and_index(new_result, self.index + offset, furthest_index)

    def update_result_and_index(self, new_result: Any | ResultProvider, next_index: int = None,
                                furthest_index: int = None):
        """Returns a new ParserState with new_result as the result and next_index as the index

        Copies all other values from self"""

        debug("{}: updating: result (`{}` -> `{}`), index ({} -> {})".format(
            self._instance_name(),
            self.result,
            new_result() if isinstance(new_result, Callable) else new_result,
            self.index,
            next_index if next_index is not None
            else self.index)
        )

        return self.update(result=new_result,
                           index=next_index,
                           furthest_index=furthest_index)

    # Error Management

    def error_target_empty(self, parser_name: str = None):
        """Returns a new ParserState with an error that the target slice is empty prefixed by 'parser_name: '

        Copies all other values from self"""

        return self.add_error("{}reached EOF".format(parser_name + ": " if parser_name is not None else ""))

    def add_error(self, message: str, index: int = None):
        """Returns a new ParserState with _is_error=True and _errors contains message

        Copies all other values from self"""

        return self.update(furthest_index=index,
                           is_error=True,
                           errors=[message] + self.errors)

    def add_errors(self, messages: list[str], index: int = None):
        """Returns a new ParserState with _is_error=True and _errors containing messages

        Copies all other values from self"""

        return self.update(furthest_index=index,
                           is_error=True,
                           errors=messages + self.errors)

    def assign_errors(self, parser_name: str):
        """Returns a new ParserState with all errors prefixed by 'parser_name: '

        Copies all other values from self"""

        return self.update(errors=['{}: {}'.format(parser_name, error) for error in self.errors])

    # Class Functions

    def print_syntax_error(self):
        idx_offset = " " * len(str(self.furthest_index))
        fidx_offset = " " * (self.furthest_index if self.furthest_index < 10 else 10)

        # print("                {}       {}V".format(idx_offset, fidx_offset))
        print("Syntax error at {} near '{}'".format(self.furthest_index, self.get_incomplete_match()))
        print("                {}       {}^".format(idx_offset, fidx_offset))

    def get_state_string(self, debugging=False):
        error_string = "Error                 = {}".format(', '.join(self.errors))

        result_string = "Parsing Result        = {}".format(self.result)

        debug_string = \
            """                        {}
        Target string         = {}
                                {}
        Can Parsers Traverse? = {}
        """.format("{}V".format(" " * self.furthest_index),
                   self.target,
                   "{}^".format(" " * self.index),
                   self.traverse)

        common_string = """{}

        {}Current Index         = {} (furthest {})
        {}"""

        return common_string.format(
            self._instance_name(),
            debug_string if debugging else "",
            self.index,
            self.furthest_index,
            error_string if self.is_error else result_string
        )

    def __str__(self):
        return self.get_state_string()

    def _instance_name(self):
        return "ParserState: {}".format(hex(id(self)))


ParserStateTransformer = Callable[[ParserState], ParserState]
ResultTransformer = Callable[[Any], Any]


@dataclasses.dataclass(frozen=True)
class PyParse:
    """Generic string parser. Specific functions must be implemented using a ParserState transformer

    Accepts an initial state transformer function.
    State transformers take in a ParserState and return a new state asthe result of their processing

    Multiple parsers (by association their state_transformer) can be chained together for more complex parsing
    (even recursively)"""

    state_transformer: ParserStateTransformer

    def run(self, target: str, traverse=False) -> ParserState:
        """INITIAL run method. Do not run this on every target in a call, it will not work

        Chained parsers will call each other"""

        # Begin the callchain >:)
        return self.state_transformer(ParserState(target=target, traverse=traverse))

    def map(self, result_transformer: ResultTransformer) -> 'PyParse':
        """Apply a result transformer to the current state transformer function

        The transformer function will be called on the result of a successful match by the base transformer function
        """

        def map_transformer(state: ParserState) -> ParserState:
            new_state = self.state_transformer(state)

            if not new_state.is_error:
                mapped_result = result_transformer(new_state.result)

                debug("{}: mapped result: `{}` -> `{}`".format(self._instance_name(),
                                                               new_state.result,
                                                               mapped_result))

                return new_state.update(result=mapped_result)

            return new_state

        map_transformer.__name__ = get_function_name(self.state_transformer) + "_with_map_transform"

        return PyParse(map_transformer)

    def between(self, left: 'PyParse', right: 'PyParse' = None) -> 'PyParse':
        """Require that this parser match in between the left parser and right parser

        Left/Right parsers will not be included in the final result"""

        return sequence_of(left, self, right if right is not None else left) \
            .map(lambda x: x[1] if is_iterable(x) else x)

    def _instance_name(self):
        return "PyParse: {}".format(hex(id(self)))


# Built-in Parsers

def string(to_match: str | tuple[str, ...]) -> PyParse:
    """Match a string exactly. Will traverse the target if enabled

    If a tuple[str, ...] is supplied a regex parser will be returned as `(to_match[0])|...`"""

    if isinstance(to_match, tuple):
        # If we want to find any of a set of strings, it's easiest to use a regex
        reg = "({})".format(')|('.join([re.escape(str(x)) for x in to_match]))

        debug("string: matching '{}' using regex `{}`".format(to_match, reg))

        return regex(reg)

    def find_string_transformer(state: ParserState) -> ParserState:
        if state.is_error:
            return state

        # First index to search on
        c_idx = state.index

        while True:
            # Check if theres anything left
            if state.is_remaining_target_empty(c_idx):
                return state.error_target_empty("string")

            # Get the current position onward
            current = state.get_target_segment(c_idx)

            debug("string: matching '{}' in '{}' (index {})".format(to_match, current, c_idx))

            if current.startswith(to_match):
                # Found it
                return state.update_result_and_index(to_match, c_idx + len(to_match))

            if state.traverse and state.has_chars_remaining(len(to_match), c_idx + 1):
                # We are allowed to keep searching and have enough string to do so, increment go deeper
                c_idx += 1
                continue
            else:
                # We are not allowed or have no chance to find the string
                return state.add_error(
                    "string: Expected '{}', found '{}{}'".format(
                        to_match,
                        state.get_target_segment() if state.traverse else current[:len(to_match) + 10],
                        "..." if len(state.get_target_segment()) > 10 else "")
                )

    return PyParse(find_string_transformer)


def regex(t_pattern: Pattern[str] | str) -> PyParse:
    """Match a regex pattern

    Accepts a compiled regex pattern or a regex string"""

    pattern = re.compile('^' + t_pattern) if isinstance(t_pattern, str) else t_pattern

    def find_regex_transformer(state: ParserState) -> ParserState:
        if state.is_error:
            return state

        if state.is_remaining_target_empty():
            return state.error_target_empty("regex")

        debug("regex: matching: '{}' in '{}'".format(pattern.pattern, state.get_target_segment()))

        match = pattern.match(state.get_target_segment())

        if match is None:
            return state.add_error(
                "regex: Expected '{}', found '{}{}'".format(pattern.pattern,
                                                            state.get_target_segment()[:10],
                                                            "..." if len(state.get_target_segment()) > 10 else "")
            )

        return state.update_result_shift_length(match.group(0))

    return PyParse(find_regex_transformer)


DIGITS = regex('[0-9]+')
LETTERS = regex('[A-Za-z]+')


# Built in processors

def optional(parser: PyParse) -> PyParse:
    """Make a target optional. Cannot be passed to many(). Instead to optional(many(target))"""

    def optional_parser_transformer(state: ParserState) -> ParserState:
        if state.is_error:
            return state

        debug("optional: attempting to match `{}` against '{}'".format(get_function_name(parser.state_transformer),
                                                                       state.get_target_segment()))

        # Execute the target
        temp_state = parser.state_transformer(state)

        if temp_state.is_error:
            # If an error occurs on an optional a blank result is set, ie. nothing happened, continue
            # The furthest index must be manually set since we are ignoring the previous state
            debug("optional: no match")
            return state.update_result_and_index(lambda: None, furthest_index=temp_state.furthest_index)

        debug("optional: found match")

        # Return the match
        return temp_state

    return PyParse(optional_parser_transformer)


def sequence_of(*parsers: PyParse) -> PyParse:
    """Match a sequence of parsers"""

    def parser_sequence_transformer(state: ParserState) -> ParserState:
        if state.is_error:
            return state

        results = []
        current = state

        for index, parser in enumerate(parsers):
            # Parsers are chained together, each will work on the state the previous one was working on

            debug("sequence ({}/{}): matching `{}` against '{}'".format(index + 1,
                                                                        len(parsers),
                                                                        get_function_name(parser.state_transformer),
                                                                        current.get_target_segment()))

            current = parser.state_transformer(current)

            if current.is_error:
                return current.add_error("sequence: component failed to match")

            results.append(current.result)

        # Move all the results back into the state
        if len(results) == 0:
            return state.add_error("sequence: parsers matched nothing!", current.furthest_index)

        return current.update_result_and_index([result for result in results if result is not None])

    return PyParse(parser_sequence_transformer)


def any_of(*parsers: PyParse) -> PyParse:
    """Match any one of the supplied parsers"""

    def any_parser_transformer(state: ParserState) -> ParserState:
        if state.is_error:
            return state

        furthest_of_all = 0

        for index, parser in enumerate(parsers):
            debug("any_of ({}/{}): matching `{}` against '{}'".format(index + 1,
                                                                      len(parsers),
                                                                      get_function_name(parser.state_transformer),
                                                                      state.get_target_segment()))

            temp_state = parser.state_transformer(state)

            if furthest_of_all < temp_state.furthest_index:
                furthest_of_all = temp_state.furthest_index

            if not temp_state.is_error:
                debug("any_of: found match")
                return temp_state

        return state.add_error("any_of: no target matched!", furthest_of_all)

    return PyParse(any_parser_transformer)


def many(parser: PyParse, minimum_number=1) -> PyParse:
    """Match many of a target"""

    def many_transformer(state: ParserState) -> ParserState:
        if state.is_error:
            return state

        results = []
        current = state

        # match the parser as many times as we can
        while True:
            debug('many ({} found): matching many {} against {}'.format(len(results),
                                                                        get_function_name(parser.state_transformer),
                                                                        current.get_target_segment()))

            temp_state = parser.state_transformer(current)

            if temp_state.is_error:
                # failed, ignore and stop searching
                if len(results) < minimum_number:
                    return state.add_error("many: {} matches, {} required!".format(len(results), minimum_number),
                                           current.furthest_index)

                return current.update_result_and_index(results, furthest_index=current.furthest_index)
            else:
                # found, try again
                results.append(temp_state.result)
                current = temp_state
                continue

    return PyParse(many_transformer)


def seperated_by(seperator: PyParse, target: PyParse) -> PyParse:
    """Find instances of a target seperated by a seperator"""

    def seperated_by_transformer(state: ParserState) -> ParserState:
        if state.is_error:
            return state

        debug('seperated_by: matching {} seperated by {}'.format(get_function_name(target.state_transformer),
                                                                 get_function_name(seperator.state_transformer)))

        results = []

        current_state = target.state_transformer(state)

        if current_state.is_error:
            # Prepend all errors
            return current_state.assign_errors("seperated_by")

        while True:
            # Append our result
            results.append(current_state.result)

            debug('seperated_by ({} found): found {}'.format(len(results), current_state.result))

            if current_state.is_remaining_target_empty():
                # Nothing left, we're done
                return current_state.update_result_and_index(results)

            # Find a seperator
            seperator_state = seperator.state_transformer(current_state)

            # If we have no more separators we're done
            if seperator_state.is_error or seperator_state.is_remaining_target_empty():
                debug('seperated_by: complete, no more separators')
                return current_state.update_result_and_index(results,
                                                             furthest_index=seperator_state.furthest_index)

            # Find the next value
            next_state = target.state_transformer(seperator_state)

            if next_state.is_error:
                debug('seperated_by: complete with warning, found seperator but no next value at',
                      next_state.furthest_index)
                # Return the results WITHOUT the last seperator
                return current_state.update_result_and_index(
                    results,
                    furthest_index=next_state.furthest_index
                )
            else:
                # Add the seperator if there is a next value
                results.append(seperator_state.result)

                current_state = next_state

    return PyParse(seperated_by_transformer)


def lazy(provider: Callable[[], PyParse]) -> PyParse:
    """Don't load the target until its being called, enables recursion within parsers"""

    def lazy_transformer(state: ParserState) -> ParserState:
        if state.is_error:
            return state

        parser = provider()

        debug("lazy: loaded " + get_function_name(parser.state_transformer))

        return parser.state_transformer(state)

    return PyParse(lazy_transformer)


# Logging

do_debugging = False

max_call_depth = 0


def get_function_name(func: Callable) -> str:
    return getattr(func, "__name__", str(func))


def debug(*varargs: Any):
    if do_debugging:
        print('debug: ', *varargs)
        print()

    global max_call_depth

    # Calculate max recursion depth
    stack_size = len(inspect.stack(0))
    if stack_size > max_call_depth:
        max_call_depth = stack_size
