project('mtdev-fixed', 'c', version: '1.1.5')

includes = include_directories('include', 'src')
mtdev = both_libraries(
  'mtdev',
  'src/caps.c',
  'src/core.c',
  'src/iobuf.c',
  'src/match.c',
  'src/match_four.c',
  include_directories: includes,
  version: '1.0.0',
  soversion: '1',
  install: true,
)

install_headers(
  'include/mtdev.h',
  'include/mtdev-mapping.h',
  'include/mtdev-plumbing.h',
)

pkg = import('pkgconfig')
pkg.generate(
  mtdev,
  name: 'mtdev',
  description: 'Multitouch Protocol Translation Library',
  version: meson.project_version(),
)
