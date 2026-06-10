
def wrap_red(text: str) -> str:

    ansi_red = "\033[2;31m"  
    bold="[1;2m"
    ansi_reset = "\033[0m"  
    return f"```ansi\n{ansi_red}{bold}{text}{ansi_reset}\n```"


def wrap_green(text: str) -> str:
    ansi_green = "\033[2;32m"
    bold="[1;2m"
    ansi_reset = "\033[0m"
    return f"```ansi\n{ansi_green}{bold}{text}{ansi_reset}\n```"

def wrap_orange(text: str) -> str:
    ansi_orange = "\033[2;33m"
    bold="[1;2m"
    ansi_reset = "\033[0m"
    return f"```ansi\n{ansi_orange}{bold}{text}{ansi_reset}\n```"

def wrap_blue(text: str) -> str:
    ansi_blue = "\033[2;34m"
    bold="[1;2m"
    ansi_reset = "\033[0m"
    return f"```ansi\n{ansi_blue}{bold}{text}{ansi_reset}\n```"

def wrap_yellow(text: str) -> str:
    ansi_yellow = "\033[2;33m"
    bold="[1;2m"
    ansi_reset = "\033[0m"
    return f"```ansi\n{ansi_yellow}{bold}{text}{ansi_reset}\n```"

def wrap_pink(text: str) -> str:
    ansi_pink = "\033[2;35m"
    bold="[1;2m"
    ansi_reset = "\033[0m"
    return f"```ansi\n{ansi_pink}{bold}{text}{ansi_reset}\n```"


def wrap_white(text: str) -> str:
    ansi_white = "\033[2;37m"
    bold="[1;2m"
    ansi_reset = "\033[0m"
    return f"```ansi\n{ansi_white}{bold}{text}{ansi_reset}\n```"

def wrap_sky_blue(text: str) -> str:
    ansi_sky_blue = "\033[1;36m"
    bold="[1;2m"
    ansi_reset = "\033[0m"
    return f"```ansi\n{ansi_sky_blue}{bold}{text}{ansi_reset}\n```"

