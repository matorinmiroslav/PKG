import math

def rgb_to_cmyk(r: int, g: int, b: int) -> tuple[float, float, float, float]:
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    k = 1.0 - max(r_n, g_n, b_n)
    if k == 1.0:
        return 0.0, 0.0, 0.0, 100.0
    c = (1.0 - r_n - k) / (1.0 - k) * 100.0
    m = (1.0 - g_n - k) / (1.0 - k) * 100.0
    y = (1.0 - b_n - k) / (1.0 - k) * 100.0
    return c, m, y, k * 100.0


def cmyk_to_rgb(c: float, m: float, y: float, k: float) -> tuple[int, int, int]:
    c_n, m_n, y_n, k_n = c / 100.0, m / 100.0, y / 100.0, k / 100.0
    r = int(round(255.0 * (1.0 - c_n) * (1.0 - k_n)))
    g = int(round(255.0 * (1.0 - m_n) * (1.0 - k_n)))
    b = int(round(255.0 * (1.0 - y_n) * (1.0 - k_n)))
    return clamp_rgb(r, g, b)[0]


def rgb_to_xyz(r: int, g: int, b: int) -> tuple[float, float, float]:
    def pivot(v):
        v /= 255.0
        return ((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92

    r_l, g_l, b_l = pivot(r), pivot(g), pivot(b)

    x = (r_l * 0.4124564 + g_l * 0.3575761 + b_l * 0.1804375) * 100.0
    y = (r_l * 0.2126729 + g_l * 0.7151522 + b_l * 0.0721750) * 100.0
    z = (r_l * 0.0193339 + g_l * 0.1191920 + b_l * 0.9503041) * 100.0
    return x, y, z


def xyz_to_lab(x: float, y: float, z: float) -> tuple[float, float, float]:
    ref_x, ref_y, ref_z = 95.047, 100.000, 108.883

    def pivot(v):
        return v ** (1.0 / 3.0) if v > 0.008856 else (7.787 * v) + (16.0 / 116.0)

    fx = pivot(x / ref_x)
    fy = pivot(y / ref_y)
    fz = pivot(z / ref_z)

    l = (116.0 * fy) - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return l, a, b


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    x, y, z = rgb_to_xyz(r, g, b)
    return xyz_to_lab(x, y, z)


def lab_to_xyz(l: float, a: float, b: float) -> tuple[float, float, float]:
    ref_x, ref_y, ref_z = 95.047, 100.000, 108.883

    fy = (l + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b / 200.0

    def pivot(v):
        v3 = v ** 3
        return v3 if v3 > 0.008856 else (v - 16.0 / 116.0) / 7.787

    x = ref_x * pivot(fx)
    y = ref_y * pivot(fy)
    z = ref_z * pivot(fz)
    return x, y, z


def xyz_to_rgb(x: float, y: float, z: float) -> tuple[tuple[int, int, int], bool]:
    x_n, y_n, z_n = x / 100.0, y / 100.0, z / 100.0

    r_l = x_n * 3.2404542 + y_n * -1.5371385 + z_n * -0.4985314
    g_l = x_n * -0.9692660 + y_n * 1.8760108 + z_n * 0.0415560
    b_l = x_n * 0.0556434 + y_n * -0.2040259 + z_n * 1.0572252

    def gamma(v):
        return (1.055 * (v ** (1.0 / 2.4)) - 0.055) if v > 0.0031308 else (12.92 * v)

    r = gamma(r_l) * 255.0
    g = gamma(g_l) * 255.0
    b = gamma(b_l) * 255.0

    out_of_gamut = not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255)
    clamped_rgb, _ = clamp_rgb(int(round(r)), int(round(g)), int(round(b)))
    return clamped_rgb, out_of_gamut


def lab_to_rgb(l: float, a: float, b: float) -> tuple[tuple[int, int, int], bool]:
    x, y, z = lab_to_xyz(l, a, b)
    return xyz_to_rgb(x, y, z)


def clamp_rgb(r: int, g: int, b: int) -> tuple[tuple[int, int, int], bool]:
    c_r = max(0, min(255, r))
    c_g = max(0, min(255, g))
    c_b = max(0, min(255, b))
    clipped = (c_r != r) or (c_g != g) or (c_b != b)
    return (c_r, c_g, c_b), clipped