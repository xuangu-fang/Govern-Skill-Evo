"""Thin adapter over the pinned SkillOpt OfficeQA local tools; no model calls."""
import calendar
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from skillopt.envs.officeqa import tool_runtime as upstream


def lines(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in str(value or '').splitlines() if x.strip()]


def source_references(source_files, source_docs, *, allow_url_sources=False):
    """Resolve each FRASER URL by bulletin month/year, never list position.

    Ordinarily the derived name must be in the declared source files. During
    explicit data repair, allow_url_sources permits files named by existing
    source URLs, with all additions recorded in the preparation report.
    """
    files, docs = lines(source_files), lines(source_docs)
    if not files or not docs:
        raise ValueError('Source files and page URLs must be nonempty')
    if any(Path(name).name != name for name in files):
        raise ValueError('Source file must be a basename')
    months = {m.lower(): f'{i:02d}' for i, m in enumerate(calendar.month_name) if m}
    result = []
    for url in docs:
        parsed = urlparse(url)
        match = re.fullmatch(r'([a-z]+)-(\d{4})-\d+', parsed.path.rstrip('/').split('/')[-1])
        if parsed.hostname != 'fraser.stlouisfed.org' or not match or match[1] not in months:
            raise ValueError(f'Unrecognized FRASER source URL: {url}')
        name = f'treasury_bulletin_{match[2]}_{months[match[1]]}.txt'
        pages = parse_qs(parsed.query).get('page', [])
        if (name not in files and not allow_url_sources) or len(pages) != 1 or not pages[0].isdigit() or int(pages[0]) < 1:
            raise ValueError(f'Unresolved source file/page: {url}')
        result.append((name, int(pages[0]), url))
    if not set(files) <= {r[0] for r in result}:
        raise ValueError('Some declared files have no matching source URL')
    return result


def aligned_item(item):
    """Return a copy compatible with the unmodified upstream positional reader."""
    refs = source_references(item['source_files'], item['source_docs'], allow_url_sources=True)
    legacy = upstream._iter_oracle_refs(item['source_files'], item['source_docs'])
    result = dict(item)
    if refs != legacy:
        result['source_files'] = [name for name, _, _ in refs]
    return result, refs, legacy


class LocalDocuments:
    """Explicit single corpus and nonempty per-task allowlist.

    Missing assets are preparation errors. Never pass an empty allowlist to
    upstream, where it would expand access to every file in the corpus.
    """
    def __init__(self, parsed_root, item):
        self.parsed_root = Path(parsed_root).resolve()
        self.text_root = self.parsed_root / 'transformed'
        self.files = list(dict.fromkeys(lines(item['source_files'])))
        if not self.files:
            raise ValueError('Empty source-file allowlist')
        self.paths = []
        for name in self.files:
            if Path(name).name != name:
                raise ValueError('Source file must be a basename')
            path = (self.text_root / name).resolve()
            if not path.is_relative_to(self.text_root.resolve()) or not path.is_file():
                raise ValueError(f'Missing or out-of-corpus source file: {name}')
            self.paths.append(str(path))

    def call(self, name, arguments):
        if name not in {'glob', 'read', 'grep'}:
            raise ValueError(f'Unsupported local tool: {name}')
        if name in {'read', 'grep'}:
            path = str(Path(str(arguments.get('path') or '')).resolve())
            if path not in self.paths:
                return name, f'[{name} error: path not allowed]'
        return upstream.run_tool(name, arguments, allowed_roots=[str(self.text_root)], allowed_files=self.files)

    def pages(self, item):
        refs = source_references(item['source_files'], item['source_docs'])
        for name, page, _ in refs:
            path = self.parsed_root / 'jsons' / (Path(name).stem + '.json')
            if not path.is_file() or not upstream._render_parsed_page(str(path), page):
                raise ValueError(f'Missing or empty parsed source page: {name}:{page}')
        return upstream.build_oracle_parsed_pages_context(
            [r[0] for r in refs], [r[2] for r in refs], [str(self.text_root)],
            evidence_note='Treat it as primary document evidence and combine it with local document tool evidence when useful.',
        )
