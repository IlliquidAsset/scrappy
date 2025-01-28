{pkgs}: {
  deps = [
    pkgs.haskellPackages.termcolor
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.openssl
  ];
}
