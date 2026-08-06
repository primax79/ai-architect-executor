#!/usr/bin/env python3
"""generate_binding.py - PROTOTYPE, not yet wired into the real skill set.

Generates a skill's SKILL.md from a `SKILL.template.md` source, either in
its own generic form (no binding map: defaults everywhere, {{ADD:...}}
anchors empty) or in a concrete binding's form (binding map supplies tool
substitutions, block overrides, and additions at named anchors).

Template syntax:
  {{NAME}} / {{DESCRIPTION}}      top-level fields, always required from the map
                                    (generic pass uses the template's own
                                    frontmatter defaults, passed via --generic-name/--generic-description)
  {{TOOL:key}}                    inline phrase substitution, map["tools"][key];
                                    left as a bare literal (unresolved) if the
                                    map has no entry AND no <default> is given
                                    inline via {{TOOL:key|default text}}
  {{BLOCK:key}}default{{/BLOCK}}  span with a generic default; a binding may
                                    override the whole span via map["blocks"][key]
  {{ADD:key}}                     anchor with no default; a binding may inject
                                    content via map["additions"][key]; empty
                                    (removed) on the generic pass and for any
                                    binding that doesn't supply it

Usage:
  # regenerate the generic SKILL.md from its own template (no binding map)
  python3 generate_binding.py --template <dir>/SKILL.template.md --out <dir>/SKILL.md

  # generate a binding's concrete SKILL.md
  python3 generate_binding.py --template <dir>/SKILL.template.md --map <binding>.json --out <out-path>

  # check mode: regenerate in memory, diff against the committed file, exit
  # non-zero on drift (for pre-commit / CI use)
  python3 generate_binding.py --template <dir>/SKILL.template.md --map <binding>.json --out <out-path> --check
"""
import argparse
import json
import re
import sys
import difflib
import pathlib

BLOCK_RE = re.compile(r'\{\{BLOCK:(\w+)\}\}(.*?)\{\{/BLOCK\}\}', re.DOTALL)
ADD_RE = re.compile(r'\{\{ADD:(\w+)\}\}')
TOOL_RE = re.compile(r'\{\{TOOL:(\w+)(?:\|([^}]*))?\}\}')

GENERATED_HEADER = "<!-- GENERATED FROM {source} — DO NOT EDIT BY HAND. Run generate_binding.py to regenerate. -->\n"


def render(template_text, name, description, tool_map, block_overrides, additions, source_label):
    text = template_text

    text = text.replace('{{NAME}}', name)
    text = text.replace('{{DESCRIPTION}}', description)

    def _block_sub(m):
        key, default = m.group(1), m.group(2)
        return block_overrides.get(key, default)
    text = BLOCK_RE.sub(_block_sub, text)

    def _add_sub(m):
        key = m.group(1)
        return additions.get(key, '')
    text = ADD_RE.sub(_add_sub, text)

    def _tool_sub(m):
        key, inline_default = m.group(1), m.group(2)
        if key in tool_map:
            return tool_map[key]
        if inline_default is not None:
            return inline_default
        return f'{{{{TOOL:{key}}}}}'  # leave visibly unresolved rather than silently blank
    text = TOOL_RE.sub(_tool_sub, text)

    header = GENERATED_HEADER.format(source=source_label)
    # header goes after the frontmatter closing '---', not before it
    parts = text.split('---\n', 2)
    if len(parts) == 3:
        text = f'---\n{parts[1]}---\n{header}\n{parts[2].lstrip(chr(10))}'

    # BLOCK/ADD substitution can leave behind runs of blank lines where a
    # block/anchor sat alone on its own line with blank lines around it in
    # the template - collapse 3+ newlines to a single blank line, and trim
    # trailing whitespace at EOF.
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.rstrip('\n') + '\n'
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--template', required=True, type=pathlib.Path)
    ap.add_argument('--map', type=pathlib.Path, default=None,
                     help='Binding map JSON; omit to generate the generic form (all defaults)')
    ap.add_argument('--generic-name', default=None,
                     help='Only used without --map: overrides {{NAME}} for the generic pass '
                          '(defaults to reading it from the current committed SKILL.md if present)')
    ap.add_argument('--generic-description', default=None)
    ap.add_argument('--out', required=True, type=pathlib.Path)
    ap.add_argument('--check', action='store_true',
                     help='Do not write; diff against --out and exit non-zero on drift')
    args = ap.parse_args()

    template_text = args.template.read_text()
    source_label = args.template.name

    if args.map:
        binding = json.loads(args.map.read_text())
        name = binding['name']
        description = binding['description']
        tool_map = binding.get('tools', {})
        block_overrides = binding.get('blocks', {})
        additions = binding.get('additions', {})
    else:
        name = args.generic_name or template_text.split('{{NAME}}', 1)[0]  # placeholder; real default below
        description = args.generic_description
        tool_map = {}
        block_overrides = {}
        additions = {}
        if not (args.generic_name and args.generic_description):
            print('Generic pass requires --generic-name and --generic-description '
                  '(the template has no defaults for its own frontmatter).', file=sys.stderr)
            sys.exit(2)
        name = args.generic_name
        description = args.generic_description

    rendered = render(template_text, name, description, tool_map, block_overrides, additions, source_label)

    if args.check:
        if not args.out.exists():
            print(f'[FAIL] {args.out} does not exist yet')
            sys.exit(1)
        current = args.out.read_text()
        if current != rendered:
            diff = difflib.unified_diff(
                current.splitlines(keepends=True), rendered.splitlines(keepends=True),
                fromfile=f'{args.out} (committed)', tofile=f'{args.out} (regenerated)',
            )
            sys.stdout.writelines(diff)
            print(f'\n[FAIL] {args.out} is stale relative to {args.template}')
            sys.exit(1)
        print(f'[ok] {args.out} matches its template')
        sys.exit(0)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(rendered)
    print(f'Wrote {args.out} ({len(rendered)} chars) from {args.template} '
          f'{"[binding: " + args.map.name + "]" if args.map else "[generic]"}')


if __name__ == '__main__':
    main()
