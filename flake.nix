{
  description = "A Python development shell for an IRC bot";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/24.05";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      myPythonEnv = pkgs.python311.withPackages (ps: [
        ps.flask
        ps.gunicorn
        ps.requests
        ps.black
      ]);

      luontopeli = pkgs.python311Packages.buildPythonApplication rec {
        pname = "luontopeli";
        version = "0.1.0";
        src = ./.;

        propagatedBuildInputs = [
          myPythonEnv
        ];

        buildInputs = with pkgs.python311Packages; [ setuptools ];
      };

    in
    {
      devShell.${system} = pkgs.mkShell {
        buildInputs = [
          luontopeli
        ];
      };
      packages.${system}.luontopeli = luontopeli;
    };
}
