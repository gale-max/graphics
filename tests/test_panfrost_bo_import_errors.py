from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_actual_bo_import_rejects_errors_without_publishing_or_leaking(tmp_path):
    source = (ROOT / 'mesa/upstream/src/gallium/drivers/panfrost/pan_bo.c').read_text(encoding='utf-8')
    body = source[source.index('struct panfrost_bo *\npanfrost_bo_import('):
                  source.index('int\npanfrost_bo_export(')]
    code = r'''
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <errno.h>
#define ASSERTED
#define PAN_BO_SHARED 1
#define PAN_DBG_DUMP 1
#define PAN_KMOD_VM_OP_TYPE_MAP 1
#define PAN_KMOD_VM_MAP_AUTO_VA UINT64_MAX
#define PAN_KMOD_VM_OP_MODE_IMMEDIATE 1
#define mesa_loge(...) ((void)0)
struct pan_kmod_dev { int fd; };
struct pan_kmod_bo { uint64_t size; };
struct panfrost_device { int bo_map_lock, debug; struct { struct pan_kmod_dev *dev; void *vm; } kmod; };
struct panfrost_bo { struct panfrost_device *dev; struct pan_kmod_bo *kmod_bo; struct { uint64_t gpu; } ptr; int flags, refcnt; };
struct pan_kmod_vm_op { int type; struct { uint64_t start,size; } va; struct { struct pan_kmod_bo *bo; uint64_t bo_offset; } map; };
static struct panfrost_bo slot;
static struct pan_kmod_bo backing={.size=4096};
static int scenario, depth, puts, imports, binds;
static void pthread_mutex_lock(int *p) { (void)p; depth++; }
static void pthread_mutex_unlock(int *p) { (void)p; assert(depth==1); depth--; }
static int drmPrimeFDToHandle(int device,int fd,unsigned *handle) { *handle=7; return scenario==1?-5:0; }
static struct panfrost_bo *pan_lookup_bo(struct panfrost_device *d,unsigned h) { return scenario==2?NULL:&slot; }
static struct pan_kmod_bo *pan_kmod_bo_import(struct pan_kmod_dev *d,int fd,int flags) { imports++; errno=ENOMEM; return scenario==3?NULL:&backing; }
static int pan_kmod_vm_bind(void *v,int mode,struct pan_kmod_vm_op *op,int count) { binds++; op->va.start=0x10000; return scenario==4?-5:0; }
static void pan_kmod_bo_put(struct pan_kmod_bo *bo) { assert(bo==&backing); puts++; }
static int panfrost_bo_mmap(struct panfrost_bo *bo) { return 0; }
static int p_atomic_read(int *n) { return *n; }
static void p_atomic_set(int *n,int value) { *n=value; }
static void panfrost_bo_reference(struct panfrost_bo *bo) { bo->refcnt++; }
''' + body + r'''
int main(void) {
    struct pan_kmod_dev kd={.fd=3}; struct panfrost_device d={.kmod={.dev=&kd}};
    int cases[]={3,1,2,4};
    for(int i=0;i<4;i++) {
        scenario=cases[i]; slot=(struct panfrost_bo){0}; puts=imports=binds=0;
        assert(panfrost_bo_import(&d,9)==NULL);
        assert(depth==0 && slot.dev==NULL && slot.kmod_bo==NULL && slot.refcnt==0);
        assert(puts==(scenario==4?1:0));
    }
    scenario=0; slot=(struct panfrost_bo){0};
    assert(panfrost_bo_import(&d,9)==&slot);
    assert(depth==0 && slot.dev==&d && slot.kmod_bo==&backing && slot.refcnt==1);
    assert(panfrost_bo_import(&d,9)==&slot && slot.refcnt==2);
    return 0;
}
'''
    compiler = shutil.which('gcc') or shutil.which('clang')
    assert compiler
    cfile, exe = tmp_path / 'import.c', tmp_path / 'import.exe'
    cfile.write_text(code, encoding='utf-8')
    subprocess.run([compiler, '-std=c11', str(cfile), '-o', str(exe)], check=True, capture_output=True)
    result = subprocess.run([str(exe)], capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
