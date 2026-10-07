<template>
  <div class="re">
    <div class="bar">
      <el-button size="small" @click="cmd('bold')"><b>B</b></el-button>
      <el-button size="small" @click="cmd('italic')"><i>I</i></el-button>
      <el-button size="small" @click="cmd('underline')"><u>U</u></el-button>
      <el-button size="small" @click="cmd('insertUnorderedList')">• 列表</el-button>
      <el-button size="small" @click="cmd('insertOrderedList')">1. 列表</el-button>
      <el-button size="small" @click="insertLink">链接</el-button>
      <el-button size="small" :loading="uploading" @click="pickImage">截图</el-button>
      <input ref="fileRef" type="file" accept="image/*" multiple hidden @change="onFiles" />
    </div>
    <div
      ref="ed"
      class="body"
      contenteditable="true"
      @input="onInput"
      @blur="onInput"
      @paste="onPaste"
      @drop.prevent="onDrop"
    />
    <div class="tip">可点「截图」或直接粘贴/拖入图片，图片会自动压缩（长边 ≤1920 转 WebP），单张不超过 20MB，建议一次 3～8 张</div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { sanitizeHtml } from '../utils/sanitize'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])
const ed = ref(null)
const fileRef = ref(null)
const uploading = ref(false)
let last = ''

function setHtml(html) {
  if (!ed.value) return
  const v = sanitizeHtml(html || '')
  if (ed.value.innerHTML !== v) ed.value.innerHTML = v
  last = v
}
function onInput() {
  const html = ed.value?.innerHTML || ''
  if (html === last) return
  last = html
  emit('update:modelValue', html)
}
function cmd(name) {
  document.execCommand(name, false, null)
  onInput()
}
function insertLink() {
  const url = window.prompt('链接地址')
  if (url) document.execCommand('createLink', false, url)
  onInput()
}
function pickImage() {
  fileRef.value?.click()
}
function onFiles(e) {
  const files = [...(e.target.files || [])]
  e.target.value = ''
  uploadFiles(files)
}
function onPaste(e) {
  const items = [...(e.clipboardData?.items || [])]
  const files = items.filter((i) => i.kind === 'file' && i.type.startsWith('image/')).map((i) => i.getAsFile()).filter(Boolean)
  if (!files.length) return
  e.preventDefault()
  uploadFiles(files)
}
function onDrop(e) {
  const files = [...(e.dataTransfer?.files || [])].filter((f) => f.type.startsWith('image/'))
  if (files.length) uploadFiles(files)
}
// 截图多为高分屏 PNG，一张好几 MB；长边压到 1920 重编码为 WebP，体积通常降 85% 以上
async function compressImage(file, maxDim = 1920, quality = 0.85) {
  if (file.type === 'image/gif' || file.size < 200 * 1024) return file
  const bmp = await createImageBitmap(file)
  const scale = Math.min(1, maxDim / Math.max(bmp.width, bmp.height))
  const w = Math.round(bmp.width * scale)
  const h = Math.round(bmp.height * scale)
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  canvas.getContext('2d').drawImage(bmp, 0, 0, w, h)
  bmp.close()
  const blob = await new Promise((r) => canvas.toBlob(r, 'image/webp', quality))
  if (!blob || blob.size >= file.size) return file
  return new File([blob], `${(file.name || 'image').replace(/\.\w+$/, '')}.webp`, { type: 'image/webp' })
}

async function uploadFiles(files) {
  if (!files.length) return
  uploading.value = true
  try {
    for (const file of files) {
      let img = file
      try { img = await compressImage(file) } catch { /* 压缩失败按原图上传 */ }
      if (img.size > 20 * 1024 * 1024) {
        ElMessage.warning(`${img.name} 超过 20MB，已跳过`)
        continue
      }
      const fd = new FormData()
      fd.append('file', img)
      const token = localStorage.getItem('token') || ''
      const res = await axios.post('/api/uploads', fd, {
        headers: { Authorization: token ? `Bearer ${token}` : '' },
      })
      const url = res.data?.url
      if (!url) continue
      const name = res.data.name || file.name
      document.execCommand('insertHTML', false, `<p><img src="${url}" alt="${name}" /></p>`)
    }
    onInput()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '图片上传失败')
  } finally { uploading.value = false }
}
onMounted(() => setHtml(props.modelValue))
watch(() => props.modelValue, (v) => {
  if ((v || '') !== last) setHtml(v)
})
</script>

<style scoped>
.re { border: 1px solid #dcdfe6; border-radius: 4px; overflow: hidden; }
.bar { padding: 6px 8px; background: #f5f7fa; border-bottom: 1px solid #ebeef5; display: flex; gap: 6px; flex-wrap: wrap; }
.body { min-height: 140px; max-height: 360px; overflow: auto; padding: 10px 12px; outline: none; line-height: 1.6; }
.body :deep(ul), .body :deep(ol) { padding-left: 20px; }
.body :deep(img) { max-width: 100%; height: auto; display: block; margin: 8px 0; border: 1px solid #ebeef5; border-radius: 4px; cursor: zoom-in; }
.tip { padding: 4px 10px 8px; color: #909399; font-size: 12px; background: #fafafa; }
</style>
