from PIL import Image
import numpy as np

# Ideal Secchi disk colors: the white half should read pure white and the black half
# pure black. How far each half's measured color drifts from that ideal is the signal -
# tint on the white half indicates dissolved color, brightening on the black half
# indicates suspended solids/turbidity. There's no per-device "clean water" reference
# photo, since every device runs the same disk/camera and collecting a calibration shot
# from customers in the field isn't practical.
BLACK_TARGET = np.array([0, 0, 0], dtype=float)
MAX_CHANNEL_DISTANCE = (3 * 255 ** 2) ** 0.5  # max possible Euclidean distance in RGB space

BORDER_TRIM_FRACTION = 0.08     # drop the outer vignette / tube-wall ring before clustering
EROSION_PIXELS_FRACTION = 0.02  # shrink each half away from the blurred black/white seam


def _trimBorder(imageData, fraction=BORDER_TRIM_FRACTION):
    height, width = imageData.shape[:2]
    marginY = int(height * fraction)
    marginX = int(width * fraction)
    return imageData[marginY:height - marginY, marginX:width - marginX]


def _otsuThreshold(luminance):
    """
    Find the luminance level that best splits the disk into its two halves. Used instead
    of a fixed brightness cutoff because disk rotation, fouling, and lighting all shift
    where "black" and "white" actually fall shot to shot.
    """
    histogram, _ = np.histogram(luminance, bins=256, range=(0, 256))
    histogram = histogram.astype(float)
    total = luminance.size

    sumAll = np.dot(np.arange(256), histogram)
    weightBackground = 0.0
    sumBackground = 0.0
    bestVariance = -1.0
    bestThreshold = 128

    for level in range(256):
        weightBackground += histogram[level]
        if weightBackground == 0:
            continue
        weightForeground = total - weightBackground
        if weightForeground == 0:
            break
        sumBackground += level * histogram[level]
        meanBackground = sumBackground / weightBackground
        meanForeground = (sumAll - sumBackground) / weightForeground
        betweenVariance = weightBackground * weightForeground * (meanBackground - meanForeground) ** 2
        if betweenVariance > bestVariance:
            bestVariance = betweenVariance
            bestThreshold = level

    return bestThreshold


def _erodeMask(mask, iterations):
    """Shrink a boolean mask inward by `iterations` pixels (4-connected)."""
    eroded = mask
    for _ in range(iterations):
        up = np.zeros_like(eroded); up[:-1, :] = eroded[1:, :]
        down = np.zeros_like(eroded); down[1:, :] = eroded[:-1, :]
        left = np.zeros_like(eroded); left[:, :-1] = eroded[:, 1:]
        right = np.zeros_like(eroded); right[:, 1:] = eroded[:, :-1]
        eroded = eroded & up & down & left & right
    return eroded


def splitDiskHalves(imageData):
    """
    Split a disk photo into its black-half and white-half pixels without assuming a
    fixed orientation (the disk's rotation varies shot to shot). Trims the outer frame
    and erodes both halves away from the blurred seam between them so neither cluster
    picks up the other's color. Either cluster (rarely both) can come back empty on a
    degenerate frame - callers fall back to whatever data is actually available.
    """
    analyzed = _trimBorder(imageData)
    luminance = analyzed.mean(axis=-1)

    threshold = _otsuThreshold(luminance)
    darkMask = luminance <= threshold
    lightMask = ~darkMask

    height, width = luminance.shape
    erosionPixels = max(3, int(min(height, width) * EROSION_PIXELS_FRACTION))
    darkMask = _erodeMask(darkMask, erosionPixels)
    lightMask = _erodeMask(lightMask, erosionPixels)

    return analyzed[darkMask], analyzed[lightMask], analyzed


def _turbidityAlpha(pixels):
    turbidity = float(np.linalg.norm(pixels.mean(axis=0) - BLACK_TARGET))
    return int(min(255, (turbidity / MAX_CHANNEL_DISTANCE) * 255))


# Main function to get RGBA value from the water photo. This is an approximation, not a
# confidence-gated measurement - it always returns its best-effort read of a photo, even
# when the black/white disk halves aren't clearly split. A separate confidence signal is
# planned as a later addition; until then a low-quality read is better than no read.
def getRgbaFromImage(waterPhotoPath):
    try:
        image = Image.open(waterPhotoPath).convert("RGB")
    except Exception as e:
        return {"error": f"Error loading image: {e}"}

    try:
        imageData = np.array(image)
        blackCluster, whiteCluster, analyzed = splitDiskHalves(imageData)
        flatAnalyzed = analyzed.reshape(-1, 3)

        hasBlack = len(blackCluster) > 0
        hasWhite = len(whiteCluster) > 0

        if hasWhite:
            # The white half's color is the color-drift signal (tint from dissolved color).
            waterColor = whiteCluster.mean(axis=0)
            # The black half's brightness is the turbidity signal (suspended solids
            # scatter light back into a surface that should otherwise read as black);
            # express it on the alpha channel, matching the original intent of alpha as
            # a magnitude signal. Falls back to the whole frame if there's no black
            # cluster to reference.
            alphaValue = _turbidityAlpha(blackCluster if hasBlack else flatAnalyzed)
        else:
            # No distinguishable light half at all - the frame reads as uniformly dark.
            # That's either total opacity/obstruction (e.g. storm blackwater) or a
            # camera/LED fault; the two look identical in pixels and can't be told apart.
            # Report the dark color directly (rather than fabricating a "white" reading
            # that isn't there) and treat it as a maximal, notable reading - missing a
            # real contamination spike is worse than occasionally mis-flagging a fault.
            waterColor = blackCluster.mean(axis=0) if hasBlack else flatAnalyzed.mean(axis=0)
            alphaValue = 255

    except Exception as e:
        return {"error": f"Error processing image: {e}"}

    return {
        'r': int(np.clip(waterColor[0], 0, 255)),
        'g': int(np.clip(waterColor[1], 0, 255)),
        'b': int(np.clip(waterColor[2], 0, 255)),
        'a': alphaValue
    }
