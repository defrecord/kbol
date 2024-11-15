{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python311
    poetry
    postgresql_15
    ollama
    ripgrep
  ];

  shellHook = ''
    export PYTHONPATH="$PWD:$PYTHONPATH"
    export DATABASE_URL="postgresql://localhost:5432/kbol_db"
    
    if [ ! -f "poetry.lock" ]; then
      poetry install
    fi
  '';
}
