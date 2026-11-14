/* Boundary fixtures only: all discovery and allocation run in real libdrm. */
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include "xf86drm.h"

struct fixture {
    unsigned int maj, min;
    mode_t mode;
    const char *driver;
    int present;
};
static struct fixture nodes[8];
static int count, replace_path;

static int add(unsigned int maj, unsigned int min, mode_t mode, const char *driver)
{
    nodes[count] = (struct fixture){maj, min, mode, driver, 1};
    return 100 + count++;
}

int __wrap_fstat(int fd, struct stat *st)
{
    if (fd < 100 || fd >= 100 + count) {
        errno = EBADF;
        return -1;
    }
    memset(st, 0, sizeof(*st));
    st->st_mode = nodes[fd - 100].mode;
    st->st_rdev = makedev(nodes[fd - 100].maj, nodes[fd - 100].min);
    return 0;
}

int __wrap_stat(const char *path, struct stat *st)
{
    int i;
    char name[80];
    for (i = 0; i < count; ++i) {
        snprintf(name, sizeof(name), nodes[i].min >= 128 ?
                 "/dev/dri/renderD%u" : "/dev/dri/card%u", nodes[i].min);
        if (nodes[i].present && !strcmp(name, path)) {
            __wrap_fstat(100 + i, st);
            if (replace_path)
                st->st_rdev = makedev(226, 10);
            return 0;
        }
    }
    errno = ENOENT;
    return -1;
}

int __wrap_ioctl(int fd, unsigned long req, ...)
{
    va_list ap;
    struct drm_version *v;
    const char *name;
    if (fd < 100 || fd >= 100 + count) {
        errno = EBADF;
        return -1;
    }
    if (req != DRM_IOCTL_VERSION) {
        errno = ENOTTY;
        return -1;
    }
    va_start(ap, req);
    v = va_arg(ap, struct drm_version *);
    va_end(ap);
    name = nodes[fd - 100].driver;
    if (v->name)
        memcpy(v->name, name, v->name_len < strlen(name) ? v->name_len : strlen(name));
    v->name_len = strlen(name);
    v->date_len = v->desc_len = 0;
    return 0;
}

static void check_name(char *actual, const char *expected)
{
    assert(actual);
    assert(!strcmp(actual, expected));
    free(actual);
}

static void check_device(int fd, int type, const char *path)
{
    drmDevicePtr dev = NULL;
    assert(drmGetNodeTypeFromFd(fd) == type);
    assert(drmGetDevice2(fd, 0, &dev) == 0);
    assert(dev && dev->available_nodes == (1 << type));
    assert(!strcmp(dev->nodes[type], path));
    drmFreeDevice(&dev);
    assert(!dev);
}

int main(int argc, char **argv)
{
    int fd, other, n;
    drmDevicePtr dev = NULL, peer = NULL, list[4] = {0};
    const char *c;
    assert(argc == 2);
    c = argv[1];
    if (!strcmp(c, "empty")) {
        assert(drmGetDevices2(0, NULL, 0) == 0);
        assert(drmGetDevices2(0, list, 4) == 0);
        goto done;
    }
    fd = add(226, 0, S_IFCHR, "virtio_gpu");
    other = add(226, 128, S_IFCHR, "virtio_gpu");
    if (!strcmp(c, "virtio_primary")) {
        check_device(fd, DRM_NODE_PRIMARY, "/dev/dri/card0");
    } else if (!strcmp(c, "virtio_render")) {
        check_device(other, DRM_NODE_RENDER, "/dev/dri/renderD128");
    } else if (!strcmp(c, "panfrost_primary")) {
        nodes[0].driver = "panfrost";
        check_device(fd, DRM_NODE_PRIMARY, "/dev/dri/card0");
    } else if (!strcmp(c, "nonzero_minor")) {
        nodes[0].min = 7;
        nodes[1].min = 133;
        check_device(fd, DRM_NODE_PRIMARY, "/dev/dri/card7");
        check_device(other, DRM_NODE_RENDER, "/dev/dri/renderD133");
    } else if (!strcmp(c, "invalid_fd")) {
        assert(drmGetDevice2(999, 0, &dev) == -EBADF);
        assert(!dev);
        assert(!drmGetDeviceNameFromFd(999));
        assert(errno == EBADF);
    } else if (!strcmp(c, "regular_file")) {
        nodes[0].mode = S_IFREG;
        assert(drmGetDevice2(fd, 0, &dev) == -EINVAL);
        assert(!drmGetDeviceNameFromFd2(fd));
    } else if (!strcmp(c, "wrong_major")) {
        nodes[0].maj = 4;
        assert(drmGetNodeTypeFromFd(fd) == -1);
        assert(drmGetDevice2(fd, 0, &dev) == -EINVAL);
        assert(!drmGetDeviceNameFromFd(fd));
    } else if (!strcmp(c, "control_minor")) {
        nodes[0].min = 64;
        assert(drmGetDevice2(fd, 0, &dev) == -EINVAL);
    } else if (!strcmp(c, "missing_path")) {
        nodes[0].present = 0;
        assert(drmGetDevice2(fd, 0, &dev) == -ENOENT);
        assert(!drmGetDeviceNameFromFd2(fd));
    } else if (!strcmp(c, "replaced_path")) {
        replace_path = 1;
        assert(drmGetDevice2(fd, 0, &dev) == -ENODEV);
        assert(!drmGetDeviceNameFromFd2(fd));
    } else if (!strcmp(c, "names")) {
        nodes[0].min = 9;
        nodes[1].min = 140;
        check_name(drmGetDeviceNameFromFd(fd), "/dev/dri/card9");
        check_name(drmGetDeviceNameFromFd(other), "/dev/dri/renderD140");
        check_name(drmGetDeviceNameFromFd2(fd), "/dev/dri/card9");
        check_name(drmGetDeviceNameFromFd2(other), "/dev/dri/renderD140");
        check_name(drmGetRenderDeviceNameFromFd(other), "/dev/dri/renderD140");
        check_name(drmGetPrimaryDeviceNameFromFd(fd), "/dev/dri/card9");
    } else if (!strcmp(c, "peer_not_guessed")) {
        assert(!drmGetRenderDeviceNameFromFd(fd));
        assert(errno == ENOTSUP);
        assert(!drmGetPrimaryDeviceNameFromFd(other));
        assert(errno == ENOTSUP);
    } else if (!strcmp(c, "from_devid")) {
        nodes[1].min = 135;
        assert(drmGetDeviceFromDevId(makedev(226, 135), 0, &dev) == 0);
        assert(dev->available_nodes == (1 << DRM_NODE_RENDER));
        assert(!strcmp(dev->nodes[DRM_NODE_RENDER], "/dev/dri/renderD135"));
        drmFreeDevice(&dev);
        assert(drmGetDeviceFromDevId(makedev(226, 136), 0, &dev) == -ENOENT);
    } else if (!strcmp(c, "invalid_args")) {
        assert(drmGetDevice2(fd, 0, NULL) == -EINVAL);
        assert(drmGetDevice2(fd, 0x80000000, &dev) == -EINVAL);
        assert(drmGetDevice2(-1, 0, &dev) == -EINVAL);
        assert(drmGetDeviceFromDevId(makedev(226, 0), 0, NULL) == -EINVAL);
        assert(drmGetDeviceFromDevId(makedev(226, 0), 2, &dev) == -EINVAL);
        assert(drmGetDevices2(2, NULL, 0) == -EINVAL);
        assert(drmGetDevices2(0, list, 0) == 0);
        assert(drmGetDevices2(0, list, -1) == 0);
    } else if (!strcmp(c, "enumeration")) {
        nodes[0].min = 7;
        nodes[1].min = 133;
        add(4, 8, S_IFCHR, "tty");
        add(226, 9, S_IFREG, "file");
        assert(drmGetDevices2(0, NULL, 0) == 2);
        n = drmGetDevices2(0, list, 4);
        assert(n == 2);
        assert(!strcmp(list[0]->nodes[DRM_NODE_PRIMARY], "/dev/dri/card7"));
        assert(!strcmp(list[1]->nodes[DRM_NODE_RENDER], "/dev/dri/renderD133"));
        assert(!drmDevicesEqual(list[0], list[1]));
        drmFreeDevices(list, n);
        assert(drmGetDevices2(0, list, 1) == 1);
        drmFreeDevices(list, 1);
    } else if (!strcmp(c, "kmsro_enumeration")) {
        drmVersionPtr version;
        nodes[0].driver = "rockchip";
        nodes[1].driver = "panfrost";
        n = drmGetDevices2(0, list, 4);
        assert(n == 2);
        assert(list[0]->bustype == DRM_BUS_PLATFORM);
        assert(list[0]->available_nodes == (1 << DRM_NODE_PRIMARY));
        assert(list[1]->bustype == DRM_BUS_PLATFORM);
        assert(list[1]->available_nodes == (1 << DRM_NODE_RENDER));
        assert(!strcmp(list[1]->nodes[DRM_NODE_RENDER], "/dev/dri/renderD128"));
        version = drmGetVersion(other);
        assert(version && !strcmp(version->name, "panfrost"));
        drmFreeVersion(version);
        drmFreeDevices(list, n);
    } else if (!strcmp(c, "independent_nodes")) {
        nodes[0].driver = "rockchip";
        nodes[1].driver = "panfrost";
        assert(drmGetDevice2(fd, 0, &dev) == 0);
        assert(drmGetDevice2(other, 0, &peer) == 0);
        assert(!drmDevicesEqual(dev, peer));
        drmFreeDevice(&peer);
        assert(drmGetDeviceFromDevId(makedev(226, 0), 0, &peer) == 0);
        assert(drmDevicesEqual(dev, peer));
        drmFreeDevice(&dev);
        drmFreeDevice(&peer);
    } else {
        assert(!"unknown case");
    }
done:
    printf("pass: %s\n", c);
    return 0;
}
