from PIL import Image
import numpy as np
import io

IMG_SIZE = (224, 224)

def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(IMG_SIZE)
    img_array = np.expand_dims((np.array(img)/127.5)-1.0, axis=0)  # scale [-1,1]
    return img_array
