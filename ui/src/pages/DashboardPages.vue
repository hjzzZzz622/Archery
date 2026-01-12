<template>
    <div style="padding: 16px;">
      <h2>Dashboard（Vue版）</h2>
  
      <div style="display: flex; gap: 8px; margin: 12px 0;">
        <label>
          start:
          <input v-model="startDate" placeholder="YYYY-MM-DD" />
        </label>
        <label>
          end:
          <input v-model="endDate" placeholder="YYYY-MM-DD" />
        </label>
        <button @click="load" :disabled="loading">刷新</button>
      </div>
  
      <div v-if="error" style="color: #b00020; white-space: pre-wrap;">
        {{ error }}
      </div>
  
      <div v-if="loading">loading...</div>
  
      <WorkflowByDateChart
        v-if="data"
        :dates="data.charts.workflowByDate.dates"
        :counts="data.charts.workflowByDate.counts"
      />
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref } from "vue";
  import WorkflowByDateChart from "../componets/WorkflowByDateChart.vue";
  import { fetchDashboardData } from "../api/dashboard";
  import type { DashboardDataResponse } from "../types/dashboard";
  
  const startDate = ref("2026-01-01");
  const endDate = ref("2026-01-12");
  
  const data = ref<DashboardDataResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  
  async function load() {
    loading.value = true;
    error.value = null;
    try {
      data.value = await fetchDashboardData({
        startDate: startDate.value,
        endDate: endDate.value,
      });
    } catch (e: any) {
      error.value = String(e?.message ?? e);
    } finally {
      loading.value = false;
    }
  }
  
  load();
  </script>