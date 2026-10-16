import http from "./http";

export function apiListProducts(params) {
  return http.get("/products", { params });
}

export function apiProductDetail(id) {
  return http.get(`/products/${id}`);
}

export function apiSearchProducts(params) {
  // 兼容旧用法：传字符串时当作 q
  if (typeof params === "string") {
    return http.get("/products/search", { params: { q: params } });
  }
  return http.get("/products/search", { params });
}

export function apiListCategories() {
  return http.get("/categories");
}

// TODO: 商品发布接口，待实现
export function apiPublishProduct(data) {
  return http.post("/products", data);
}

// TODO: 商品编辑接口，待实现
export function apiEditProduct(id, data) {
  return http.put(`/products/${id}`, data);
}

// TODO: 商品删除接口，待实现
export function apiDeleteProduct(id) {
  return http.delete(`/products/${id}`);
}
