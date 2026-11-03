<template>
  <div class="skill-admin">
    <div class="toolbar">
      <el-input v-model="filters.keyword" placeholder="编号 / code / 名称" clearable style="width: 220px" @keyup.enter="load(1)" />
      <el-select v-model="filters.module" placeholder="模块" clearable style="width: 150px" @change="load(1)">
        <el-option v-for="item in modules" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px" @change="load(1)">
        <el-option label="草稿" value="draft" />
        <el-option label="已发布" value="published" />
        <el-option label="已禁用" value="disabled" />
      </el-select>
      <el-button type="primary" @click="load(1)">查询</el-button>
      <el-button type="success" @click="openCreate">新建 Skill</el-button>
    </div>

    <el-table :data="items" stripe v-loading="loading">
      <el-table-column prop="skill_no" label="编号" width="100" />
      <el-table-column label="Skill" min-width="180">
        <template #default="{ row }">
          <div class="skill-name">{{ row.name }}</div>
          <div class="skill-code">{{ row.code }}</div>
        </template>
      </el-table-column>
      <el-table-column label="模块" width="120">
        <template #default="{ row }">{{ moduleLabel(row.module) }}</template>
      </el-table-column>
      <el-table-column prop="scope" label="Scope" min-width="160" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="80" />
      <el-table-column prop="updated_at" label="更新时间" width="180" />
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="success" plain @click="test(row)">测试</el-button>
          <el-button v-if="row.status !== 'published'" size="small" type="primary" @click="publish(row)">发布</el-button>
          <el-button v-if="row.status === 'published'" size="small" type="warning" plain @click="disable(row)">禁用</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      class="pager"
      background
      layout="total, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="load"
    />

    <el-dialog v-model="editVisible" :title="editingId ? '编辑 Skill' : '新建 Skill'" width="760px" destroy-on-close>
      <el-form :model="form" label-width="130px">
        <el-form-item label="Skill 编号">
          <el-input v-model="form.skill_no" placeholder="例如 SK-005" />
        </el-form-item>
        <el-form-item label="Code" required>
          <el-input v-model="form.code" :disabled="!!editingId" placeholder="例如 product_detail" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="模块" required>
          <el-select v-model="form.module" style="width: 100%">
            <el-option v-for="item in modules" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="Scope" required>
          <el-input v-model="form.scope" placeholder="product:view" />
        </el-form-item>
        <el-form-item label="输入 Schema">
          <el-input v-model="form.input_schema_json" type="textarea" :rows="5" />
        </el-form-item>
        <el-form-item label="输出 Schema">
          <el-input v-model="form.output_schema_json" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="允许操作">
          <el-input v-model="form.allowed_operations" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="禁止操作">
          <el-input v-model="form.forbidden_operations" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="Handler 类型">
          <el-select v-model="form.handler_type" style="width: 100%">
            <el-option label="Java" value="java" />
            <el-option label="Python HTTP" value="python_http" />
          </el-select>
        </el-form-item>
        <el-form-item label="Handler 目标">
          <el-input v-model="form.handler_target" placeholder="默认使用 Skill code" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="testVisible" title="测试 Skill" width="680px" destroy-on-close>
      <p class="test-title">{{ testSkill?.name }} <span class="skill-code">{{ testSkill?.code }}</span></p>
      <el-input v-model="testParams" type="textarea" :rows="8" placeholder='示例：{"category":"手机","max_price":1000}' />
      <div v-if="testResult" class="test-result">
        <div class="test-meta">耗时：{{ testResult.latency_ms }} ms</div>
        <pre>{{ formattedResult }}</pre>
      </div>
      <template #footer>
        <el-button @click="testVisible = false">关闭</el-button>
        <el-button type="primary" :loading="testing" @click="runTest">执行测试</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import {
  apiCreateSkill,
  apiDisableSkill,
  apiGetSkills,
  apiPublishSkill,
  apiTestSkill,
  apiUpdateSkill
} from "../api/admin";

const modules = [
  { value: "product", label: "商品" },
  { value: "trade", label: "交易" },
  { value: "recommendation", label: "推荐" },
  { value: "user", label: "用户" },
  { value: "admin", label: "管理" },
  { value: "system", label: "系统" }
];

const filters = reactive({ keyword: "", module: "", status: "" });
const items = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const loading = ref(false);

const editVisible = ref(false);
const editingId = ref(null);
const saving = ref(false);
const form = reactive(defaultForm());

const testVisible = ref(false);
const testing = ref(false);
const testSkill = ref(null);
const testParams = ref("{}");
const testResult = ref(null);

const formattedResult = computed(() => {
  if (!testResult.value) return "";
  return JSON.stringify(testResult.value.result, null, 2);
});

function defaultForm() {
  return {
    skill_no: "",
    code: "",
    name: "",
    module: "product",
    description: "",
    input_schema_json: "{}",
    output_schema_json: "{}",
    allowed_operations: "",
    forbidden_operations: "",
    scope: "product:view",
    handler_type: "java",
    handler_target: ""
  };
}

function resetForm(data = {}) {
  Object.assign(form, defaultForm(), data);
}

function moduleLabel(value) {
  return modules.find((item) => item.value === value)?.label || value || "-";
}

function statusType(status) {
  return { draft: "info", published: "success", disabled: "danger" }[status] || "info";
}

function statusLabel(status) {
  return { draft: "草稿", published: "已发布", disabled: "已禁用" }[status] || status;
}

async function load(nextPage = 1) {
  page.value = nextPage;
  loading.value = true;
  try {
    const res = await apiGetSkills({ ...filters, page: page.value, page_size: pageSize });
    items.value = res.data.data || [];
    total.value = res.data.pagination?.total || 0;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  resetForm();
  editVisible.value = true;
}

function openEdit(row) {
  editingId.value = row.id;
  resetForm({
    skill_no: row.skill_no || "",
    code: row.code || "",
    name: row.name || "",
    module: row.module || "product",
    description: row.description || "",
    input_schema_json: row.input_schema_json || "{}",
    output_schema_json: row.output_schema_json || "{}",
    allowed_operations: row.allowed_operations || "",
    forbidden_operations: row.forbidden_operations || "",
    scope: row.scope || "",
    handler_type: row.handler_type || "java",
    handler_target: row.handler_target || ""
  });
  editVisible.value = true;
}

async function save() {
  saving.value = true;
  try {
    if (editingId.value) {
      await apiUpdateSkill(editingId.value, { ...form });
      ElMessage.success("Skill 已更新");
    } else {
      await apiCreateSkill({ ...form });
      ElMessage.success("Skill 已创建，当前为草稿");
    }
    editVisible.value = false;
    await load(editingId.value ? page.value : 1);
  } finally {
    saving.value = false;
  }
}

async function publish(row) {
  await ElMessageBox.confirm(`确认发布 Skill「${row.name}」？发布后将可被 Agent 调用。`, "发布 Skill");
  await apiPublishSkill(row.id);
  ElMessage.success("已发布");
  await load(page.value);
}

async function disable(row) {
  await ElMessageBox.confirm(`确认禁用 Skill「${row.name}」？禁用后 Agent 将无法调用。`, "禁用 Skill", { type: "warning" });
  await apiDisableSkill(row.id);
  ElMessage.success("已禁用");
  await load(page.value);
}

function test(row) {
  testSkill.value = row;
  testParams.value = "{}";
  testResult.value = null;
  testVisible.value = true;
}

async function runTest() {
  let params;
  try {
    params = JSON.parse(testParams.value || "{}");
  } catch {
    ElMessage.error("参数必须是合法 JSON");
    return;
  }
  testing.value = true;
  try {
    const res = await apiTestSkill(testSkill.value.id, params);
    testResult.value = res.data.data;
  } finally {
    testing.value = false;
  }
}

onMounted(() => load(1));
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.skill-name {
  font-weight: 600;
}
.skill-code {
  color: var(--text-secondary);
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
.test-title {
  margin: 0 0 12px;
  font-weight: 600;
}
.test-result {
  margin-top: 14px;
}
.test-meta {
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 8px;
}
.test-result pre {
  max-height: 320px;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: var(--bg-hover);
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
