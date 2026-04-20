<template>
  <div class="map-page" :data-initial-loading="isInitialLoading ? '1' : '0'">
    <div ref="mapEl" class="leaflet-map" />

    <!-- 初次加载：地图区域居中 loading -->
    <div v-if="isInitialLoading" class="map-loading">
      <div class="loading-card">
        <div class="loading-spinner" />
        <div class="loading-text">正在加载地图数据…</div>
      </div>
    </div>

    <!-- 左侧固定浮层 -->
    <aside class="left-panel" @mousedown.stop @click.stop>
      <div class="panel-title">地图探索</div>

      <div class="panel-block">
        <div class="block-label">
          <span>年代范围</span>
          <span class="block-value">{{ yearRange[0] }}–{{ yearRange[1] }}</span>
        </div>
        <el-slider
          v-model="yearRange"
          range
          :min="1900"
          :max="2024"
          :step="1"
          :show-tooltip="false"
        />
        <div class="hint">拖动后将于 400ms 后刷新</div>
      </div>

      <div class="panel-block">
        <div class="block-label">
          <span>类型</span>
          <span v-if="isFetching" class="fetching-badge">更新中</span>
        </div>
        <div class="genre-tags">
          <button
            v-for="g in genreOptions"
            :key="g.value ?? 'all'"
            type="button"
            :class="['genre-tag', { active: selectedGenre === g.value }]"
            @click="onGenreClick(g.value)"
          >
            {{ g.label }}
          </button>
        </div>
      </div>

      <div class="panel-block performance-block">
        <div class="block-label">
          <span>渲染策略</span>
          <span class="performance-chip">性能模式</span>
        </div>
        <div class="hint">远景显示国家区域内的光晕粒子，近景切换为电影封面；缩放越近展示越密。</div>
        <div class="performance-meta">当前视野显示 {{ renderedCount }} / {{ stats.movieCount }} 个标记</div>
      </div>
    </aside>

    <!-- 右上角统计 -->
    <div class="top-right-stats" @mousedown.stop @click.stop>
      <div class="stats-line">
        当前 <span class="stats-strong">{{ stats.movieCount }}</span> 部影片 · 来自
        <span class="stats-strong">{{ stats.countryCount }}</span> 个国家
      </div>
      <div class="stats-subline">当前视野渲染 <span class="stats-strong">{{ renderedCount }}</span> 个地图标记</div>
    </div>

    <!-- 底部详情面板：点封面弹出，不跳走 -->
    <transition name="sheet">
      <div
        v-if="selectedMovie"
        class="sheet-backdrop"
        @click="closeSheet"
      >
        <section class="bottom-sheet" @click.stop>
          <button class="sheet-close" type="button" title="关闭" @click="closeSheet">×</button>

          <div class="sheet-content">
            <div class="sheet-poster">
              <img :src="selectedMovie.poster_url" :alt="selectedMovie.title" />
            </div>

            <div class="sheet-info">
              <div class="sheet-title">{{ selectedMovie.title }}</div>

              <div class="sheet-meta">
                {{ selectedMovie.country || 'Unknown' }}
                <span class="sep">·</span>
                {{ selectedMovie.release_year ?? '—' }}
                <span class="sep">·</span>
                {{ selectedMovie.genre || '—' }}
              </div>

              <div class="sheet-rating">
                <span class="stars" :title="selectedMovie.avg_rating == null ? '暂无评分' : `${selectedMovie.avg_rating}`">
                  <span
                    v-for="i in 5"
                    :key="i"
                    :class="['star', { filled: i <= starFill(selectedMovie.avg_rating) }]"
                  >
                    ★
                  </span>
                </span>
                <span class="rating-text">
                  <template v-if="selectedMovie.avg_rating != null">
                    {{ selectedMovie.avg_rating.toFixed(1) }} 分
                  </template>
                  <template v-else>暂无评分</template>
                  <span class="muted">（{{ formatCount(selectedMovie.rating_count) }} 人评分）</span>
                </span>
              </div>

              <div class="sheet-desc">
                {{ shortDesc(selectedMovie.description) }}
              </div>

              <div class="sheet-actions">
                <button class="btn ghost" type="button" @click="closeSheet">关闭</button>
                <button class="btn primary" type="button" @click="goToDetail(selectedMovie.id)">
                  查看完整详情 →
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import http from "../api/http";

import "leaflet/dist/leaflet.css";
import L from "leaflet";

const router = useRouter();

const mapEl = ref(null);
const mapRef = ref(null);
const markersLayerRef = ref(null);
const countryLayerRef = ref(null);
const countryGeoJsonRef = ref(null);
const countryFeatureMapRef = ref(new Map());
const countryMetaMapRef = ref(new Map());

const isInitialLoading = ref(true);
const isFetching = ref(false);

const yearRange = ref([1900, 2024]);
const selectedGenre = ref(null); // null = 全部

const items = ref([]);
const selectedMovie = ref(null);
const renderedCount = ref(0);

const markerCache = new Map();
const COUNTRY_GEOJSON_URL = "/data/countries.geojson";

const genreOptions = [
  { label: "全部", value: null },
  { label: "剧情", value: "剧情" },
  { label: "动作", value: "动作" },
  { label: "科幻", value: "科幻" },
  { label: "喜剧", value: "喜剧" },
  { label: "悬疑", value: "悬疑" },
  { label: "动画", value: "动画" },
];

const stats = computed(() => {
  const set = new Set();
  for (const m of items.value) {
    if (m?.country) set.add(m.country);
  }
  return { movieCount: items.value.length, countryCount: set.size };
});

const countrySummaries = computed(() => {
  const map = new Map();
  for (const movie of items.value) {
    const key = normalizeCountryName(movie?.country);
    if (!key) continue;
    const prev = map.get(key);
    if (!prev) {
      map.set(key, { count: 1, representativeMovie: movie });
      continue;
    }
    prev.count += 1;
    if (Number(movie.rating_count || 0) > Number(prev.representativeMovie.rating_count || 0)) {
      prev.representativeMovie = movie;
    }
  }
  return map;
});

const countryCounts = computed(() => {
  const counts = new Map();
  for (const [key, summary] of countrySummaries.value.entries()) counts.set(key, summary.count);
  return counts;
});

let debounceTimer = null;
let renderRafId = 0;
let lastRequestKey = 0;
let initialMarkerRenderTimer = null;

const COUNTRY_NAME_ALIASES = {
  "united states of america": "united states",
  "usa": "united states",
  "united kingdom": "united kingdom",
  "uk": "united kingdom",
  "russian federation": "russia",
  "korea, republic of": "south korea",
  "republic of korea": "south korea",
  "korea (south)": "south korea",
  "korea, democratic people's republic of": "north korea",
  "iran (islamic republic of)": "iran",
  "syrian arab republic": "syria",
  "viet nam": "vietnam",
  "czechia": "czech republic",
  "moldova, republic of": "moldova",
  "bolivia (plurinational state of)": "bolivia",
  "venezuela (bolivarian republic of)": "venezuela",
  "tanzania, united republic of": "tanzania",
  "palestine, state of": "palestine",
  "lao people's democratic republic": "laos",
  "brunei darussalam": "brunei",
  "north macedonia": "macedonia",
  "myanmar": "myanmar (burma)",
};

function onGenreClick(v) {
  selectedGenre.value = v;
  fetchGeo(false);
}

function closeSheet() {
  selectedMovie.value = null;
}

function goToDetail(id) {
  // 现有项目详情页路由是 /movies/:id（不是 /movie/:id）
  router.push(`/movies/${id}`);
}

function shortDesc(desc) {
  const s = (desc || "").toString().replace(/\s+/g, " ").trim();
  if (!s) return "暂无简介";
  return s.length > 100 ? `${s.slice(0, 100)}…` : s;
}

function formatCount(n) {
  const x = Number(n || 0);
  if (x >= 1000000) return `${(x / 1000000).toFixed(1)}M`;
  if (x >= 10000) return `${(x / 10000).toFixed(1)}万`;
  return `${Math.floor(x)}`;
}

function starFill(avg) {
  if (avg == null) return 0;
  // 后端当前为 1~5 分制；四舍五入到最近的整数星级（不做半星）
  const v = Math.max(0, Math.min(5, Number(avg)));
  return Math.round(v);
}

function escapeHtml(s) {
  return (s ?? "")
    .toString()
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function mulberry32(seed) {
  let t = seed >>> 0;
  return function () {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function normalizeCountryName(name) {
  const raw = (name || "").toString().trim().toLowerCase();
  if (!raw) return "";
  return COUNTRY_NAME_ALIASES[raw] || raw;
}

function getFeatureCountryName(feature) {
  const props = feature?.properties || {};
  return props.ADMIN || props.name || props.NAME || props.country || "";
}

function getCountryCount(name) {
  return countryCounts.value.get(normalizeCountryName(name)) ?? 0;
}
function getCountryFeatureByName(name) {
  return countryFeatureMapRef.value.get(normalizeCountryName(name)) || null;
}

function getCountryMetaByName(name) {
  return countryMetaMapRef.value.get(normalizeCountryName(name)) || null;
}

function pointInRing(point, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const intersect = yi > point[1] !== yj > point[1] && point[0] < ((xj - xi) * (point[1] - yi)) / ((yj - yi) || 1e-9) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function pointInGeometry(lat, lng, geometry) {
  const point = [lng, lat];
  if (!geometry) return false;
  if (geometry.type === "Polygon") {
    const [outer, ...holes] = geometry.coordinates || [];
    if (!outer || !pointInRing(point, outer)) return false;
    return !holes.some((ring) => pointInRing(point, ring));
  }
  if (geometry.type === "MultiPolygon") {
    return (geometry.coordinates || []).some((polygon) => {
      const [outer, ...holes] = polygon;
      if (!outer || !pointInRing(point, outer)) return false;
      return !holes.some((ring) => pointInRing(point, ring));
    });
  }
  return false;
}

function createFeatureMeta(feature) {
  const bounds = L.geoJSON(feature).getBounds();
  return {
    bounds,
    center: bounds.isValid() ? bounds.getCenter() : L.latLng(0, 0),
    particlePositionsByCount: new Map(),
  };
}

function featureBounds(feature) {
  return getCountryMetaByName(getFeatureCountryName(feature))?.bounds ?? L.latLngBounds();
}

function getParticleTargetCount(count, scale) {
  return Math.max(3, Math.min(18, Math.round(Math.sqrt(count) * 1.6 * scale)));
}

function generateParticlePositions(feature, count, seedBase = 1) {
  const meta = getCountryMetaByName(getFeatureCountryName(feature));
  const bounds = meta?.bounds ?? L.latLngBounds();
  if (!bounds.isValid()) return [];
  const cacheKey = `${count}:${seedBase}`;
  if (meta?.particlePositionsByCount.has(cacheKey)) return meta.particlePositionsByCount.get(cacheKey);

  const positions = [];
  const rnd = mulberry32(seedBase >>> 0);
  let guard = 0;
  while (positions.length < count && guard < count * 25) {
    guard += 1;
    const lat = bounds.getSouth() + rnd() * (bounds.getNorth() - bounds.getSouth());
    const lng = bounds.getWest() + rnd() * (bounds.getEast() - bounds.getWest());
    if (pointInGeometry(lat, lng, feature.geometry)) positions.push([lat, lng]);
  }
  if (!positions.length) {
    const center = meta?.center ?? bounds.getCenter();
    positions.push([center.lat, center.lng]);
  }
  meta?.particlePositionsByCount.set(cacheKey, positions);
  return positions;
}


function getCountryFillColor(count) {
  if (count >= 80) return "rgba(255, 193, 92, 0.46)";
  if (count >= 40) return "rgba(255, 160, 96, 0.34)";
  if (count >= 15) return "rgba(255, 120, 110, 0.22)";
  if (count >= 5) return "rgba(104, 154, 255, 0.14)";
  if (count > 0) return "rgba(104, 154, 255, 0.08)";
  return "rgba(255, 255, 255, 0.02)";
}

function getCountryStyle(feature) {
  const count = getCountryCount(getFeatureCountryName(feature));
  return {
    color: count > 0 ? "rgba(255,255,255,0.22)" : "rgba(255,255,255,0.08)",
    weight: count > 0 ? 1.1 : 0.7,
    fillColor: getCountryFillColor(count),
    fillOpacity: count > 0 ? 0.9 : 0.5,
    opacity: count > 0 ? 0.95 : 0.6,
  };
}

function highlightCountryLayer(layer, feature) {
  const count = getCountryCount(getFeatureCountryName(feature));
  layer.setStyle({
    color: count > 0 ? "rgba(255, 224, 148, 0.95)" : "rgba(167, 196, 255, 0.82)",
    weight: count > 0 ? 2.2 : 1.4,
    fillOpacity: count > 0 ? 1 : 0.7,
  });
  if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) layer.bringToFront();
}

function resetCountryLayerStyle(layer, feature) {
  layer.setStyle(getCountryStyle(feature));
}

function attachCountryInteractions(feature, layer) {
  const countryName = getFeatureCountryName(feature);
  const count = getCountryCount(countryName);
  layer.bindTooltip(`${countryName || "Unknown"} · ${count} 部电影`, {
    sticky: true,
    direction: "top",
    className: "country-tooltip",
    offset: [0, -6],
  });
  layer.on({
    mouseover: () => highlightCountryLayer(layer, feature),
    mouseout: () => resetCountryLayerStyle(layer, feature),
    click: () => {
      if (!mapRef.value) return;
      mapRef.value.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 5.5, animate: true });
    },
  });
}

async function ensureCountryGeoJsonLoaded() {
  if (countryGeoJsonRef.value) return countryGeoJsonRef.value;
  const resp = await fetch(COUNTRY_GEOJSON_URL);
  countryGeoJsonRef.value = await resp.json();
  return countryGeoJsonRef.value;
}

function renderCountryOverlay() {
  if (!mapRef.value || !countryGeoJsonRef.value) return;
  if (countryLayerRef.value) countryLayerRef.value.remove();
  countryFeatureMapRef.value = new Map();
  countryMetaMapRef.value = new Map();

  const geoLayer = L.geoJSON(countryGeoJsonRef.value, {
    pane: "countryPane",
    style: getCountryStyle,
    onEachFeature: (feature, layer) => {
      const normalized = normalizeCountryName(getFeatureCountryName(feature));
      countryFeatureMapRef.value.set(normalized, feature);
      countryMetaMapRef.value.set(normalized, createFeatureMeta(feature));
      attachCountryInteractions(feature, layer);
    },
  }).addTo(mapRef.value);

  countryLayerRef.value = geoLayer;
}

function jitterLatLng(movie, indexInCountry) {
  const baseLat = Number(movie.latitude);
  const baseLng = Number(movie.longitude);
  const seed = (Number(movie.id || 0) + indexInCountry * 9973) >>> 0;
  const rnd = mulberry32(seed);
  const offLat = (rnd() * 2 - 1) * 0.5;
  const offLng = (rnd() * 2 - 1) * 0.5;
  return [baseLat + offLat, baseLng + offLng];
}

function buildPosterHtml(movie, size) {
  const title = escapeHtml(movie.title);
  const year = movie.release_year ?? "—";
  const poster = escapeHtml(movie.poster_url || "");

  return `
    <div class="poster-marker" data-mid="${escapeHtml(movie.id)}" style="width:${size.width}px;height:${size.height}px;">
      <img class="poster-img" src="${poster}" alt="${title}" loading="lazy" style="width:${size.width}px;height:${size.height}px;" />
      <div class="poster-tooltip">
        <div class="tooltip-title">${title}</div>
        <div class="tooltip-sub">${escapeHtml(year)}</div>
      </div>
    </div>
  `;
}

function buildParticleHtml(entry, profile) {
  const countLabel = `${entry.count} 部电影`;
  const country = escapeHtml(entry.countryName || "Unknown");
  const size = profile.particleSize;
  return `
    <div class="particle-marker" style="width:${size}px;height:${size}px;">
      <span class="particle-core"></span>
      <div class="dot-tooltip">
        <div class="tooltip-title">${country} · ${escapeHtml(countLabel)}</div>
        <div class="tooltip-sub">点击可放大到该国家</div>
      </div>
    </div>
  `;
}

function getZoomProfile(zoom) {
  if (zoom <= 2.5) return { mode: "particle", particleSize: 10, poster: { width: 32, height: 44 }, particleScale: 0.9 };
  if (zoom <= 3.5) return { mode: "particle", particleSize: 12, poster: { width: 36, height: 50 }, particleScale: 1.2 };
  if (zoom <= 4.5) return { mode: "poster", cellDeg: 3, maxMarkers: 380, poster: { width: 42, height: 58 } };
  if (zoom <= 5.5) return { mode: "poster", cellDeg: 1.8, maxMarkers: 560, poster: { width: 52, height: 72 } };
  return { mode: "poster", cellDeg: 1.1, maxMarkers: 820, poster: { width: 64, height: 88 } };
}

function prepareDisplayCoordinates(list) {
  const perCountryIndex = new Map();
  return list.map((m) => {
    const key = (m.country || "Unknown").toString();
    const idx = perCountryIndex.get(key) ?? 0;
    perCountryIndex.set(key, idx + 1);
    const [lat, lng] = jitterLatLng(m, idx);
    return { ...m, _displayLat: lat, _displayLng: lng };
  });
}

function getPosterEntries(movies, profile) {
  if (!mapRef.value) return [];
  const bounds = mapRef.value.getBounds().pad(0.2);
  const buckets = new Map();

  for (const m of movies) {
    if (m?._displayLat == null || m?._displayLng == null) continue;
    if (!bounds.contains([m._displayLat, m._displayLng])) continue;
    const bucketKey = `${Math.floor((m._displayLng + 180) / profile.cellDeg)}:${Math.floor((m._displayLat + 90) / profile.cellDeg)}`;
    const prev = buckets.get(bucketKey);
    if (!prev) {
      buckets.set(bucketKey, { bucketKey, movie: m, count: 1 });
      continue;
    }
    prev.count += 1;
    if (Number(m.rating_count || 0) > Number(prev.movie.rating_count || 0)) prev.movie = m;
  }

  return Array.from(buckets.values())
    .sort((a, b) => Number(b.movie.rating_count || 0) - Number(a.movie.rating_count || 0))
    .slice(0, profile.maxMarkers);
}

function getParticleEntries(_movies, profile) {
  if (!mapRef.value) return [];
  const bounds = mapRef.value.getBounds().pad(0.15);
  const entries = [];

  for (const [key, summary] of countrySummaries.value.entries()) {
    const feature = countryFeatureMapRef.value.get(key);
    const meta = countryMetaMapRef.value.get(key);
    if (!feature || !meta?.bounds?.isValid() || !bounds.intersects(meta.bounds)) continue;

    const countryName = getFeatureCountryName(feature);
    const target = getParticleTargetCount(summary.count, profile.particleScale);
    const positions = generateParticlePositions(feature, target, Number(summary.representativeMovie.id || 0) + summary.count * 37);

    for (let idx = 0; idx < positions.length; idx += 1) {
      const pos = positions[idx];
      entries.push({
        id: `${key}:${idx}`,
        countryName,
        count: summary.count,
        movie: summary.representativeMovie,
        lat: pos[0],
        lng: pos[1],
        feature,
        bounds: meta.bounds,
      });
    }
  }

  return entries;
}

function getRenderableEntries(movies) {
  const profile = getZoomProfile(mapRef.value?.getZoom?.() ?? 4);
  const entries = profile.mode === "particle" ? getParticleEntries(movies, profile) : getPosterEntries(movies, profile);
  return { entries, profile };
}

function getPosterMarker(entry, profile) {
  const cacheKey = `${entry.movie.id}:${profile.poster.width}x${profile.poster.height}`;
  const cached = markerCache.get(cacheKey);
  if (cached) return cached;

  const icon = L.divIcon({
    className: "movie-div-icon",
    html: buildPosterHtml(entry.movie, profile.poster),
    iconSize: [profile.poster.width, profile.poster.height],
    iconAnchor: [Math.round(profile.poster.width / 2), profile.poster.height],
  });

  const marker = L.marker([entry.movie._displayLat, entry.movie._displayLng], { icon, keyboard: false, riseOnHover: true, zIndexOffset: 0 });
  marker.on("click", () => {
    selectedMovie.value = entry.movie;
    marker.setZIndexOffset(1000);
  });
  marker.on("mouseout", () => marker.setZIndexOffset(0));
  markerCache.set(cacheKey, marker);
  return marker;
}

function createParticleMarker(entry, profile) {
  const size = profile.particleSize;
  const icon = L.divIcon({
    className: "movie-div-icon particle-div-icon",
    html: buildParticleHtml(entry, profile),
    iconSize: [size, size],
    iconAnchor: [Math.round(size / 2), Math.round(size / 2)],
  });

  const marker = L.marker([entry.lat, entry.lng], { icon, keyboard: false, zIndexOffset: 0 });
  marker.on("click", () => {
    if (!mapRef.value) return;
    mapRef.value.fitBounds(entry.bounds || featureBounds(entry.feature), { padding: [40, 40], maxZoom: 5.5, animate: true });
  });
  return marker;
}

function renderMarkers(movies) {
  if (!markersLayerRef.value) return;
  markersLayerRef.value.clearLayers();
  const { entries, profile } = getRenderableEntries(movies);
  for (const entry of entries) {
    const marker = profile.mode === "particle" ? createParticleMarker(entry, profile) : getPosterMarker(entry, profile);
    markersLayerRef.value.addLayer(marker);
  }
  renderedCount.value = entries.length;
}

function scheduleRenderMarkers(delay = 0) {
  if (renderRafId) cancelAnimationFrame(renderRafId);
  if (initialMarkerRenderTimer) window.clearTimeout(initialMarkerRenderTimer);

  const run = () => {
    renderRafId = requestAnimationFrame(() => {
      renderRafId = 0;
      renderMarkers(items.value);
    });
  };

  if (delay > 0) {
    initialMarkerRenderTimer = window.setTimeout(() => {
      initialMarkerRenderTimer = null;
      run();
    }, delay);
    return;
  }

  run();
}

async function fetchGeo(isFirstLoad) {
  const reqKey = ++lastRequestKey;
  if (isFirstLoad) isInitialLoading.value = true;
  isFetching.value = !isFirstLoad;

  const params = {
    year_from: yearRange.value[0],
    year_to: yearRange.value[1],
  };
  if (selectedGenre.value) params.genre = selectedGenre.value;

  try {
    const resp = await http.get("/movies/geo", { params });
    if (reqKey !== lastRequestKey) return; // 丢弃过期响应
    const list = prepareDisplayCoordinates(resp?.data?.items || []);

    items.value = list;
    markerCache.clear();
    renderCountryOverlay();
    scheduleRenderMarkers(isFirstLoad ? 80 : 0);
  } finally {
    if (reqKey === lastRequestKey) {
      isInitialLoading.value = false;
      isFetching.value = false;
    }
  }
}

function scheduleFetchDebounced() {
  if (debounceTimer) window.clearTimeout(debounceTimer);
  debounceTimer = window.setTimeout(() => {
    fetchGeo(false);
  }, 400);
}

function initMap() {
  if (!mapEl.value) return;

  const map = L.map(mapEl.value, {
    zoomControl: false,
    preferCanvas: true,
    // 限制缩放与范围，避免“重复大陆/无限平移”
    minZoom: 2,
    maxZoom: 6.5,
    zoomSnap: 0.25,
    zoomDelta: 0.5,
    wheelPxPerZoomLevel: 140,
  });

  const bounds = L.latLngBounds(L.latLng(-85, -180), L.latLng(85, 180));
  map.setMaxBounds(bounds);
  map.options.maxBoundsViscosity = 1.0;

  map.createPane("countryPane");
  map.getPane("countryPane").style.zIndex = 350;

  // 深色底图（无需 API Key）：CartoDB Dark Matter
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    maxZoom: 19,
    noWrap: true,
    bounds,
  }).addTo(map);

  L.control.zoom({ position: "bottomright" }).addTo(map);

  map.setView([20, 0], 2);

  const layer = L.layerGroup().addTo(map);
  map.on("moveend zoomend", scheduleRenderMarkers);
  mapRef.value = map;
  markersLayerRef.value = layer;
}

onMounted(async () => {
  await nextTick();
  initMap();
  await ensureCountryGeoJsonLoaded();
  renderCountryOverlay();
  await fetchGeo(true);
});

onBeforeUnmount(() => {
  if (debounceTimer) window.clearTimeout(debounceTimer);
  debounceTimer = null;

  if (renderRafId) cancelAnimationFrame(renderRafId);
  renderRafId = 0;
  if (initialMarkerRenderTimer) window.clearTimeout(initialMarkerRenderTimer);
  initialMarkerRenderTimer = null;
  markerCache.clear();

  if (countryLayerRef.value) {
    countryLayerRef.value.remove();
    countryLayerRef.value = null;
  }

  if (mapRef.value) {
    mapRef.value.off("moveend zoomend", scheduleRenderMarkers);
    mapRef.value.remove();
    mapRef.value = null;
    markersLayerRef.value = null;
  }
});

watch(
  () => yearRange.value.slice(),
  () => scheduleFetchDebounced(),
  { deep: false }
);
</script>

<style scoped>
.map-page {
  --app-header-h: 70px;
  position: fixed;
  left: 0;
  right: 0;
  top: var(--app-header-h);
  bottom: 0;
  z-index: 2; /* 覆盖 footer/main 区域，但低于 header */
  background: #0b0f18;
  overflow: hidden;
}

.leaflet-map {
  width: 100vw;
  height: calc(100vh - var(--app-header-h));
}

/* 让 leaflet 背景更“深色” */
:deep(.leaflet-container) {
  background: #070a12;
  outline: none;
}

/* 初次加载：居中遮罩 */
.map-loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  z-index: 30;
  background: radial-gradient(circle at 50% 30%, rgba(88, 101, 242, 0.15), transparent 55%);
  pointer-events: none;
}

.loading-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(14px);
  color: rgba(255, 255, 255, 0.88);
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.25);
  border-top-color: rgba(255, 255, 255, 0.9);
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.left-panel {
  position: absolute;
  left: 16px;
  top: 16px;
  width: 320px;
  z-index: 20;
  padding: 16px;
  border-radius: 16px;
  background: rgba(0, 0, 0, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(18px);
  box-shadow: 0 14px 60px rgba(0, 0, 0, 0.45);
  color: rgba(255, 255, 255, 0.9);
}

.panel-title {
  font-weight: 800;
  font-size: 16px;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.panel-block {
  margin-top: 14px;
}

.performance-block {
  padding-top: 4px;
}

.block-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.82);
  margin-bottom: 10px;
}

.block-value {
  font-variant-numeric: tabular-nums;
  color: rgba(255, 255, 255, 0.95);
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
}

.performance-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(72, 187, 120, 0.18);
  color: #9af0b5;
  font-size: 11px;
  font-weight: 700;
}

.performance-meta,
.stats-subline {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.fetching-badge {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.genre-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.genre-tag {
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.82);
  padding: 8px 10px;
  border-radius: 12px;
  font-size: 13px;
  cursor: pointer;
  transition: transform 120ms ease, background 120ms ease, border-color 120ms ease;
}

.genre-tag:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.1);
}

.genre-tag.active {
  background: rgba(88, 101, 242, 0.35);
  border-color: rgba(88, 101, 242, 0.6);
  color: rgba(255, 255, 255, 0.95);
}

:deep(.country-tooltip) {
  background: rgba(0, 0, 0, 0.82);
  color: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}

:deep(.country-tooltip:before) {
  border-top-color: rgba(0, 0, 0, 0.82);
}

.top-right-stats {
  position: absolute;
  right: 16px;
  top: 16px;
  z-index: 20;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(18px);
  color: rgba(255, 255, 255, 0.88);
  font-size: 13px;
}

.stats-strong {
  font-weight: 800;
  color: rgba(255, 255, 255, 0.98);
}

/* --- Marker HTML（divIcon）样式 --- */
:deep(.movie-div-icon) {
  background: transparent;
  border: none;
}

:deep(.poster-marker) {
  border-radius: 4px;
  overflow: visible;
  position: relative;
  transform-origin: center bottom;
}

:deep(.poster-img) {
  border-radius: 4px;
  object-fit: cover;
  display: block;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transform: scale(1);
  transition: transform 150ms ease;
}

:deep(.particle-div-icon) {
  background: transparent;
  border: none;
}

:deep(.particle-marker) {
  position: relative;
  display: grid;
  place-items: center;
}

:deep(.particle-core) {
  width: 100%;
  height: 100%;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(255, 239, 180, 0.98) 0%, rgba(255, 195, 80, 0.92) 32%, rgba(255, 132, 78, 0.42) 68%, rgba(255, 132, 78, 0.04) 100%);
  box-shadow: 0 0 12px rgba(255, 201, 120, 0.95), 0 0 28px rgba(255, 126, 88, 0.42);
  animation: particlePulse 2.4s ease-in-out infinite;
}

@keyframes particlePulse {
  0%, 100% {
    transform: scale(0.9);
    opacity: 0.8;
  }
  50% {
    transform: scale(1.15);
    opacity: 1;
  }
}

:deep(.dot-tooltip) {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 10px);
  transform: translateX(-50%);
  min-width: 150px;
  max-width: 220px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.82);
  color: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  opacity: 0;
  pointer-events: none;
  transition: opacity 120ms ease, transform 120ms ease;
}

:deep(.particle-marker:hover .dot-tooltip) {
  opacity: 1;
  transform: translateX(-50%) translateY(-2px);
}

:deep(.poster-tooltip) {
  position: absolute;
  left: 50%;
  bottom: 62px;
  transform: translateX(-50%);
  min-width: 140px;
  max-width: 220px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.82);
  color: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
  opacity: 0;
  pointer-events: none;
  transition: opacity 120ms ease, transform 120ms ease;
}

:deep(.tooltip-title) {
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.tooltip-sub) {
  margin-top: 3px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
}

:deep(.poster-marker:hover .poster-img) {
  transform: scale(1.5);
}

:deep(.poster-marker:hover .poster-tooltip) {
  opacity: 1;
  transform: translateX(-50%) translateY(-2px);
}

/* --- Bottom sheet --- */
.sheet-backdrop {
  position: fixed;
  left: 0;
  right: 0;
  top: var(--app-header-h);
  bottom: 0;
  z-index: 40;
  background: rgba(0, 0, 0, 0);
}

.bottom-sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 32vh;
  min-height: 220px;
  max-height: 420px;
  background: rgba(0, 0, 0, 0.85);
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(18px);
  box-shadow: 0 -20px 60px rgba(0, 0, 0, 0.55);
  padding: 18px 18px 16px;
  color: rgba(255, 255, 255, 0.92);
}

.sheet-close {
  position: absolute;
  right: 12px;
  top: 10px;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
  transition: background 120ms ease, transform 120ms ease;
}

.sheet-close:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateY(-1px);
}

.sheet-content {
  height: 100%;
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 16px;
  align-items: start;
}

.sheet-poster img {
  width: 120px;
  height: 170px;
  border-radius: 10px;
  object-fit: cover;
  display: block;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
}

.sheet-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.sheet-title {
  font-size: 20px;
  font-weight: 900;
  letter-spacing: 0.2px;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 44px;
}

.sheet-meta {
  margin-top: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.sep {
  margin: 0 6px;
  color: rgba(255, 255, 255, 0.35);
}

.sheet-rating {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.stars {
  display: inline-flex;
  gap: 2px;
}

.star {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.22);
}

.star.filled {
  color: #ffd166;
}

.rating-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.muted {
  color: rgba(255, 255, 255, 0.55);
  margin-left: 4px;
}

.sheet-desc {
  margin-top: 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.sheet-actions {
  margin-top: auto;
  display: flex;
  gap: 10px;
  padding-top: 12px;
}

.btn {
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
  padding: 10px 14px;
  border-radius: 12px;
  cursor: pointer;
  transition: transform 120ms ease, background 120ms ease, border-color 120ms ease;
  font-weight: 700;
}

.btn:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.12);
}

.btn.primary {
  border-color: rgba(88, 101, 242, 0.6);
  background: rgba(88, 101, 242, 0.35);
}

.btn.primary:hover {
  background: rgba(88, 101, 242, 0.45);
}

.btn.ghost {
  background: rgba(255, 255, 255, 0.06);
}

/* 面板滑入滑出动画 */
.sheet-enter-active,
.sheet-leave-active {
  transition: transform 250ms ease-out, opacity 250ms ease-out;
}
.sheet-enter-from,
.sheet-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
.sheet-enter-to,
.sheet-leave-from {
  transform: translateY(0);
  opacity: 1;
}
</style>

