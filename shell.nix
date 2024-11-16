{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python311
    poetry
    postgresql_15
    ollama
    ripgrep
    direnv
  ];

  shellHook = ''
    eval $(direnv export bash)
    export PYTHONPATH="$PWD:$PYTHONPATH"
    export DIRENV_LOG_FORMAT=""
  '';
}