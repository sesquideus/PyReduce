import colorama
from colorama import Fore, Style

colorama.init()


def colour(what, how):
    return f"{how}{what}{Style.RESET_ALL}"


colours = {
    'debug': Fore.LIGHTBLACK_EX,
    'ok': Fore.GREEN,
    'warn': Fore.YELLOW,
    'error': Fore.RED,
    'critical': Fore.RED,
    'param': Fore.LIGHTCYAN_EX,
    'path': Fore.LIGHTMAGENTA_EX,
    'name': Fore.MAGENTA,
    'over':  Fore.LIGHTGREEN_EX,
    'act': Fore.LIGHTBLUE_EX,
    'step': Fore.LIGHTYELLOW_EX,
}

#for key, clr in colours.items():
#    setattr(, key, lambda x: colours[clr](x))

def step(what):
    return colour(what, Fore.LIGHTBLUE_EX)


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