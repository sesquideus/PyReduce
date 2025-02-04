# -*- coding: utf-8 -*-
"""
Combine several fits files into one master frame

Used to create master bias and master flat
"""

import datetime
import logging

import astropy.io.fits as fits
import matplotlib.pyplot as plt
import numpy as np

from pathlib import Path
from scipy.ndimage.filters import median_filter
from tqdm import tqdm

from .clipnflip import clipnflip
from .instruments.instrument_info import load_instrument
from .util import gaussbroad, gaussfit, remove_bias, ConfigurationError
from .instruments import Instrument
from . import colour as c

logger = logging.getLogger(__name__)


def running_median(arr: np.ndarray, size: int) -> np.ndarray:
    """Calculate the running median of a 2D sequence

    Parameters
    ----------
    arr : 2d array [n, l]
        n datasets of length l
    size : int
        number of elements to consider for each median
    Returns
    -------
    2d array [n, l-size]
        running median
    """

    ret = np.array([median_filter(s, size=size, mode="constant") for s in arr])
    m = size // 2
    return ret[:, m:-m]


def running_sum(arr: np.ndarray, size: int) -> np.ndarray:
    """Calculate the running sum over the 2D sequence

    Parameters
    ----------
    arr : array[n, l]
        sequence to calculate running sum over, n datasets of length l
    size : int
        number of elements to sum
    Returns
    -------
    2D array
        running sum
    """

    ret = np.cumsum(arr, axis=1)
    ret[:, size:] -= ret[:, :-size]
    return ret[:, size - 1:]


def calculate_probability(buffer: np.ndarray, window: int, method: str = "sum") -> np.ndarray:
    """
    Construct a probability function based on buffer data.

    Parameters
    ----------
    buffer : array of shape (nx, ny)
        buffer
    window : int
        size of the running window
    method : {"sum", "median"}, optional
        which method to use to average the probabilities (default: "sum")
        "sum" is much faster, but "median" is more resistant to outliers

    Returns
    -------
    weights : array of shape (nx, ny - 2 * window)
        probabilities
    """

    buffer = np.require(buffer, dtype=float)

    # Take the median/sum for each file
    match method:
        case "median":
            # Running median is slow
            weights = running_median(buffer, 2 * window + 1)
            sum_of_weights = np.mean(weights, axis=0)
        case "sum":
            # Running sum is fast
            weights = running_sum(buffer, 2 * window + 1)
            sum_of_weights = np.sum(weights, axis=0)
        case _:
            raise ValueError(f"Expected 'sum' or 'median', got {method}")

    # norm the probability
    np.divide(weights, sum_of_weights, where=sum_of_weights > 0, out=weights)
    return weights


def fix_bad_pixels(probability: np.ndarray[float],
                   buffer: np.ndarray[float],
                   readnoise: float,
                   gain: float,
                   threshold: float):
    """
    find and fix bad pixels

    Parameters
    ----------
    probability : array(float)
        probabilities
    buffer : array(int)
        image buffer
    readnoise : float
        readnoise of current amplifier
    gain : float
        gain of current amplifier
    threshold : float
        sigma threshold between observation and fit for bad pixels

    Returns
    -------
    array(int)
        input buffer, with bad pixels fixed
    """
    # Fit signal
    ratio = np.zeros_like(probability)
    np.divide(buffer, probability, where=probability > 0, out=ratio)
    # ratio = np.where(probability > 0, buffer / probability, 0.)
    amplitude = (np.sum(ratio, axis=0) - np.min(ratio, axis=0) - np.max(ratio, axis=0)) / (buffer.shape[0] - 2)

    fitted_signal = np.where(probability > 0, amplitude[None, :] * probability, 0)
    predicted_noise = np.zeros_like(fitted_signal)
    tmp = readnoise ** 2 + (fitted_signal / gain)
    np.sqrt(tmp, where=tmp >= 0, out=predicted_noise)

    # Identify outliers
    badpixels = buffer - fitted_signal > threshold * predicted_noise
    nbad = len(np.nonzero(badpixels.flat)[0])

    # Construct the summed flat
    corrected_signal = np.where(badpixels, fitted_signal, buffer)
    corrected_signal = np.sum(corrected_signal, axis=0)
    return corrected_signal, nbad


def combine_frames(files: list[Path],
                   instrument: Instrument,
                   mode: str,
                   extension: int = None,
                   threshold: float = 3.5,
                   window: int = 50,
                   dtype: np.dtype = np.float32,
                   **kwargs) -> (np.ndarray, fits.Header):
    """
    Subroutine to correct cosmic rays blemishes, while adding otherwise
    similar images.

    combine_frames co-adds a group of FITS files with 2D images of identical dimensions.
    In the process it rejects cosmic ray, detector defects etc. It is capable of
    handling images that have strip pattern (e.g. echelle spectra) using the REDUCE
    modinfo conventions to figure out image orientation and useful pixel ranges.
    It can handle many frames. Special cases: 1 file in the list (the input is returned as output)
    and 2 files (straight sum is returned).

    If the image orientation is not predominantly vertical, the image is rotated 90 degrees (and rotated back afterwards).

    Open all FITS files in the list.
    Loop through the rows. Read next row from each file into a row buffer mBuff[nCol, nFil].
    Optionally correct the data for non-linearity.

    calc_probability::

        Go through the row creating "probability" vector. That is for column iCol take the median of
        the part of the row mBuff[iCol-win:iCol+win,iFil] for each file and divide these medians by the
        mean of them computed across the stack of files. In other words:
        >>> filwt[iFil] = median(mBuff[iCol-win:iCol+win,iFil])
        >>> norm_filwt = mean(filwt)
        >>> prob[iCol,iFil] = (norm_filtwt > 0) ? filwt[iCol]/norm_filwt : filwt[iCol]

        This is done for all iCol in the range of [win:nCol-win-1]. It is then linearly extrapolated to
        the win zones of both ends. E.g. for iCol in [0:win-1] range:
        >>> prob[iCol,iFil]=2*prob[win,iFil]-prob[2*win-iCol,iFil]

        For the other end ([nCol-win:nCol-1]) it is similar:
        >>> prob[iCol,iFil]=2*prob[nCol-win-1,iFil]-prob[2*(nCol-win-1)-iCol,iFil]

    fix_bad_pixels::

        Once the probailities are constructed we can do the fitting, measure scatter and detect outliers.
        We ignore negative or zero probabilities as it should not happen. For each iCol with (some)
        positive probabilities we compute tha ratios of the original data to the probabilities and get
        the mean amplitude of these ratios after rejecting extreme values:
        >>> ratio = mBuff[iCol,iFil]/prob[iCol,iFil]
        >>> amp = (total(ratio)-min(ratio)-max(ratio))/(nFil-2)
        >>> mFit[iCol,iFil] = amp*prob[iCol,iFil]

        Note that for iFil whereprob[iCol,iFil] is zero we simply set mFit to zero. The scatter (noise)
        consists readout noise and shot noise of the model (fit) co-added in quadratures:
        >>> sig=sqrt(rdnoise*rdnoise + abs(mFit[iCol,iFil]/gain))

        and the outliers are defined as:
        >>> iBad=where(mBuff-mFit gt thresh*sig)

        >>> # Bad values are replaced from the fit:
        >>> mBuff[iBad]=mFit[iBad]

        and mBuff is summed across the file dimension to create an output row.

    Parameters
    ----------
    files : list(str)
        list of fits files to combine
    instrument : str
        instrument id for modinfo
    mode : str
        instrument mode
    extension : int, optional
        fits extension to load (default: 1)
    threshold : float, optional
        threshold for bad pixels (default: 3.5)
    window : int, optional
        horizontal window size (default: 50)
    mask : array(bool), optional
        mask for the fits image (default: None)
    xr : int, optional
        xrange (default: None)
    yr : int, optional
        yrange (default: None)
    debug : bool, optional
        show debug plot of noise distribution (default: False)
    dtype : np.dtype, optional
        datatype of the combined image (default float32)

    Returns
    -------
    combined_data, header
        combined image data, header
    """

    assert isinstance(files, list), f"A list of files is expected as an input, got {type(files)}"
    assert isinstance(instrument, Instrument), "All instruments must be Instrument instances at this stage"

    logger.info(f"Combining frames for instrument {c.name(instrument.name)} in mode {c.name(mode)} for files:")
    for i, file in zip(range(len(files)), files):
        logger.info(f"\t{i}\t{c.path(file)}")

    DEBUG_NROWS = 128  # print status update every DEBUG_NROWS rows (if debug is True)

    # Only one image
    if len(files) == 0:
        raise ValueError(f"No files given for {c.name('combining frames')}")
    elif len(files) == 1:
        result, head = instrument.load_fits(files[0], mode, extension=extension, dtype=dtype, **kwargs)
        return result, head
    # Two images
    elif len(files) == 2:
        bias1, head1 = instrument.load_fits(files[0], mode, extension=extension, dtype=dtype, **kwargs)
        exp1 = head1.get("exptime", 0)

        bias2, head2 = instrument.load_fits(files[1], mode, extension=extension, dtype=dtype, **kwargs)
        exp2 = head2.get("exptime", 0)
        readnoise = head2.get("e_readn", 0)

        result = bias2 + bias1
        head = head2

        total_exposure_time = exp1 + exp2
        readnoise = np.atleast_1d(readnoise)
        n_fixed = 0
        linear = head.get("e_linear", True)
    # More than two images
    else:
        # Get information from headers
        # TODO: check if all values are the same in all the headers?

        headers = [
            instrument.load_fits(f, mode, extension=extension, header_only=True, dtype=dtype, **kwargs)
            for f in files
        ]
        _, head = headers[0]

        # if sizes vary, it will show during loading of the data
        n_columns = head["naxis1"]
        n_rows = head["naxis2"]

        # check if we deal with multiple amplifiers
        n_amplifier = head.get("e_ampl", 1)
        # check orientation of the image
        # orient 0, 2, 5, 7: orders are horizontal
        # orient 1, 3, 4, 6: orders are vertical
        orientation = head["e_orient"]
        transpose = head.get("e_transpose", False)
        orientation = orientation % 8
        # check if non-linearity correction
        linear = head.get("e_linear", True)

        # section(s) of the detector to process, x_low, x_high, y_low, y_high
        # head["e_xlo*"] will find all entries with * as a wildcard
        # we also ensure that we will have one dimensional arrays (not just the value)
        cards = sorted(head["e_xlo*"].cards, key=lambda c: c[0])
        x_low = [card[1] for card in cards]
        cards = sorted(head["e_xhi*"].cards, key=lambda c: c[0])
        x_high = [card[1] for card in cards]
        cards = sorted(head["e_ylo*"].cards, key=lambda c: c[0])
        y_low = [card[1] for card in cards]
        cards = sorted(head["e_yhi*"].cards, key=lambda c: c[0])
        y_high = [card[1] for card in cards]

        cards = sorted(head["e_gain*"].cards, key=lambda c: c[0])
        gain = [card[1] for card in cards]
        cards = sorted(head["e_readn*"].cards, key=lambda c: c[0])
        readnoise = [card[1] for card in cards]
        total_exposure_time = sum(h.get("exptime", 0) for _, h in headers)

        # Scaling for image data
        bscale = [h.get("bscale", 1) for _, h in headers]
        bzero = [h.get("bzero", 0) for _, h in headers]

        result = np.zeros((n_rows, n_columns), dtype=dtype)  # the combined image
        n_fixed = 0  # number of fixed pixels

        # Load all image hdus, but leave the data on the disk, using memmap
        # Need to scale data later
        if extension is None:
            extension = [instrument.get_extension(h, mode) for h in headers]
        else:
            extension = [extension] * len(headers)

        data = [
            fits.open(f, memmap=True, do_not_scale_image_data=True)[e]
            for f, e in zip(files, extension)
        ]

        if window >= n_columns / 2:
            window = n_columns // 10
            logger.warning("Reduce Window size to fit the image")

        # depending on the orientation the indexing changes and the borders of the image change
        if orientation in [1, 3, 4, 6]:
            # idx gives the index for accessing the data in the image, which is rotated depending on the orientation
            # We could just rotate the whole image, but that requires reading the whole image at once
            index = lambda row, x_left, x_right: (slice(x_left, x_right), row)
            # Exchange the borders of the image
            x_low, x_high, y_low, y_high = y_low, y_high, x_low, x_high
        else:
            index = lambda row, x_left, x_right: (row, slice(x_left, x_right))

        # For several amplifiers, different sections of the image are set
        # One for each amplifier, each amplifier is treated seperately
        for amplifier in range(n_amplifier):
            # Pick data for current amplifier
            x_left = x_low[amplifier]
            x_right = x_high[amplifier]
            y_bottom = y_low[amplifier]
            y_top = y_high[amplifier]

            gain_amp = gain[amplifier]
            readnoise_amp = readnoise[amplifier]

            # Prepare temporary arrays
            buffer = np.zeros((len(files), x_right - x_left))
            probability = np.zeros((len(files), x_right - x_left))

            # for each row
            for row in tqdm(range(y_bottom, y_top), desc="Rows"):
                if row % DEBUG_NROWS == 0:
                    logger.trace(f"{c.num(f'{row:5d}')} rows processed - {c.num(f'{n_fixed:6d}')} pixels fixed so far")

                # load current row
                idx = index(row, x_left, x_right)
                for i in range(len(files)):
                    # TODO: does memmap not work with compressed files?
                    buffer[i, :] = data[i].data[idx] * bscale[i] + bzero[i]

                # Calculate probabilities
                probability[:, window:-window] = calculate_probability(buffer, window)

                # extrapolate to edges
                probability[:, :window] = (
                        2 * probability[:, window][:, None]
                        - probability[:, 2 * window: window: -1]
                )
                probability[:, -window:] = (
                        2 * probability[:, -window - 1][:, None]
                        - probability[:, -window - 1: -2 * window - 1: -1]
                )

                # fix bad pixels
                result[idx], n_bad = fix_bad_pixels(
                    probability, buffer, readnoise_amp, gain_amp, threshold
                )
                n_fixed += n_bad

        logger.debug("total cosmic ray hits identified and removed: %i", n_fixed)

        result = clipnflip(result, head)
        result = np.ma.masked_array(result, mask=kwargs.get("mask"))

    # Add info to header.
    head["bzero"] = 0.0
    head["bscale"] = 1.0
    head["exptime"] = total_exposure_time
    head["darktime"] = total_exposure_time
    # Because we do not divide the signal by the number of files the
    # read-out noise goes up by the square root of the number of files

    for n_amp, rdn in enumerate(readnoise):
        head["rdnoise{:0>1}".format(n_amp + 1)] = (
            rdn * np.sqrt(len(files)),
            " noise in combined image, electrons",
        )

    head["nimages"] = (len(files), " number of images summed")
    head["npixfix"] = (n_fixed, " pixels corrected for cosmic rays")
    head.add_history(
        "images coadded by combine_frames.py on %s" % datetime.datetime.now()
    )

    if not linear:  # pragma: no cover
        # non-linearity was fixed. mark this in the header
        raise NotImplementedError()  # TODO Nonlinear
        # i = np.where(head["e_linear"] >= 0)
        # head[i] = np.array((head[0 : i - 1 + 1], head[i + 1 :]))
        # head["e_linear"] = ("t", " image corrected of non-linearity")

        # ii = np.where(head["e_gain*"] >= 0)
        # if len(ii[0]) > 0:
        #     for i in range(len(ii[0])):
        #         k = ii[i]
        #         head = np.array((head[0 : k - 1 + 1], head[k + 1 :]))
        # head["e_gain"] = (1, " image was converted to e-")

    return result, head


def combine_calibrate(files: list[Path],
                      instrument: Instrument,
                      mode: str,
                      mask: np.ndarray | None = None,
                      bias: np.ndarray | None = None,
                      bhead=None,
                      norm=None,
                      *,
                      bias_scaling: str = "exposure_time",
                      norm_scaling: str = "divide",
                      plot: bool = False,
                      plot_title: str = None,
                      **kwargs):
    """
    Combine the input files and then calibrate the image with the bias
    and normalized flat field if provided

    Parameters
    ----------
    files : list
        list of file names to load
    instrument : Instrument
        PyReduce instrument object with load_fits method
    mode : str
        descriptor of the instrument mode
    mask : array
        2D Bad Pixel Mask to apply to the master image
    bias : tuple(bias, bhead), optional
        # ToDo: this is probably in fact just a np.ndarray
        bias correction to apply to the combiend image, if bias has 3 dimensions
        it is used as polynomial coefficients scaling with the exposure time, by default None
    bias_scaling : str, optional
        defines how the bias is subtracted, by default "exposure_time"
    norm_scaling : tuple(norm, blaze), optional
        normalized flat to divide the combined image with after
        the bias subtraction, by default None
    plot : bool, optional
        whether to plot the results, by default False
    plot_title : str, optional
        Name to put on the plot, by default None

    Returns
    -------
    orig : array
        combined image with calibrations applied
    thead : fits.Header
        header of the combined image

    Raises
    ------
    ValueError
        Unrecognised bias_scaling option
    """
    logger.debug(f"Running {c.name(combine_calibrate.__qualname__)} for instrument {c.name(instrument.name)} "
                 f"on data {c.print_list(files, lambda x: c.path(str(x)))}")

    # Combine the images and try to remove bad pixels
    orig, thead = combine_frames(files, instrument, mode, mask=mask, **kwargs)

    # Subtract bias
    if bias is not None and bias_scaling is not None and bias_scaling != "none":
        if bias.ndim == 2:
            degree = 0
            if bhead["exptime"] == 0 and bias_scaling == "exposure_time":
                logger.warning("No exposure time set in bias, using number of files instead")
                bias_scaling = "number_of_files"
            match bias_scaling:
                case "exposure_time":
                    orig -= bias * thead["exptime"] / bhead["exptime"]
                case "number_of_files":
                    orig -= bias * len(files)
                case "mean":
                    orig -= bias * np.ma.mean(orig) / np.ma.mean(bias)
                case "median":
                    orig -= bias * np.ma.median(orig) / np.ma.median(bias)
                case "none":
                    pass
                case _:
                    raise ValueError("Unexpected value for 'bias_scaling', expected one of "
                                     "['exposure_time', 'number_of_files', 'mean', 'median', 'none'], "
                                     f"but got {bias_scaling}")
        else:
            degree = bias.shape[0]
            if bias_scaling == "exposure_time":
                orig -= np.polyval(bias, thead["exptime"])
            # elif bias_scaling == "number_of_files":
            #     flat -= bias * len(files)
            # elif bias_scaling == "mean":
            #     flat -= bias * np.ma.mean(flat) / np.ma.mean(bias)
            # elif bias_scaling == "median":
            #     flat -= bias * np.ma.median(flat) / np.ma.median(bias)
            # ToDo maybe these here should be enabled as well
            else:
                raise ValueError("Unexpected value for 'bias_scaling', expected one of "
                                 f"['exposure_time'], but got {bias_scaling}")

    # Remove the Flat
    if norm is not None and norm_scaling != "none":
        if norm_scaling == "divide":
            orig /= norm
        else:
            raise ValueError(f"Unexpected value for 'norm_scaling', expected one of "
                             f"['divide', 'none'], but got {norm_scaling}")

    if plot:  # pragma: no cover
        title = "Master"
        if plot_title is not None:
            title = f"{plot_title}\n{title}"
        plt.title(title)
        plt.xlabel("x [pixel]")
        plt.ylabel("y [pixel]")
        bot, top = np.percentile(orig[orig != 0], (10, 90))
        plt.imshow(orig, vmin=bot, vmax=top, origin="lower")
        if plot != "png":
            plt.savefig("crires_master_flat.png")
        else:
            plt.show()

    return orig, thead


def combine_polynomial(files: list[Path],
                       instrument: Instrument,
                       mode: str,
                       *,
                       mask: np.ndarray[bool],
                       degree: int = 1,
                       plot: bool = False,
                       plot_title: str = None,
                       plot_cmap: str = 'viridis'):
    """
    Combine the input files by fitting a polynomial of the pixel value versus
    the exposure time of each pixel

    Parameters
    ----------
    files : list
        list of file names
    instrument : Instrument
        PyReduce instrument object with load_fits method
    mode : str
        mode identifier for this instrument
    mask : array
        bad pixel mask to apply to the coefficients
    degree : int, optional
        polynomial degree of the fit, by default 1
    plot : bool, optional
        whether to plot the results, by default False
    plot_title : str, optional
        Title of the plot, by default None
    plot_cmap : str, optional
        Colormap to use in the plot

    Returns
    -------
    bias : array
        3d array with the coefficients for each pixel
    bhead : Header
        combined FITS header of the coefficients
    """
    assert isinstance(instrument, Instrument), "The instrument must be an Instrument object"

    hdus = [instrument.load_fits(f, mode) for f in tqdm(files)]
    data = np.array([h[0] for h in hdus])
    exptimes = np.array([h[1]["EXPTIME"] for h in hdus])
    # Numpy polyfit can fit all polynomials at the same time,
    # but we need to flatten the pixels into 1 dimension
    data_flat = data.reshape((len(exptimes), -1))
    coeffs = np.polyfit(exptimes, data_flat, degree)
    # Afterwards we reshape the coefficients into the image shape
    shape = (degree + 1, data.shape[1], data.shape[2])
    coeffs = coeffs.reshape(shape)
    # And apply the mask to each image of coefficients
    if mask is not None:
        bias = np.ma.masked_array(coeffs, mask=[mask for _ in range(degree + 1)])
    # We arbitralily pick the first header as the bias header
    # and change the exposure time
    bhead = hdus[0][1]
    bhead["EXPTIME"] = np.sum(exptimes)

    if plot:
        title = "Master"
        if plot_title is not None:
            title = f"{plot_title}\n{title}"

        for i in range(degree + 1):
            plt.subplot(1, degree + 1, i + 1)
            plt.title("Coefficient %i" % (degree - i))
            plt.xlabel("x [pixel]")
            plt.ylabel("y [pixel]")
            bot, top = np.percentile(bias[i], (10, 90))
            plt.imshow(bias[i], vmin=bot, vmax=top, origin="lower", cmap=plot_cmap)

        plt.suptitle(title)
        if plot != "png":
            plt.show()
        else:
            plt.savefig("master_bias.png")

    return bias, bhead


def combine_bias(files: list[Path],
                 instrument: Instrument,
                 mode: str,
                 extension: int | str = None,  # ToDo I guess only int makes sense...?
                 plot: bool = False,
                 plot_title: str = None,
                 science_observation_time=None,
                 debug: bool = False,
                 **kwargs):
    """
    Combine bias frames, determine read noise, reject bad pixels.
    Read noise calculation only valid if both lists yield similar noise.

    Parameters
    ----------
    files : list(str)
        bias files to combine
    instrument : str
        name of the instrument
    mode: str
        mode for modinfo
    extension : {int, str}, optional
        fits extension to use (default: 1)
    xr : 2-tuple(int), optional
        x range to use (default: None, i.e. whole image)
    yr : 2-tuple(int), optional
        y range to use (default: None, i.e. whole image)
    dtype : np.dtype, optional
        datatype of the combined bias frame (default: float32)
    Returns
    -------
    bias, bhead
        bias image and header
    """
    logger.debug(f"Combining bias from {len(files)} files")

    n = len(files)
    if n == 0:
        raise ConfigurationError("Cannot combine bias: no bias file(s) given")
    elif n == 1:
        # if there is just one element compare it with itself, not really useful, but it works
        list1 = list2 = files
        n = 2
    else:
        list1, list2 = files[: n // 2], files[n // 2:]

    # Lists of images.
    n1 = len(list1)
    n2 = len(list2)

    # Separately images in two groups.
    bias1, head1 = combine_frames(list1, instrument, mode, extension, **kwargs)
    bias1 /= n1

    bias2, head = combine_frames(list2, instrument, mode, extension, **kwargs)
    bias2 /= n2

    # Make sure we know the gain.
    gain = head.get("e_gain*", (1,))[0]

    # Construct normalized sum.
    bias = (bias1 * n1 + bias2 * n2) / n
    exptime_1 = head1.get("exptime", 0)
    exptime_2 = head.get("exptime", 0)
    head["exptime"] = (exptime_1 + exptime_2) / n

    # Compute noise in difference image by fitting Gaussian to distribution.
    diff = 0.5 * (bias1 - bias2)
    if np.min(diff) != np.max(diff):
        crude = np.ma.median(np.abs(diff))  # estimate of noise
        hmin = -5.0 * crude
        hmax = +5.0 * crude
        bin_size = np.clip(2 / n, 0.5, None)
        nbins = int((hmax - hmin) / bin_size)

        h, _ = np.histogram(diff, range=(hmin, hmax), bins=nbins)
        xh = hmin + bin_size * (np.arange(0.0, nbins) + 0.5)

        hfit, par = gaussfit(xh, h)
        noise = abs(par[2])  # noise in diff, bias

        # Determine where wings of distribution become significantly non-Gaussian.
        contam = (h - hfit) / np.sqrt(np.clip(hfit, 1, None))
        imid = np.where(abs(xh) < 2 * noise)
        consig = np.std(contam[imid])

        smcontam = gaussbroad(xh, contam, 0.1 * noise)
        igood = np.where(smcontam < 3 * consig)
        gmin = np.min(xh[igood])
        gmax = np.max(xh[igood])

        # Find and fix bad pixels.
        ibad = np.where((diff <= gmin) | (diff >= gmax))
        nbad = len(ibad[0])

        bias[ibad] = np.clip(bias1[ibad], None, bias2[ibad])

        # Compute read noise.
        biasnoise = gain * noise
        bgnoise = biasnoise * np.sqrt(n)

        # Print diagnostics.
        logger.debug(f"Change in bias between image sets = {c.num(gain * par[1])} electrons")
        logger.debug(f"Measured background noise per image = {c.num(bgnoise)}")
        logger.debug(f"Background noise in combined image = {c.num(biasnoise)}")
        logger.debug(f"Fixing {c.num(nbad)} bad pixels")

        if debug:  # pragma: no cover
            # Plot noise distribution.
            plt.subplot(211)
            plt.plot(xh, h)
            plt.plot(xh, hfit, c="r")
            plt.title("noise distribution")
            plt.axvline(gmin, c="b")
            plt.axvline(gmax, c="b")

            # Plot contamination estimation.
            plt.subplot(212)
            plt.plot(xh, contam)
            plt.plot(xh, smcontam, c="r")
            plt.axhline(3 * consig, c="b")
            plt.axvline(gmin, c="b")
            plt.axvline(gmax, c="b")
            plt.title("Contamination estimation")
            plt.show()
    else:
        diff = 0
        biasnoise = 1.0
        nbad = 0

    if plot:  # pragma: no cover
        title = "Master Bias"
        if plot_title is not None:
            title = f"{plot_title}\n{title}"
        plt.title(title)
        plt.xlabel("x [pixel]")
        plt.ylabel("y [pixel]")
        bot, top = np.percentile(bias, (1, 99))
        plt.imshow(bias, vmin=bot, vmax=top, origin="lower")
        plt.show()

    head["obslist"] = " ".join([f.name for f in files])
    head["nimages"] = (n, "number of images summed")
    head["npixfix"] = (nbad, "pixels corrected for cosmic rays")
    head["bgnoise"] = (biasnoise, "noise in combined image, electrons")
    return bias, head
