"""真实 C 布局计算：保持缓冲尺寸，八个缩放窗口在工作区内不重叠。"""
from pathlib import Path
import subprocess


def test_grid_is_opt_in_and_app_scoped():
    source = (Path(__file__).parents[1] / "upstream/desktop-shell/shell.c").read_text(encoding="utf-8")
    assert '&shell->test_glmark_grid, false)' in source
    helper = source.split("map_test_grid(struct desktop_shell", 1)[1].split("static void\nmap(", 1)[0]
    assert 'strcmp(app_id, "com.github.glmark2.glmark2") != 0' in helper
    assert "weston_matrix_scale(" in helper
    assert "weston_desktop_surface_set_size" not in helper


def test_grid_geometry(tmp_path):
    header = Path(__file__).parents[1] / "upstream/desktop-shell/test-grid.h"
    assert header.is_file(), "test grid helper missing"
    main = r'''
int main(void) {
    struct weston_test_grid_place slots[8];
    for (unsigned int i = 0; i < 8; i++) {
        if (!weston_test_grid_calculate(1920, 1048, 832, 664, i, &slots[i])) return 1;
        if (slots[i].scale <= 0 || slots[i].scale > 1) return 2;
        if (slots[i].x < 0 || slots[i].y < 0 || slots[i].x + 832 * slots[i].scale > 1920 || slots[i].y + 664 * slots[i].scale > 1048) return 3;
        for (unsigned int j = 0; j < i; j++) {
            if (slots[i].x < slots[j].x + 832 * slots[j].scale && slots[j].x < slots[i].x + 832 * slots[i].scale && slots[i].y < slots[j].y + 664 * slots[j].scale && slots[j].y < slots[i].y + 664 * slots[i].scale) return 4;
        }
    }
    if (weston_test_grid_calculate(0, 100, 832, 664, 0, &slots[0])) return 5;
    if (weston_test_grid_calculate(1920, 1048, 0, 664, 0, &slots[0])) return 6;
    struct weston_test_grid_place repeat;
    if (!weston_test_grid_calculate(1920, 1048, 832, 664, 8, &repeat)) return 7;
    if (repeat.x != slots[0].x || repeat.y != slots[0].y) return 8;
    return 0;
}
'''
    path, binary = tmp_path / "grid.c", tmp_path / "grid"
    path.write_text(header.read_text(encoding="utf-8") + main, encoding="utf-8")
    def linux(p):
        value = p.resolve().as_posix()
        return "/mnt/" + value[0].lower() + value[2:]
    subprocess.run(["wsl.exe", "-d", "ubuntu20.04", "--", "gcc", linux(path), "-o", linux(binary)], check=True, capture_output=True)
    result = subprocess.run(["wsl.exe", "-d", "ubuntu20.04", "--", linux(binary)], capture_output=True)
    assert result.returncode == 0, f"grid geometry failed: {result.returncode}"
