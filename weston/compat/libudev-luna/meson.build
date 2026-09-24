project('libudev-luna', 'c', version: '249')

install_headers('libudev.h')
libudev = both_libraries(
  'udev',
  'libudev-luna.c',
  version: '1.7.5',
  soversion: '1',
  install: true,
)

pkg = import('pkgconfig')
pkg.generate(
  libudev,
  name: 'libudev',
  description: 'Luna device manager compatibility for libudev consumers',
  version: meson.project_version(),
)
