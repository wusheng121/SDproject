import http from "./http";

export function apiListProducts(params) {
  return http.get("/products", { params });
}

export function apiProductDetail(id) {
  return http.get(`/products/${id}`);
}

export function apiSearchProducts(params) {
  if (typeof params === "string") {
    return http.get("/products/search", { params: { q: params } });
  }
  return http.get("/products/search", { params });
}

export function apiListCategories() {
  return http.get("/categories");
}

export function apiPublishProduct(data) {
  return http.post("/products", data);
}

export function apiUploadProductImage(image) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const raw = String(reader.result || "");
      const comma = raw.indexOf(",");
      http.post("/products/images", {
        image_base64: comma >= 0 ? raw.slice(comma + 1) : raw,
        mime: image.type || "image/jpeg"
      }, { timeout: 30000 }).then(resolve, reject);
    };
    reader.onerror = () => reject(reader.error || new Error("图片读取失败"));
    reader.readAsDataURL(image);
  });
}

export function apiFilterNl(text) {
  return http.post("/ai/filter/nl", { text });
}

export function apiRecognizeProduct(image) {
  const data = new FormData();
  data.append("image", image);
  return http.post("/ai/recognize", data, { timeout: 60000 });
}

export function apiRecognizeListing(image) {
  const data = new FormData();
  data.append("image", image);
  return http.post("/ai/listing-recognize", data, { timeout: 60000 });
}

export function apiGetPriceReference(params) {
  return http.get("/products/price-reference", { params });
}

export function apiEditProduct(id, data) {
  return http.put(`/products/${id}`, data);
}

export function apiDeleteProduct(id) {
  return http.delete(`/products/${id}`);
}

export function apiMyProducts() {
  return http.get("/v1/users/me/products");
}
