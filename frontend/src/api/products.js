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

export function apiRecognizeProduct(image) {
  const data = new FormData();
  data.append("image", image);
  return http.post("/ai/recognize", data);
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
