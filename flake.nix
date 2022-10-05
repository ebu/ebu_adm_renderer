{
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
            propagatedBuildInputs = with python3.pkgs; [ numpy scipy enum34 six attrs multipledispatch lxml ruamel_yaml setuptools ];
            doCheck = true;
            checkInputs = with python3.pkgs; [ pytest soundfile ];
            postPatch = ''
              # latest attrs should be fine...
              sed -i "s/'attrs.*'/'attrs'/" setup.py
            '';
          };
          defaultPackage = packages.ear;

          devShells.ear = packages.ear.overridePythonAttrs (attrs: {
            propagatedBuildInputs = attrs.propagatedBuildInputs ++ [
              python3.pkgs.matplotlib
            ];
            # dontUseSetuptoolsShellHook = true;
          });
          devShell = devShells.ear;
        }
      );
}

