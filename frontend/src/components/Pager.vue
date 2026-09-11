<template>
  <el-pagination
    class="pager"
    background
    layout="total, sizes, prev, pager, next"
    :total="total"
    :page-size="size"
    :current-page="page"
    :page-sizes="[10, 20, 50, 100]"
    @current-change="(p) => emit('update:page', p)"
    @size-change="onSize"
  />
</template>

<script setup>
const props = defineProps({
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  size: { type: Number, default: 10 },
})
const emit = defineEmits(['update:page', 'update:size'])
function onSize(s) {
  emit('update:size', s)
  emit('update:page', 1)
}
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
</style>
