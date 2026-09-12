# Copyright © 2017 Intel Corporation
# SPDX-License-Identifier: MIT

inc_wayland_drm = include_directories('.')
inc_luna_wayland_drm = include_directories('../../../../../generated/wayland/25.2.8')

if get_option('luna-prebuilt-wayland')
  wayland_drm_protocol_c = files('../../../../../generated/wayland/25.2.8/wayland-drm-protocol.c')
  wayland_drm_client_protocol_h = files('../../../../../generated/wayland/25.2.8/wayland-drm-client-protocol.h')
  wayland_drm_server_protocol_h = files('../../../../../generated/wayland/25.2.8/wayland-drm-server-protocol.h')
else
  wayland_drm_protocol_c = custom_target(
    'wayland-drm-protocol.c',
    input : 'wayland-drm.xml',
    output : 'wayland-drm-protocol.c',
    command : [prog_wl_scanner, wl_scanner_arg, '@INPUT@', '@OUTPUT@'],
  )

  wayland_drm_client_protocol_h = custom_target(
    'wayland-drm-client-protocol.h',
    input : 'wayland-drm.xml',
    output : 'wayland-drm-client-protocol.h',
    command : [prog_wl_scanner, 'client-header', '@INPUT@', '@OUTPUT@'],
  )

  wayland_drm_server_protocol_h = custom_target(
    'wayland-drm-server-protocol.h',
    input : 'wayland-drm.xml',
    output : 'wayland-drm-server-protocol.h',
    command : [prog_wl_scanner, 'server-header', '@INPUT@', '@OUTPUT@'],
  )
endif

libwayland_drm = static_library(
  'wayland_drm',
  ['wayland-drm.c', wayland_drm_protocol_c, wayland_drm_server_protocol_h],
  gnu_symbol_visibility : 'hidden',
  dependencies : [dep_wayland_server],
  include_directories : [inc_include, inc_luna_wayland_drm],
  build_by_default : false,
)
