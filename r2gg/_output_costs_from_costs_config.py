def output_costs_from_costs_config(costs_config, row):
    values = {}
    output_costs = ()

    for variable in costs_config["variables"]:
        if variable["mapping"] == "value":
            values[variable["name"]] = row[variable["alias"]]
        else:
            values[variable["name"]] = variable["mapping"][str(row[variable["alias"]])]

    for output in costs_config["outputs"]:
        result = 0
        for flag in output["negative_flags"]:
            if values[flag] == -1:
                result = -1
        if result != -1:
            for operation in output["operations"]:
                if operation[0] == "add":
                    if isinstance(operation[1], str):
                        result += values[operation[1]]
                    else:
                        result += operation[1]
                elif operation[0] == "substract":
                    if isinstance(operation[1], str):
                        result -= values[operation[1]]
                    else:
                        result -= operation[1]
                elif operation[0] == "multiply":
                    if isinstance(operation[1], str):
                        result *= values[operation[1]]
                    else:
                        result *= operation[1]
                elif operation[0] == "divide":
                    if isinstance(operation[1], str):
                        result /= values[operation[1]]
                    else:
                        result /= operation[1]

        output_costs += (result,)

    return output_costs
