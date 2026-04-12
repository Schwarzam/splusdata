from argparse import ArgumentParser, RawDescriptionHelpFormatter


class readFileArgumentParser(ArgumentParser):
    """
    A class that extends :class:`argparse.ArgumentParser` to read arguments from file.

    Methods
    -------
    convert_arg_line_to_args: yeld's arguments reading a file.
    """

    def __init__(self, *args, **kwargs):
        super(readFileArgumentParser, self).__init__(*args, **kwargs)

    def convert_arg_line_to_args(self, line):
        for arg in line.split():
            if not arg.strip():
                continue
            if arg[0] == "#":
                break
            yield arg


def create_parser(args_dict, program_description=None):
    """
    Create the parser for the arguments keys on `args_dict` to `s-cubes`
    entry-points console scripts.

    It uses :class:`readFileArgumentParser` to include the option to read the
    arguments from a file using the prefix @ before the filename::

        entrypoint @file.args

    Parameters
    ----------
    args_dict : dict
        Dictionary to with the long options as keys and a list containing the short
        option char at the first position and the `kwargs` for the argument
        configuration.

    program_description : str, optional
        Program description. Default is None.

    Returns
    -------
    parser : argparse.ArgumentParser
        The arguments parser.

    See Also
    --------
    `argparse.ArgumentParser.add_argument()`
    """
    _formatter = lambda prog: RawDescriptionHelpFormatter(prog, max_help_position=30)

    parser = readFileArgumentParser(
        fromfile_prefix_chars="@",
        description=program_description,
        formatter_class=_formatter,
    )
    for k, v in args_dict.items():
        long_option = k
        short_option, kwargs = v
        option_string = []
        positional = False
        if short_option != "":
            if short_option == "pos":
                positional = True
            else:
                option_string.append(f"-{short_option}")
        if positional:
            option_string.append(long_option)
        else:
            option_string.append(f"--{long_option}")
        if (long_option != "verbose") and (kwargs.get("default") is not None):
            _tmp = kwargs["help"]
            kwargs["help"] = f"{_tmp} Default value is %(default)s"
        parser.add_argument(*option_string, **kwargs)
    return parser
