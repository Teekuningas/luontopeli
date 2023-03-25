{
  inputs.nixpkgs.url = "nixpkgs/22.11";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in {
        formatter = pkgs.nixfmt;
        devShell = pkgs.mkShell {
          packages = [
            (pkgs.python39.withPackages
              (ps: with ps; [ flask gunicorn requests ]))
          ];
        };
      });
}

