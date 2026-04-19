from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import mobi
from markitdown import MarkItDown


SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".txt", ".html"}
FALLBACK_EXTENSIONS = {".mobi", ".azw3"}


@dataclass
class ConversionResult:
    source: Path
    destination: Path | None
    status: str
    detail: str = ""


def iter_books(root: Path) -> Iterable[Path]:
    priority = {
        ".txt": 0,
        ".epub": 1,
        ".pdf": 2,
        ".mobi": 3,
        ".azw3": 4,
    }
    for path in sorted(root.iterdir(), key=lambda item: (priority.get(item.suffix.lower(), 99), item.name.lower())):
        if path.is_file() and path.suffix.lower() in (SUPPORTED_EXTENSIONS | FALLBACK_EXTENSIONS):
            yield path


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    index = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def extract_ebook_with_python_fallback(source: Path) -> tuple[Path, Path]:
    tempdir, extracted_path = mobi.extract(str(source))
    return Path(tempdir), Path(extracted_path)


def convert_source_to_markdown(converter: MarkItDown, source: Path, destination: Path) -> None:
    result = converter.convert(str(source))
    destination.write_text(result.markdown, encoding="utf-8")


def convert_file(converter: MarkItDown, source: Path, output_dir: Path, overwrite: bool) -> ConversionResult:
    extension = source.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        if extension not in FALLBACK_EXTENSIONS:
            return ConversionResult(
                source=source,
                destination=None,
                status="skipped",
                detail=f"Extensao fora do escopo configurado: {extension or '<sem extensao>'}",
            )

    destination = output_dir / f"{source.stem}.md"
    if not overwrite:
        destination = ensure_unique_path(destination)

    tempdir: Path | None = None
    try:
        conversion_source = source
        detail = ""
        if extension in FALLBACK_EXTENSIONS:
            tempdir, conversion_source = extract_ebook_with_python_fallback(source)
            detail = f"python-fallback via {conversion_source.suffix.lower() or '<sem extensao>'}"

        convert_source_to_markdown(converter, conversion_source, destination)
        return ConversionResult(source=source, destination=destination, status="converted", detail=detail)
    except Exception as exc:
        return ConversionResult(
            source=source,
            destination=destination,
            status="failed",
            detail=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if tempdir and tempdir.exists():
            shutil.rmtree(tempdir, ignore_errors=True)


def write_report(report_path: Path, results: list[ConversionResult]) -> None:
    converted = [result for result in results if result.status == "converted"]
    skipped = [result for result in results if result.status == "skipped"]
    failed = [result for result in results if result.status == "failed"]

    lines = [
        "Conversao de livros para Markdown com MarkItDown",
        "",
        f"Convertidos: {len(converted)}",
        f"Ignorados: {len(skipped)}",
        f"Falhas: {len(failed)}",
        "",
        "Detalhes:",
    ]

    for result in results:
        if result.destination:
            lines.append(f"- {result.status.upper()}: {result.source.name} -> {result.destination.name}")
        else:
            lines.append(f"- {result.status.upper()}: {result.source.name}")
        if result.detail:
            lines.append(f"  {result.detail}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Converte livros suportados para Markdown com MarkItDown.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Diretorio que contem os livros. Padrao: diretorio atual.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "markdown",
        help="Diretorio de saida para os arquivos Markdown.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescreve arquivos .md existentes com o mesmo nome.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = MarkItDown()
    results: list[ConversionResult] = []
    for source in iter_books(root):
        print(f"Processando: {source.name}", flush=True)
        results.append(convert_file(converter, source, output_dir, args.overwrite))
    write_report(output_dir / "conversion-report.txt", results)

    converted_count = sum(result.status == "converted" for result in results)
    skipped_count = sum(result.status == "skipped" for result in results)
    failed_count = sum(result.status == "failed" for result in results)

    print(f"Convertidos: {converted_count}")
    print(f"Ignorados: {skipped_count}")
    print(f"Falhas: {failed_count}")
    print(f"Relatorio: {output_dir / 'conversion-report.txt'}")
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
