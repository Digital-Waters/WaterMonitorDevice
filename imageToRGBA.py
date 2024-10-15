from PIL import Image
import numpy as np

# Function to create a mask for disk detection
def maskSecchiDisk(imageData, blackThreshold=60, whiteThreshold=180):
    """
    Create a mask to detect the disk by finding black and white regions.
    The remaining areas are assumed to be water.
    """
    # Define thresholds for black and white regions
    blackMask = np.all(imageData < blackThreshold, axis=-1)
    whiteMask = np.all(imageData > whiteThreshold, axis=-1)

    # Combine black and white masks
    diskMask = blackMask | whiteMask

    return ~diskMask  # Invert mask to get the water region

# Function to calculate the water color difference between the reference image and the target image
def calculateWaterColorDifference(referenceWaterRegion, targetWaterRegion):
    """
    Calculate the water color difference by comparing the masked areas
    between the reference image and the target image.
    """
    # Calculate the difference between the two regions
    waterColorDifference = targetWaterRegion.mean(axis=0) - referenceWaterRegion.mean(axis=0)
    
    return waterColorDifference

# Function to calculate alpha (transparency) based on color difference magnitude
def calculateAlpha(waterColorDifference):
    """
    Calculate an alpha value based on the magnitude of the color difference.
    A larger difference will result in a more opaque color (higher alpha).
    """
    # Use the Euclidean distance (magnitude) of the color difference as a measure for alpha
    differenceMagnitude = np.linalg.norm(waterColorDifference)
    
    # Normalize the magnitude to fit within a range (0-255) for alpha
    maxDifferenceMagnitude = 442  # Maximum possible color difference magnitude in RGB space
    alpha = min(255, (differenceMagnitude / maxDifferenceMagnitude) * 255)
    
    return int(alpha)

# Main function to get RGBA value from the image comparison
def getRgbaFromImage(waterPhotoPath, referencePhotoPath):
    # Load the reference and target images
    try:
        imageReference = Image.open(referencePhotoPath)
        imageColoredWater = Image.open(waterPhotoPath)
    except Exception as e:
        return {"error": f"Error loading images: {e}"}

    # Convert both images to RGB
    imageReferenceRgb = imageReference.convert("RGB")
    imageColoredWaterRgb = imageColoredWater.convert("RGB")

    # Convert images to numpy arrays
    imageReferenceData = np.array(imageReferenceRgb)
    imageColoredWaterData = np.array(imageColoredWaterRgb)

    # Get water masks for both images
    waterMaskReference = maskSecchiDisk(imageReferenceData)
    waterMaskColoredWater = maskSecchiDisk(imageColoredWaterData)

    try: 
        # Get the water regions for both images
        referenceWaterRegion = imageReferenceData[waterMaskReference]
        targetWaterRegion = imageColoredWaterData[waterMaskColoredWater]

        # Calculate the color difference between the reference image and the target image
        waterColorDifference = calculateWaterColorDifference(referenceWaterRegion, targetWaterRegion)

        # Calculate the alpha value based on the color difference
        alphaValue = calculateAlpha(waterColorDifference)

    except Exception as e:
        return {"error": f"Error processing images: {e}"}

    # Use the mean color of the target water region as the actual water color
    actualWaterColor = targetWaterRegion.mean(axis=0)

    # Ensure the RGB values are valid integers between 0 and 255
    actualWaterColor = np.clip(actualWaterColor, 0, 255).astype(int)

    # Combine the RGB values with the alpha value to form RGBA
    rgbaWaterColor = {
        'r': int(actualWaterColor[0]),
        'g': int(actualWaterColor[1]),
        'b': int(actualWaterColor[2]),
        'a': alphaValue
    }

    return rgbaWaterColor
