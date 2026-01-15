{
  description = "Project Spatia: AI-Native Systems Environment";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      nixpkgsFor = forAllSystems (system: import nixpkgs { inherit system; });
    in
    {
      devShells = forAllSystems (system:
        let pkgs = nixpkgsFor.${system}; in
        {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [
              kakoune tmux sqlite gcc gnumake cmake
              (python311.withPackages (ps: with ps; [ tree-sitter ]))
            ];
            shellHook = ''
              export SPATIA_ROOT=$(pwd)
              export PATH=$SPATIA_ROOT/.spatia/bin:$PATH
              echo "--- 🌌 SPATIA MISSION ENVIRONMENT LOADED ---"
            '';
          };
        });
    };
}
