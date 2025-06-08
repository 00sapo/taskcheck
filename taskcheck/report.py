import random
import sys
from datetime import timedelta
from datetime import datetime
import json
import re
import subprocess


from rich import print
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

from random_unicode_emoji import random_emoji


DEFAULT_EMOJI_KEYWORDS = {
    "meet": ":busts_in_silhouette:",
    "incontr": ":busts_in_silhouette:",
    "rencontr": ":busts_in_silhouette:",
    "reun": ":busts_in_silhouette:",
    "treff": ":busts_in_silhouette:",
    "review": ":mag_right:",
    "revis": ":mag_right:",
    "révis": ":mag_right:",
    "überprüf": ":mag_right:",
    "write": ":pencil2:",
    "scriv": ":pencil2:",
    "écri": ":pencil2:",
    "escrib": ":pencil2:",
    "schreib": ":pencil2:",
    "read": ":books:",
    "legg": ":books:",
    "lis": ":books:",
    "le": ":books:",
    "les": ":books:",
    "posta": ":email:",
    "courri": ":email:",
    "corre": ":email:",
    "mail": ":email:",
    "call": ":telephone_receiver:",
    "chiam": ":telephone_receiver:",
    "appel": ":telephone_receiver:",
    "llam": ":telephone_receiver:",
    "ruf": ":telephone_receiver:",
    "présent": ":chart_with_upwards_trend:",
    "present": ":chart_with_upwards_trend:",
    "präsent": ":chart_with_upwards_trend:",
    "learn": ":mortar_board:",
    "impar": ":mortar_board:",
    "appren": ":mortar_board:",
    "aprend": ":mortar_board:",
    "lern": ":mortar_board:",
    "search": ":mag:",
    "cerc": ":mag:",
    "cherch": ":mag:",
    "busc": ":mag:",
    "such": ":mag:",
    "idea": ":bulb:",
    "idé": ":bulb:",
    "ide": ":bulb:",
    "break": ":coffee:",
    "paus": ":coffee:",
    "descans": ":coffee:",
    "lunch": ":fork_and_knife:",
    "pranz": ":fork_and_knife:",
    "déjeun": ":fork_and_knife:",
    "almorz": ":fork_and_knife:",
    "mittag": ":fork_and_knife:",
    "test": ":test_tube:",
    "develop": ":hammer_and_wrench:",
    "svilupp": ":hammer_and_wrench:",
    "développ": ":hammer_and_wrench:",
    "desarroll": ":hammer_and_wrench:",
    "entwickl": ":hammer_and_wrench:",
    "disegn": ":art:",
    "diseñ": ":art:",
    "design": ":art:",
    "dafar": ":memo:",
    "tarea": ":memo:",
    "todo": ":memo:",
    "bug": ":beetle:",
    "käfer": ":beetle:",
    "fix": ":wrench:",
    "corregg": ":wrench:",
    "répar": ":wrench:",
    "beheb": ":wrench:",
    "urgent": ":exclamation:",
    "dringend": ":exclamation:",
    "deadlin": ":hourglass_flowing_sand:",
    "scadenz": ":hourglass_flowing_sand:",
    "délais": ":hourglass_flowing_sand:",
    "fechalim": ":hourglass_flowing_sand:",
    "frist": ":hourglass_flowing_sand:",
    "updat": ":arrows_counterclockwise:",
    "aggiorn": ":arrows_counterclockwise:",
    "mett": ":arrows_counterclockwise:",
    "actualiz": ":arrows_counterclockwise:",
    "aktualisier": ":arrows_counterclockwise:",
    "clean": ":broom:",
    "pul": ":broom:",
    "nettoy": ":broom:",
    "limpi": ":broom:",
    "reinig": ":broom:",
    "deploy": ":rocket:",
    "rilasc": ":rocket:",
    "déploy": ":rocket:",
    "despleg": ":rocket:",
    "bereitstell": ":rocket:",
    "festegg": ":tada:",
    "célébr": ":tada:",
    "celebr": ":tada:",
    "feier": ":tada:",
    "research": ":microscope:",
    "ricerc": ":microscope:",
    "recherch": ":microscope:",
    "investig": ":microscope:",
    "forsch": ":microscope:",
    "shop": ":shopping_cart:",
    "achet": ":shopping_cart:",
    "compr": ":shopping_cart:",
    "einkauf": ":shopping_cart:",
    "social": ":handshake:",
    "sozial": ":handshake:",
    "exercis": ":running_shoe:",
    "eserciz": ":running_shoe:",
    "exercic": ":running_shoe:",
    "ejerc": ":running_shoe:",
    "übun": ":running_shoe:",
    "évènement": ":calendar:",
    "event": ":calendar:",
    "movie": ":clapper:",
    "pelicul": ":clapper:",
    "film": ":clapper:",
    "music": ":musical_note:",
    "musik": ":musical_note:",
    "travel": ":airplane:",
    "viagg": ":airplane:",
    "voyag": ":airplane:",
    "viaj": ":airplane:",
    "reis": ":airplane:",
    "home": ":house:",
    "mais": ":house:",
    "cas": ":house:",
    "haus": ":house:",
    "docu": ":notebook:",
    "dokum": ":notebook:",
    "backup": ":floppy_disk:",
    "salvat": ":floppy_disk:",
    "sauveg": ":floppy_disk:",
    "copiaseg": ":floppy_disk:",
    "sicher": ":floppy_disk:",
    "debug": ":bug:",
    "débug": ":bug:",
    "note": ":spiral_notepad:",
    "not": ":spiral_notepad:",
    "focus": ":dart:",
    "concentr": ":dart:",
    "konzentrier": ":dart:",
    "codic": ":computer:",
    "cod": ":computer:",
    "code": ":computer:",
    "serveur": ":cloud:",
    "servidor": ":cloud:",
    "server": ":cloud:",
    "client": ":briefcase:",
    "priorid": ":bangbang:",
    "priorit": ":bangbang:",
    "star": ":star:",
    "stell": ":star:",
    "étoil": ":star:",
    "estrell": ":star:",
    "stern": ":star:",
    "critic": ":fire:",
    "kritisch": ":fire:",
}


def get_tasks(config, tasks, year, month, day):
    regex = re.compile(rf"{year:04d}-{month:02d}-{day:02d} - ([PDTHM0-9]+)")
    valid_tasks = []
    for task in tasks:
        for line in task["scheduling"].split("\n"):
            m = regex.match(line)
            if m:
                due = task.get("due", "")
                if due:
                    due = datetime.strptime(due, "%Y%m%dT%H%M%SZ")
                    due = due - datetime.today()
                valid_tasks.append(
                    {
                        "id": task["id"],
                        "project": task.get("project", ""),
                        "description": task["description"],
                        "urgency": task["urgency"],
                        "scheduling_day": f"{year}-{month}-{day}",
                        "scheduling_hours": m.group(1),
                        **{
                            attr: task.get(attr, "")
                            for attr in config.get("additional_attributes", [])
                        },
                    }
                )
    valid_tasks = sorted(valid_tasks, key=lambda x: x["urgency"], reverse=True)
    return valid_tasks


def get_taskwarrior_date(date, _retry=True, taskrc=None):
    from taskcheck.common import get_task_env

    env = get_task_env(taskrc)
    date = subprocess.run(
        ["task", "calc", date],
        capture_output=True,
        text=True,
        env=env,
    )
    date = date.stdout.strip()
    try:
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
    except Exception as _:
        if _retry:
            return get_taskwarrior_date("today+" + date, False, taskrc)
        else:
            print(
                "Please provide a valid date. Check with `task calc` that your date is in the format YYYY-MM-DDTHH:MM:SS",
                file=sys.stderr,
            )
            exit(2)
    return date


def get_days_in_constraint(constraint, taskrc=None):
    current_date = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    constraint = get_taskwarrior_date(constraint, taskrc=taskrc)
    while current_date <= constraint:
        yield current_date.year, current_date.month, current_date.day
        current_date += timedelta(days=1)


def tostring(value):
    if isinstance(value, bool):
        return "Yes" if value else "No"
    elif isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    elif isinstance(value, str):
        try:
            date = datetime.strptime(value, "%Y%m%dT%H%M%SZ")
            return date.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value
    else:
        return str(value)


def get_unplanned_tasks(config, tasks, taskrc=None):
    from taskcheck.common import get_task_env

    env = get_task_env(taskrc)
    tasks = subprocess.run(
        ["task", "scheduling:", "status:pending", "export"],
        capture_output=True,
        text=True,
        env=env,
    )
    tasks = json.loads(tasks.stdout)
    return tasks


def generate_report(config, constraint, verbose=False, force_update=False, taskrc=None, scheduling_results=None):
    config = config["report"]
    console = Console()
    
    if scheduling_results is not None:
        # Use provided scheduling results (from dry-run mode)
        tasks = scheduling_results
    else:
        # Fetch tasks from Taskwarrior normally
        tasks = fetch_tasks(taskrc)

    if config.get("include_unplanned"):
        unplanned_tasks = get_unplanned_tasks(config, tasks, taskrc=taskrc)
        display_unplanned_tasks(console, config, unplanned_tasks)

    for year, month, day in get_days_in_constraint(constraint, taskrc=taskrc):
        this_day_tasks = get_tasks(config, tasks, year, month, day)

        display_date_header(console, year, month, day)

        display_tasks_table(console, config, this_day_tasks)


def fetch_tasks(taskrc=None):
    """Fetch tasks from the task manager and return them as a JSON object."""
    from taskcheck.common import get_task_env

    env = get_task_env(taskrc)
    tasks = subprocess.run(
        ["task", "scheduling~.", "(", "+PENDING", "or", "+WAITING", ")", "export"],
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(tasks.stdout)


def display_date_header(console, year, month, day):
    """Display a date header with a calendar emoji."""
    date_str = f":calendar: [bold cyan]{year}-{month}-{day}[/bold cyan]"
    console.print(Panel(date_str, style="bold blue", expand=False))


def display_tasks_table(console, config, tasks):
    """Display a table of tasks for a specific day."""
    if tasks:
        table = build_tasks_table(config, tasks)
        console.print(table)
    else:
        console.print("[italic dim]No tasks scheduled for this day.[/italic dim]")


def build_tasks_table(config, tasks):
    """Build a Rich table for displaying tasks."""
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Task", style="dim", width=12)
    table.add_column("Project", style="dim", width=12)
    table.add_column("Description")
    table.add_column("Time", justify="right")
    for attr in config.get("additional_attributes", []):
        table.add_column(attr.capitalize(), justify="right")

    for task in tasks:
        task_id = f"[bold green]#{task['id']}[/bold green]"
        project = task.get("project", "")
        description = Text(task["description"], style="italic")
        hours = f"[yellow]{task['scheduling_hours']}[/yellow]"
        emoji = get_task_emoji(config, task)

        table.add_row(
            f"{emoji} {task_id}",
            project,
            description,
            hours,
            *[
                tostring(task.get(attr, ""))
                for attr in config.get("additional_attributes", [])
            ],
        )
    return table


def get_task_emoji(config, task):
    """Get an emoji based on keywords in the task description."""
    for keyword in config.get("emoji_keywords", []):
        if keyword in task["description"].lower():
            return config["emoji_keywords"][keyword]
    for keyword, emoji in DEFAULT_EMOJI_KEYWORDS.items():
        if keyword in task["description"].lower():
            return emoji
    # sum the unicode numbers of each letter in the description and use it as seed to get a random unicode
    # emoji
    seed = sum(ord(char) for char in task["description"])
    emoji = ""
    # seed the next call to random.choice
    random.seed(seed)
    emoji = random_emoji()[0]
    # some emoji coutn for more than one character and misbehave the tables of rich
    if len(emoji) > 1:
        while len(emoji) != 1:
            emoji = random_emoji()[0]
    return emoji


def display_unplanned_tasks(console, config, tasks):
    """Display unplanned tasks if any are found."""
    if tasks:
        table = build_unplanned_tasks_table(config, tasks)
        console.print(Panel("Unplanned Tasks", style="bold blue", expand=False))
        console.print(table)
    else:
        console.print(
            Panel(
                "[italic dim]No unplanned tasks found.[/italic dim]",
                style="bold blue",
                expand=False,
            )
        )


def build_unplanned_tasks_table(config, tasks):
    """Build a Rich table for displaying unplanned tasks."""
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Task", style="dim", width=12)
    table.add_column("Project", style="dim", width=12)
    table.add_column("Description")
    for attr in config.get("additional_attributes_unplanned", []):
        table.add_column(attr.capitalize(), justify="right")

    for task in tasks:
        task_id = f"[bold green]#{task['id']}[/bold green]"
        project = task.get("project", "")
        description = Text(task["description"], style="italic")
        emoji = get_task_emoji(config, task)

        table.add_row(
            f"{emoji} {task_id}",
            project,
            description,
            *[
                tostring(task.get(attr, ""))
                for attr in config.get("additional_attributes_unplanned", [])
            ],
        )
    return table
