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
            propagatedBuildInputs = with python3.pkgs; [ numpy scipy six attrs multipledispatch lxml pyyaml setuptools ];

            doCheck = true;
            nativeCheckInputs = with python3.pkgs; [ pytest pytestCheckHook pytest-cov pytest-datafiles soundfile ];
            pytestFlagsArray = [ "ear" ];
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
          };

          devShells.ear = packages.ear.overridePythonAttrs (attrs: {
            propagatedBuildInputs = attrs.propagatedBuildInputs ++ [
              python3.pkgs.matplotlib
              python3.pkgs.flake8
              python3.pkgs.ipython
            ];
            nativeBuildInputs = [
              python3.pkgs.matplotlib
              python3.pkgs.flake8
              python3.pkgs.ipython
              python3.pkgs.black
              packages.darker
            ];
            postShellHook = ''
              export PYTHONPATH=$(pwd):$PYTHONPATH
            '';
          });
          devShell = devShells.ear;
        }
      );
}

