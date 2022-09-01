# Execute a mathematical operation
# Only Multiplication, Addition, and Parenthesis are allowed on NON-negative integers
# Follows modified PEMDAS: Parenthesis, Multiplication, Addition
# Nested parenthesis are processed recursively
# Examples: 1+2; 5; 1+2*3; (1+2) * 3; (4 + 3) * (9 + 1) * (4 + (4 + ( 4 + 4 )))
def do_math(statement):
    # Hold each individual portion of the problem
    open_statements = []
    # How many parenthesis the parse has open right now
    currently_open_pars = 0
    # The current statement we are parsing
    current_statement = ""
    # The current number we are parsing
    current_number = ""

    # Begin parsing
    for symbol in statement:
        # Ignore spaces
        if symbol == ' ':
            continue

        par_val = parenthesis_value(symbol)

        # Check if we're opening new parenthesis
        if par_val == 1:
            currently_open_pars += par_val

        # Parsing multi-digit numbers
        try:
            # See if its a number
            current_number += int(symbol)
            # Pass it to the next iteration to see if the number continues
            continue
        except:
            pass

        # Current symbol must be one of '(', ')', '*', '+'

        # Parse the previous int, if it exists and we have nothing more to add to it
        if not current_number == "":
            # We have a number stored
            current_statement += int(current_number)
            # Reset it
            current_number = ""

        # Add the current symbol (if it is either 1. the first/last parenthesis OR 2. not a parenthesis
        if not abs(par_val) == currently_open_pars or par_val == 0:
            current_statement += symbol

        was_complex_statement = currently_open_pars > 0

        # Check if we just closed the parenthesis
        if par_val == -1:
            currently_open_pars += par_val

        # Check if we can push the value to the open statements
        if currently_open_pars == 0:
            # Push the statement to the list
            if was_complex_statement:
                open_statements.append(do_math(current_statement))
            else:
                open_statements.append(current_statement)

            # Reset
            current_statement = ""
        elif currently_open_pars < 0:
            return None

    if not current_number == "":
        # If the last character is a digit the loop won't automatically add it
        open_statements.append(current_number)
        current_number = ""

    if not currently_open_pars == 0:
        return None

    return execute(open_statements)


# Get the increment value for a symbol
# -1 = Closing, 0 = None, 1 = Opening
def parenthesis_value(symbol):
    if symbol == '(':
        return 1
    elif symbol == ')':
        return -1
    else:
        return 0


# Computes the result of an array representing a mathematical equation
# Acceptable components: integer, '+', '*'
# Components may also be another list of components that will be processed recursively
# Returns the integer result or an exception
def execute(components):
    # If a component is an array (subcomponent) execute this method on it first
    preprocessed = []

    for component in components:
        if type(component) == 'list':
            # subcomponent
            preprocessed.append(execute(component))
        else:
            preprocessed.append(component)

    # All the indexes we need to multiply at
    multiply = []

    for index in range(0, len(preprocessed)):
        component = preprocessed[index]

        if component == '*':
            multiply.append(index)

    # Process multiplication from back to front
    # Processing from back to front ensures that sequential multiplication operations can be processed correctly
    for index in reversed(multiply):
        # Get the values on either side
        val_one = int(preprocessed[index - 1])
        val_two = int(preprocessed[index + 1])

        # Replace the operator with the processed value
        preprocessed[index] = val_one * val_two

        # Remove the values on either side
        preprocessed.pop(index + 1)
        preprocessed.pop(index - 1)

    # All sub-components (parenthesis) and multiplication operations have been simplified to one value
    # Assuming the remaining components need to be added together
    result = 0
    for component in preprocessed:
        try:
            result += int(component)
        except:
            # Probably a '+'
            pass

    return result
