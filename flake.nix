{
  inputs.nixpkgs.url = "nixpkgs/nixos-23.11";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem
      (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python3 = pkgs.python3;
        in
        rec {
          packages.ear = python3.pkgs.buildPythonPackage rec {
            name = "ear";
            src = ./.;
            propagatedBuildInputs = with python3.pkgs; [ numpy scipy six attrs multipledispatch lxml pyyaml importlib-resources ];
            nativeBuildInputs = with python3.pkgs; [ setuptools ];
            pyproject = true;

            doCheck = true;
            nativeCheckInputs = with python3.pkgs; [ pytest pytestCheckHook pytest-cov pytest-datafiles soundfile ];
            pytestFlagsArray = [ "ear" "-x" ];
            preCheck = ''
              export PATH="$PATH:$out/bin"
            '';
          };
          defaultPackage = packages.ear;

          packages.darker = python3.pkgs.buildPythonPackage rec {
            pname = "darker";
            version = "1.7.1";
            src = python3.pkgs.fetchPypi {
              inherit pname version;
              hash = "sha256-z0FzvkrSmC5bLrq34IvQ0nFz8kWewbHPZq7JKQ2oDM4=";
            };
            propagatedBuildInputs = with python3.pkgs; [ black toml isort ];
            nativeBuildInputs = with python3.pkgs; [ setuptools ];
            pyproject = true;
          };

          devShells.ear = packages.ear.overridePythonAttrs (attrs: {
            propagatedBuildInputs = attrs.propagatedBuildInputs ++ [
              python3.pkgs.matplotlib
              python3.pkgs.flake8
              python3.pkgs.ipython
            ];
            nativeBuildInputs = attrs.nativeBuildInputs ++ [
              python3.pkgs.matplotlib
              python3.pkgs.flake8
              python3.pkgs.ipython
              python3.pkgs.black
              python3.pkgs.pip
              packages.darker
              python3.pkgs.venvShellHook

              # for building docs
              python3.pkgs.sphinx
              python3.pkgs.sphinx-rtd-theme
              pkgs.graphviz
            ];
            venvDir = "./venv";
            postShellHook = ''
              python -m pip install -e .
            '';
          });
          devShell = devShells.ear;
        }
      );
}

