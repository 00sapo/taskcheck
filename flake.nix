{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = {
    self,
    nixpkgs,
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
  };
}
