import pytest
from unittest.mock import patch, Mock, mock_open

from taskcheck.__main__ import main, load_config, arg_parser


class TestArgumentParsing:
    def test_arg_parser_defaults(self):
        """Test default argument values."""
        args = arg_parser.parse_args([])

        assert args.verbose is False
        assert args.install is False
        assert args.report is None
        assert args.schedule is False
        assert args.force_update is False
        assert args.taskrc is None
        assert args.urgency_weight is None
        assert args.dry_run is False
        assert args.auto_adjust_urgency is True

    def test_arg_parser_all_flags(self):
        """Test all command line flags."""
        args = arg_parser.parse_args(
            [
                "-v",
                "-i",
                "-r",
                "today",
                "-s",
                "-f",
                "--taskrc",
                "/custom/path",
                "--urgency-weight",
                "0.7",
            ]
        )

        assert args.verbose is True
        assert args.install is True
        assert args.report == "today"
        assert args.schedule is True
        assert args.force_update is True
        assert args.taskrc == "/custom/path"
        assert args.urgency_weight == 0.7

    def test_arg_parser_long_form(self):
        """Test long form arguments."""
        args = arg_parser.parse_args(
            [
                "--verbose",
                "--install",
                "--report",
                "eow",
                "--schedule",
                "--force-update",
                "--taskrc",
                "/test",
                "--urgency-weight",
                "0.3",
            ]
        )

        assert args.verbose is True
        assert args.install is True
        assert args.report == "eow"
        assert args.schedule is True
        assert args.force_update is True
        assert args.taskrc == "/test"
        assert args.urgency_weight == 0.3

    def test_urgency_weight_argument(self):
        """Test urgency weight argument parsing."""
        args = arg_parser.parse_args(["--urgency-weight", "0.7"])
        assert args.urgency_weight == 0.7

    def test_urgency_weight_argument_validation(self):
        """Test urgency weight argument with valid boundary values."""
        # This should work
        args = arg_parser.parse_args(["--urgency-weight", "0.0"])
        assert args.urgency_weight == 0.0

        args = arg_parser.parse_args(["--urgency-weight", "1.0"])
        assert args.urgency_weight == 1.0

    def test_dry_run_argument(self):
        """Test dry-run argument parsing."""
        args = arg_parser.parse_args(["--dry-run"])
        assert args.dry_run is True

        args = arg_parser.parse_args([])
        assert args.dry_run is False

    def test_auto_adjust_urgency_argument(self):
        """Test auto-adjust-urgency argument parsing."""
        args = arg_parser.parse_args([])
        assert args.auto_adjust_urgency is True

        args = arg_parser.parse_args(["--no-auto-adjust-urgency"])
        assert args.auto_adjust_urgency is False


class TestConfigLoading:
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=b"[scheduler]\ndays_ahead = 7",
    )
    @patch("tomllib.load")
    def test_load_config_success(self, mock_toml_load, mock_file, sample_config):
        """Test successful config loading."""
        mock_toml_load.return_value = sample_config

        config = load_config()

        assert config == sample_config
        mock_file.assert_called_once()
        mock_toml_load.assert_called_once()

    @patch("builtins.open")
    def test_load_config_file_not_found(self, mock_file):
        """Test config loading when file doesn't exist."""
        mock_file.side_effect = FileNotFoundError("Config file not found")

        with pytest.raises(FileNotFoundError):
            load_config()

    @patch("builtins.open", new_callable=mock_open, read_data=b"invalid toml content")
    @patch("tomllib.load")
    def test_load_config_invalid_toml(self, mock_toml_load, mock_file):
        """Test config loading with invalid TOML."""
        mock_toml_load.side_effect = Exception("Invalid TOML")

        with pytest.raises(Exception):
            load_config()


class TestMainFunction:
    def test_main_no_args_shows_help(self, capsys):
        """Test that main shows help when no arguments provided."""
        with patch("sys.argv", ["taskcheck"]):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = False
                mock_args.report = None
                mock_parse.return_value = mock_args

                with patch.object(arg_parser, "print_help") as mock_help:
                    main()
                    mock_help.assert_called_once()

    @patch("taskcheck.install.install")
    def test_main_install_command(self, mock_install):
        """Test install command execution."""
        with patch("sys.argv", ["taskcheck", "--install"]):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = True
                mock_args.schedule = False
                mock_args.report = None
                mock_parse.return_value = mock_args

                main()

                mock_install.assert_called_once()

    @patch("taskcheck.__main__.load_config")
    @patch("taskcheck.__main__.check_tasks_parallel")
    def test_main_schedule_command(
        self,
        mock_check_tasks,
        mock_load_config,
        sample_config,
        test_taskrc,
        mock_task_export_with_taskrc,
    ):
        """Test schedule command execution."""
        mock_load_config.return_value = sample_config

        with patch("sys.argv", ["taskcheck", "--schedule", "--taskrc", test_taskrc]):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = True
                mock_args.report = None
                mock_args.verbose = False
                mock_args.force_update = False
                mock_args.taskrc = test_taskrc
                mock_args.urgency_weight = None
                mock_args.dry_run = False
                mock_parse.return_value = mock_args

                main()

                mock_load_config.assert_called_once()
                mock_check_tasks.assert_called_once_with(
                    sample_config,
                    verbose=False,
                    force_update=False,
                    taskrc=test_taskrc,
                    urgency_weight_override=None,
                    dry_run=False,
                )

    @patch("taskcheck.__main__.load_config")
    @patch("taskcheck.report.generate_report")
    def test_main_report_command(
        self, mock_generate_report, mock_load_config, sample_config, test_taskrc
    ):
        """Test report command execution."""
        mock_load_config.return_value = sample_config

        with patch(
            "sys.argv", ["taskcheck", "--report", "today", "--taskrc", test_taskrc]
        ):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = False
                mock_args.report = "today"
                mock_args.verbose = True
                mock_args.force_update = True
                mock_args.taskrc = test_taskrc
                mock_args.dry_run = False
                mock_parse.return_value = mock_args

                main()

                mock_load_config.assert_called_once()
                mock_generate_report.assert_called_once_with(
                    sample_config,
                    "today",
                    True,
                    force_update=True,
                    taskrc=test_taskrc,
                    scheduling_results=None,
                )

    @patch("taskcheck.__main__.load_config")
    @patch("taskcheck.__main__.check_tasks_parallel")
    @patch("taskcheck.report.generate_report")
    def test_main_schedule_and_report(
        self,
        mock_generate_report,
        mock_check_tasks,
        mock_load_config,
        sample_config,
        test_taskrc,
        mock_task_export_with_taskrc,
    ):
        """Test both schedule and report commands together."""
        mock_load_config.return_value = sample_config

        with patch(
            "sys.argv",
            ["taskcheck", "--schedule", "--report", "eow", "--taskrc", test_taskrc],
        ):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = True
                mock_args.report = "eow"
                mock_args.verbose = False
                mock_args.force_update = False
                mock_args.taskrc = test_taskrc
                mock_args.urgency_weight = None
                mock_args.dry_run = False
                mock_parse.return_value = mock_args

                main()

                # Config should be loaded twice (once for each command)
                assert mock_load_config.call_count == 2
                mock_check_tasks.assert_called_once()
                mock_generate_report.assert_called_once()

    @patch("taskcheck.__main__.load_config")
    @patch("taskcheck.__main__.check_tasks_parallel")
    def test_main_schedule_with_verbose_and_force_update(
        self,
        mock_check_tasks,
        mock_load_config,
        sample_config,
        test_taskrc,
        mock_task_export_with_taskrc,
    ):
        """Test schedule command with verbose and force update flags."""
        mock_load_config.return_value = sample_config

        with patch(
            "sys.argv",
            [
                "taskcheck",
                "--schedule",
                "--verbose",
                "--force-update",
                "--taskrc",
                test_taskrc,
            ],
        ):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = True
                mock_args.report = None
                mock_args.verbose = True
                mock_args.force_update = True
                mock_args.taskrc = test_taskrc
                mock_args.urgency_weight = None
                mock_args.dry_run = False
                mock_parse.return_value = mock_args

                main()

                mock_check_tasks.assert_called_once_with(
                    sample_config,
                    verbose=True,
                    force_update=True,
                    taskrc=test_taskrc,
                    urgency_weight_override=None,
                    dry_run=False,
                )

    @patch("taskcheck.__main__.load_config")
    @patch("taskcheck.__main__.check_tasks_parallel")
    def test_main_schedule_with_urgency_weight_override(
        self,
        mock_check_tasks,
        mock_load_config,
        sample_config,
        test_taskrc,
        mock_task_export_with_taskrc,
    ):
        """Test schedule command with urgency weight override."""
        mock_load_config.return_value = sample_config

        with patch(
            "sys.argv",
            [
                "taskcheck",
                "--schedule",
                "--urgency-weight",
                "0.3",
                "--taskrc",
                test_taskrc,
            ],
        ):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = True
                mock_args.report = None
                mock_args.verbose = False
                mock_args.force_update = False
                mock_args.taskrc = test_taskrc
                mock_args.urgency_weight = 0.3
                mock_args.dry_run = False
                mock_parse.return_value = mock_args

                main()

                mock_check_tasks.assert_called_once_with(
                    sample_config,
                    verbose=False,
                    force_update=False,
                    taskrc=test_taskrc,
                    urgency_weight_override=0.3,
                    dry_run=False,
                )

    @patch("taskcheck.__main__.load_config")
    @patch("taskcheck.__main__.check_tasks_parallel")
    def test_main_schedule_with_dry_run(
        self, mock_check_tasks, mock_load_config, sample_config, test_taskrc
    ):
        """Test that dry-run mode returns scheduling results without modifying tasks."""
        mock_load_config.return_value = sample_config

        # Mock dry-run results
        dry_run_results = [
            {
                "id": "1",
                "uuid": "test-uuid-1",
                "description": "Test task 1",
                "project": "test",
                "urgency": 5.0,
                "estimated": "PT2H",
                "due": "20241225T120000Z",
                "scheduled": "2024-12-20",
                "completion_date": "2024-12-20",
                "scheduling": "2024-12-20 - PT2H",
            }
        ]
        mock_check_tasks.return_value = dry_run_results

        with patch(
            "sys.argv",
            ["taskcheck", "--schedule", "--dry-run", "--taskrc", test_taskrc],
        ):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = True
                mock_args.report = None
                mock_args.verbose = False
                mock_args.force_update = False
                mock_args.taskrc = test_taskrc
                mock_args.urgency_weight = None
                mock_args.dry_run = True
                mock_parse.return_value = mock_args

                main()

        # Verify that check_tasks_parallel was called with dry_run=True
        mock_check_tasks.assert_called_once_with(
            sample_config,
            verbose=False,
            force_update=False,
            taskrc=test_taskrc,
            urgency_weight_override=None,
            dry_run=True,
        )
        mock_load_config.assert_called_once()

    @patch("taskcheck.__main__.load_config")
    @patch("taskcheck.__main__.check_tasks_parallel")
    @patch("taskcheck.report.generate_report")
    def test_main_schedule_dry_run_with_report(
        self,
        mock_generate_report,
        mock_check_tasks,
        mock_load_config,
        sample_config,
        test_taskrc,
    ):
        """Test that dry-run results are passed to report generation."""
        mock_load_config.return_value = sample_config

        # Mock dry-run results
        dry_run_results = [
            {
                "id": "1",
                "uuid": "test-uuid-1",
                "description": "Test task 1",
                "project": "test",
                "urgency": 5.0,
                "estimated": "PT2H",
                "due": "20241225T120000Z",
                "scheduled": "2024-12-20",
                "completion_date": "2024-12-20",
                "scheduling": "2024-12-20 - PT2H",
            }
        ]
        mock_check_tasks.return_value = dry_run_results

        with patch(
            "sys.argv",
            [
                "taskcheck",
                "--schedule",
                "--dry-run",
                "--report",
                "today",
                "--taskrc",
                test_taskrc,
            ],
        ):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = True
                mock_args.report = "today"
                mock_args.verbose = False
                mock_args.force_update = False
                mock_args.taskrc = test_taskrc
                mock_args.urgency_weight = None
                mock_args.dry_run = True
                mock_parse.return_value = mock_args

                main()

        # Verify that generate_report was called with the dry-run results
        mock_generate_report.assert_called_once_with(
            sample_config,
            "today",
            False,
            force_update=False,
            taskrc=test_taskrc,
            scheduling_results=dry_run_results,
        )

        # Verify that check_tasks_parallel was called with dry_run=True
        mock_check_tasks.assert_called_once_with(
            sample_config,
            verbose=False,
            force_update=False,
            taskrc=test_taskrc,
            urgency_weight_override=None,
            dry_run=True,
        )

    @patch("taskcheck.__main__.load_config")
    def test_main_config_loading_error(self, mock_load_config):
        """Test behavior when config loading fails."""
        mock_load_config.side_effect = FileNotFoundError("Config not found")

        with patch("sys.argv", ["taskcheck", "--schedule"]):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = True
                mock_args.report = None
                mock_parse.return_value = mock_args

                with pytest.raises(FileNotFoundError):
                    main()

    def test_main_help_display(self):
        """Test that help is displayed when no valid commands are given."""
        with patch("sys.argv", ["taskcheck"]):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = False
                mock_args.report = None
                mock_parse.return_value = mock_args

                with patch.object(arg_parser, "print_help") as mock_help:
                    main()
                    mock_help.assert_called_once()

    @patch("taskcheck.install.install")
    def test_main_install_returns_early(self, mock_install):
        """Test that install command returns without processing other commands."""
        with patch("sys.argv", ["taskcheck", "--install", "--schedule"]):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = True
                mock_args.schedule = True
                mock_args.report = None
                mock_parse.return_value = mock_args

                with patch("taskcheck.__main__.load_config") as mock_load:
                    main()

                    mock_install.assert_called_once()
                    # load_config should not be called because install returns early
                    mock_load.assert_not_called()


class TestImportErrorHandling:
    def test_install_import_error(self):
        """Test behavior when install module cannot be imported."""
        with patch("sys.argv", ["taskcheck", "--install"]):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = True
                mock_args.schedule = False
                mock_args.report = None
                mock_parse.return_value = mock_args

                with patch(
                    "builtins.__import__",
                    side_effect=ImportError("Install module not found"),
                ):
                    with pytest.raises(ImportError):
                        main()

    def test_report_import_error(self):
        """Test behavior when report module cannot be imported."""
        with patch("sys.argv", ["taskcheck", "--report", "today"]):
            with patch("taskcheck.__main__.arg_parser.parse_args") as mock_parse:
                mock_args = Mock()
                mock_args.install = False
                mock_args.schedule = False
                mock_args.report = "today"
                mock_parse.return_value = mock_args

                with patch("taskcheck.__main__.load_config", return_value={}):
                    with patch(
                        "builtins.__import__",
                        side_effect=ImportError("Report module not found"),
                    ):
                        with pytest.raises(ImportError):
                            main()
