import colorama
from colorama import Fore, Style

colorama.init()


def colour(what, how):
    return f"{how}{what}{Style.RESET_ALL}"


def debug(what, how):
    return colour(what, Fore.LIGHTBLACK_EX)


def ok(what):
    return colour(what, Fore.GREEN)


def num(what):
    return colour(what, Fore.CYAN)


def act(what):
    return colour(what, Fore.LIGHTYELLOW_EX)


def warn(what):
    return colour(what, Fore.YELLOW)


def err(what):
    return colour(what, Fore.RED)


def critical(what):
    return colour(what, Fore.RED)


def param(what):
    return colour(what, Fore.LIGHTCYAN_EX)


def path(what):
    return colour(what, Fore.LIGHTMAGENTA_EX)


def name(what):
    return colour(what, Fore.YELLOW)


def over(what):
    return colour(what, Fore.LIGHTGREEN_EX)


def script(what):
    return colour(what, Fore.LIGHTGREEN_EX)


def print_list(what, fun=lambda x: x):
    return f"[{', '.join(list(map(fun, what)))}]"