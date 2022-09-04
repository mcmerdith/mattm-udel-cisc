from misc.pyparse.pyparse import *
import re
from re import Pattern


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
