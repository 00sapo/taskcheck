# Taskcheck reference

## `taskcheck --install`

Installs Taskwarrior-side configuration and creates the default Taskcheck config file.

### What it does
`--install` is interactive. It asks three separate questions:

1. **Required settings** — if you confirm, it creates the Taskwarrior UDAs/settings listed below.
2. **Optional settings** — only if you confirm, it applies the urgency/report tuning listed below.
3. **Default config file** — only if you confirm, it creates `~/.config/task/taskcheck.toml` when that file does not already exist.

### What it does not do
- it does not schedule tasks
- it does not fetch calendar events
- it does not modify task dates (`scheduled`, `completion_date`) beyond setup
- it does not authenticate Google Calendar

## Config file: `~/.config/task/taskcheck.toml`

### `[time_maps.<name>]`
Working-hour profiles used by tasks via `time_map`.

Each day key maps to a list of `[start, end]` ranges in 24h time.

Example:
```toml
[time_maps.work]
monday = [[9, 12.30], [14, 17]]
tuesday = [[9, 12.30], [14, 17]]
```

### `[scheduler]`
- `days_ahead`: how far ahead to search for slots
- `weight_urgency`: urgency weight used by scheduling; override with `--urgency-weight`

### `[calendars.<name>]`
Blocks unavailable time from iCal / Google Calendar.
- `url`: iCal URL or `google://<calendar-id>`
- `expiration`: cache lifetime in hours
- `timezone`: optional forced timezone
- `event_all_day_is_blocking`: treat all-day events as blocking
- Google only: `provider = "google"`, `calendar_id`, `token_path`

### `[report]`
- `include_unplanned`: show unplanned tasks too
- `additional_attributes`: extra columns for planned tasks
- `additional_attributes_unplanned`: extra columns for unplanned tasks
- `unplanned_max_due`: hide dated unplanned tasks beyond a Taskwarrior-relative horizon
- `emoji_keywords`: map description keywords to emoji

## Taskwarrior settings installed by `taskcheck --install`

### Required — installed only after confirming the first prompt

These [User Defined Attributes (UDAs)](https://taskwarrior.org/docs/udas/) store Taskcheck's input and results in Taskwarrior.

| Setting | Meaning |
| --- | --- |
| `uda.time_map.type = string` | Adds `time_map`: the named working-hours profile used by a task. |
| `uda.time_map.default = work` | Uses the `work` profile if a task does not specify one. |
| `uda.estimated.type = duration` | Adds `estimated`: expected task duration, for example `2h`. |
| `uda.completion_date.type = date` | Adds `completion_date`: Taskcheck's predicted finish date. |
| `uda.scheduling.type = string` | Adds `scheduling`: schedule data used by Taskcheck reports. |
| `uda.min_block.type = numeric` | Adds `min_block`: the work chunk assigned before Taskcheck recalculates urgency; default `2` hours. |
| `recurrence.confirmation = no` | Prevents confirmation prompts while Taskcheck updates recurring tasks. See [recurring tasks](https://taskwarrior.org/docs/recurrence/). |

### Optional — installed only after confirming the second prompt

These settings are optional; Taskcheck works without them.

| Setting | Meaning |
| --- | --- |
| `urgency.uda.estimated.*.coefficient` | Gives estimates from 1 to 36 hours an urgency contribution. See [urgency](https://taskwarrior.org/docs/urgency/). |
| `report.ready.columns` | Replaces the columns shown by `task ready` with Taskcheck-friendly scheduling columns. See [reports](https://taskwarrior.org/docs/report/). |
| `journal.info = 0` | Hides informational journal entries in task details. See [configuration](https://taskwarrior.org/docs/configuration/). |
| `urgency.inherit = 1` | Makes dependent tasks inherit urgency from tasks that depend on them. See [urgency](https://taskwarrior.org/docs/urgency/). |
| `urgency.blocked.coefficient = 0` | Removes Taskwarrior's urgency adjustment for tasks blocked by dependencies. |
| `urgency.blocking.coefficient = 0` | Removes Taskwarrior's urgency adjustment for tasks blocking dependencies. |
| `urgency.waiting.coefficient = 0` | Removes Taskwarrior's urgency adjustment for waiting tasks. |
| `urgency.scheduled.coefficient = 0` | Removes Taskwarrior's urgency adjustment for scheduled tasks. |

The final four settings use Taskwarrior's [urgency configuration](https://taskwarrior.org/docs/urgency/). Taskcheck accounts for those states itself while scheduling.

## CLI flags

- `-v`, `--verbose`: increase output verbosity
- `-i`, `--install`: install Taskwarrior settings + default config
- `-r`, `--report REPORT`: render a report up to the given Taskwarrior date spec
- `-s`, `--schedule`: run scheduling and write results back
- `-f`, `--force-update`: refresh calendars, ignoring cache
- `--taskrc TASKRC`: use a custom TASKRC directory
- `--urgency-weight FLOAT`: override scheduler urgency weight
- `--dry-run`: preview scheduling without modifying Taskwarrior
- `--no-auto-adjust-urgency`: disable automatic urgency reduction when deadlines cannot be met
- `--add-google-calendar`: authenticate with Google and print a ready-to-paste config block

## Common flows

- first install: `pipx install taskcheck && taskcheck --install`
- schedule now: `taskcheck --schedule`
- preview only: `taskcheck --schedule --dry-run`
- report: `taskcheck --report today`
