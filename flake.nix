{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    home-manager.url = "github:nix-community/home-manager";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = {
    self,
    nixpkgs,
    home-manager,
  }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs {inherit system;};

    pyproject = builtins.fromTOML (builtins.readFile ./pyproject.toml);
    inherit (pyproject) project;

    taskcheck = pkgs.python3Packages.buildPythonApplication {
      pname = project.name;
      inherit (project) version;
      pyproject = true;
      src = ./.;
      nativeBuildInputs = with pkgs.python3Packages; [setuptools];

      dependencies = with pkgs.python3Packages; [
        appdirs
        icalendar
        random-unicode-emoji
        requests
        rich
      ];
    };
    random-unicode-emoji = pkgs.python3Packages.buildPythonPackage rec {
      pname = "random-unicode-emoji";

      version = "2.9";

      pyproject = true;

      nativeBuildInputs = with pkgs.python3Packages; [setuptools];

      src = pkgs.fetchFromGitHub {
        owner = "NicPWNs";
        repo = "random-unicode-emoji-py";
        rev = version;
        hash = "sha256-8BfwcZSzQpq1jJuvavIrW84rDvLfKdXr6TLXP8echM4=";
      };
    };
  in {
    packages.${system}.default = taskcheck;
    homeManagerModules.default = {
      config,
      lib,
      pkgs,
      ...
    }: let
      inherit (lib) mkOption mkEnableOption mkIf mkMerge;

      cfg = config.programs.taskcheck;

      toml = pkgs.formats.toml {};
    in {
      options = {
        programs.taskcheck = {
          enable = mkEnableOption "taskcheck";

          optional_hm_config = mkEnableOption "Set Optional HM Configurations";

          package = mkOption {
            default = taskcheck;
          };

          settings = mkOption {
            default = {
              time_maps = {
                work = {
                  monday = [[9 12.30] [14 17]];
                  tuesday = [[9 12.30] [14 17]];
                  wednesday = [[9 12.30] [14 17]];
                  thursday = [[9 12.30] [14 17]];
                  friday = [[9 12.30] [14 17]];
                };
              };
              scheduler = {
                days_ahead = 365;
                weight_urgency = 1.0;
              };
              report = {
                include_unplanned = true;
                additional_attributes = [];
                additional_attributes_unplanned = [];
                # emoji_keywords = {};
              };
              calendars = {
                holidays = {
                  url = "https://www.officeholidays.com/ics-clean/usa/nebraska";
                  event_all_day_is_blocking = true;
                  expiration = 720; # In hours (720 hours = 30 days)
                };
              };
            };
            inherit (toml) type;
          };
        };
      };

      config = mkIf cfg.enable {
        home.packages = mkIf (cfg.package != null) [cfg.package];
        programs.taskwarrior.enable = true;
        programs.taskwarrior.config = mkMerge [
          {
            uda = {
              time_map = {
                type = "string";
                label = "Time Map";
                default = "work";
              };
              estimated.type = "duration";
              estimated.label = "Estimated Time";
              completion_date.type = "date";
              completion_date.label = "Expected Completion Date";
              scheduling.type = "string";
              scheduling.label = "Scheduling";
              min_block = {
                type = "numeric";
                label = "Minimum Time Block";
                default = "2";
              };
            };
            recurrence.confirmation = "no";
          }
          (mkIf
            cfg.optional_hm_config {
              urgency = {
                uda.estimated = {
                  PT1H.coefficient = 1;
                  PT2H.coefficient = 2.32;
                  PT3H.coefficient = 3.67;
                  PT4H.coefficient = 4.64;
                  PT5H.coefficient = 5.39;
                  PT6H.coefficient = 6.02;
                  PT7H.coefficient = 6.56;
                  PT8H.coefficient = 7.03;
                  PT9H.coefficient = 7.45;
                  PT10H.coefficient = 7.82;
                  PT11H.coefficient = 8.16;
                  PT12H.coefficient = 8.47;
                  PT13H.coefficient = 8.75;
                  PT14H.coefficient = 9.01;
                  PT15H.coefficient = 9.25;
                  PT16H.coefficient = 9.47;
                  PT17H.coefficient = 9.68;
                  PT18H.coefficient = 9.87;
                  PT19H.coefficient = 10.05;
                  PT20H.coefficient = 10.22;
                  PT21H.coefficient = 10.38;
                  PT22H.coefficient = 10.53;
                  PT23H.coefficient = 10.67;
                  P1D.coefficient = 10.80;
                  P1DT1H.coefficient = 10.93;
                  P1DT2H.coefficient = 11.05;
                  P1DT3H.coefficient = 11.16;
                  P1DT4H.coefficient = 11.27;
                  P1DT5H.coefficient = 11.37;
                  P1DT6H.coefficient = 11.47;
                  P1DT7H.coefficient = 11.56;
                  P1DT8H.coefficient = 11.65;
                  P1DT9H.coefficient = 11.73;
                  P1DT10H.coefficient = 11.81;
                  P1DT11H.coefficient = 11.89;
                  P1DT12H.coefficient = 11.96;
                };
                "inherit" = 1;
                blocked.coefficient = 0;
                blocking.coefficient = 0;
                waiting.coefficient = 0;
                scheduled.coefficient = 0;
              };
              report.ready.columns = [
                "id"
                "start.age"
                "entry.age"
                "depends.indicator"
                "priority"
                "project"
                "tags"
                "recur.indicator"
                "scheduled.relative"
                "due.relative"
                "until.remaining"
                "description"
                "urgency"
              ];
              journal.info = 0;
            })
        ];
        xdg.configFile."task/taskcheck.toml".source = toml.generate "taskcheck.toml" cfg.settings;
      };
    };
    checks.x86_64-linux = {
      moduleTest = pkgs.testers.runNixOSTest {
        name = "moduleTest";

        nodes.machine1 = {
          imports = [home-manager.nixosModules.home-manager];

          users.users.alice = {
            isNormalUser = true;
          };

          home-manager.users.alice = _:
          # { config, ... }: # config is home-manager's config, not the OS one
          {
            imports = [self.homeManagerModules.default];
            home.stateVersion = "24.05";

            programs.taskcheck = {
              enable = true;
              optional_hm_config = true;
            };
          };
        };

        testScript = ''
          machine.wait_for_unit("default.target")

          assert machine.execute("su - alice bash -c 'task add estimated:2h time_map:work project:docs Write Documentation'")[0] == 0
          assert machine.execute("su - alice bash -c 'task add estimated:1h time_map:work project:dev due:eom Code review meeting'")[0] == 0
          assert machine.execute("su - alice bash -c 'task add estimated:3h time_map:personal project:hobby Personal Project'")[0] == 0
          assert machine.execute("su - alice bash -c 'task 1'")[0] == 0

          assert machine.execute("su - alice bash -c 'taskcheck'")[0] == 0

          assert machine.execute("su - alice bash -c 'ls -lath ~/.config/task/'")[0] == 0

          print("taskcheck.toml:\n", machine.execute("su - alice bash -c 'cat ~/.config/task/taskcheck.toml'")[1])

          print("taskrc:\n", machine.execute("su - alice bash -c 'cat ~/.config/task/home-manager-taskrc'")[1])

          print("task report:\n", machine.execute("su - alice bash -c 'taskcheck -r 1w'")[1])

          # TODO: setup nameserver to resolve calendar host
          # print("task report:\n", machine.execute("su - alice bash -c 'taskcheck --schedule && taskcheck -r 1w'")[1])

        '';
      };
    };
  };
}
