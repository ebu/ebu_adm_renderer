import numpy as np
from . import bs2051, point_source, layout


def plot_triplet(tri, ax, color=None):
    import matplotlib.colors as colors
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    tri = Poly3DCollection([tri.positions])

    if color is None:
        color = colors.rgb2hex(np.random.rand(3))

    tri.set_color(color)
    tri.set_edgecolor('k')
    ax.add_collection3d(tri)


def plot_virtual_ngon(ngon, ax):
    import matplotlib.colors as colors

    color = colors.rgb2hex(np.random.rand(3))
    for tri in ngon.regions:
        plot_triplet(tri, ax, color)


def plot_quad(quad, ax):
    import matplotlib.colors as colors
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    quad_poly = Poly3DCollection([quad.positions[quad.order]])

    color = colors.rgb2hex(np.random.rand(3))

    quad_poly.set_color(color)
    quad_poly.set_edgecolor('k')
    ax.add_collection3d(quad_poly)


def plot_stereo_pan(stereo, ax):
    from mpl_toolkits.mplot3d.art3d import Line3DCollection

    line = Line3DCollection(np.array([[[1, 0, 0], [-1, 0, 0]]]))
    line.set_edgecolor('k')
    ax.add_collection3d(line)


plot_by_type = {
    point_source.Triplet: plot_triplet,
    point_source.VirtualNgon: plot_virtual_ngon,
    point_source.QuadRegion: plot_quad,
    point_source.StereoPanDownmix: plot_stereo_pan,
}


def plot_triangulation(point_source_panner):
    import matplotlib.pyplot as plt
    import mpl_toolkits.mplot3d.art3d  # noqa

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d', aspect=1)

    if isinstance(point_source_panner, point_source.PointSourcePannerDownmix):
        point_source_panner = point_source_panner.psp

    for region in point_source_panner.regions:
        if type(region) in plot_by_type:
            plot_by_type[type(region)](region, ax)

    ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_zlim(-1, 1)
    ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")

    return fig, ax


def show_triangulation(point_source_panner):
    import matplotlib.pyplot as plt
    plot_triangulation(point_source_panner)
    plt.show()


def get_arg_parser():
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Plot point source configuration for a layout.")
    parser.add_argument("--layout", choices=bs2051.layout_names, required=True)
    parser.add_argument("--speakers", type=argparse.FileType('r'), metavar="speakers_file",
                        help="YAML format speakers file")
    parser.add_argument("--options", type=json.loads, default="{}", help="JSON-format configuration options.")  # noqa: P103
    try:
        import matplotlib
        parser.add_argument("--mpl_backend",
                            choices=matplotlib.rcsetup.interactive_bk, default="TkAgg",
                            help="matplotlib backend to use. default: %(default)s")
    except ImportError:
        parser.add_argument("--mpl_backend", default="TkAgg",
                            help="matplotlib backend to use (install matplotlib to seee choices; default: %(default)s).")

    return parser


def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    try:
        import matplotlib
    except ImportError:
        parser.error("matplotlib must be installed to use this program")

    matplotlib.use(args.mpl_backend)

    spkr_layout = bs2051.get_layout(args.layout)

    if args.speakers is not None:
        speakers = layout.load_speakers(args.speakers)
        spkr_layout, _upmix = spkr_layout.with_speakers(speakers)

    config = point_source.configure(spkr_layout.without_lfe, **args.options)
    show_triangulation(config)


if __name__ == "__main__":
    main()
