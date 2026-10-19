"""Export an installed Windows/AArch64 SDK without changing its source tree."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def require_new_destination(path):
    if path.exists():
        raise FileExistsError(path)


def rewrite(text, pairs):
    # Normalize only known Windows path prefixes, not arbitrary backslash escapes.
    for old in sorted(pairs, key=len, reverse=True):
        windows = old.replace('/', '\\')
        if windows != old:
            text = re.sub(re.escape(windows) + r'(?=[\\/\s;"\)]|$)',
                          lambda _: old, text)
    for old, new in sorted(pairs.items(), key=lambda pair: len(pair[0]), reverse=True):
        pattern = re.escape(old) + r'(?=[/\\\s;"\)]|$)(?:[\\/][^\s;"\)]*)?'
        text = re.sub(pattern, lambda m: new + m[0][len(old):].replace('\\', '/'), text)
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--graphics', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--refresh-metadata', action='store_true')
    args = parser.parse_args()
    source, toolchain, graphics, out = (p.resolve() for p in
        (args.source, args.toolchain, args.graphics, args.output))
    if args.refresh_metadata:
        previous = json.loads((out / 'sdk-copy-manifest.json').read_text(encoding='utf-8'))
        if any(previous[key] != str(value) for key, value in
               (('source', source), ('toolchain', toolchain), ('graphics', graphics), ('output', out))):
            raise ValueError('export provenance mismatch')
    else:
        require_new_destination(out)
    for parent in (source, toolchain, graphics):
        if out.is_relative_to(parent) or parent.is_relative_to(out):
            raise ValueError('output and inputs must be disjoint')
    trees = ('bin', 'include', 'lib', 'mkspecs', 'plugins', 'qml', 'staging', 'src', 'examples')
    for name in trees:
        if not (source / name).is_dir():
            raise FileNotFoundError(source / name)
    if not (toolchain / 'bin/aarch64-none-linux-gnu-g++.exe').is_file():
        raise FileNotFoundError('cross compiler missing')
    if not args.refresh_metadata:
        out.mkdir(parents=True)
        for name in trees:
            shutil.copytree(source / name, out / name)
        shutil.copytree(toolchain, out / 'toolchain')
    for src, dst in (('mesa/upstream/include', 'graphics-headers/mesa'),
                     ('mesa/upstream/src/gbm/main', 'graphics-headers/gbm'),
                     ('libdrm/upstream', 'graphics-headers/libdrm')):
        if not args.refresh_metadata:
            shutil.copytree(graphics / src, out / dst,
                            ignore=shutil.ignore_patterns('.git', 'build', '__pycache__'))
    shutil.copy2(graphics / 'qt5/upstream/qtbase-everywhere-src-5.15.19/bin/syncqt.pl', out / 'bin/syncqt.pl')
    dest = out.as_posix()
    old_graphics = 'D:/workspace/luna-workspace/os/graphics'
    pairs = {
        source.as_posix(): dest,
        toolchain.as_posix(): dest + '/toolchain',
        '/mnt/d/workspace/luna-workspace/tools/toolchains/aarch64-none-linux-gnu': dest + '/toolchain',
        old_graphics + '/qt5/build/qt5-armv8a/staging': dest + '/staging',
        old_graphics + '/qt5/build/qt5-armv8a': dest,
        '/home/surest/nanopc-workspace/graphics/qt5/build/qt5-armv8a-linux': dest,
        old_graphics + '/mesa/upstream/include': dest + '/graphics-headers/mesa',
        old_graphics + '/mesa/upstream/src/gbm/main': dest + '/graphics-headers/gbm',
        old_graphics + '/libdrm/upstream': dest + '/graphics-headers/libdrm',
        '/mnt/d/workspace/luna-workspace/os/graphics/mesa/upstream/include': dest + '/graphics-headers/mesa',
        '//home/surest/nanopc-workspace/graphics/qt5/build/target-armv8a-luna': dest,
        old_graphics + '/qt5/upstream/qtbase-everywhere-src-5.15.19/bin': dest + '/bin',
    }
    for module in ('qtbase', 'qtdeclarative', 'qtwayland', 'qttools'):
        prefix = old_graphics + '/qt5/upstream/' + module + '-everywhere-src-5.15.19'
        pairs[prefix + '/include'] = dest + '/include'
        linux_prefix = '/home/surest/nanopc-workspace/graphics/qt5/upstream/' + module + '-everywhere-src-5.15.19'
        pairs[linux_prefix + '/include'] = dest + '/include'
        pairs['/home/surest/nanopc-workspace/graphics/qt5/build/' + module + '-armv8a-luna'] = dest
        if module == 'qtbase':
            pairs[prefix + '/src'] = dest + '/src'
            pairs[linux_prefix + '/src'] = dest + '/src'
    modified = []
    for root in ('bin', 'mkspecs', 'lib'):
        for path in (out / root).rglob('*'):
            if path.is_file() and path.suffix in ('.conf', '.pri', '.prl', '.cmake', '.pc', '.la'):
                original = (source / path.relative_to(out)).read_text(encoding='utf-8')
                changed = rewrite(original, pairs)
                if changed != original:
                    path.write_text(changed, encoding='utf-8')
                    modified.append(path.relative_to(out).as_posix())
    files = []
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name != 'sdk-copy-manifest.json':
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            files.append({'path': path.relative_to(out).as_posix(),
                          'bytes': path.stat().st_size, 'sha256': digest})
    (out / 'sdk-copy-manifest.json').write_text(json.dumps({
        'source': str(source), 'toolchain': str(toolchain), 'graphics': str(graphics),
        'output': str(out), 'modified_metadata': modified, 'files': files,
        'scope': 'installed sdk export; not a source rebuild or board acceptance',
    }, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'files': len(files), 'metadata': len(modified)}))


if __name__ == '__main__':
    main()
