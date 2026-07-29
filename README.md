![immagine](https://github.com/user-attachments/assets/27b83bb1-7a50-4923-a453-0a958fbe11ed)

A Taskwarrior scheduler for people who want a realistic plan, not a manual to-do list.
It turns tasks, working hours, and calendar blocks into an actionable schedule — then keeps due dates visible.

Use it if you want to:
- stop guessing what to do next
- fit tasks into real availability
- catch overload before deadlines slip
- keep Taskwarrior as the source of truth

> [!IMPORTANT]
> This repo is actively maintained again

## Features

- ✨ Auto-schedule tasks from working hours + calendar blocks
- 🧭 Support complex working-hour maps
- ⏱️ Consider urgency, due dates, and dependencies
- 🧪 Dry-run mode to preview changes
- 🧠 Auto-adjust urgency when deadlines cannot be met
- 🔄 Force-refresh iCal calendars
- 📊 Custom reports for planned and unplanned tasks
- 🎨 Report styling with emoji and extra attributes
- 🗓️ Block time with iCal or Google Calendar, including all-day events

## Quick start

1. `pipx install taskcheck`
2. `taskcheck --install` ← setup only
3. add `estimated` + `time_map` UDAs
4. edit `~/.config/task/taskcheck.toml` (see [Reference](#Reference))
5. `taskcheck --schedule`

## How it works

Taskcheck reads your pending and waiting tasks, estimates when each one can be worked on, and writes back a schedule.
It respects:
- your working hours
- task duration estimates
- calendar events and vacations from iCal / Google Calendar
- task urgency and due dates

It updates Taskwarrior with:
- `scheduled` → when work should start
- `completion_date` → when work is expected to finish
- a warning when a task will miss its due date

### Required UDAs

- `estimated`: expected duration in hours
- `time_map`: which working-hour profile applies to the task, for example `work` or `weekend`

Example:

```toml
[time_maps.work]
monday = [[9, 12.30], [14, 17]]
tuesday = [[9, 12.30], [14, 17]]
```

### Reports

- `taskcheck -r today` → tasks planned for today
- `taskcheck -r 1w` → tasks planned for the next week

## Reference

📚 Full reference: [REFERENCE.md](REFERENCE.md)

In short:
- `taskcheck --install` is interactive
- it installs required Taskwarrior settings if you confirm the first prompt
- it installs optional urgency/report tuning if you confirm the second prompt
- it can also create the default config file if you confirm the third prompt
- it does **not** schedule tasks or fetch calendars
- scheduling happens with `taskcheck --schedule`
- all flags/config keys/settings are documented in `REFERENCE.md`

## Algorithm

The algorithm simulates a workday one chunk at a time.

For each day starting from today, it sorts tasks by urgency and picks the most urgent task that fits the available time.
It assigns a small block of work, then recomputes urgency exactly as Taskwarrior would on that day.
If urgency changes, the next task choice can change too.

For `today`, taskcheck skips past hours.

The default work chunk is 2 hours (or less if the task is shorter); you can tune it with the Taskwarrior UDA `min_block`.

If any task would finish after its `due_date`, taskcheck reduces `weight_urgency` by 0.1 and retries until deadlines are respected or the weight reaches 0.

## Tips and Tricks

- You can exclude a task from being scheduled by removing the `time_map` or `estimated` attributes.
- You can see tasks that you can execute now with the `task ready` report.

See the reference section above for flags, config keys, and installed Taskwarrior settings.
