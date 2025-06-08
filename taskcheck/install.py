import subprocess
from taskcheck.common import config_dir


default_config = """
[time_maps]
[time_maps.work]
monday = [[9, 12.30], [14, 17]]
tuesday = [[9, 12.30], [14, 17]]
wednesday = [[9, 12.30], [14, 17]]
thursday = [[9, 12.30], [14, 17]]
friday = [[9, 12.30], [14, 17]]

[scheduler]
days_ahead = 365
weight_urgency = 1.0

[report]
include_unplanned = true
additional_attributes = []
additional_attributes_unplanned = []
emoji_keywords = {}
"""


def apply_config(key, value):
    subprocess.run(
        [
            "task",
            "rc.confirmation=0",
            "config",
            key,
            value,
        ],
        stdout=subprocess.DEVNULL,
    )


def install():
    """
    Adds the required and optional settings explaining them to the user.
    Also initialize the config file with some sane default.
    """

    # Define the required configurations
    required_configs = [
        ("uda.time_map.type", "string"),
        ("uda.time_map.label", "Time Map"),
        ("uda.time_map.default", "work"),
        ("uda.estimated.type", "duration"),
        ("uda.estimated.label", "Estimated Time"),
        ("uda.completion_date.type", "date"),
        ("uda.completion_date.label", "Expected Completion Date"),
        ("uda.scheduling.type", "string"),
        ("uda.scheduling.label", "Scheduling"),
        ("uda.min_block.type", "numeric"),
        ("uda.min_block.label", "Minimum Time Block"),
        ("uda.min_block.default", "2"),
        ("recurrence.confirmation", "no"),
    ]

    # Optional configurations
    optional_configs = [
        ("urgency.uda.estimated.PT1H.coefficient", "1"),
        ("urgency.uda.estimated.PT2H.coefficient", "2.32"),
        ("urgency.uda.estimated.PT3H.coefficient", "3.67"),
        ("urgency.uda.estimated.PT4H.coefficient", "4.64"),
        ("urgency.uda.estimated.PT5H.coefficient", "5.39"),
        ("urgency.uda.estimated.PT6H.coefficient", "6.02"),
        ("urgency.uda.estimated.PT7H.coefficient", "6.56"),
        ("urgency.uda.estimated.PT8H.coefficient", "7.03"),
        ("urgency.uda.estimated.PT9H.coefficient", "7.45"),
        ("urgency.uda.estimated.PT10H.coefficient", "7.82"),
        ("urgency.uda.estimated.PT11H.coefficient", "8.16"),
        ("urgency.uda.estimated.PT12H.coefficient", "8.47"),
        ("urgency.uda.estimated.PT13H.coefficient", "8.75"),
        ("urgency.uda.estimated.PT14H.coefficient", "9.01"),
        ("urgency.uda.estimated.PT15H.coefficient", "9.25"),
        ("urgency.uda.estimated.PT16H.coefficient", "9.47"),
        ("urgency.uda.estimated.PT17H.coefficient", "9.68"),
        ("urgency.uda.estimated.PT18H.coefficient", "9.87"),
        ("urgency.uda.estimated.PT19H.coefficient", "10.05"),
        ("urgency.uda.estimated.PT20H.coefficient", "10.22"),
        ("urgency.uda.estimated.PT21H.coefficient", "10.38"),
        ("urgency.uda.estimated.PT22H.coefficient", "10.53"),
        ("urgency.uda.estimated.PT23H.coefficient", "10.67"),
        ("urgency.uda.estimated.P1D.coefficient", "10.80"),
        ("urgency.uda.estimated.P1DT1H.coefficient", "10.93"),
        ("urgency.uda.estimated.P1DT2H.coefficient", "11.05"),
        ("urgency.uda.estimated.P1DT3H.coefficient", "11.16"),
        ("urgency.uda.estimated.P1DT4H.coefficient", "11.27"),
        ("urgency.uda.estimated.P1DT5H.coefficient", "11.37"),
        ("urgency.uda.estimated.P1DT6H.coefficient", "11.47"),
        ("urgency.uda.estimated.P1DT7H.coefficient", "11.56"),
        ("urgency.uda.estimated.P1DT8H.coefficient", "11.65"),
        ("urgency.uda.estimated.P1DT9H.coefficient", "11.73"),
        ("urgency.uda.estimated.P1DT10H.coefficient", "11.81"),
        ("urgency.uda.estimated.P1DT11H.coefficient", "11.89"),
        ("urgency.uda.estimated.P1DT12H.coefficient", "11.96"),
        (
            "report.ready.columns",
            "id,start.age,entry.age,depends.indicator,priority,project,tags,recur.indicator,scheduled.relative,due.relative,until.remaining,description,urgency",
        ),
        ("journal.info", "0"),
        ("urgency.inherit", "1"),
        ("urgency.blocked.coefficient", "0"),
        ("urgency.blocking.coefficient", "0"),
        ("urgency.waiting.coefficient", "0"),
        ("urgency.scheduled.coefficient", "0"),
    ]

    answer = input(
        """
_________________________________________________________________________________________
Required configuration for taskcheck includes:
- 3 UDA fields 
- turning off confirmation for recurring tasks 

Do you want to continue? [y/N] """
    )
    if answer.lower() not in ["y", "yes"]:
        return

    answer = input(
        """
_________________________________________________________________________________________
Optional configuration for taskcheck includes:
- urgency coefficients for estimated time (up to 36 hour duration)
- better `ready` report columns
- turning off printing journal logs in the task details
- turning on urgency inheritance from dependant tasks and disabling blocked and blocking urgency coefficients (as recommended by Taskwarrior documentation)
- turning off urgency for waiting and scheduled tasks (taskcheck already take them into account)

Do you want to apply optional configurations? [y/N] """
    )
    if answer.lower() not in ["y", "yes"]:
        configs = required_configs
    else:
        configs = required_configs + optional_configs

    # Apply configurations using apply_config
    try:
        for key, value in configs:
            apply_config(key, value)
        print("Taskwarrior configurations have been applied successfully.")
    except Exception as e:
        print(f"Failed to apply configurations: {e}")

    answer = input(
        """
_________________________________________________________________________________________
Do you want to create a default config file for taskcheck? [y/N] """
    )
    if answer.lower() not in ["y", "yes"]:
        return

    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "taskcheck.toml"
    if config_file.exists():
        print(f"Config file already exists at {config_file}")
        return
    with open(config_file, "w") as f:
        f.write(default_config)

    print(f"Default config file created at {config_file}")


if __name__ == "__main__":
    install()
