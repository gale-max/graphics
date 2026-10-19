"""Execute the compositor framebuffer creation path and its unwind."""
from pathlib import Path
import shutil
import subprocess


def test_luna_dumb_buffer_excluded_from_helper_fork(tmp_path):
    source = (Path(__file__).resolve().parents[1] / 'upstream/libweston/backend-drm/fb.c').read_text(encoding='utf-8')
    start = source.index('struct drm_fb *\ndrm_fb_create_dumb(')
    end = source.index('\nstruct drm_fb *\ndrm_fb_ref(', start)
    c = tmp_path / 'fb.c'
    exe = tmp_path / 'fb.exe'
    c.write_text(PRELUDE + source[start:end] + MAIN, encoding='utf-8')
    subprocess.run([shutil.which('gcc'), '-DLUNA_OS=1', '-Wall', '-Werror', '-Wno-unused-function', str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)


PRELUDE = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define BUFFER_PIXMAN_DUMB 1
#define DRM_FORMAT_MOD_INVALID 0
#define DRM_IOCTL_MODE_CREATE_DUMB 1
#define DRM_IOCTL_MODE_MAP_DUMB 2
#define DRM_IOCTL_MODE_DESTROY_DUMB 3
#define PROT_WRITE 2
#define MAP_SHARED 1
#define MAP_FAILED ((void *)-1)
#define MADV_DONTFORK 10
struct pixel_format_info { int depth,bpp; };
struct drm_fb { int refcnt,type,num_planes,width,height,fd; uint64_t modifier,size; uint32_t handles[4],strides[4],fb_id; const struct pixel_format_info *format; void *map; };
struct drm_backend { struct { int fd; } drm; };
struct drm_mode_create_dumb { uint32_t bpp,width,height,handle,pitch; uint64_t size; };
struct drm_mode_destroy_dumb { uint32_t handle; };
struct drm_mode_map_dumb { uint32_t handle; uint64_t offset; };
static int advised,unmapped,removed,destroyed,fail_advice;
static char buffer[4096];
static void *zalloc(size_t n) {return calloc(1,n);}
static const struct pixel_format_info *pixel_format_get_info(uint32_t f) {static struct pixel_format_info p={24,32};(void)f;return &p;}
#define weston_log(...) ((void)0)
static int drmIoctl(int fd,int op,void *arg) {(void)fd;if(op==1){struct drm_mode_create_dumb *c=arg;c->handle=7;c->pitch=128;c->size=4096;}else if(op==2){((struct drm_mode_map_dumb *)arg)->offset=0;}else {assert(((struct drm_mode_destroy_dumb *)arg)->handle==7);destroyed++;}return 0;}
static int drm_fb_addfb(struct drm_backend *b,struct drm_fb *f) {(void)b;f->fb_id=8;return 0;}
static int drmModeRmFB(int fd,uint32_t id) {(void)fd;assert(id==8);removed++;return 0;}
static void *mmap(void *p,size_t n,int prot,int flags,int fd,uint64_t off) {(void)p;(void)prot;(void)flags;(void)fd;(void)off;assert(n==4096);return buffer;}
static int madvise(void *p,size_t n,int advice) {assert(p==buffer&&n==4096&&advice==MADV_DONTFORK);advised++;return fail_advice?-1:0;}
static int munmap(void *p,size_t n) {assert(p==buffer&&n==4096);unmapped++;return 0;}
'''
MAIN = r'''
int main(void) {
 struct drm_backend b={{3}};
 struct drm_fb *f=drm_fb_create_dumb(&b,32,32,1);
 assert(f&&advised==1&&!unmapped&&!removed&&!destroyed);free(f);
 fail_advice=1;f=drm_fb_create_dumb(&b,32,32,1);
 assert(!f&&advised==2&&unmapped==1&&removed==1&&destroyed==1);
 return 0;
}
'''
