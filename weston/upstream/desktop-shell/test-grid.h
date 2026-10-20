#ifndef WESTON_TEST_GRID_H
#define WESTON_TEST_GRID_H

struct weston_test_grid_place {
    float x;
    float y;
    float scale;
};

/**
 * @brief 计算观察网格，不改变客户端渲染缓冲大小。
 * @details desktop-shell 首次映射 glmark2 时调用。工作区分成四列，
 *          每格保留八像素边距，完整窗口等比缩放后居中；不放大窗口。
 *          返回的位置相对工作区原点，调用者负责应用 view 变换。
 * @return 工作区或缓冲无效返回 0；成功返回 1 并填写位置和缩放比例。
 */
static inline int
weston_test_grid_calculate(int area_width, int area_height,
                          int width, int height, int rows, unsigned int slot,
                          struct weston_test_grid_place *place)
{
    float cell_width = area_width / 4.0f;
    float cell_height;
    float scale_x;
    float scale_y;

    if (!place || width <= 0 || height <= 0 || rows < 2 || rows > 4) {
        return 0;
    }
    cell_height = area_height / (float)rows;
    if (cell_width <= 16.0f || cell_height <= 16.0f) {
        return 0;
    }
    scale_x = (cell_width - 16.0f) / width;
    scale_y = (cell_height - 16.0f) / height;
    place->scale = scale_x < scale_y ? scale_x : scale_y;
    if (place->scale > 1.0f) {
        place->scale = 1.0f;
    }
    slot %= 4U * (unsigned int)rows;
    place->x = (slot % 4U) * cell_width +
               (cell_width - width * place->scale) / 2.0f;
    place->y = (slot / 4U) * cell_height +
               (cell_height - height * place->scale) / 2.0f;
    return 1;
}

#endif
