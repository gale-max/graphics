/*
 * Copyright © 2012 Linaro Limited
 * Copyright © 2013 Canonical Ltd
 *
 * This file is part of the glmark2 OpenGL (ES) 2.0 benchmark.
 *
 * glmark2 is free software: you can redistribute it and/or modify it under the
 * terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 *
 * glmark2 is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
 * details.
 *
 * You should have received a copy of the GNU General Public License along with
 * glmark2.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *  Simon Que 
 *  Jesse Barker
 *  Alexandros Frantzis
 */
#include "native-state-drm.h"
#include "log.h"
#include "options.h"

#include <errno.h>
#include <fcntl.h>
#include <cstring>
#include <string>

/******************
 * Public methods *
 ******************/

namespace
{

std::string const drm_device_opt{"drm-device"};

std::string get_drm_device_option()
{
    std::string drm_device{""};

    for (auto const& opt : Options::winsys_options)
    {
        if (opt.name == drm_device_opt)
            drm_device = opt.value;
    }

    return drm_device;
}

}

NativeStateDRM::NativeStateDRM() :
    fd_(0),
    resources_(0),
    connector_(0),
    encoder_(0),
    crtc_(0),
    mode_(0),
    dev_(0),
    surface_(0),
    pending_bo_(0),
    flipped_bo_(0),
    presented_bo_(0),
    crtc_set_(false),
    use_async_flip_(false)
{
    Options::winsys_options_help =
       "  drm-device=DRM-DEVICE  The DRM device to use (autodetected if unspecified)\n";
}

bool
NativeStateDRM::init_display()
{
    if (!dev_)
        init();

    return (dev_ != 0);
}

void*
NativeStateDRM::display()
{
    return static_cast<void*>(dev_);
}

bool
NativeStateDRM::create_window(WindowProperties const& properties)
{
    if (!dev_) {
        Log::error("Error: DRM device has not been initialized!\n");
        return false;
    }

    /* egl config's native visual id is drm fourcc */
    surface_ = gbm_surface_create(dev_, mode_->hdisplay, mode_->vdisplay,
                                  properties.visual_id,
                                  GBM_BO_USE_SCANOUT | GBM_BO_USE_RENDERING);
    if (!surface_) {
        Log::error("Failed to create GBM surface\n");
        return false;
    }

    return true;
}

void*
NativeStateDRM::window(WindowProperties& properties)
{
    properties = WindowProperties(mode_->hdisplay,
                                  mode_->vdisplay,
                                  true, 0);
    return static_cast<void*>(surface_);
}

void
NativeStateDRM::visible(bool /*visible*/)
{
}

bool
NativeStateDRM::should_quit()
{
    return should_quit_;
}

void
NativeStateDRM::flip()
{
    if (!crtc_set_ && drmSetMaster(fd_) < 0) {
        Log::error("Failed to become DRM master "
                   "(hint: glmark2-drm needs to be run in a VT)\n");
        should_quit_ = true;
        return;
    }

    if (pending_bo_)
        gbm_surface_release_buffer(surface_, pending_bo_);
    pending_bo_ = gbm_surface_lock_front_buffer(surface_);

    DRMFBState* pending_fb = fb_get_from_bo(pending_bo_);

    if (!pending_bo_ || !pending_fb) {
        Log::error("Failed to get gbm front buffer\n");
        return;
    }

    if (Options::swap_mode == Options::SwapModeFIFO || use_async_flip_)
    {
        /* When using either FIFO mode (vsync) or an async flip, wait for the
         * current flip to finish. */
        while (flipped_bo_ && check_for_page_flip(-1) >= 0)
            continue;
    }
    else
    {
        /* When not using async flips, i.e., mailbox-like presentation,
         * and the flip is still not done, we can continue potentially
         * without flipping. */
        check_for_page_flip(0);
    }

    /* If a flip is not in progress we can schedule another one. */
    if (!flipped_bo_) {
        if (!crtc_set_) {
            int status = drmModeSetCrtc(fd_, encoder_->crtc_id, pending_fb->fb_id, 0, 0,
                                        &connector_->connector_id, 1, mode_);
            if (status >= 0) {
                crtc_set_ = true;
                if (presented_bo_)
                    gbm_surface_release_buffer(surface_, presented_bo_);
                presented_bo_ = pending_bo_;
                flipped_bo_ = nullptr;
                pending_bo_ = nullptr;
            }
            else {
                Log::error("Failed to set crtc: %d\n", status);
            }
            return;
        }

        uint32_t flip_flags = DRM_MODE_PAGE_FLIP_EVENT;
        if (use_async_flip_)
            flip_flags |= DRM_MODE_PAGE_FLIP_ASYNC;

        int status = drmModePageFlip(fd_, encoder_->crtc_id, pending_fb->fb_id,
                                     flip_flags, this);
        if (status < 0) {
            Log::error("Failed to enqueue page flip: %d\n", status);
            return;
        }

        flipped_bo_ = pending_bo_;
        pending_bo_ = nullptr;
    }

    /* We need to ensure our surface has a free buffer, otherwise GL will
     * have no buffer to render on. */
    while (!gbm_surface_has_free_buffers(surface_) &&
           check_for_page_flip(-1) >= 0)
    {
        continue;
    }
}

/*******************
 * Private methods *
 *******************/

/* Simple helpers */

inline static bool valid_fd(int fd)
{
    return fd >= 0;
}

inline static bool valid_drm_node_path(std::string const& provided_node_path)
{
    return !provided_node_path.empty();
}

static int open_default_drm_device()
{
    return open("/dev/dri/card0", O_RDWR);
}

void
NativeStateDRM::fb_destroy_callback(gbm_bo* bo, void* data)
{
    DRMFBState* fb = reinterpret_cast<DRMFBState*>(data);
    if (fb && fb->fb_id) {
        drmModeRmFB(fb->fd, fb->fb_id);
    }
    delete fb;
    gbm_device* dev = gbm_bo_get_device(bo);
    Log::debug("Got GBM device handle %p from buffer object\n", dev);
}

NativeStateDRM::DRMFBState*
NativeStateDRM::fb_get_from_bo(gbm_bo* bo)
{
    if (!bo) {
        return NULL;
    }

    DRMFBState* fb = reinterpret_cast<DRMFBState*>(gbm_bo_get_user_data(bo));
    if (fb) {
        return fb;
    }

    unsigned int width = gbm_bo_get_width(bo);
    unsigned int height = gbm_bo_get_height(bo);
    unsigned int handles[4] = { 0, }, strides[4] = { 0, }, offsets[4] = { 0, };
    unsigned int format = gbm_bo_get_format(bo);
    unsigned int fb_id(0);
    int status;

#ifdef GBM_HAS_PLANES
    int i;
    for (i = 0; i < gbm_bo_get_plane_count(bo); i++) {
        handles[i] = gbm_bo_get_handle_for_plane(bo, i).u32;
        strides[i] = gbm_bo_get_stride_for_plane(bo, i);
        offsets[i] = gbm_bo_get_offset(bo, i);
    }
#else
    handles[0] = gbm_bo_get_handle(bo).u32;
    strides[0] = gbm_bo_get_stride(bo);
#endif

    status = drmModeAddFB2(fd_, width, height, format, handles,
                           strides, offsets, &fb_id, 0);
    if (status < 0) {
        Log::error("Failed to create FB: %d\n", status);
        return 0;
    }

    fb = new DRMFBState();
    fb->fd = fd_;
    fb->bo = bo;
    fb->fb_id = fb_id;

    gbm_bo_set_user_data(bo, fb, fb_destroy_callback);
    return fb;
}

bool
NativeStateDRM::init_gbm()
{
    dev_ = gbm_create_device(fd_);
    if (!dev_) {
        Log::error("Failed to create GBM device\n");
        return false;
    }

    return true;
}

bool
NativeStateDRM::init()
{
    int fd = -1;
    std::string drm_device = get_drm_device_option();

    if (valid_drm_node_path(drm_device)) {
        Log::debug("Trying to use DRM node %s from --winsys-options\n",
                   drm_device.c_str());
        fd = open(drm_device.c_str(), O_RDWR);
        if (!valid_fd(fd)) {
            Log::error("Tried to use '%s' but failed.\nReason : %s\n",
                       drm_device.c_str(), strerror(errno));
            return false;
        }
    }

    if (!valid_fd(fd)) {
        fd = open_default_drm_device();
    }

    if (!valid_fd(fd)) {
        Log::error("Failed to find a suitable DRM device\n");
        return false;
    }

    fd_ = fd;

    resources_ = drmModeGetResources(fd);
    if (!resources_) {
        Log::error("drmModeGetResources failed\n");
        return false;
    }

    // Find a connected connector
    for (int c = 0; c < resources_->count_connectors; c++) {
        connector_ = drmModeGetConnector(fd, resources_->connectors[c]);
        if (DRM_MODE_CONNECTED == connector_->connection) {
            break;
        }
        drmModeFreeConnector(connector_);
        connector_ = 0;
    }

    if (!connector_) {
        Log::error("Failed to find a suitable connector\n");
        return false;
    }

    // Find the best resolution (we will always operate full-screen).
    unsigned int bestArea(0);
    for (int m = 0; m < connector_->count_modes; m++) {
        drmModeModeInfo* curMode = &connector_->modes[m];
        unsigned int curArea = curMode->hdisplay * curMode->vdisplay;
        if (curArea > bestArea) {
            mode_ = curMode;
            bestArea = curArea;
        }
    }

    if (!mode_) {
        Log::error("Failed to find a suitable mode\n");
        return false;
    }

    // Find a suitable encoder
    for (int e = 0; e < resources_->count_encoders; e++) {
        bool found = false;
        encoder_ = drmModeGetEncoder(fd_, resources_->encoders[e]);
        for (int ce = 0; ce < connector_->count_encoders; ce++) {
            if (encoder_ && encoder_->encoder_id == connector_->encoders[ce]) {
                found = true;
                break;
            }
        }
        if (found)
            break;
        drmModeFreeEncoder(encoder_);
        encoder_ = 0;
    }

    // If encoder is not connected to the connector try to find
    // a suitable one
    if (!encoder_) {
        for (int e = 0; e < connector_->count_encoders; e++) {
            encoder_ = drmModeGetEncoder(fd, connector_->encoders[e]);
            for (int c = 0; c < resources_->count_crtcs; c++) {
                if (encoder_->possible_crtcs & (1 << c)) {
                    encoder_->crtc_id = resources_->crtcs[c];
                    break;
                }
            }
            if (encoder_->crtc_id) {
                break;
            }

            drmModeFreeEncoder(encoder_);
            encoder_ = 0;
        }
    }

    if (!encoder_) {
        Log::error("Failed to find a suitable encoder\n");
        return false;
    }

    if (!init_gbm()) {
        return false;
    }

    crtc_ = drmModeGetCrtc(fd_, encoder_->crtc_id);
    if (!crtc_) {
        // if there is no current CRTC, make sure to attach a suitable one
        for (int c = 0; c < resources_->count_crtcs; c++) {
            if (encoder_->possible_crtcs & (1 << c)) {
                encoder_->crtc_id = resources_->crtcs[c];
                break;
            }
        }
    }

    uint64_t cap_async;
    if (Options::swap_mode == Options::SwapModeDefault ||
        Options::swap_mode == Options::SwapModeImmediate) {
        use_async_flip_ = drmGetCap(fd_, DRM_CAP_ASYNC_PAGE_FLIP, &cap_async) == 0 &&
                          cap_async == 1;
        if (!use_async_flip_) {
            Log::info("Warning: DRM_CAP_ASYNC_PAGE_FLIP not supported, falling"
                      " back to 'mailbox' mode for SwapInterval(0).\n");
        }
    } else {
        use_async_flip_ = false;
    }

    signal(SIGINT, &NativeStateDRM::quit_handler);

    return true;
}

volatile std::sig_atomic_t NativeStateDRM::should_quit_(false);

void
NativeStateDRM::quit_handler(int /*signo*/)
{
    should_quit_ = true;
}

void
NativeStateDRM::page_flip_handler(int/*  fd */, unsigned int /* frame */, unsigned int /* sec */, unsigned int /* usec */, void* data)
{
    NativeStateDRM* state = reinterpret_cast<NativeStateDRM*>(data);
    if (state->presented_bo_)
        gbm_surface_release_buffer(state->surface_, state->presented_bo_);
    state->presented_bo_ = state->flipped_bo_;
    state->flipped_bo_ = nullptr;
}

void
NativeStateDRM::cleanup()
{
    // Restore CRTC state if necessary
    if (crtc_) {
        /* 没有原扫描缓冲区时恢复为关闭状态，不能以 FB 0 设置有效模式。 */
        const bool restore_mode = crtc_->mode_valid && crtc_->buffer_id;
        int status = drmModeSetCrtc(fd_, crtc_->crtc_id,
                                    restore_mode ? crtc_->buffer_id : 0,
                                    restore_mode ? crtc_->x : 0,
                                    restore_mode ? crtc_->y : 0,
                                    restore_mode ? &connector_->connector_id : nullptr,
                                    restore_mode ? 1 : 0,
                                    restore_mode ? &crtc_->mode : nullptr);
        if (status < 0) {
            Log::error("Failed to restore original CRTC: %d\n", status);
        }
        drmModeFreeCrtc(crtc_);
        crtc_ = 0;
    }
    if (surface_) {
        gbm_surface_destroy(surface_);
        surface_ = 0;
    }
    if (dev_) {
        gbm_device_destroy(dev_);
        dev_ = 0;
    }
    if (connector_) {
        drmModeFreeConnector(connector_);
        connector_ = 0;
    }
    if (encoder_) {
        drmModeFreeEncoder(encoder_);
        encoder_ = 0;
    }
    if (resources_) {
        drmModeFreeResources(resources_);
        resources_ = 0;
    }
    if (fd_ > 0) {
        drmClose(fd_);
    }
    fd_ = 0;
    mode_ = 0;
}

int
NativeStateDRM::check_for_page_flip(int timeout_ms)
{
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(fd_, &fds);

    drmEventContext evCtx;
    memset(&evCtx, 0, sizeof(evCtx));
    evCtx.version = 2;
    evCtx.page_flip_handler = page_flip_handler;

    struct timeval timeout = {0, timeout_ms * 1000};
    int status = select(fd_ + 1, &fds, 0, 0,
                        timeout_ms < 0 ? nullptr : &timeout);
    if (status == 1)
        drmHandleEvent(fd_, &evCtx);

    return status;
}
