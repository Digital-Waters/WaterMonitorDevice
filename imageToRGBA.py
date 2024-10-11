from PIL import Image
import numpy as np

# Paths to the reference and target images
#imageReferencePath = '/mnt/data/image_2024-09-14_15-55-42.jpg'
#imageBrownWaterPath = '/mnt/data/image_2024-09-14_16-04-59.jpg'

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

# Function to calculate the water color difference between the reference image and the brown water image
def calculateWaterColorDifference(referenceImageData, targetImageData, mask):
    """
    Calculate the water color difference by masking the disk and comparing the masked areas
    between the reference image and the target image.
    """
    # Apply the mask to both images (to exclude the black and white disk)
    referenceWaterRegion = referenceImageData[mask]
    targetWaterRegion = targetImageData[mask]
    
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
    maxDifferenceMagnitude = 400  # Assume a maximum possible color difference magnitude
    alpha = min(255, (differenceMagnitude / maxDifferenceMagnitude) * 255)
    
    return int(alpha)

# Main function to get RGBA value from the image comparison
def getRgbaFromImage(waterPhotoPath, referencePhotoPath):
    # Load the reference and target images
    try:
        imageReference = Image.open(referencePhotoPath)
        imageColoredWater = Image.open(waterPhotoPath)
    except Exception as e:
        return "getRGBA Error: referenceImage.jpg doesn't exist"

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
        # Calculate the color difference between the reference image (clear water) and the brown water image
        waterColorDifference = calculateWaterColorDifference(imageReferenceData, imageColoredWaterData, waterMaskColoredWater)

        # Calculate the alpha value for the brown water based on the color difference
        alphaValue = calculateAlpha(waterColorDifference)

    except Exception as e:
        return "getRGBA Error: Couldn't calculate RGBA"

    # Calculate the actual water color by adjusting the reference water color with the color difference
    actualWaterColor = imageReferenceData[waterMaskColoredWater].mean(axis=0) + waterColorDifference

    # Combine the RGB values with the alpha value to form RGBA
    rgbaWaterColor = np.append(actualWaterColor, alphaValue)

    return rgbaWaterColor