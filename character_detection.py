import numpy as np
import tensorflow as tf
import skimage.transform as ski
import PIL.Image as Image
from PIL import ImageDraw


def bad_image(i_p_a):

    # All white = bad
    if np.sum(i_p_a) == 255 * len(i_p_a):
        return True
    # If both two top or bottom rows of the image are white then this is an error
    if np.sum(i_p_a[:40]) >= 255*39 or np.sum(i_p_a[-41:]) >= 255*39:
        return True

    og_color = i_p_a[0]

    two_connected_sides_white = og_color == 255 and i_p_a[19] == 255 or \
                                og_color == 255 and i_p_a[-20] == 255 or \
                                i_p_a[19] == 255 and i_p_a[-1] == 255 or \
                                i_p_a[-20] == 255 and i_p_a[-1] == 255
    all_corners_white = og_color == 255 and i_p_a[19] == 255 and i_p_a[-20] == 255 and i_p_a[-1] == 255
    num_whites = np.sum(np.vectorize(lambda p: p == 255)(i_p_a))

    if num_whites > 200:
        return True

    if two_connected_sides_white and num_whites > 100 and not all_corners_white:
        return True

    return False


def close_similar_predictions(predictions, x, y, c):
    return (x + 1, y) in predictions.keys() and predictions[x + 1, y] == c or \
                 (x - 1, y) in predictions.keys() and predictions[x - 1, y] == c or \
                 (x, y + 1) in predictions.keys() and predictions[x, y + 1] == c or \
                 (x, y - 1) in predictions.keys() and predictions[x, y - 1] == c


def sliding_window(classifier, image, window_side_pixels=20, stride=1):
    predictions = dict()
    image_x, image_y = image.size


    ignore_to_x = False
    reset_y = 41

    # Based on the training images we ignore the outlying pixels
    for y in range(40, image_y-2*window_side_pixels, stride):
        for x in range(40, image_x-2*window_side_pixels, stride):

            # Flags to ignore if we have set a box already
            if ignore_to_x and ignore_to_x > x:
                if reset_y == y:
                    ignore_to_x = False
                else:
                    continue
            elif ignore_to_x:
                ignore_to_x = False

            # Extracts a window by using cropping, find logit-value of best as well as predicted character
            cropp = image.crop((x, y, x+window_side_pixels, y+window_side_pixels))
            cropped_image = np.reshape(cropp, window_side_pixels*window_side_pixels)

            # Check this box to see if should be classified
            if bad_image(cropped_image):
                continue

            # Make prediction from model and save logit-value as well as character predicted
            preds = classifier({"x": cropped_image})
            og_most_certain_logit = max(preds["logits"][0])
            og_character = chr(97 + np.argmax(preds["probabilities"]))

            # Check if above threshold for classification
            if og_most_certain_logit> 4000:

                # Test if any of the previous ones have been classified as something
                for i in range(1,6):
                    if (x,y-i) in predictions.keys():
                        continue

                ignore_to_x = x + 20
                reset_y = y+1
                predictions[(x, y)] = og_character

            else:
                best_mcl = 0
                best_char = None
                for i in range(1,4):
                    turned = cropp.rotate(i*90)
                    turned_vector = np.reshape(turned, window_side_pixels*window_side_pixels)
                    preds = classifier({"x": turned_vector})
                    most_certain_logit = max(preds["logits"][0])
                    character = chr(97+np.argmax(preds["probabilities"]))
                    if most_certain_logit > best_mcl:
                        best_mcl = most_certain_logit
                        best_char = character

                # Check if above threshold for classification
                if best_mcl > og_most_certain_logit and best_mcl > 4000:
                    for i in range(1, 6):
                        if (x, y - i) in predictions.keys():
                            continue
                    ignore_to_x = x + 20
                    reset_y = y + 1
                    predictions[(x,y)] = best_char

    # RGB so we can see the marked classifications
    rgb = Image.new("RGBA", image.size)
    rgb.paste(image)
    i = ImageDraw.Draw(rgb)

    # Only draw a box if there are several boxes in the same area agreeing with this classification
    for xy, c in predictions.items():
        x, y = xy
        #if close_similar_predictions(predictions, x, y, c):
        i.rectangle(xy=(xy[0], xy[1], xy[0]+window_side_pixels, xy[1]+window_side_pixels), outline="orange")
        # i.text(xy=(xy[0], xy[1]), text=c)
    rgb.show()
    return rgb


if __name__ == "__main__":

    image1 = Image.open("detection-images/detection-1.jpg")
    image2 = Image.open("detection-images/detection-2.jpg")

    predict_fn = tf.contrib.predictor.from_saved_model("savedmodels_3cnn_tweak/1525084475")

    print(sliding_window(
        classifier=predict_fn,
        image=image2,
        stride=1
    ))

    import datetime
    print(datetime.datetime.now())





