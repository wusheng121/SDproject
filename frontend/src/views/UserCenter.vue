<template>
  <div class="user-center">
    <header class="page-heading">
      <div><p class="eyebrow">MY CAMPUS MARKET</p><h1>个人中心</h1><p>管理你的交易、收藏和个性化推荐。</p></div>
      <el-button @click="openEditProfile">编辑资料</el-button>
    </header>

    <section class="profile-panel">
      <div class="avatar">{{ (userStore.profile?.username || "同").slice(0, 1) }}</div>
      <div class="identity"><h2>{{ userStore.profile?.username || "校园用户" }}</h2><p>{{ userStore.profile?.email || "邮箱暂未设置" }}</p></div>
      <el-tag v-if="userStore.profile?.email_verified" type="success">邮箱已验证</el-tag>
      <el-tag v-else type="info">校园交易账户</el-tag>
    </section>

    <section class="stats-grid">
      <button class="stat-item" type="button" @click="router.push('/favorites')"><strong>{{ stats.favorites }}</strong><span>我的收藏</span></button>
      <div class="stat-item"><strong>{{ stats.products }}</strong><span>发布商品</span></div>
      <div class="stat-item"><strong>{{ stats.behaviors }}</strong><span>浏览与互动</span></div>
      <button class="stat-item" type="button" @click="openPreferenceDialog"><strong>{{ preferences.length }}</strong><span>兴趣品类</span></button>
    </section>

    <div class="content-layout">
      <div class="main-column">
        <section class="content-section">
          <div class="section-title"><div><h2>我的交易</h2><p>查看你的商品发布和交易进度</p></div></div>
          <div class="transaction-links">
            <button type="button" @click="router.push('/publish')"><span class="link-mark">+</span><span><strong>发布闲置</strong><small>让闲置物品找到新主人</small></span><b>›</b></button>
            <button type="button" @click="router.push('/search')"><span class="link-mark">市</span><span><strong>继续逛集市</strong><small>发现同学发布的校园好物</small></span><b>›</b></button>
          </div>
          <div class="notice-line">商品发布后需通过审核，审核状态可在管理端查看。</div>
        </section>

        <section class="content-section">
          <div class="section-title"><div><h2>兴趣偏好</h2><p>偏好会直接影响首页推荐内容</p></div><el-button text type="primary" @click="openPreferenceDialog">{{ preferences.length ? "调整偏好" : "设置偏好" }}</el-button></div>
          <div v-if="preferences.length" class="preference-list"><el-tag v-for="category in preferences" :key="category" effect="plain">{{ category }}</el-tag></div>
          <div v-else class="empty-preferences">还没有设置品类偏好。设置后，首页将优先推荐相关商品。</div>
          <button class="recommendation-link" type="button" @click="router.push('/recommendation-test')"><span><strong>推荐效果测试</strong><small>查看 A/B/C/D 阶段与推荐结果</small></span><b>›</b></button>
        </section>
      </div>

      <aside class="side-column">
        <section class="content-section quick-section">
          <div class="section-title"><div><h2>常用入口</h2></div></div>
          <button type="button" @click="router.push('/favorites')">我的收藏 <span>›</span></button>
          <button type="button" @click="router.push('/publish')">发布商品 <span>›</span></button>
          <button type="button" @click="router.push('/')">首页推荐 <span>›</span></button>
          <button type="button" @click="handleLogout">退出登录 <span>›</span></button>
        </section>
        <section class="tip-panel"><strong>让推荐更懂你</strong><p>浏览、收藏和互动会帮助系统逐步了解你感兴趣的品类。</p><el-button type="primary" @click="router.push('/')">查看首页推荐</el-button></section>
      </aside>
    </div>

    <PreferenceDialog v-model="showPreferenceDialog" @saved="onPreferenceSaved" />
    <el-dialog v-model="showEditProfile" title="编辑个人资料" width="420px">
      <el-form label-width="76px"><el-form-item label="用户名"><el-input v-model="profileForm.username" maxlength="50" /></el-form-item><el-form-item label="手机号"><el-input v-model="profileForm.phone" placeholder="留空则不修改" /></el-form-item></el-form>
      <template #footer><el-button @click="showEditProfile = false">取消</el-button><el-button type="primary" :loading="savingProfile" @click="saveProfile">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useUserStore } from "../stores/user";
import { apiGetPreferences, apiUpdateProfile, apiUserStats } from "../api/user";
import PreferenceDialog from "../components/PreferenceDialog.vue";

const router = useRouter();
const userStore = useUserStore();
const showPreferenceDialog = ref(false);
const showEditProfile = ref(false);
const savingProfile = ref(false);
const profileForm = ref({ username: "", phone: "" });
const preferences = ref([]);
const stats = ref({ favorites: 0, products: 0, behaviors: 0, categories: 0 });

async function loadUserData() {
  try {
    await userStore.fetchProfile();
    const [prefResp, statsResp] = await Promise.all([apiGetPreferences(), apiUserStats()]);
    preferences.value = prefResp?.data?.data?.preferred_categories || [];
    stats.value = statsResp?.data?.data || stats.value;
  } catch (error) {
    console.error("加载用户数据失败:", error);
  }
}

function openPreferenceDialog() { showPreferenceDialog.value = true; }
function openEditProfile() {
  profileForm.value = { username: userStore.profile?.username || "", phone: "" };
  showEditProfile.value = true;
}
async function saveProfile() {
  savingProfile.value = true;
  try {
    const payload = { username: profileForm.value.username };
    if (profileForm.value.phone.trim()) payload.phone = profileForm.value.phone.trim();
    const response = await apiUpdateProfile(payload);
    userStore.profile = response?.data?.data?.user || userStore.profile;
    ElMessage.success("资料已更新");
    showEditProfile.value = false;
    await loadUserData();
  } catch (error) {
    ElMessage.error(error?.message || "更新资料失败");
  } finally {
    savingProfile.value = false;
  }
}
async function onPreferenceSaved() {
  await loadUserData();
  ElMessage.success("兴趣偏好已更新，首页推荐已刷新");
}
async function handleLogout() {
  await userStore.logout();
  router.push("/login");
}
onMounted(() => {
  if (!userStore.token) { router.push("/login"); return; }
  loadUserData();
});
</script>

<style scoped>
.user-center { max-width: 1080px; margin: 0 auto; padding: 34px 0; }
.page-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 22px; }
.eyebrow { margin: 0 0 7px; color: var(--primary-color); font-size: 11px; font-weight: 800; letter-spacing: 1px; }
.page-heading h1 { margin: 0; color: var(--text-primary); font-size: 30px; }
.page-heading p:last-child { margin: 7px 0 0; color: var(--text-secondary); font-size: 13px; }
.profile-panel { display: flex; align-items: center; gap: 16px; padding: 22px; border: 1px solid var(--border-color); background: var(--bg-card); }
.avatar { display: grid; width: 58px; height: 58px; flex: 0 0 auto; place-items: center; color: white; background: var(--primary-color); border-radius: 50%; font-size: 22px; font-weight: 700; }
.identity { flex: 1; min-width: 0; }
.identity h2 { margin: 0 0 6px; color: var(--text-primary); font-size: 19px; }
.identity p { margin: 0; color: var(--text-secondary); font-size: 13px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); margin-top: 14px; border: 1px solid var(--border-color); background: var(--bg-card); }
.stat-item { display: flex; flex-direction: column; gap: 6px; min-height: 86px; justify-content: center; border: 0; border-right: 1px solid var(--border-color); color: var(--text-primary); background: transparent; text-align: center; }
.stat-item:last-child { border-right: 0; }
button.stat-item { cursor: pointer; }
button.stat-item:hover { background: var(--bg-hover); }
.stat-item strong { color: var(--primary-color); font-size: 23px; }
.stat-item span { color: var(--text-secondary); font-size: 12px; }
.content-layout { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(240px, .8fr); gap: 16px; margin-top: 16px; }
.main-column, .side-column { display: flex; flex-direction: column; gap: 16px; }
.content-section { padding: 21px; border: 1px solid var(--border-color); background: var(--bg-card); }
.section-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 17px; }
.section-title h2 { margin: 0; color: var(--text-primary); font-size: 17px; }
.section-title p { margin: 5px 0 0; color: var(--text-secondary); font-size: 12px; }
.transaction-links { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.transaction-links button, .recommendation-link { display: flex; align-items: center; gap: 11px; width: 100%; min-width: 0; padding: 13px; border: 1px solid var(--border-color); color: var(--text-primary); background: transparent; cursor: pointer; text-align: left; }
.transaction-links button:hover, .recommendation-link:hover { border-color: var(--primary-color); background: var(--bg-hover); }
.link-mark { display: grid; width: 34px; height: 34px; flex: 0 0 auto; place-items: center; border: 1px solid var(--primary-color); border-radius: 50%; color: var(--primary-color); font-weight: 700; }
.transaction-links button > span:nth-child(2), .recommendation-link span { display: flex; flex: 1; flex-direction: column; gap: 5px; min-width: 0; }
.transaction-links strong, .recommendation-link strong { font-size: 13px; }
.transaction-links small, .recommendation-link small { overflow: hidden; color: var(--text-secondary); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.transaction-links b, .recommendation-link b { color: var(--text-secondary); font-size: 21px; font-weight: 400; }
.notice-line { margin-top: 14px; padding: 10px 12px; color: var(--text-secondary); background: var(--bg-hover); font-size: 11px; }
.preference-list { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.empty-preferences { margin-bottom: 16px; padding: 14px; color: var(--text-secondary); background: var(--bg-hover); font-size: 12px; line-height: 1.7; }
.recommendation-link { margin-top: 4px; }
.quick-section { display: flex; flex-direction: column; gap: 2px; }
.quick-section .section-title { margin-bottom: 8px; }
.quick-section > button { display: flex; justify-content: space-between; padding: 11px 0; border: 0; border-bottom: 1px solid var(--border-color); color: var(--text-primary); background: transparent; cursor: pointer; text-align: left; font-size: 13px; }
.quick-section > button:last-child { border-bottom: 0; }
.quick-section > button:hover { color: var(--primary-color); }
.quick-section > button span { color: var(--text-secondary); font-size: 19px; line-height: 14px; }
.tip-panel { padding: 20px; color: white; background: #263b35; }
.tip-panel strong { font-size: 15px; }
.tip-panel p { margin: 9px 0 15px; color: rgba(255,255,255,.75); font-size: 12px; line-height: 1.7; }
@media (max-width: 740px) { .user-center { padding: 24px 0; } .content-layout { grid-template-columns: 1fr; } .transaction-links { grid-template-columns: 1fr; } }
@media (max-width: 500px) { .profile-panel { flex-wrap: wrap; } .stats-grid { grid-template-columns: repeat(2, 1fr); } .stat-item:nth-child(2) { border-right: 0; } .stat-item:nth-child(-n+2) { border-bottom: 1px solid var(--border-color); } .page-heading h1 { font-size: 25px; } }
</style>
