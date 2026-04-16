<template>
  <div class="min-h-screen bg-slate-50">
    <router-view />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useSessionStore } from '@/stores/sessionStore'

const store = useSessionStore()
onMounted(() => store.fetchSessions())
</script>
