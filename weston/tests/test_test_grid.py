"""Execute grid geometry for 8, 12 and 16 non-overlapping scaled windows."""
from pathlib import Path
import pytest
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
        if (!weston_test_grid_calculate(1920, 1048, 832, 664, 2, i, &slots[i])) return 1;
        if (slots[i].scale <= 0 || slots[i].scale > 1) return 2;
        if (slots[i].x < 0 || slots[i].y < 0 || slots[i].x + 832 * slots[i].scale > 1920 || slots[i].y + 664 * slots[i].scale > 1048) return 3;
        for (unsigned int j = 0; j < i; j++) {
            if (slots[i].x < slots[j].x + 832 * slots[j].scale && slots[j].x < slots[i].x + 832 * slots[i].scale && slots[i].y < slots[j].y + 664 * slots[j].scale && slots[j].y < slots[i].y + 664 * slots[i].scale) return 4;
        }
    }
    if (weston_test_grid_calculate(0, 100, 832, 664, 2, 0, &slots[0])) return 5;
    if (weston_test_grid_calculate(1920, 1048, 0, 664, 2, 0, &slots[0])) return 6;
    struct weston_test_grid_place repeat;
    if (!weston_test_grid_calculate(1920, 1048, 832, 664, 2, 8, &repeat)) return 7;
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


@pytest.mark.parametrize("rows", [3, 4])
def test_grid_rows_geometry(tmp_path, rows):
    header = Path(__file__).parents[1] / "upstream/desktop-shell/test-grid.h"
    main = r'''
int main(void) {
    struct weston_test_grid_place slots[4 * ROWS];
    for (unsigned int i = 0; i < 4 * ROWS; i++) {
        if (!weston_test_grid_calculate(1920, 1048, 832, 664, ROWS, i, &slots[i])) return 1;
        if (slots[i].scale <= 0 || slots[i].scale > 1) return 2;
        if (slots[i].x < 0 || slots[i].y < 0 || slots[i].x + 832 * slots[i].scale > 1920 || slots[i].y + 664 * slots[i].scale > 1048) return 3;
        for (unsigned int j = 0; j < i; j++) {
            if (slots[i].x < slots[j].x + 832 * slots[j].scale && slots[j].x < slots[i].x + 832 * slots[i].scale && slots[i].y < slots[j].y + 664 * slots[j].scale && slots[j].y < slots[i].y + 664 * slots[i].scale) return 4;
        }
    }
    struct weston_test_grid_place repeat;
    if (!weston_test_grid_calculate(1920, 1048, 832, 664, ROWS, 4 * ROWS, &repeat)) return 5;
    if (repeat.x != slots[0].x || repeat.y != slots[0].y) return 6;
    if (weston_test_grid_calculate(1920, 1048, 832, 664, 5, 0, &repeat)) return 7;
    return 0;
}
'''
    path, binary = tmp_path / "grid12.c", tmp_path / "grid12"
    path.write_text(f"#define ROWS {rows}\n" + header.read_text(encoding="utf-8") + main, encoding="utf-8")
    def linux(p):
        value = p.resolve().as_posix()
        return "/mnt/" + value[0].lower() + value[2:]
    subprocess.run(["wsl.exe", "-d", "ubuntu20.04", "--", "gcc", linux(path), "-o", linux(binary)], check=True, capture_output=True)
    result = subprocess.run(["wsl.exe", "-d", "ubuntu20.04", "--", linux(binary)], capture_output=True)
    assert result.returncode == 0, f"{4 * rows} slot grid geometry failed: {result.returncode}"
