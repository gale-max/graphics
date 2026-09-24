/* SPDX-License-Identifier: LGPL-2.1-or-later */
#define _GNU_SOURCE
#include "libudev.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <fnmatch.h>
#include <linux/input.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

struct udev {
    unsigned int refs;
    void *userdata;
};

struct udev_list_entry {
    char *name;
    char *value;
    struct udev_list_entry *next;
};

struct udev_device {
    unsigned int refs;
    struct udev *udev;
    char syspath[128];
    char devnode[128];
    char subsystem[16];
    char sysname[64];
    char sysnum[32];
    char action[16];
    dev_t devnum;
    bool mouse;
    bool touchscreen;
    bool keyboard;
    struct udev_list_entry *properties;
};

struct udev_enumerate {
    unsigned int refs;
    struct udev *udev;
    char subsystem[16];
    char sysname[64];
    struct udev_list_entry *devices;
};

struct udev_monitor {
    unsigned int refs;
    struct udev *udev;
    int pipefd[2];
    char subsystem[16];
};

static void free_list(struct udev_list_entry *entry)
{
    while (entry) {
        struct udev_list_entry *next = entry->next;
        free(entry->name);
        free(entry->value);
        free(entry);
        entry = next;
    }
}

static int add_list_entry_value(struct udev_list_entry **head, const char *name,
                                const char *value)
{
    struct udev_list_entry **tail = head;
    struct udev_list_entry *entry;

    while (*tail) {
        tail = &(*tail)->next;
    }
    entry = calloc(1, sizeof(*entry));
    if (!entry) {
        return -ENOMEM;
    }
    entry->name = strdup(name);
    if (!entry->name) {
        free(entry);
        return -ENOMEM;
    }
    if (value) {
        entry->value = strdup(value);
        if (!entry->value) {
            free(entry->name);
            free(entry);
            return -ENOMEM;
        }
    }
    *tail = entry;
    return 0;
}

static int add_list_entry(struct udev_list_entry **head, const char *name)
{
    return add_list_entry_value(head, name, NULL);
}

static void build_device_properties(struct udev_device *device)
{
    if (strcmp(device->subsystem, "input") != 0) {
        return;
    }
    (void)add_list_entry_value(&device->properties, "ID_SEAT", "seat0");
    (void)add_list_entry_value(&device->properties, "ID_INPUT", "1");
    if (device->mouse) {
        (void)add_list_entry_value(&device->properties, "ID_INPUT_MOUSE", "1");
    }
    if (device->touchscreen) {
        (void)add_list_entry_value(&device->properties,
                                   "ID_INPUT_TOUCHSCREEN", "1");
    }
    if (device->keyboard) {
        (void)add_list_entry_value(&device->properties,
                                   "ID_INPUT_KEYBOARD", "1");
    }
}

static void classify_input(struct udev_device *device)
{
    unsigned long evbits[(EV_MAX + sizeof(unsigned long) * 8) /
                         (sizeof(unsigned long) * 8)] = {0};
    unsigned long keybits[(KEY_MAX + sizeof(unsigned long) * 8) /
                          (sizeof(unsigned long) * 8)] = {0};
    unsigned long absbits[(ABS_MAX + sizeof(unsigned long) * 8) /
                          (sizeof(unsigned long) * 8)] = {0};
    int fd = open(device->devnode, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    const unsigned int bits = sizeof(unsigned long) * 8;

    if (fd < 0) {
        return;
    }
    (void)ioctl(fd, EVIOCGBIT(0, sizeof(evbits)), evbits);
    (void)ioctl(fd, EVIOCGBIT(EV_KEY, sizeof(keybits)), keybits);
    (void)ioctl(fd, EVIOCGBIT(EV_ABS, sizeof(absbits)), absbits);
    close(fd);

    device->mouse = (keybits[BTN_MOUSE / bits] &
                     (1UL << (BTN_MOUSE % bits))) != 0;
    device->touchscreen =
        (keybits[BTN_TOUCH / bits] & (1UL << (BTN_TOUCH % bits))) != 0 &&
        (absbits[ABS_X / bits] & (1UL << (ABS_X % bits))) != 0 &&
        (absbits[ABS_Y / bits] & (1UL << (ABS_Y % bits))) != 0;
    device->keyboard =
        (keybits[KEY_A / bits] & (1UL << (KEY_A % bits))) != 0;
}

static struct udev_device *device_from_parts(struct udev *udev,
                                              const char *subsystem,
                                              const char *sysname)
{
    struct udev_device *device;
    struct stat st;
    const char *directory;

    if (!udev || !subsystem || !sysname) {
        errno = EINVAL;
        return NULL;
    }
    if (strcmp(subsystem, "input") == 0) {
        directory = "/dev/input";
    } else if (strcmp(subsystem, "drm") == 0) {
        directory = "/dev/dri";
    } else {
        errno = ENODEV;
        return NULL;
    }
    device = calloc(1, sizeof(*device));
    if (!device) {
        return NULL;
    }
    device->refs = 1;
    device->udev = udev_ref(udev);
    snprintf(device->subsystem, sizeof(device->subsystem), "%s", subsystem);
    snprintf(device->sysname, sizeof(device->sysname), "%s", sysname);
    snprintf(device->devnode, sizeof(device->devnode), "%s/%s", directory,
             sysname);
    snprintf(device->syspath, sizeof(device->syspath), "/sys/class/%s/%s",
             subsystem, sysname);
    snprintf(device->sysnum, sizeof(device->sysnum), "%s",
             sysname + strcspn(sysname, "0123456789"));
    if (stat(device->devnode, &st) != 0) {
        udev_device_unref(device);
        return NULL;
    }
    device->devnum = st.st_rdev;
    if (strcmp(subsystem, "input") == 0) {
        classify_input(device);
        build_device_properties(device);
    }
    return device;
}

struct udev *udev_new(void)
{
    struct udev *udev = calloc(1, sizeof(*udev));
    if (udev) {
        udev->refs = 1;
    }
    return udev;
}

struct udev *udev_ref(struct udev *udev)
{
    if (udev) {
        udev->refs++;
    }
    return udev;
}

struct udev *udev_unref(struct udev *udev)
{
    if (udev && --udev->refs == 0) {
        free(udev);
        return NULL;
    }
    return udev;
}

void *udev_get_userdata(struct udev *udev) { return udev ? udev->userdata : NULL; }
void udev_set_userdata(struct udev *udev, void *data) { if (udev) udev->userdata = data; }

struct udev_list_entry *udev_list_entry_get_next(struct udev_list_entry *entry)
{ return entry ? entry->next : NULL; }
const char *udev_list_entry_get_name(struct udev_list_entry *entry)
{ return entry ? entry->name : NULL; }
const char *udev_list_entry_get_value(struct udev_list_entry *entry)
{ return entry ? entry->value : NULL; }
struct udev_list_entry *udev_list_entry_get_by_name(struct udev_list_entry *entry,
                                                     const char *name)
{
    for (; entry; entry = entry->next) {
        if (strcmp(entry->name, name) == 0) return entry;
    }
    return NULL;
}

struct udev_device *udev_device_new_from_syspath(struct udev *udev,
                                                  const char *path)
{
    const char *name = strrchr(path ? path : "", '/');
    const char *subsystem;
    if (!name || name[1] == '\0') return NULL;
    subsystem = strstr(path, "/input/") ? "input" :
                strstr(path, "/drm/") ? "drm" : NULL;
    return subsystem ? device_from_parts(udev, subsystem, name + 1) : NULL;
}

struct udev_device *udev_device_new_from_subsystem_sysname(struct udev *udev,
                                                            const char *subsystem,
                                                            const char *sysname)
{ return device_from_parts(udev, subsystem, sysname); }

struct udev_device *udev_device_new_from_devnum(struct udev *udev, char type,
                                                 dev_t devnum)
{
    const char *directories[] = {"/dev/input", "/dev/dri"};
    const char *subsystems[] = {"input", "drm"};
    size_t index;
    (void)type;
    for (index = 0; index < 2; index++) {
        DIR *dir = opendir(directories[index]);
        struct dirent *entry;
        if (!dir) continue;
        while ((entry = readdir(dir)) != NULL) {
            struct udev_device *device =
                device_from_parts(udev, subsystems[index], entry->d_name);
            if (device && device->devnum == devnum) {
                closedir(dir);
                return device;
            }
            udev_device_unref(device);
        }
        closedir(dir);
    }
    return NULL;
}

struct udev_device *udev_device_ref(struct udev_device *device)
{ if (device) device->refs++; return device; }
struct udev_device *udev_device_unref(struct udev_device *device)
{
    if (device && --device->refs == 0) {
        free_list(device->properties);
        udev_unref(device->udev);
        free(device);
        return NULL;
    }
    return device;
}
struct udev *udev_device_get_udev(struct udev_device *device)
{ return device ? device->udev : NULL; }
struct udev_device *udev_device_get_parent(struct udev_device *device)
{ (void)device; return NULL; }
struct udev_device *udev_device_get_parent_with_subsystem_devtype(
    struct udev_device *device, const char *subsystem, const char *devtype)
{ (void)device; (void)subsystem; (void)devtype; return NULL; }
const char *udev_device_get_devpath(struct udev_device *device)
{ return device ? device->syspath : NULL; }
const char *udev_device_get_subsystem(struct udev_device *device)
{ return device ? device->subsystem : NULL; }
const char *udev_device_get_devtype(struct udev_device *device)
{ (void)device; return NULL; }
const char *udev_device_get_syspath(struct udev_device *device)
{ return device ? device->syspath : NULL; }
const char *udev_device_get_sysname(struct udev_device *device)
{ return device ? device->sysname : NULL; }
const char *udev_device_get_sysnum(struct udev_device *device)
{ return device ? device->sysnum : NULL; }
const char *udev_device_get_devnode(struct udev_device *device)
{ return device ? device->devnode : NULL; }
const char *udev_device_get_action(struct udev_device *device)
{ return device && device->action[0] ? device->action : NULL; }
dev_t udev_device_get_devnum(struct udev_device *device)
{ return device ? device->devnum : 0; }
int udev_device_get_is_initialized(struct udev_device *device)
{ return device != NULL; }
const char *udev_device_get_sysattr_value(struct udev_device *device,
                                           const char *key)
{ (void)device; (void)key; return NULL; }

const char *udev_device_get_property_value(struct udev_device *device,
                                            const char *key)
{
    if (!device || !key) return NULL;
    if (strcmp(key, "ID_SEAT") == 0) return "seat0";
    if (strcmp(key, "ID_INPUT") == 0 &&
        strcmp(device->subsystem, "input") == 0) return "1";
    if (strcmp(key, "ID_INPUT_MOUSE") == 0 && device->mouse) return "1";
    if (strcmp(key, "ID_INPUT_TOUCHSCREEN") == 0 && device->touchscreen)
        return "1";
    if ((strcmp(key, "ID_INPUT_KEYBOARD") == 0 ||
         strcmp(key, "ID_INPUT_KEY") == 0) && device->keyboard) return "1";
    return NULL;
}

struct udev_list_entry *udev_device_get_properties_list_entry(
    struct udev_device *device)
{
    return device ? device->properties : NULL;
}

struct udev_enumerate *udev_enumerate_new(struct udev *udev)
{
    struct udev_enumerate *enumerate = calloc(1, sizeof(*enumerate));
    if (enumerate) {
        enumerate->refs = 1;
        enumerate->udev = udev_ref(udev);
    }
    return enumerate;
}
struct udev_enumerate *udev_enumerate_ref(struct udev_enumerate *enumerate)
{ if (enumerate) enumerate->refs++; return enumerate; }
struct udev_enumerate *udev_enumerate_unref(struct udev_enumerate *enumerate)
{
    if (enumerate && --enumerate->refs == 0) {
        free_list(enumerate->devices);
        udev_unref(enumerate->udev);
        free(enumerate);
        return NULL;
    }
    return enumerate;
}
int udev_enumerate_add_match_subsystem(struct udev_enumerate *enumerate,
                                        const char *subsystem)
{
    if (!enumerate || !subsystem) return -EINVAL;
    snprintf(enumerate->subsystem, sizeof(enumerate->subsystem), "%s", subsystem);
    return 0;
}
int udev_enumerate_add_match_sysname(struct udev_enumerate *enumerate,
                                      const char *sysname)
{
    if (!enumerate || !sysname) return -EINVAL;
    snprintf(enumerate->sysname, sizeof(enumerate->sysname), "%s", sysname);
    return 0;
}
int udev_enumerate_scan_devices(struct udev_enumerate *enumerate)
{
    const char *directory;
    DIR *dir;
    struct dirent *entry;
    if (!enumerate) return -EINVAL;
    free_list(enumerate->devices);
    enumerate->devices = NULL;
    directory = strcmp(enumerate->subsystem, "input") == 0 ? "/dev/input" :
                strcmp(enumerate->subsystem, "drm") == 0 ? "/dev/dri" : NULL;
    if (!directory) return -ENODEV;
    dir = opendir(directory);
    if (!dir) return -errno;
    while ((entry = readdir(dir)) != NULL) {
        char syspath[128];
        int pathLength;

        if (entry->d_name[0] == '.') continue;
        if (enumerate->sysname[0] &&
            fnmatch(enumerate->sysname, entry->d_name, 0) != 0) continue;
        pathLength = snprintf(syspath, sizeof(syspath), "/sys/class/%s/%s",
                              enumerate->subsystem, entry->d_name);
        if (pathLength < 0 || (size_t)pathLength >= sizeof(syspath)) {
            closedir(dir);
            return -ENAMETOOLONG;
        }
        if (add_list_entry(&enumerate->devices, syspath) != 0) {
            closedir(dir);
            return -ENOMEM;
        }
    }
    closedir(dir);
    return 0;
}
struct udev_list_entry *udev_enumerate_get_list_entry(
    struct udev_enumerate *enumerate)
{ return enumerate ? enumerate->devices : NULL; }

struct udev_monitor *udev_monitor_new_from_netlink(struct udev *udev,
                                                    const char *name)
{
    struct udev_monitor *monitor;
    (void)name;
    monitor = calloc(1, sizeof(*monitor));
    if (!monitor) return NULL;
    monitor->pipefd[0] = -1;
    monitor->pipefd[1] = -1;
    if (pipe2(monitor->pipefd, O_NONBLOCK | O_CLOEXEC) != 0) {
        free(monitor);
        return NULL;
    }
    monitor->refs = 1;
    monitor->udev = udev_ref(udev);
    return monitor;
}
struct udev_monitor *udev_monitor_ref(struct udev_monitor *monitor)
{ if (monitor) monitor->refs++; return monitor; }
struct udev_monitor *udev_monitor_unref(struct udev_monitor *monitor)
{
    if (monitor && --monitor->refs == 0) {
        close(monitor->pipefd[0]);
        close(monitor->pipefd[1]);
        udev_unref(monitor->udev);
        free(monitor);
        return NULL;
    }
    return monitor;
}
int udev_monitor_filter_add_match_subsystem_devtype(struct udev_monitor *monitor,
                                                     const char *subsystem,
                                                     const char *devtype)
{
    (void)devtype;
    if (!monitor || !subsystem) return -EINVAL;
    snprintf(monitor->subsystem, sizeof(monitor->subsystem), "%s", subsystem);
    return 0;
}
int udev_monitor_enable_receiving(struct udev_monitor *monitor)
{ return monitor ? 0 : -EINVAL; }
int udev_monitor_get_fd(struct udev_monitor *monitor)
{ return monitor ? monitor->pipefd[0] : -1; }
struct udev_device *udev_monitor_receive_device(struct udev_monitor *monitor)
{ (void)monitor; errno = EAGAIN; return NULL; }
