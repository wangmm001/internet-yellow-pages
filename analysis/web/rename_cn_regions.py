"""Rename 中国/香港/台湾/澳门 references to 中国大陆/中国香港/中国台湾/中国澳门.

Runs idempotently on a tree of HTML files.  Context-aware: skips
brand/entity names (中国电信, 中国移动, 香港科技大学, etc.) and already-
qualified forms (中国大陆, 中国香港, ...).

Used by build_offline.py as a post-process step and can also be
invoked standalone.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# (main_word, new_word, skip_after_list, skip_before_list)
RULES = [
    ('中国', '中国大陆', [
        '电信', '移动', '联通', '网通', '铁通', '卫通',
        '教育网', '科技网', '科学院', '互联网协会', '互联网信息中心',
        '银联', '红十字',
        '大陆', '香港', '台湾', '澳门', '区',
        '人民', '特色',
    ], ['中华']),
    ('香港', '中国香港', [
        '大学', '政府', '特别行政区',
    ], ['中国', '中港', '港澳', '沪港', '粤港', '深港']),
    ('台湾', '中国台湾', [
        '大学', '海峡',
    ], ['中国']),
    ('澳门', '中国澳门', [
        '大学',
    ], ['中国', '港澳']),
]


def rewrite(text: str) -> tuple[str, dict[str, int]]:
    counts = {new: 0 for _, new, _, _ in RULES}
    for main_word, new_word, skip_after, skip_before in RULES:
        # Build regex: (?<!skip_before) main_word (?!skip_after)
        sb = '|'.join(re.escape(s) for s in skip_before)
        sa = '|'.join(re.escape(s) for s in skip_after)
        pattern_parts = [re.escape(main_word)]
        if sa:
            pattern_parts.append(f'(?!{sa})')
        if sb:
            pattern = f'(?<!{sb})' + ''.join(pattern_parts)
        else:
            pattern = ''.join(pattern_parts)
        # NOTE: Python re has fixed-width lookbehind (pre 3.7 limitation).
        # Our skip_before tokens are all 1-2 Chinese chars; need alternation
        # with equal widths.  Workaround: split into per-width groups.
        # Simpler: use a compiled regex and a custom replace function that
        # checks skip_before manually in the callback.
        pat = re.compile(re.escape(main_word) + (f'(?!{sa})' if sa else ''))

        def repl(m, _text=text, _main_word=main_word, _new_word=new_word,
                 _skip_before=skip_before, _counts=counts):
            start = m.start()
            # Check skip_before manually
            for sbw in _skip_before:
                if start >= len(sbw) and _text[start - len(sbw):start] == sbw:
                    return _main_word  # no replacement
            _counts[_new_word] += 1
            return _new_word

        # Apply on the running text (outer scope 'text')
        text = pat.sub(repl, text)
    return text, counts


def rewrite_file(path: Path, dry_run: bool = False) -> dict[str, int]:
    try:
        original = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return {}
    new, counts = rewrite(original)
    if new != original and not dry_run:
        path.write_text(new, encoding='utf-8')
    return counts if new != original else {}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('paths', nargs='*', type=Path,
                    help='HTML files or dirs to rewrite (recurses)')
    ap.add_argument('--dry-run', action='store_true',
                    help='Report but do not write')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()

    if args.self_test:
        self_test()
        print('self-test OK')
        return 0

    if not args.paths:
        ap.error('need at least one path')

    total = {new: 0 for _, new, _, _ in RULES}
    files_changed = 0
    for p in args.paths:
        paths = [p] if p.is_file() else list(p.rglob('*.html'))
        for html in paths:
            counts = rewrite_file(html, dry_run=args.dry_run)
            if counts:
                files_changed += 1
                for k, v in counts.items():
                    total[k] += v
                print(f'  {html}: {counts}')
    print(f'\nChanged {files_changed} files. Totals: {total}')
    return 0


def self_test():
    # 中国 → 中国大陆
    assert rewrite('中国的互联网')[0] == '中国大陆的互联网'
    # 中国电信: skip
    assert rewrite('中国电信骨干网')[0] == '中国电信骨干网'
    # 中国移动: skip
    assert rewrite('中国移动 9808')[0] == '中国移动 9808'
    # 中国区: skip
    assert rewrite('中国区整体 8,624 个 AS')[0] == '中国区整体 8,624 个 AS'
    # 中国大陆: skip (already qualified)
    assert rewrite('中国大陆的 AS')[0] == '中国大陆的 AS'
    # 中华人民共和国: skip (preceded by 中华 / inside 中华...)
    s, _ = rewrite('中华人民共和国')
    assert s == '中华人民共和国', repr(s)
    # 香港: 香港 → 中国香港
    assert rewrite('香港 (HK)')[0] == '中国香港 (HK)'
    # 中国香港: already qualified
    assert rewrite('中国香港 HK')[0] == '中国香港 HK'
    # 香港大学: skip
    assert rewrite('香港大学')[0] == '香港大学'
    # 港澳: 港 after 港澳 - already contextualised (skip_before of 澳 is 港澳)
    assert rewrite('港澳地区')[0] == '港澳地区'
    # 台湾: 台湾 → 中国台湾
    assert rewrite('台湾 (TW)')[0] == '中国台湾 (TW)'
    # 台湾海峡: skip
    assert rewrite('台湾海峡')[0] == '台湾海峡'
    # 澳门: 澳门 → 中国澳门
    assert rewrite('澳门人口')[0] == '中国澳门人口'
    # Mixed doc
    s, c = rewrite('中国 / 中国电信 / 中国香港 / 香港 / 台湾 / 澳门')
    assert s == '中国大陆 / 中国电信 / 中国香港 / 中国香港 / 中国台湾 / 中国澳门', repr(s)
    assert c['中国大陆'] == 1
    assert c['中国香港'] == 1
    assert c['中国台湾'] == 1
    assert c['中国澳门'] == 1


if __name__ == '__main__':
    raise SystemExit(main())
