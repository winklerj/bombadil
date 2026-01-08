{
  rustPlatform,
  pkg-config,
  gitignoreSource,
  esbuild,
  chromium,
}:
rustPlatform.buildRustPackage rec {
  pname = "antithesis_browser";
  version = "0.1.0";

  src = gitignoreSource ../.;

  buildInputs = [ ];
  nativeBuildInputs = [
    pkg-config
    esbuild
    chromium
  ];
  cargoLock = {
    lockFile = ../Cargo.lock;
  };
  cargoTestFlags = "--bin antithesis_browser";
}
