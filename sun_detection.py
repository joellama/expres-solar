import cv2
from astropy.io import fits 

def find_disk(img, threshold=1500):
    """Finds the center and radius of a single solar disk present in the supplied image.

    Uses cv2.inRange, cv2.findContours and cv2.minEnclosingCircle to determine the centre and 
    radius of the solar disk present in the supplied image.

    Args:
        img (numpy.ndarray): greyscale image containing a solar disk against a background that is below `threshold`.
        threshold (int): threshold of min pixel value to consider as part of the solar disk

    Returns:
        tuple: center coordinates in x,y form (int) 
        int: radius
    """
    if img is None:
        raise TypeError("img argument is None - check that the path of the loaded image is correct.")

    if len(img.shape) > 2:
        raise TypeError("Expected single channel (grayscale) image.")

    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    mask = cv2.inRange(blurred, threshold, 255)
    contours, img_mod = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Find and use the biggest contour
    r = 0
    for cnt in contours:
        (c_x, c_y), c_r = cv2.minEnclosingCircle(cnt)
        # cv2.circle(img, (round(c_x), round(c_y)), round(c_r), (255, 255, 255), 2)
        if c_r > r:
            x = c_x
            y = c_y
            r = c_r

    # print("Number of contours found: {}".format(len(contours)))
    # cv2.imwrite("mask.jpg", mask)
    # cv2.imwrite("circled_contours.jpg", img)

    if x is None:
        raise RuntimeError("No disks detected in the image.")

    return (round(x), round(y)), round(r)


if __name__ == "__main__":
    image = cv2.imread("test.jpg")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    center, radius = find_disk(img=gray, threshold=1000)

    print("circle x,y: {},{}".format(center[0], center[1]))
    print("circle radius: {}".format(radius))

    # Output the original image with the detected disk superimposed
    cv2.circle(image, center, radius, (0, 0, 255), 1)
    cv2.rectangle(image, (center[0] - 2, center[1] - 2), (center[0] + 2, center[1] + 2), (0, 0, 255), -1)
    cv2.imwrite("disk_superimposed.jpg", image)