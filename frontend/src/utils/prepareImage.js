// Images are sent to the server as base64 inside a JSON request, which Django caps
// at 2.5 MB. Base64 adds about a third, so keep the raw image under ~1.5 MB.
const MAX_IMAGE_BYTES = 1.5 * 1024 * 1024;
const MAX_DIMENSION = 1600;
const SUPPORTED_TYPES = ['image/png', 'image/jpeg', 'image/gif'];

const readAsBase64 = (blob) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });

const loadImage = (file) =>
  new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('This image format is not supported. Try a PNG or JPEG.'));
    };
    img.src = url;
  });

const canvasToJpeg = (canvas, quality) =>
  new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));

// Re-encode as a JPEG no larger than MAX_DIMENSION on its longest side
const compressToJpeg = async (file) => {
  const img = await loadImage(file);
  const scale = Math.min(1, MAX_DIMENSION / Math.max(img.width, img.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(img.width * scale);
  canvas.height = Math.round(img.height * scale);
  const context = canvas.getContext('2d');
  // JPEG has no transparency, so give transparent PNGs a white background
  context.fillStyle = '#fff';
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(img, 0, 0, canvas.width, canvas.height);

  for (const quality of [0.85, 0.7, 0.55]) {
    const blob = await canvasToJpeg(canvas, quality);
    if (blob && blob.size <= MAX_IMAGE_BYTES) {
      return blob;
    }
  }
  throw new Error('This image is too large to post. Try a smaller image.');
};

// Returns { content, contentType } ready to send as an image post
export const prepareImageForPost = async (file) => {
  if (SUPPORTED_TYPES.includes(file.type) && file.size <= MAX_IMAGE_BYTES) {
    return {
      content: await readAsBase64(file),
      contentType: `${file.type};base64`,
    };
  }

  if (file.type === 'image/gif') {
    // compressing would drop the animation
    throw new Error('GIFs must be 1.5 MB or smaller.');
  }

  const jpeg = await compressToJpeg(file);
  return {
    content: await readAsBase64(jpeg),
    contentType: 'image/jpeg;base64',
  };
};
