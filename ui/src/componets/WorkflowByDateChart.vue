<template>
    <div ref="el" style="width: 100%; height: 360px;"></div>
  </template>
  
  <script setup lang="ts">
  import * as echarts from "echarts";
  import { onBeforeUnmount, onMounted, ref, watch } from "vue";
  
  const props = defineProps<{
    dates: string[];
    counts: number[];
  }>();
  
  const el = ref<HTMLDivElement | null>(null);
  let chart: echarts.ECharts | null = null;
  
  function render() {
    if (!chart) return;
  
    chart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 40, right: 20, top: 20, bottom: 40 },
      xAxis: { type: "category", data: props.dates },
      yAxis: { type: "value" },
      series: [
        {
          name: "SQL上线工单数",
          type: "line",
          smooth: true,
          data: props.counts,
        },
      ],
    });
  }
  
  onMounted(() => {
    if (!el.value) return;
    chart = echarts.init(el.value);
    render();
    window.addEventListener("resize", onResize);
  });
  
  function onResize() {
    chart?.resize();
  }
  
  watch(
    () => [props.dates, props.counts],
    () => render(),
    { deep: true }
  );
  
  onBeforeUnmount(() => {
    window.removeEventListener("resize", onResize);
    chart?.dispose();
    chart = null;
  });
  </script>