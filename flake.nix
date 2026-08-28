{
  description = "QGIS Monthly News Gatherer - Automated content collection for QGIS YouTube news segments";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        pythonPackages = pkgs.python312Packages;

        python = pkgs.python312.withPackages (ps: with ps; [
          # HTTP and async
          httpx
          aiofiles

          # Parsing
          beautifulsoup4
          lxml
          feedparser

          # CLI and output
          click
          rich

          # Data validation
          pydantic
          pydantic-settings

          # Date handling
          python-dateutil

          # PDF and templating
          weasyprint
          markdown
          jinja2
          pypdf

          # Documentation
          mkdocs
          mkdocs-material

          # Development tools
          pytest
          pytest-asyncio
          pytest-cov
          mypy
          ruff

          # Types
          types-beautifulsoup4
          types-python-dateutil
        ]);

        # Bundle Noto Sans + Noto Sans CJK so WeasyPrint can render
        # Latin, CJK, and a broad emoji/symbol set without missing glyphs.
        # Use the static (non-variable) Noto CJK instance so mobile PDF
        # viewers — which often choke on variable-font subsetting — can
        # render the embedded subset cleanly.
        fontsConf = pkgs.makeFontsConf {
          fontDirectories = [
            pkgs.dejavu_fonts
            pkgs.noto-fonts
            pkgs.noto-fonts-cjk-sans-static
            pkgs.noto-fonts-color-emoji
          ];
        };

      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pkgs.pre-commit
            pkgs.gh
            pkgs.git
          ];

          shellHook = ''
            echo "🌍 QGIS News Gatherer Development Environment"
            echo ""
            echo "Available commands:"
            echo "  nix run .#run          - Run the news gatherer (pass any CLI args)"
            echo "  nix run .#report-md    - Generate markdown show notes (optional: YYYY-MM)"
            echo "  nix run .#report-pdf   - Generate PDF show notes (optional: YYYY-MM)"
            echo "  nix run .#report-pdf-no-cache - Generate PDF, bypass cache"
            echo "  nix run .#report-html  - Generate HTML show notes (optional: YYYY-MM)"
            echo "  nix run .#report-youtube - Show YouTube description (optional: YYYY-MM)"
            echo "  nix run .#test         - Run tests"
            echo "  nix run .#lint         - Run linter"
            echo "  nix run .#format       - Format code"
            echo "  nix run .#docs         - Build the documentation site"
            echo "  nix run .#docs-serve   - Serve the docs with live reload"
            echo ""
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
            export FONTCONFIG_FILE="${fontsConf}"
          '';
        };

        packages = {
          default = pythonPackages.buildPythonApplication {
            pname = "qgis-news-gatherer";
            version = "0.3.0";
            src = ./.;
            format = "pyproject";

            propagatedBuildInputs = with pythonPackages; [
              httpx
              aiofiles
              beautifulsoup4
              lxml
              feedparser
              click
              rich
              pydantic
              pydantic-settings
              python-dateutil
              pypdf
            ];
          };
        };

        apps = let
          srcDir = toString ./.;
          monthArg = "$(date +%Y-%m)";
          runGatherer = args: toString (pkgs.writeShellScript "run-news-gatherer" ''
            OUTDIR="$(pwd)"
            export PYTHONPATH="${srcDir}/src:$PYTHONPATH"
            export FONTCONFIG_FILE="${fontsConf}"
            MONTH="''${1:-${monthArg}}"
            cd "$OUTDIR"
            ${python}/bin/python -m qgis_news_gatherer.cli --month "$MONTH" ${args}
          '');
        in {
          run = {
            type = "app";
            program = toString (pkgs.writeShellScript "run-news-gatherer-default" ''
              export PYTHONPATH="${srcDir}/src:$PYTHONPATH"
              ${python}/bin/python -m qgis_news_gatherer.cli "$@"
            '');
          };

          report-md = {
            type = "app";
            program = runGatherer ''-f markdown -o "$OUTDIR/qgis-shownotes-$MONTH.md"'';
          };

          report-pdf = {
            type = "app";
            program = runGatherer ''-f pdf -o "$OUTDIR/qgis-news-$MONTH.pdf"'';
          };

          report-pdf-no-cache = {
            type = "app";
            program = runGatherer ''--force -f pdf -o "$OUTDIR/qgis-news-$MONTH.pdf"'';
          };

          report-html = {
            type = "app";
            program = runGatherer ''-f html -o "$OUTDIR/qgis-news-$MONTH.html"'';
          };

          report-youtube = {
            type = "app";
            program = runGatherer ''--show-youtube-desc'';
          };

          test = {
            type = "app";
            program = toString (pkgs.writeShellScript "run-tests" ''
              export PYTHONPATH="${srcDir}/src:$PYTHONPATH"
              ${python}/bin/pytest "${srcDir}/tests/" -v "$@"
            '');
          };

          lint = {
            type = "app";
            program = toString (pkgs.writeShellScript "run-lint" ''
              ${python}/bin/ruff check "${srcDir}/src/" "${srcDir}/tests/"
              ${python}/bin/mypy "${srcDir}/src/"
            '');
          };

          format = {
            type = "app";
            program = toString (pkgs.writeShellScript "run-format" ''
              ${python}/bin/ruff format "${srcDir}/src/" "${srcDir}/tests/"
              ${python}/bin/ruff check --fix "${srcDir}/src/" "${srcDir}/tests/"
            '');
          };

          docs = {
            type = "app";
            program = toString (pkgs.writeShellScript "build-docs" ''
              cd "${srcDir}"
              ${python}/bin/python scripts/sync_root_docs.py
              ${python}/bin/python scripts/generate_reports_index.py
              ${python}/bin/mkdocs build "$@"
            '');
          };

          docs-serve = {
            type = "app";
            program = toString (pkgs.writeShellScript "serve-docs" ''
              cd "${srcDir}"
              ${python}/bin/python scripts/sync_root_docs.py
              ${python}/bin/python scripts/generate_reports_index.py
              ${python}/bin/mkdocs serve "$@"
            '');
          };
        };
      });
}
