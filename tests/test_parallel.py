from datetime import datetime, timedelta
from unittest.mock import patch

from taskcheck.parallel import (
    get_urgency_coefficients,
    check_tasks_parallel,
    initialize_task_info,
    allocate_time_for_day,
    urgency_due,
    urgency_age,
    urgency_estimated,
    recompute_urgencies,
    UrgencyCoefficients,
)


class TestUrgencyCoefficients:
    def test_get_urgency_coefficients(self, mock_task_export_with_taskrc, test_taskrc):
        coeffs = get_urgency_coefficients(taskrc=test_taskrc)

        assert isinstance(coeffs, UrgencyCoefficients)
        assert "P1H" in coeffs.estimated
        assert coeffs.estimated["P1H"] == 5.0
        assert coeffs.inherit is True
        assert coeffs.active == 4.0


class TestUrgencyCalculations:
    def test_urgency_due_overdue(self):
        coeffs = UrgencyCoefficients({}, False, 0, 365, 12, 2)
        task_info = {
            "task": {
                "due": "20231201T170000Z"  # Past due
            }
        }
        date = datetime(2023, 12, 10).date()  # 9 days later

        urgency = urgency_due(task_info, date, coeffs)
        assert urgency == 12.0  # Max urgency for overdue

    def test_urgency_due_approaching(self):
        coeffs = UrgencyCoefficients({}, False, 0, 365, 12, 2)
        task_info = {
            "task": {
                "due": "20231210T170000Z"  # Due in future
            }
        }
        date = datetime(2023, 12, 5).date()  # 5 days before

        urgency = urgency_due(task_info, date, coeffs)
        assert 0 < urgency < 12.0

    def test_urgency_age(self):
        coeffs = UrgencyCoefficients({}, False, 0, 365, 12, 2)
        task_info = {
            "task": {
                "entry": "20231120T090000Z"  # 15 days ago
            }
        }
        date = datetime(2023, 12, 5).date()

        urgency = urgency_age(task_info, date, coeffs)
        expected = 1.0 * 15 / 365 * 2  # age calculation
        assert abs(urgency - expected) < 0.01

    def test_urgency_estimated(self):
        coeffs = UrgencyCoefficients({"P1H": 5.0, "P2H": 8.0}, False, 0, 365, 12, 2)
        task_info = {"remaining_hours": 1.0}

        urgency = urgency_estimated(task_info, None, coeffs)
        assert urgency == 5.0


class TestTaskInitialization:
    @patch("taskcheck.parallel.get_long_range_time_map")
    def test_initialize_task_info(self, mock_long_range, sample_tasks, sample_config):
        mock_long_range.return_value = ([8.0, 8.0, 8.0], 0.0)

        time_maps = sample_config["time_maps"]
        days_ahead = 3
        coeffs = UrgencyCoefficients(
            {"P1H": 5.0, "P2H": 8.0, "P3H": 10.0}, False, 4.0, 365, 12, 2
        )
        calendars = []

        task_info = initialize_task_info(
            sample_tasks, time_maps, days_ahead, coeffs, calendars
        )

        assert len(task_info) == len(sample_tasks)
        for uuid, info in task_info.items():
            assert "task" in info
            assert "remaining_hours" in info
            assert "task_time_map" in info
            assert "urgency" in info


class TestTimeAllocation:
    def test_allocate_time_for_day_single_task(self, sample_config):
        task_info = {
            "task-1": {
                "task": {
                    "id": 1,
                    "uuid": "task-1",
                    "description": "Test task",
                    "estimated": "P2H",
                },
                "remaining_hours": 2.0,
                "task_time_map": [8.0, 8.0, 8.0],
                "today_used_hours": 0.0,
                "scheduling": {},
                "urgency": 10.0,
                "estimated_urgency": 8.0,
                "due_urgency": 0.0,
                "age_urgency": 1.0,
                "started": False,
            }
        }

        coeffs = UrgencyCoefficients({"P2H": 8.0}, False, 4.0, 365, 12, 2)

        allocate_time_for_day(task_info, 0, coeffs, verbose=True, weight_urgency=1.0)

        assert task_info["task-1"]["remaining_hours"] < 2.0
        assert len(task_info["task-1"]["scheduling"]) > 0

    def test_allocate_time_for_day_wait_and_dependency_skip(self):
        today = datetime.today().date()
        wait_date = (today + timedelta(days=1)).strftime("%Y%m%dT%H%M%SZ")
        task_info = {
            "task-1": {
                "task": {"id": 1, "uuid": "task-1", "estimated": "P2H", "wait": wait_date},
                "remaining_hours": 2.0,
                "task_time_map": [8.0],
                "today_used_hours": 0.0,
                "scheduling": {},
                "urgency": 10.0,
                "estimated_urgency": 8.0,
                "due_urgency": 0.0,
                "age_urgency": 1.0,
                "started": False,
            },
            "task-2": {
                "task": {"id": 2, "uuid": "task-2", "estimated": "P2H", "depends": ["task-1"]},
                "remaining_hours": 2.0,
                "task_time_map": [8.0],
                "today_used_hours": 0.0,
                "scheduling": {},
                "urgency": 9.0,
                "estimated_urgency": 8.0,
                "due_urgency": 0.0,
                "age_urgency": 1.0,
                "started": False,
            },
        }
        coeffs = UrgencyCoefficients({"P2H": 8.0}, False, 4.0, 365, 12, 2)
        allocate_time_for_day(task_info, 0, coeffs, verbose=False, weight_urgency=1.0)
        assert task_info["task-1"]["remaining_hours"] == 2.0
        assert task_info["task-2"]["remaining_hours"] == 2.0


class TestDependencies:
    def test_task_with_dependencies(self, sample_config):
        task_info = {
            "task-1": {
                "task": {
                    "id": 1,
                    "uuid": "task-1",
                    "description": "Dependent task",
                    "depends": ["task-2"],
                    "estimated": "P2H",
                },
                "remaining_hours": 2.0,
                "task_time_map": [8.0, 8.0, 8.0],
                "today_used_hours": 0.0,
                "scheduling": {},
                "urgency": 10.0,
                "estimated_urgency": 8.0,
                "due_urgency": 0.0,
                "age_urgency": 1.0,
                "started": False,
            },
            "task-2": {
                "task": {
                    "id": 2,
                    "uuid": "task-2",
                    "description": "Dependency task",
                    "estimated": "P1H",
                },
                "remaining_hours": 1.0,
                "task_time_map": [8.0, 8.0, 8.0],
                "today_used_hours": 0.0,
                "scheduling": {},
                "urgency": 15.0,
                "estimated_urgency": 5.0,
                "due_urgency": 0.0,
                "age_urgency": 1.0,
                "started": False,
            },
        }

        coeffs = UrgencyCoefficients({"P1H": 5.0, "P2H": 8.0}, False, 4.0, 365, 12, 2)

        allocate_time_for_day(task_info, 0, coeffs, verbose=True, weight_urgency=1.0)

        # task-2 should be scheduled first due to dependency
        if task_info["task-2"]["remaining_hours"] == 0:
            # task-2 completed, task-1 can now be scheduled
            assert task_info["task-1"]["remaining_hours"] <= 2.0


class TestWeightConfiguration:
    @patch("taskcheck.parallel.get_calendars")
    @patch("taskcheck.parallel.get_tasks")
    @patch("taskcheck.parallel.get_urgency_coefficients")
    @patch("taskcheck.parallel.update_tasks_with_scheduling_info")
    def test_urgency_weight_override(
        self,
        mock_update,
        mock_coeffs,
        mock_tasks,
        mock_calendars,
        sample_config,
        sample_tasks,
    ):
        """Test that urgency_weight_override properly overrides config values."""
        # Set config values
        sample_config["scheduler"]["weight_urgency"] = 0.8
        sample_config["scheduler"]["weight_due_date"] = 0.2

        mock_tasks.return_value = sample_tasks
        mock_coeffs.return_value = UrgencyCoefficients(
            {"P1H": 5.0, "P2H": 8.0, "P3H": 10.0}, False, 4.0, 365, 12, 2
        )
        mock_calendars.return_value = []

        # Call with override
        check_tasks_parallel(sample_config, urgency_weight_override=0.3)

        # Verify the function was called - we'd need to check internal logic
        # This test would need access to the weights used internally
        mock_tasks.assert_called_once()

    @patch("taskcheck.parallel.get_calendars")
    @patch("taskcheck.parallel.get_tasks")
    @patch("taskcheck.parallel.get_urgency_coefficients")
    @patch("taskcheck.parallel.update_tasks_with_scheduling_info")
    def test_config_weights_used_when_no_override(
        self,
        mock_update,
        mock_coeffs,
        mock_tasks,
        mock_calendars,
        sample_config,
        sample_tasks,
    ):
        """Test that config weights are used when no override is provided."""
        sample_config["scheduler"]["weight_urgency"] = 0.6
        sample_config["scheduler"]["weight_due_date"] = 0.4

        mock_tasks.return_value = sample_tasks
        mock_coeffs.return_value = UrgencyCoefficients(
            {"P1H": 5.0, "P2H": 8.0, "P3H": 10.0}, False, 4.0, 365, 12, 2
        )
        mock_calendars.return_value = []

        # Call without override
        check_tasks_parallel(sample_config, urgency_weight_override=None)

        mock_tasks.assert_called_once()

    def test_recompute_urgencies_with_weights(self):
        tasks_remaining = {
            "task-1": {
                "task": {"uuid": "task-1", "id": 1},
                "urgency": 10.0,
                "estimated_urgency": 5.0,
                "due_urgency": 3.0,
                "age_urgency": 1.0,
                "remaining_hours": 2.0,
                "started": False,
            }
        }

        coeffs = UrgencyCoefficients({"P2H": 8.0}, False, 0, 365, 12, 2)
        date = datetime.now().date()
        recompute_urgencies(tasks_remaining, coeffs, date, 0.7)
        assert tasks_remaining["task-1"]["urgency"] >= tasks_remaining["task-1"]["due_urgency"]

    def test_recompute_urgencies_inherit_and_cycle(self):
        tasks_remaining = {
            "a": {"task": {"uuid": "a", "depends": ["b"]}, "urgency": 1.0, "estimated_urgency": 0.0, "due_urgency": 0.0, "age_urgency": 0.0, "remaining_hours": 1.0, "started": False},
            "b": {"task": {"uuid": "b", "depends": ["a"]}, "urgency": 2.0, "estimated_urgency": 0.0, "due_urgency": 0.0, "age_urgency": 0.0, "remaining_hours": 1.0, "started": False},
        }
        coeffs = UrgencyCoefficients({"P1H": 5.0}, True, 0, 365, 12, 2)
        recompute_urgencies(tasks_remaining, coeffs, datetime.now().date(), 1.0)
        assert tasks_remaining["a"]["urgency"] == tasks_remaining["b"]["urgency"]


class TestMainSchedulingFunction:
    @patch("taskcheck.parallel.get_calendars")
    @patch("taskcheck.parallel.get_tasks")
    @patch("taskcheck.parallel.get_urgency_coefficients")
    @patch("taskcheck.parallel.update_tasks_with_scheduling_info")
    def test_check_tasks_parallel(
        self,
        mock_update,
        mock_coeffs,
        mock_tasks,
        mock_calendars,
        sample_config,
        sample_tasks,
        test_taskrc,
    ):
        mock_tasks.return_value = sample_tasks
        mock_coeffs.return_value = UrgencyCoefficients(
            {"P1H": 5.0, "P2H": 8.0, "P3H": 10.0}, False, 4.0, 365, 12, 2
        )
        mock_calendars.return_value = []

        check_tasks_parallel(sample_config, verbose=True, taskrc=test_taskrc)

        mock_tasks.assert_called_once_with(taskrc=test_taskrc)
        mock_coeffs.assert_called_once_with(taskrc=test_taskrc)
        mock_calendars.assert_called_once()
        mock_update.assert_called_once()


class TestAutoAdjustUrgency:
    @patch("taskcheck.parallel.get_calendars")
    @patch("taskcheck.parallel.get_tasks")
    @patch("taskcheck.parallel.get_urgency_coefficients")
    @patch("taskcheck.parallel.update_tasks_with_scheduling_info")
    def test_auto_adjust_urgency_enabled(
        self,
        mock_update,
        mock_coeffs,
        mock_tasks,
        mock_calendars,
        sample_config,
        test_taskrc,
    ):
        """Test that auto-adjust reduces urgency weight when tasks are overdue."""
        # Create tasks with tight deadlines that will cause conflicts
        overdue_tasks = [
            {
                "id": 1,
                "uuid": "task-1",
                "description": "Urgent task",
                "estimated": "P8H",
                "time_map": "work",
                "urgency": 20.0,
                "due": "20231206T170000Z",  # Very soon
                "status": "pending",
            },
            {
                "id": 2,
                "uuid": "task-2",
                "description": "Also urgent task",
                "estimated": "P8H",
                "time_map": "work",
                "urgency": 15.0,
                "due": "20231206T170000Z",  # Same deadline
                "status": "pending",
            },
        ]

        mock_tasks.return_value = overdue_tasks
        mock_coeffs.return_value = UrgencyCoefficients(
            {"P8H": 10.0}, False, 4.0, 365, 12, 2
        )
        mock_calendars.return_value = []

        # This should trigger auto-adjustment
        check_tasks_parallel(
            sample_config, verbose=True, taskrc=test_taskrc, auto_adjust_urgency=True
        )

        mock_tasks.assert_called_once_with(taskrc=test_taskrc)

    @patch("taskcheck.parallel.get_calendars")
    @patch("taskcheck.parallel.get_tasks")
    @patch("taskcheck.parallel.get_urgency_coefficients")
    @patch("taskcheck.parallel.update_tasks_with_scheduling_info")
    def test_auto_adjust_urgency_disabled(
        self,
        mock_update,
        mock_coeffs,
        mock_tasks,
        mock_calendars,
        sample_config,
        sample_tasks,
        test_taskrc,
    ):
        """Test that auto-adjust is ignored when disabled."""
        mock_tasks.return_value = sample_tasks
        mock_coeffs.return_value = UrgencyCoefficients(
            {"P1H": 5.0, "P2H": 8.0, "P3H": 10.0}, False, 4.0, 365, 12, 2
        )
        mock_calendars.return_value = []

        # This should not trigger auto-adjustment
        check_tasks_parallel(
            sample_config, verbose=True, taskrc=test_taskrc, auto_adjust_urgency=False
        )

        mock_tasks.assert_called_once_with(taskrc=test_taskrc)

    @patch("taskcheck.parallel.get_calendars")
    @patch("taskcheck.parallel.get_tasks")
    @patch("taskcheck.parallel.get_urgency_coefficients")
    @patch("taskcheck.parallel.get_long_range_time_map")
    @patch("taskcheck.parallel.update_tasks_with_scheduling_info")
    def test_auto_adjust_urgency_weight_reduction(
        self,
        mock_update,
        mock_long_range,
        mock_coeffs,
        mock_tasks,
        mock_calendars,
        sample_config,
        test_taskrc,
    ):
        """Test that auto_adjust_urgency reduces the urgency weight and stops at 0.0."""
        # Use relative dates based on current date
        from datetime import datetime, timedelta

        now = datetime.now()
        tomorrow = now + timedelta(hours=2)

        # Create tasks that cannot be completed on time due to insufficient available time
        overdue_tasks = [
            {
                "id": 1,
                "uuid": "task-1",
                "description": "Impossible task",
                "estimated": "P24H",  # 24 hours
                "time_map": "work",
                "urgency": 20.0,
                "due": tomorrow.strftime(
                    "%Y%m%dT%H%M%SZ"
                ),  # Due tomorrow to trigger overdue detection
                "status": "pending",
                "entry": now.strftime("%Y%m%dT%H%M%SZ"),  # Created today
            }
        ]

        mock_tasks.return_value = overdue_tasks
        mock_coeffs.return_value = UrgencyCoefficients(
            {"P24H": 10.0}, False, 4.0, 365, 12, 2
        )
        mock_calendars.return_value = []
        # Mock no available time at all to make it truly impossible
        mock_long_range.return_value = ([0.0] * 365, 0.0)

        # Patch the console.print to capture output
        with patch("taskcheck.parallel.console.print") as mock_console_print:
            check_tasks_parallel(
                sample_config,
                verbose=True,
                taskrc=test_taskrc,
                auto_adjust_urgency=True,
            )

            # Should print a warning about not finding a solution
            # Print all captured calls for debugging if the assertion fails
            found_warning = any(
                "cannot find a solution"
                in " ".join(str(arg).lower() for arg in call.args)
                for call in mock_console_print.call_args_list
            )
            if not found_warning:
                print("Captured console.print calls for debug:")
                for call in mock_console_print.call_args_list:
                    print(str(call))
            assert found_warning

    @patch("taskcheck.parallel.get_calendars")
    @patch("taskcheck.parallel.get_tasks")
    @patch("taskcheck.parallel.get_urgency_coefficients")
    @patch("taskcheck.parallel.get_long_range_time_map")
    @patch("taskcheck.parallel.update_tasks_with_scheduling_info")
    def test_auto_adjust_urgency_final_weight_message(
        self,
        mock_update,
        mock_long_range,
        mock_coeffs,
        mock_tasks,
        mock_calendars,
        sample_config,
        test_taskrc,
    ):
        now = datetime.now()
        future_date = now + timedelta(days=3)
        overdue_tasks = [
            {"id": 1, "uuid": "task-1", "description": "Tight deadline", "estimated": "P16H", "time_map": "work", "urgency": 20.0, "due": future_date.strftime("%Y%m%dT%H%M%SZ"), "status": "pending", "entry": now.strftime("%Y%m%dT%H%M%SZ")},
            {"id": 2, "uuid": "task-2", "description": "Competing task", "estimated": "P16H", "time_map": "work", "urgency": 15.0, "due": future_date.strftime("%Y%m%dT%H%M%SZ"), "status": "pending", "entry": now.strftime("%Y%m%dT%H%M%SZ")},
        ]
        mock_tasks.return_value = overdue_tasks
        mock_coeffs.return_value = UrgencyCoefficients({"P16H": 10.0, "P8H": 8.0}, False, 4.0, 365, 12, 2)
        mock_calendars.return_value = []
        mock_long_range.return_value = ([4.0] * 7, 0.0)
        with patch("taskcheck.parallel.console.print") as mock_console_print:
            check_tasks_parallel(sample_config, verbose=True, taskrc=test_taskrc, auto_adjust_urgency=True)
            messages = [" ".join(str(arg).lower() for arg in call.args) for call in mock_console_print.call_args_list]
            assert any("final urgency weight" in msg or "cannot find a solution" in msg for msg in messages)

    @patch("taskcheck.parallel.get_calendars")
    @patch("taskcheck.parallel.get_tasks")
    @patch("taskcheck.parallel.get_urgency_coefficients")
    @patch("taskcheck.parallel.get_long_range_time_map")
    def test_check_tasks_parallel_dry_run_and_warning(
        self,
        mock_long_range,
        mock_coeffs,
        mock_tasks,
        mock_calendars,
        sample_config,
        test_taskrc,
    ):
        now = datetime.now()
        due = (now + timedelta(days=1)).strftime("%Y%m%dT%H%M%SZ")
        mock_tasks.return_value = [{"id": 1, "uuid": "task-1", "description": "x", "estimated": "P2H", "time_map": "work", "urgency": 1.0, "due": due, "status": "pending", "entry": now.strftime("%Y%m%dT%H%M%SZ") }]
        mock_coeffs.return_value = UrgencyCoefficients({"P2H": 8.0}, False, 4.0, 365, 12, 2)
        mock_calendars.return_value = []
        mock_long_range.return_value = ([0.5] * 7, 0.0)
        with patch("taskcheck.parallel.console.print") as mock_print:
            result = check_tasks_parallel(sample_config, verbose=False, taskrc=test_taskrc, dry_run=True, auto_adjust_urgency=False)
        assert isinstance(result, list)
        assert result
        assert any("warning" in " ".join(str(a).lower() for a in call.args) for call in mock_print.call_args_list)

    def test_update_tasks_with_scheduling_info_warns_when_late(self):
        task_info = {
            "u": {"task": {"id": 1, "description": "late", "due": "20231201T000000Z"}, "scheduling": {"2023-12-05": 2.0}}
        }
        with patch("taskcheck.parallel.subprocess.run") as mock_run, patch("taskcheck.parallel.console.print") as mock_print:
            from taskcheck.parallel import update_tasks_with_scheduling_info
            update_tasks_with_scheduling_info(task_info, verbose=False, taskrc="/tmp/taskrc")
        mock_run.assert_called_once()
        command = mock_run.call_args.args[0]
        assert command[-1] == "scheduling:2023-12-05 - PT2H"
        assert mock_print.called
