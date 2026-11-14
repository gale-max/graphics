/* Minimal target probe: no EGL, GL, Mesa, DRM master or GPU submissions. */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>
#include "xf86drm.h"

static int probe(const char *path)
{
    struct stat st;
    drmDevicePtr dev = NULL;
    char *name = NULL, *typed = NULL;
    int fd, type, ret = 1;

    fd = open(path, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        fprintf(stderr, "open failed: %s: %s\n", path, strerror(errno));
        return ret;
    }
    if (fstat(fd, &st) || !S_ISCHR(st.st_mode))
        goto out;
    type = drmGetNodeTypeFromFd(fd);
    if (type < 0 || drmGetDevice2(fd, 0, &dev))
        goto out;
    name = drmGetDeviceNameFromFd2(fd);
    typed = type == DRM_NODE_RENDER ? drmGetRenderDeviceNameFromFd(fd) :
                                     drmGetPrimaryDeviceNameFromFd(fd);
    if (!name || !typed || !(dev->available_nodes & (1 << type)) ||
        strcmp(name, dev->nodes[type]) || strcmp(name, typed))
        goto out;
    printf("discovery pass: fd=%d rdev=%u:%u type=%d mask=%x node=%s id=%s\n",
           fd, major(st.st_rdev), minor(st.st_rdev), type,
           dev->available_nodes, name, dev->businfo.platform->fullname);
    ret = 0;
out:
    if (ret)
        fprintf(stderr, "discovery failed: %s\n", path);
    free(typed);
    free(name);
    drmFreeDevice(&dev);
    close(fd);
    return ret;
}

int main(int argc, char **argv)
{
    drmDevicePtr *devices;
    int i, type, count, total, failed = 0;

    if (argc > 1) {
        for (i = 1; i < argc; ++i)
            failed |= probe(argv[i]);
        return failed;
    }
    total = drmGetDevices2(0, NULL, 0);
    if (total <= 0) {
        fprintf(stderr, "discovery failed: no nodes (%d)\n", total);
        return 1;
    }
    devices = calloc(total, sizeof(*devices));
    if (!devices)
        return 1;
    count = drmGetDevices2(0, devices, total);
    if (count <= 0)
        failed = 1;
    for (i = 0; i < count; ++i)
        for (type = 0; type < DRM_NODE_MAX; ++type)
            if (devices[i]->available_nodes & (1 << type))
                failed |= probe(devices[i]->nodes[type]);
    drmFreeDevices(devices, count > 0 ? count : 0);
    free(devices);
    return failed;
}
