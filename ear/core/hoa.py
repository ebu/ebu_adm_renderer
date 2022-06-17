from __future__ import division
import numpy as np
import scipy.special
from scipy.special import eval_legendre, legendre


def fact(n):
    """Exact factorial function."""
    return scipy.special.factorial(n, exact=True).astype(float)


def Alegendre(n, m, x):
    """Associated Legendre function P_n^m(x), ommitting the (-1)^m
    Condon-Shortley phase term."""
    return (-1.0)**m * scipy.special.lpmv(m, n, x)


def norm_N3D(n, abs_m):
    """N3D normalisation for order n and degree m."""
    return np.sqrt((2.0*n + 1.0) * fact(n-abs_m) / fact(n+abs_m))


def norm_SN3D(n, abs_m):
    """SN3D normalisation for order n and degree m."""
    return np.sqrt(fact(n-abs_m) / fact(n+abs_m))


def norm_FuMa(n, abs_m):
    """FuMa normalisation for order n and degree m."""
    if np.any(n > 3):
        raise ValueError("The FuMa normalization is only defined up to order 3, not {order}.".format(order=np.max(n)))

    convert = {(0, 0): 1/np.sqrt(2),
               (1, 0): 1,
               (1, 1): 1,
               (2, 0): 1,
               (2, 1): 2/np.sqrt(3),
               (2, 2): 2/np.sqrt(3),
               (3, 0): 1,
               (3, 1): np.sqrt(45/32),
               (3, 2): 3/np.sqrt(5),
               (3, 3): np.sqrt(8/5)}
    conv_factor = np.apply_along_axis(lambda a: convert[tuple(a)],
                                      0, [n, abs_m])

    return norm_SN3D(n, abs_m) * conv_factor


norm_functions = dict(
    FuMa=norm_FuMa,
    N3D=norm_N3D,
    SN3D=norm_SN3D,
)


def sph_harm(n, m, az, el, norm=norm_SN3D):
    """Spherical harmonic function Y_n^m(ax, el)."""
    n, m, az, el = np.broadcast_arrays(n, m, az, el)
    scale = np.ones_like(m, dtype=float)
    select = m > 0
    scale[select] = np.sqrt(2) * np.cos(m[select] * az[select])
    select = m < 0
    scale[select] = -np.sqrt(2) * np.sin(m[select] * az[select])

    # in the spec, this is cos(el), where elevation is measured downwards
    # from the top of the coordinate system; el here is from the centre.
    return norm(n, np.abs(m)) * Alegendre(n, np.abs(m), np.sin(el)) * scale


def to_acn(n, m):
    """Ambisonics Channel Number for order n and degree m."""
    return n*n + n + m


def from_acn(acn):
    """Get the order n and degree m from a given Ambisonics Channel Number."""
    n = np.sqrt(acn).astype(int)
    m = acn - n*n - n
    return n, m


def allrad_calc_G_virt(points, panning_func):
    """See allrad_design."""
    return np.apply_along_axis(panning_func, 1, points).T


def allrad_design(points, panning_func, n, m, norm=norm_SN3D, G_virt=None):
    """Decoder matrix design using the AllRAD[0] technique.

    Parameters:
        points (ndarray of (k, 3)): k virtual loudspeaker positions, from a
            spherical t-design
        panning_func (callable): function mapping from a cartesian position (as
            an ndarray of (3,)) to a vector of l loudspeaker gains (as an ndarray
            of (l,))
        n (ndarray of (c,) integers): order for each input channel
        m (ndarray of (c,) integers): degree for each input channel
        norm (calable): normalisation function passed to sph_harm
        G_virt: result of calling allrad_calc_G_virt(points, panning_func); can be
            used to speed up creating multiple designs with the same loudspeaker
            layout.

    Returns:
        ndarray of (l, c): decoder matrix

    [0] F. Zotter and M. Frank, "All-round ambisonic panning and decoding,"
    Journal of the audio engineering society, vol. 60, no. 10, pp. 807-820, 2012.
    http://www.aes.org/e-lib/browse.cfm?elib=16554
    """
    az = -np.arctan2(points[:, 0], points[:, 1])
    el = np.arctan2(points[:, 2], np.hypot(points[:, 0], points[:, 1]))

    Y_virt = sph_harm(n[:, np.newaxis], m[:, np.newaxis], az[np.newaxis], el[np.newaxis], norm=norm_N3D)

    D_virt = Y_virt.T / len(points)

    if G_virt is None:
        G_virt = allrad_calc_G_virt(points, panning_func)
    D = np.dot(G_virt, D_virt)

    # weight the resulting matrix by "Compensation" value to avoid the panning
    # error (Loss of energy introduced by the panning)
    D *= np.sqrt(len(points)) / np.linalg.norm(np.dot(D, Y_virt))

    D *= norm_N3D(n, np.abs(m)) / norm(n, np.abs(m))

    return D


def load_points(fname="data/Design_5200_100_random.dat"):
    """Load a spherical t-design from a file."""
    # see data/README.md
    import pkg_resources
    with pkg_resources.resource_stream(__name__, fname) as points_file:
        data = np.loadtxt(points_file)

    if data.shape[1] == 2:
        phi, theta = data.T
        return np.array([
            np.sin(theta) * np.cos(phi),
            np.sin(theta) * np.sin(phi),
            np.cos(theta),
        ]).T
    elif data.shape[1] == 3:
        return data
    else:
        assert False


def HankSph(n, kr):
    """Evaluate the spherical Hankel function for order n and vector kr"""
    return scipy.special.spherical_jn(n, kr) - 1j*scipy.special.spherical_yn(n, kr)


def F(n, kr):
    """Evaluate the filters used in the computation of the NFC filters for
    order n and vector kr
    """
    return 1j**(-n) * HankSph(n, kr) / HankSph(0, kr)


def H(n, r1, r2, k):
    """Evaluate the NFC filters for order n, reference distance r1, restitution
    distance r2, and vector k
    """
    return F(n, k * r1) / F(n, k * r2)


def FreqRespH(n, r1, r2, k):
    """Compute the "gain-less" NFC filter. Indeed, experience shows that the
    phase-only NFC filter provides better results.
    """
    h = H(n, r1, r2, k)
    return h / np.abs(h)


def WindowMethod(Filter, NbPointsFFT, NbPointsFilter):
    """Compute the Impulse Response of the filter "Filter" by computing its
    IFFT on NbPointsFFT points, and then apply a "NbPointsFilter" points Tukey
    window to reduce the filter length and avoid the Gibbs oscillations.
    """
    ImpResp = np.fft.irfft(Filter, NbPointsFFT)  # IFFT to compute the impulse response of the filter ("Filter" contains the frequency response)
    ImpRespShifted = np.fft.fftshift(ImpResp)  # We shift the impulse response to bring all the energy together
    # Window = tukey(NbPointsFilter) #Computation of the Tukey window
    # Multiplication of the window with the impulse response.
    ImpRespFinal = ImpRespShifted[len(ImpResp)//2-NbPointsFilter//2:len(ImpResp)//2+NbPointsFilter//2]  # *Window
    return ImpRespFinal


def MultipleImpResp(Orders, r1, r2, Fs):
    """Compute NFC filters for orders vector n, reference distance r1,
    restitution distance r2, and sampling frequency Fs.
    """
    NbPointsFilter = 1024  # After looking at several impulse response of NFC filters, we decided to only keep 1024 points.
    NbPointsFFT = 2**15
    # Sampling indices. The sampling do not begin at 0 because it causes issues dues to the limit of the filters in 0.
    x = np.concatenate(([1], np.linspace(1, Fs/2, NbPointsFFT//2)))
    k = 2*np.pi*x/340.0  # Computation of the wavenumber

    # Computation of the NFC filters for several orders contained in the n vector, weighted by a Tukey window.
    filter_for_order = np.array([WindowMethod(FreqRespH(order, r1, r2, k),
                                              NbPointsFFT, NbPointsFilter)
                                 for order in range(max(Orders) + 1)])
    return filter_for_order[Orders]


def MaxRECoefficients(Nmax):
    """rE computation (maximum zero of the Nmax+1 degree legendre polynomial)"""
    from scipy.optimize import fsolve
    t = np.arange(0.5, 1.0, 0.05)  # Sampling the interval [0.5,1]
    # Search the highest root of the N+1 degree legendre polynom in the interval [0.5,1]. This value is the highest rE reachable.
    rE = np.max(fsolve(legendre(Nmax+1), t))

    # The coefficient we need to apply to the n order HOA signals is just the n order legendre polynom evaluate at the value rE.
    return eval_legendre(np.arange(Nmax + 1), rE)


def ApproxMaxRECoefficients(Nmax):
    """Approximate maxRE coefficients for a given order, from [0].

    [0] Zotter, Franz, and Matthias Frank. "All-round ambisonic panning and
    decoding." Journal of the audio engineering society 60.10 (2012)
    """
    rE = np.cos(np.radians(137.9 / (Nmax + 1.51)))

    return eval_legendre(np.arange(Nmax + 1), rE)
