from misc import pyparse as p

__operation_parser = p.any_one(
    p.string('*'),
    p.string('/'),
    p.string('+'),
    p.string('-'),
    p.string('%'),
    p.string('**')
)

__value_parser = p.any_one(
    # Recursively add parenthesis, which contain a value (which could be more parenthesis)
    p.lazy(lambda: __expression_parser.between(p.string('('), p.string(')'))),
    # Or a raw value
    p.DIGITS,
    p.string('e'),
    p.string('pi')
)


# Expressions contain a value/parenthesis seperated by an operation
__expression_parser = p.seperated_by(__operation_parser, __value_parser)

expression = "12+13*((41-567)/921)"

p.do_debugging = True

result = __expression_parser.run(expression)

print(result)
