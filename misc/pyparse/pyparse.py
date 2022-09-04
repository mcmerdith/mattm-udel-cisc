import dataclasses
import inspect
import misc.pyparse.parsers as p
from collections.abc import Callable, Sequence
from typing import Any, ClassVar


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

    total_transformations: ClassVar[int] = None
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

        ParserState.total_transformations += 1
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

        return p.sequence_of(left, self, right if right is not None else left) \
            .map(lambda x: x[1] if is_iterable(x) else x)

    def _instance_name(self):
        return "PyParse: {}".format(hex(id(self)))


def get_function_name(func: Callable) -> str:
    return getattr(func, "__name__", str(func))


# Logging

do_debugging = False

max_call_depth = 0


def setup_debugging(enable_logging: bool = False):
    global do_debugging

    do_debugging = enable_logging
    ParserState.total_transformations = 0


def debug(*varargs: Any):
    if do_debugging:
        print('debug: ', *varargs)
        print()

    global max_call_depth

    # Calculate max recursion depth
    stack_size = len(inspect.stack(0))
    if stack_size > max_call_depth:
        max_call_depth = stack_size
